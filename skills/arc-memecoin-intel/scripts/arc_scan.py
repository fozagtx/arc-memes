#!/usr/bin/env python3
"""Arc memecoin scanner: discover new tokens, detect bundles, score risk.

Stdlib only. Talks to an Arc JSON-RPC endpoint and, optionally, a Blockscout
explorer API (Arcscan) for wallet funding origins.

Subcommands:
  discover   find new pools (and, with --mints, launchpad tokens); --scan N ranks them
  scan       full forensic scan of one token (holders, bundles, LP, risk score)
  wallet     trace who funded a wallet and its first activity
  watch      follow new blocks and scan every new pool as it appears

Every number this tool prints is derived from chain data it fetched; when a
signal could not be computed it says so instead of guessing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field

DEFAULT_RPC = os.environ.get("ARC_RPC_URL", "https://rpc.testnet.arc.network")
DEFAULT_EXPLORER = os.environ.get("ARC_EXPLORER_URL", "https://testnet.arcscan.app")

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
V2_PAIR_CREATED = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
V3_POOL_CREATED = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"

ZERO = "0x" + "0" * 40
BURN_ADDRS = {ZERO, "0x000000000000000000000000000000000000dead"}

SEL = {
    "name": "0x06fdde03",
    "symbol": "0x95d89b41",
    "decimals": "0x313ce567",
    "totalSupply": "0x18160ddd",
    "owner": "0x8da5cb5b",
    "token0": "0x0dfe1681",
    "token1": "0xd21220a7",
}
# Function selectors whose presence in bytecode is worth flagging.
RISKY_SELECTORS = {
    "40c10f19": "mint(address,uint256)",
    "8456cb59": "pause()",
    "f2fde38b": "transferOwnership(address)",
}


def load_labels(path: str | None) -> dict[str, str]:
    """{address: label} from a JSON file. Labels starting with cex/bridge/router/locker are
    treated as shared infrastructure: never merged into funder clusters."""
    if not path:
        return {}
    with open(path) as f:
        raw = json.load(f)
    return {k.lower(): str(v) for k, v in raw.items() if not k.startswith("_")}


INFRA_PREFIXES = ("cex", "bridge", "router", "locker", "launchpad")


def is_infra(addr: str | None, labels: dict[str, str]) -> bool:
    return bool(addr) and labels.get(addr, "").lower().startswith(INFRA_PREFIXES)


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------
class RPCError(RuntimeError):
    pass


class RPC:
    def __init__(self, url: str, timeout: float = 20.0, retries: int = 3):
        self.url, self.timeout, self.retries = url, timeout, retries
        self._id = 0

    def call(self, method: str, params: list):
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}).encode()
        last = None
        for attempt in range(self.retries):
            try:
                req = urllib.request.Request(self.url, body, {"content-type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    resp = json.loads(r.read())
                if "error" in resp:
                    raise RPCError(f"{method}: {resp['error']}")
                return resp["result"]
            except RPCError:
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = e
                time.sleep(2 ** attempt)
        raise RPCError(f"{method}: transport failed after {self.retries} tries: {last}")

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def eth_call(self, to: str, data: str, block: str = "latest") -> str | None:
        try:
            return self.call("eth_call", [{"to": to, "data": data}, block])
        except RPCError:
            return None

    def code(self, addr: str, block: str = "latest") -> str:
        return self.call("eth_getCode", [addr, block])

    def nonce(self, addr: str) -> int:
        return int(self.call("eth_getTransactionCount", [addr, "latest"]), 16)

    def logs(self, from_block: int, to_block: int, address=None, topics=None, max_span: int = 5000) -> list:
        """eth_getLogs with chunking and adaptive halving when the node complains."""
        out, start, span = [], from_block, max_span
        while start <= to_block:
            end = min(start + span - 1, to_block)
            flt = {"fromBlock": hex(start), "toBlock": hex(end)}
            if address:
                flt["address"] = address
            if topics:
                flt["topics"] = topics
            try:
                out.extend(self.call("eth_getLogs", [flt]))
                start = end + 1
            except RPCError:
                if span <= 1:
                    raise
                span = max(1, span // 2)
        return out


class Explorer:
    """Thin Blockscout client (Arcscan). All methods fail soft and return None."""

    def __init__(self, base: str | None, timeout: float = 20.0):
        self.base = base.rstrip("/") if base else None
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        if not self.base:
            return None
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None

    def address_info(self, addr: str):
        return self._get(f"/api/v2/addresses/{addr}")

    def first_txs(self, addr: str, n: int = 5):
        res = self._get("/api", {"module": "account", "action": "txlist", "address": addr,
                                 "sort": "asc", "page": 1, "offset": n})
        return res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), list) else None

    def first_token_txs(self, addr: str, n: int = 5):
        res = self._get("/api", {"module": "account", "action": "tokentx", "address": addr,
                                 "sort": "asc", "page": 1, "offset": n})
        return res.get("result") if isinstance(res, dict) and isinstance(res.get("result"), list) else None

    def funder(self, addr: str) -> str | None:
        """Address that first sent value (native USDC gas or ERC-20) to `addr`."""
        a = addr.lower()
        for tx in self.first_txs(addr) or []:
            if tx.get("to", "").lower() == a and int(tx.get("value") or 0) > 0:
                return tx["from"].lower()
        for tx in self.first_token_txs(addr) or []:
            if tx.get("to", "").lower() == a:
                return tx["from"].lower()
        return None


# --------------------------------------------------------------------------
# ABI helpers
# --------------------------------------------------------------------------
def topic_addr(t: str) -> str:
    return "0x" + t[-40:].lower()


def pad_addr(a: str) -> str:
    return "0x" + a.lower().replace("0x", "").rjust(64, "0")


def dec_uint(h: str | None) -> int | None:
    if not h or h == "0x":
        return None
    try:
        return int(h[:66], 16)
    except ValueError:
        return None


def dec_string(h: str | None) -> str | None:
    if not h or h == "0x":
        return None
    raw = bytes.fromhex(h[2:])
    if len(raw) >= 64:
        off = int.from_bytes(raw[:32], "big")
        if off + 32 <= len(raw):
            ln = int.from_bytes(raw[off:off + 32], "big")
            if off + 32 + ln <= len(raw):
                return raw[off + 32:off + 32 + ln].decode("utf-8", "replace")
    return raw[:32].rstrip(b"\0").decode("utf-8", "replace") or None  # bytes32 style


def dec_addr(h: str | None) -> str | None:
    if not h or len(h) < 66:
        return None
    return "0x" + h[26:66].lower()


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------
@dataclass
class Transfer:
    block: int
    tx: str
    log_index: int
    frm: str
    to: str
    value: int

    @classmethod
    def from_log(cls, lg: dict) -> "Transfer | None":
        t = lg.get("topics") or []
        if len(t) != 3 or t[0].lower() != TRANSFER:  # ERC-721 has 4 topics
            return None
        return cls(int(lg["blockNumber"], 16), lg["transactionHash"], int(lg["logIndex"], 16),
                   topic_addr(t[1]), topic_addr(t[2]), int(lg["data"], 16) if lg["data"] != "0x" else 0)


@dataclass
class Analysis:
    balances: dict
    pools: set
    first_liquidity_block: int | None
    early_buys: list
    same_block_groups: dict
    shared_tx_groups: dict
    deployer_seeded: dict
    findings: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Pure analysis (unit-tested, no network)
# --------------------------------------------------------------------------
def build_balances(transfers: list[Transfer]) -> dict[str, int]:
    bal: dict[str, int] = defaultdict(int)
    for t in transfers:
        if t.frm != ZERO:
            bal[t.frm] -= t.value
        bal[t.to] += t.value
    return {a: v for a, v in bal.items() if v > 0}


def analyze(transfers: list[Transfer], pools: set[str], deployer: str | None,
            early_window: int = 5, min_cluster: int = 3) -> Analysis:
    """Find launch-time bundle patterns from a token's transfer history.

    - first_liquidity_block: first block where tokens move into a known pool.
    - early_buys: pool -> wallet transfers within `early_window` blocks of that.
    - same_block_groups: blocks where >= min_cluster distinct wallets bought.
    - shared_tx_groups: single txs that delivered tokens from a pool to >= 2
      wallets (a bundler contract / multi-recipient buy, the clearest signal).
    - deployer_seeded: wallets that received tokens straight from the deployer
      or the mint, other than pools (pre-distributed "team" / sniper supply).
    """
    transfers = sorted(transfers, key=lambda t: (t.block, t.log_index))
    pools = {p.lower() for p in pools}
    deployer = deployer.lower() if deployer else None

    first_liq = next((t.block for t in transfers if t.to in pools), None)
    early_buys, by_block, by_tx = [], defaultdict(set), defaultdict(set)
    if first_liq is not None:
        for t in transfers:
            if t.block > first_liq + early_window:
                break
            if t.frm in pools and t.to not in pools and t.to not in BURN_ADDRS:
                early_buys.append(t)
                by_block[t.block].add(t.to)
                by_tx[t.tx].add(t.to)

    seeded: dict[str, int] = defaultdict(int)
    sources = {ZERO} | ({deployer} if deployer else set())
    for t in transfers:
        if t.frm in sources and t.to not in pools and t.to not in sources and t.to not in BURN_ADDRS:
            seeded[t.to] += t.value

    return Analysis(
        balances=build_balances(transfers),
        pools=pools,
        first_liquidity_block=first_liq,
        early_buys=early_buys,
        same_block_groups={b: sorted(w) for b, w in by_block.items() if len(w) >= min_cluster},
        shared_tx_groups={tx: sorted(w) for tx, w in by_tx.items() if len(w) >= 2},
        deployer_seeded=dict(seeded),
    )


def cluster_by_funder(funders: dict[str, str | None], min_size: int = 2,
                      labels: dict[str, str] | None = None) -> dict[str, list[str]]:
    groups = defaultdict(list)
    for w, f in funders.items():
        if f and not is_infra(f, labels or {}):
            groups[f].append(w)
    return {f: sorted(ws) for f, ws in groups.items() if len(ws) >= min_size}


def sell_through(transfers: list[Transfer], wallets: set[str], balances: dict[str, int]) -> dict:
    """How much of what `wallets` ever received they have since moved out."""
    received = sum(t.value for t in transfers if t.to in wallets)
    held = sum(balances.get(w, 0) for w in wallets)
    sold = max(0, received - held)
    return {"received": received, "held": held, "sold_pct": pct(sold, received)}


def pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 2) if whole else 0.0


def score(ctx: dict) -> tuple[int, str, list[str]]:
    """Weighted 0-100 risk score. Higher = more dangerous. Returns (score, label, reasons)."""
    s, why = 0, []

    def add(points, reason):
        nonlocal s
        s += points
        why.append(f"+{points} {reason}")

    if ctx.get("bundled_supply_pct", 0) >= 20:
        add(30, f"bundle clusters hold {ctx['bundled_supply_pct']}% of supply")
    elif ctx.get("bundled_supply_pct", 0) >= 8:
        add(18, f"bundle clusters hold {ctx['bundled_supply_pct']}% of supply")
    elif ctx.get("bundled_supply_pct", 0) > 0:
        add(8, f"bundle clusters hold {ctx['bundled_supply_pct']}% of supply")

    if ctx.get("shared_tx_groups"):
        add(15, f"{ctx['shared_tx_groups']} tx(s) bought for multiple wallets at once")
    if ctx.get("same_block_groups"):
        add(10, f"{ctx['same_block_groups']} launch block(s) with coordinated multi-wallet buys")
    if ctx.get("funder_clusters"):
        add(12, f"{ctx['funder_clusters']} group(s) of buyers funded by the same address")

    top10 = ctx.get("top10_pct", 0)
    if top10 >= 50:
        add(15, f"top 10 holders own {top10}% (ex-pools/burn)")
    elif top10 >= 30:
        add(8, f"top 10 holders own {top10}% (ex-pools/burn)")
    if ctx.get("max_holder_pct", 0) >= 3.5:
        add(5, f"single wallet holds {ctx['max_holder_pct']}% (Spyzer ~3.5% trench rule)")

    if ctx.get("deployer_seeded_pct", 0) >= 10:
        add(10, f"deployer pre-distributed {ctx['deployer_seeded_pct']}% to wallets")
    if ctx.get("deployer_holds_pct", 0) >= 5:
        add(8, f"deployer still holds {ctx['deployer_holds_pct']}%")
    if ctx.get("mint_fn") and not ctx.get("ownership_renounced"):
        add(12, "mint() present and owner not renounced")
    if ctx.get("pause_fn") and not ctx.get("ownership_renounced"):
        add(6, "pause() present and owner not renounced")
    if ctx.get("fresh_wallet_ratio", 0) >= 0.5:
        add(6, f"{int(ctx['fresh_wallet_ratio'] * 100)}% of early buyers are fresh wallets")
    if not ctx.get("pools"):
        add(5, "no liquidity pool detected (can't verify tradability)")
    lp = ctx.get("lp_burned_pct")
    if lp is not None and lp < 50 and not ctx.get("lp_locked_known"):
        add(8, f"only {lp}% of LP tokens burned and no known locker holds them (liquidity can be pulled)")
    sold = ctx.get("bundle_sold_pct")
    if sold is not None and 20 <= sold < 90 and ctx.get("bundled_supply_pct", 0) > 0:
        add(6, f"bundle wallets have sold {sold}% and are still holding the rest (active distribution)")

    s = min(100, s)
    label = "CRITICAL" if s >= 70 else "HIGH" if s >= 45 else "ELEVATED" if s >= 25 else "LOW"
    return s, label, why


# --------------------------------------------------------------------------
# Network-backed steps
# --------------------------------------------------------------------------
def token_meta(rpc: RPC, token: str) -> dict:
    m = {
        "address": token.lower(),
        "name": dec_string(rpc.eth_call(token, SEL["name"])),
        "symbol": dec_string(rpc.eth_call(token, SEL["symbol"])),
        "decimals": dec_uint(rpc.eth_call(token, SEL["decimals"])),
        "total_supply": dec_uint(rpc.eth_call(token, SEL["totalSupply"])),
        "owner": dec_addr(rpc.eth_call(token, SEL["owner"])),
    }
    code = rpc.code(token).lower()
    m["is_contract"] = code not in ("0x", "0x0")
    m["mint_fn"] = "63" + "40c10f19" in code
    m["pause_fn"] = "63" + "8456cb59" in code
    m["flagged_selectors"] = [sig for sel, sig in RISKY_SELECTORS.items() if "63" + sel in code]
    m["ownership_renounced"] = m["owner"] in BURN_ADDRS if m["owner"] else None
    return m


def find_creation_block(rpc: RPC, explorer: Explorer, token: str, head: int) -> tuple[int, str | None]:
    """Return (creation_block, deployer). Explorer first, binary search on code as fallback."""
    info = explorer.address_info(token)
    if info and info.get("creation_tx_hash"):
        tx = rpc.call("eth_getTransactionByHash", [info["creation_tx_hash"]])
        if tx:
            return int(tx["blockNumber"], 16), (info.get("creator_address_hash") or tx["from"]).lower()
    lo, hi = 0, head
    try:
        while lo < hi:
            mid = (lo + hi) // 2
            if rpc.code(token, hex(mid)) not in ("0x", "0x0"):
                hi = mid
            else:
                lo = mid + 1
        return lo, None
    except RPCError:  # non-archive node
        return max(0, head - 50_000), None


def detect_pools(rpc: RPC, token: str, candidates: set[str]) -> set[str]:
    """Contracts among `candidates` that expose token0/token1 with our token = AMM pools."""
    pools, t = set(), token.lower()
    for c in candidates:
        if c in BURN_ADDRS:
            continue
        t0 = dec_addr(rpc.eth_call(c, SEL["token0"]))
        t1 = dec_addr(rpc.eth_call(c, SEL["token1"]))
        if t in (t0, t1):
            pools.add(c)
    return pools


def lp_status(rpc: RPC, pool: str, labels: dict[str, str]) -> dict | None:
    """For a V2-style pair (the pool is itself an ERC-20 LP token): share of LP burned / held by
    labelled lockers. V3 positions are NFTs, so this returns None for them."""
    lp_supply = dec_uint(rpc.eth_call(pool, SEL["totalSupply"]))
    if not lp_supply:
        return None
    head = rpc.block_number()
    try:
        raw = rpc.logs(max(0, head - 2_000_000), head, address=pool, topics=[TRANSFER])
    except RPCError:
        return None
    bal = build_balances([t for t in (Transfer.from_log(lg) for lg in raw) if t])
    # Uniswap V2 permanently locks MINIMUM_LIQUIDITY at address(0); count all of zero/dead as burned.
    minted = sum(t for t in bal.values())
    burned = sum(bal.get(a, 0) for a in BURN_ADDRS)
    locked = {a: v for a, v in bal.items() if labels.get(a, "").lower().startswith("locker")}
    top = sorted(((a, v) for a, v in bal.items() if a not in BURN_ADDRS), key=lambda x: -x[1])[:3]
    return {"pool": pool, "burned_pct": pct(burned, minted), "locked_pct": pct(sum(locked.values()), minted),
            "top_lp_holders": [{"address": a, "pct": pct(v, minted), "label": labels.get(a)} for a, v in top]}


def cmd_scan(args) -> dict:
    rpc, explorer = RPC(args.rpc), Explorer(None if args.no_explorer else args.explorer)
    labels = load_labels(getattr(args, "labels", None))
    token = args.token.lower()
    head = rpc.block_number()
    meta = token_meta(rpc, token)
    if not meta["is_contract"]:
        raise SystemExit(f"{token} has no contract code on this network ({args.rpc})")

    created, deployer = find_creation_block(rpc, explorer, token, head)
    deployer = (args.deployer or deployer or "").lower() or None
    to_block = head if args.blocks is None else min(head, created + args.blocks)
    raw = rpc.logs(created, to_block, address=token, topics=[TRANSFER])
    transfers = [t for t in (Transfer.from_log(lg) for lg in raw) if t]
    if not deployer:  # fall back to whoever received the initial mint
        deployer = next((t.to for t in sorted(transfers, key=lambda t: (t.block, t.log_index)) if t.frm == ZERO), None)

    # Pools: user-supplied, else top receivers that look like AMM pairs.
    if args.pool:
        pools = {p.lower() for p in args.pool}
    else:
        inbound = Counter()
        for t in transfers:
            inbound[t.to] += 1
        pools = detect_pools(rpc, token, {a for a, _ in inbound.most_common(25)})

    a = analyze(transfers, pools, deployer, args.early_window, args.min_cluster)
    supply = meta["total_supply"] or sum(a.balances.values())
    excluded = a.pools | BURN_ADDRS | {token}
    holders = sorted(((w, b) for w, b in a.balances.items() if w not in excluded), key=lambda x: -x[1])

    early_wallets = sorted({t.to for t in a.early_buys})
    funders = {}
    if explorer.base and early_wallets:
        for w in early_wallets[: args.max_trace]:
            funders[w] = explorer.funder(w)
    funder_clusters = cluster_by_funder(funders, labels=labels)

    fresh = 0
    for w in early_wallets[: args.max_trace]:
        try:
            if rpc.nonce(w) <= 3:
                fresh += 1
        except RPCError:
            pass
    traced = min(len(early_wallets), args.max_trace)

    bundled = set()
    for ws in a.same_block_groups.values():
        bundled.update(ws)
    for ws in a.shared_tx_groups.values():
        bundled.update(ws)
    for ws in funder_clusters.values():
        bundled.update(ws)
    if deployer:
        bundled.update(w for w in a.deployer_seeded if w in a.balances)
    bundled -= excluded
    bundled_now = sum(a.balances.get(w, 0) for w in bundled)
    bundle_flow = sell_through(transfers, bundled, a.balances) if bundled else None

    lp = [x for x in (lp_status(rpc, pl, labels) for pl in sorted(a.pools)) if x]
    best_lp = max(lp, key=lambda x: x["burned_pct"] + x["locked_pct"]) if lp else None

    ctx = {
        "pools": sorted(a.pools),
        "bundled_supply_pct": pct(bundled_now, supply),
        "shared_tx_groups": len(a.shared_tx_groups),
        "same_block_groups": len(a.same_block_groups),
        "funder_clusters": len(funder_clusters),
        "top10_pct": pct(sum(b for _, b in holders[:10]), supply),
        "max_holder_pct": pct(holders[0][1], supply) if holders else 0,
        "deployer_seeded_pct": pct(sum(a.deployer_seeded.values()), supply),
        "deployer_holds_pct": pct(a.balances.get(deployer, 0), supply) if deployer else 0,
        "mint_fn": meta["mint_fn"],
        "pause_fn": meta["pause_fn"],
        "ownership_renounced": meta["ownership_renounced"],
        "fresh_wallet_ratio": round(fresh / traced, 2) if traced else 0,
        "bundle_sold_pct": bundle_flow["sold_pct"] if bundle_flow else None,
        "lp_burned_pct": best_lp["burned_pct"] if best_lp else None,
        "lp_locked_known": bool(best_lp and best_lp["locked_pct"] >= 50),
    }
    risk, label, reasons = score(ctx)
    dec = meta["decimals"] or 0

    return {
        "network": {"rpc": args.rpc, "explorer": explorer.base, "head_block": head},
        "token": meta,
        "window": {"from_block": created, "to_block": to_block, "transfers": len(transfers),
                   "complete_history": to_block == head},
        "deployer": deployer,
        "first_liquidity_block": a.first_liquidity_block,
        "holders_count": len(holders),
        "top_holders": [{"address": w, "pct": pct(b, supply), "amount": b / 10 ** dec if dec else b,
                         "bundled": w in bundled} for w, b in holders[:15]],
        "bundles": {
            "same_block_groups": {str(k): v for k, v in a.same_block_groups.items()},
            "shared_tx_groups": a.shared_tx_groups,
            "funder_clusters": funder_clusters,
            "deployer_seeded": {w: pct(v, supply) for w, v in sorted(a.deployer_seeded.items(), key=lambda x: -x[1])[:20]},
            "bundled_wallets": sorted(bundled),
            "early_buyers": len(early_wallets),
            "funders_traced": len(funders),
            "sell_through": bundle_flow,
            "funders_labelled": {f: labels[f] for f in set(funders.values()) if f in labels},
        },
        "liquidity": lp,
        "signals": ctx,
        "risk": {"score": risk, "label": label, "reasons": reasons},
        "not_computed": [n for n, ok in [
            ("funder clustering (explorer unavailable)", bool(funders)),
            ("pool detection (no AMM pool found)", bool(a.pools)),
            ("full history (window truncated by --blocks)", to_block == head),
            ("LP burn/lock (no V2-style LP token found)", bool(lp) or not a.pools),
        ] if not ok],
    }


def pools_in_range(rpc: RPC, start: int, end: int, quote: set[str]) -> list[dict]:
    rows = []
    for lg in rpc.logs(start, end, topics=[[V2_PAIR_CREATED, V3_POOL_CREATED]]):
        t = lg["topics"]
        t0, t1 = topic_addr(t[1]), topic_addr(t[2])
        data = lg["data"][2:]
        if t[0].lower() == V2_PAIR_CREATED:
            pool, kind = "0x" + data[24:64], "v2"
        else:
            pool, kind = "0x" + data[64 + 24:128], "v3"
        base = t1 if t0 in quote else t0 if t1 in quote else None
        if quote and base is None:
            continue
        for tok in ([base] if base else [t0, t1]):
            rows.append({"block": int(lg["blockNumber"], 16), "factory": lg["address"].lower(), "kind": kind,
                         "pool": pool.lower(), "token": tok, "paired_with": t1 if tok == t0 else t0,
                         "source": "pool"})
    return rows


def mints_in_range(rpc: RPC, start: int, end: int, known: set[str]) -> list[dict]:
    """Tokens whose first-ever mint (Transfer from 0x0) lands in range: catches launchpad /
    bonding-curve tokens that never emit a standard PairCreated."""
    seen, rows = set(known), []
    for lg in rpc.logs(start, end, topics=[TRANSFER, pad_addr(ZERO)]):
        tok = lg["address"].lower()
        if tok in seen or len(lg.get("topics") or []) != 3:
            continue
        seen.add(tok)
        blk = int(lg["blockNumber"], 16)
        try:  # only genuinely new contracts: skip tokens that already had code before the window
            if blk > 1 and rpc.code(tok, hex(max(0, start - 1))) not in ("0x", "0x0"):
                continue
        except RPCError:
            pass
        rows.append({"block": blk, "factory": None, "kind": "mint", "pool": None, "token": tok,
                     "paired_with": None, "source": "mint"})
    return rows


def rank(args, rows: list[dict]) -> list[dict]:
    """Quick-scan the newest N distinct tokens and attach risk. Lower risk sorts first."""
    out, done = [], set()
    for r in rows:
        if len(done) >= args.scan or r["token"] in done:
            continue
        done.add(r["token"])
        ns = argparse.Namespace(rpc=args.rpc, explorer=args.explorer, token=r["token"],
                                pool=[r["pool"]] if r["pool"] else None, deployer=None, blocks=None,
                                early_window=5, min_cluster=3, max_trace=args.max_trace,
                                no_explorer=args.no_explorer, labels=args.labels)
        try:
            res = cmd_scan(ns)
            out.append({**r, "symbol": res["token"]["symbol"], "score": res["risk"]["score"],
                        "label": res["risk"]["label"], "bundled_pct": res["signals"]["bundled_supply_pct"],
                        "top10_pct": res["signals"]["top10_pct"],
                        "note": (res["risk"]["reasons"] or ["no red flags visible"])[0]})
        except (RPCError, SystemExit) as e:
            out.append({**r, "score": None, "label": "ERROR", "note": str(e)[:120]})
    return sorted(out, key=lambda x: (x["score"] is None, x["score"] or 0))


def cmd_discover(args) -> dict:
    rpc = RPC(args.rpc)
    head = rpc.block_number()
    start = max(0, head - args.blocks)
    quote = {q.lower() for q in args.quote} if args.quote else set()
    rows = pools_in_range(rpc, start, head, quote)
    if args.mints:
        rows += mints_in_range(rpc, start, head, {r["token"] for r in rows} | quote)
    rows.sort(key=lambda r: -r["block"])
    rows = rows[: args.limit]
    for r in rows:
        r["symbol"] = dec_string(rpc.eth_call(r["token"], SEL["symbol"]))
    out = {"head_block": head, "from_block": start, "new_pools": rows}
    if args.scan:
        out["ranked"] = rank(args, rows)
    return out


def cmd_watch(args) -> int:
    """Poll for new blocks; scan each new pool/token once and print a one-line alert."""
    rpc = RPC(args.rpc)
    quote = {q.lower() for q in args.quote} if args.quote else set()
    last, seen = rpc.block_number(), set()
    print(f"watching Arc from block {last} (poll {args.interval}s, Ctrl-C to stop)", file=sys.stderr)
    try:
        while True:
            time.sleep(args.interval)
            head = rpc.block_number()
            if head <= last:
                continue
            rows = pools_in_range(rpc, last + 1, head, quote)
            if args.mints:
                rows += mints_in_range(rpc, last + 1, head, {r["token"] for r in rows} | quote | seen)
            last = head
            fresh = [r for r in rows if r["token"] not in seen]
            seen.update(r["token"] for r in fresh)
            for r in rank(argparse.Namespace(**{**vars(args), "scan": len(fresh)}), fresh):
                line = {"block": r["block"], "token": r["token"], "symbol": r.get("symbol"),
                        "label": r["label"], "score": r["score"], "note": r["note"]}
                print(json.dumps(line) if args.format == "json" else
                      f"[{r['block']}] {r.get('symbol') or '?':<10} {r['token']}  {r['label']:<8} "
                      f"{r['score'] if r['score'] is not None else '-':>3}  {r['note']}", flush=True)
    except KeyboardInterrupt:
        return 0


def cmd_wallet(args) -> dict:
    rpc, ex = RPC(args.rpc), Explorer(args.explorer)
    w = args.address.lower()
    return {"address": w, "nonce": rpc.nonce(w), "is_contract": rpc.code(w) not in ("0x", "0x0"),
            "funder": ex.funder(w), "first_txs": ex.first_txs(w), "first_token_txs": ex.first_token_txs(w)}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render_scan_md(r: dict) -> str:
    t, risk, b, s = r["token"], r["risk"], r["bundles"], r["signals"]
    ex = r["network"]["explorer"]
    link = (lambda a: f"[`{a[:8]}…{a[-4:]}`]({ex}/address/{a})") if ex else (lambda a: f"`{a}`")
    L = [f"# {t.get('symbol') or '?'} — {t.get('name') or 'unknown'}",
         f"`{t['address']}` · Arc · head block {r['network']['head_block']}", "",
         f"## Verdict: **{risk['label']}** ({risk['score']}/100)", ""]
    L += [f"- {x}" for x in risk["reasons"]] or ["- no risk signals fired"]
    L += ["", "## Bundle forensics",
          f"- Bundled wallets: **{len(b['bundled_wallets'])}** holding **{s['bundled_supply_pct']}%** of supply",
          f"- Multi-recipient buy txs: {len(b['shared_tx_groups'])}",
          f"- Coordinated launch blocks: {len(b['same_block_groups'])}",
          f"- Shared-funder clusters: {len(b['funder_clusters'])} (traced {b['funders_traced']} of {b['early_buyers']} early buyers)",
          f"- Deployer pre-distribution: {s['deployer_seeded_pct']}% · deployer still holds {s['deployer_holds_pct']}%"]
    if b.get("sell_through"):
        L.append(f"- Bundle sell-through: sold {b['sell_through']['sold_pct']}% of what they received")
    for f, ws in list(b["funder_clusters"].items())[:5]:
        L.append(f"  - funder {link(f)} → {len(ws)} wallets")
    L += ["", "## Contract",
          f"- Owner: {t['owner'] or 'none/unknown'} (renounced: {t['ownership_renounced']})",
          f"- Flagged functions: {', '.join(t['flagged_selectors']) or 'none'}",
          f"- Pools: {', '.join(s['pools']) or 'none detected'}",
          *[f"- LP `{x['pool'][:10]}…`: {x['burned_pct']}% burned, {x['locked_pct']}% in labelled lockers"
            for x in r.get("liquidity") or []],
          "", "## Top holders (ex-pools/burn)", "", "| # | Wallet | % | Bundled |", "|---|---|---|---|"]
    for i, h in enumerate(r["top_holders"][:10], 1):
        L.append(f"| {i} | {link(h['address'])} | {h['pct']} | {'⚠️' if h['bundled'] else ''} |")
    L += ["", f"Top 10: {s['top10_pct']}% · holders: {r['holders_count']}"]
    if r["not_computed"]:
        L += ["", "**Not computed:** " + "; ".join(r["not_computed"])]
    L += ["", "_On-chain heuristics, not proof of intent. Not financial advice._"]
    return "\n".join(L)


def render_discover_md(r: dict) -> str:
    L = [f"# New pools on Arc (blocks {r['from_block']}–{r['head_block']})", "",
         "| Block | Token | Symbol | Pool | Type |", "|---|---|---|---|---|"]
    for x in r["new_pools"]:
        L.append(f"| {x['block']} | `{x['token']}` | {x['symbol'] or '?'} | `{x['pool'] or '-'}` | {x['kind']} |")
    if not r["new_pools"]:
        L.append("| — | none found | | | |")
    if r.get("ranked"):
        L += ["", "## Ranked (lowest risk first)", "",
              "| Token | Symbol | Score | Label | Bundled % | Top10 % | Note |", "|---|---|---|---|---|---|---|"]
        for x in r["ranked"]:
            L.append(f"| `{x['token']}` | {x.get('symbol') or '?'} | {x['score'] if x['score'] is not None else '-'} "
                     f"| {x['label']} | {x.get('bundled_pct', '-')} | {x.get('top10_pct', '-')} | {x['note']} |")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rpc", default=DEFAULT_RPC)
    p.add_argument("--explorer", default=DEFAULT_EXPLORER)
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--labels", default=os.environ.get("ARC_LABELS"),
                   help="JSON {address: label}; cex/bridge/router/locker labels are not clustered")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="list pools created in recent blocks")
    d.add_argument("--blocks", type=int, default=20_000)
    d.add_argument("--limit", type=int, default=50)
    d.add_argument("--quote", nargs="*", help="quote token addresses (e.g. USDC, WUSDC) to orient pairs")
    d.add_argument("--mints", action="store_true", help="also find new tokens by first mint (launchpads)")
    d.add_argument("--scan", type=int, default=0, help="quick-scan and rank the newest N tokens")
    d.add_argument("--max-trace", type=int, default=15)
    d.add_argument("--no-explorer", action="store_true")

    wa = sub.add_parser("watch", help="follow new blocks and scan new pools live")
    wa.add_argument("--interval", type=float, default=5.0)
    wa.add_argument("--quote", nargs="*")
    wa.add_argument("--mints", action="store_true")
    wa.add_argument("--max-trace", type=int, default=10)
    wa.add_argument("--no-explorer", action="store_true")

    s = sub.add_parser("scan", help="forensic scan of one token")
    s.add_argument("token")
    s.add_argument("--pool", nargs="*", help="known pool/pair addresses (skips auto-detection)")
    s.add_argument("--deployer")
    s.add_argument("--blocks", type=int, help="limit history to N blocks after creation")
    s.add_argument("--early-window", type=int, default=5, help="blocks after first liquidity counted as launch")
    s.add_argument("--min-cluster", type=int, default=3, help="distinct buyers in one block to flag")
    s.add_argument("--max-trace", type=int, default=40, help="max early buyers to trace funders for")
    s.add_argument("--no-explorer", action="store_true")

    w = sub.add_parser("wallet", help="funding origin and first activity of a wallet")
    w.add_argument("address")

    args = p.parse_args(argv)
    if args.cmd == "watch":
        try:
            return cmd_watch(args)
        except RPCError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    try:
        result = {"discover": cmd_discover, "scan": cmd_scan, "wallet": cmd_wallet}[args.cmd](args)
    except RPCError as e:
        print(f"error: {e}\nCheck --rpc / ARC_RPC_URL (currently {args.rpc}).", file=sys.stderr)
        return 1
    if args.format == "json" or args.cmd == "wallet":
        print(json.dumps(result, indent=2, default=str))
    elif args.cmd == "scan":
        print(render_scan_md(result))
    else:
        print(render_discover_md(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
