---
name: arc-memecoin-intel
description: "Memecoin intelligence for Circle's Arc network. Use when asked to scan, research, vet, or rug-check a token on Arc; to find new Arc memecoins or launches; to detect bundled supply, snipers, insider or shared-funder wallet clusters; to score a token's risk; or to write an Arc memecoin research report. Runs an on-chain scanner (scripts/arc_scan.py) and applies the Spyzer memecoin frameworks."
---

<!-- argument-hint: [token address | "discover" | wallet address | topic] -->

# Arc Memecoin Intel

Scan Arc memecoins on-chain, find bundled supply, score the risk, and write the report.
The scanner does the counting. You read what it found, check it against the frameworks,
and say plainly what the data shows and what it doesn't.

Arc is Circle's EVM Layer 1. Things that matter here: **USDC is the gas token**, finality is
deterministic and under a second, and there's no public mempool auction. So buys landing in
the same block at launch were almost always planned ahead, not won from a mempool race.
That makes same-block and same-transaction clusters a **stronger** bundle signal on Arc than
on Ethereum. Read [references/arc-network.md](references/arc-network.md) before giving
Arc-specific advice.

## Modes

| User says | Do |
|---|---|
| a token address (`0x…`) / "scan", "rug check", "is this bundled" | **Scan workflow** below |
| "find new coins", "what launched", "discover" | `discover --mints --scan 5` (finds and ranks in one go) |
| "watch launches", "alert me", "live" | `watch --mints` (scans every new pool as it lands) |
| a wallet address / "who funded this", "is this a sniper" | `wallet`, then explain the funding trail |
| a concept ("bundling", "vamping", "sizing") | answer from references + Spyzer frameworks |
| "build a suite", "dashboard", "track over time" | [references/suite-blueprint.md](references/suite-blueprint.md) |

## Scanner

`scripts/arc_scan.py` needs only Python 3.9+ (no installs). Run it from the skill directory:

```bash
python3 scripts/arc_scan.py scan 0xTOKEN                 # markdown report
python3 scripts/arc_scan.py --format json scan 0xTOKEN   # machine-readable, use for reasoning
python3 scripts/arc_scan.py discover --blocks 20000      # new V2/V3 pools in recent blocks
python3 scripts/arc_scan.py discover --mints --scan 5    # + launchpad tokens, ranked by risk
python3 scripts/arc_scan.py watch --mints                # live: scan each new pool as it appears
python3 scripts/arc_scan.py wallet 0xWALLET              # funder + first activity
```

Network config: `--rpc` / `ARC_RPC_URL` (defaults to Arc testnet), `--explorer` /
`ARC_EXPLORER_URL` (Arcscan, a Blockscout instance used for funder tracing). For mainnet or a
private node, set both. Useful `scan` flags: `--pool` (skip pool auto-detection),
`--deployer`, `--early-window N` (launch window in blocks, default 5), `--min-cluster N`,
`--max-trace N` (how many early buyers to trace funders for), `--blocks N` (cap history).
`--labels labels.json` (or `ARC_LABELS`) loads address labels you've verified (copy
`labels.example.json`). Funders labelled `cex…`/`bridge…`/`router…` are never clustered, and LP
held by a `locker…` label counts as locked. Never invent labels: only add addresses you
verified on Arcscan.

If the scanner can't reach the network, say so, show the exact command you ran, and ask for
an RPC URL. **Never make up chain data.**

## Scan workflow

1. **Run** `--format json scan <token>`. Look at `not_computed` first. Any signal listed
   there is unknown, not clean. Don't call it clean.
2. **Bundle forensics.** Use [references/bundle-detection.md](references/bundle-detection.md) to read each signal:
   - `shared_tx_groups`: one tx delivered tokens from the pool to several wallets. That's a bundler contract. This is the strongest signal.
   - `same_block_groups`: 3+ wallets bought in the same launch block.
   - `funder_clusters`: early buyers whose first USDC came from the same address.
   - `deployer_seeded`: wallets the deployer or mint sent tokens to before or outside the pool.
   - `bundled_supply_pct`: what those clustered wallets **still hold now**. This is the real dump risk.
   - `bundles.sell_through.sold_pct`: how much of what the bundle received it has already sold. Near 0 means a full overhang. 20–90 means it's selling right now. ≥90 means it already dumped and is mostly history.
3. **Concentration.** Look at `top10_pct` and `max_holder_pct` (pools and burn excluded). In fresh trenches, any one wallet over ~3.5% is a single-sell risk (Spyzer rule).
4. **Contract & liquidity.** A live `mint()` or `pause()` with an owner that hasn't renounced means the supply or trading can still be changed. `liquidity[].burned_pct` / `locked_pct` show whether the V2 LP can be pulled. If neither is at least 50%, the deployer can rug the pool. V3 positions are NFTs and aren't checked, so say so. A missing pool means you can't confirm the token is tradable.
5. **Judge the intent.** Bundling is supply control. It isn't automatically a scam. Bundles that are getting smaller over time, are disclosed, or are locked read differently from fresh-wallet clusters that are still full. Check the chart and the wallets' current behavior if you can.
6. **Score.** The scanner's `risk.score` and `risk.label` come from fixed weights ([references/scoring.md](references/scoring.md)). You can move the verdict **one band** with a stated reason (for example, "bundle wallets already sold 90%, so the overhang is gone"). Never move it silently.
7. **Report** using [references/report-template.md](references/report-template.md): verdict first, then the evidence with explorer links, what wasn't checked, and what would change the call.

For `discover`: pass `--quote <USDC/WUSDC addresses>` so pairs show the meme token, `--mints`
to also catch launchpad/bonding-curve tokens that never emit `PairCreated`, and `--scan N` to
quick-scan the newest N and get a ranked table. Do a full `scan` on any token you'll actually
recommend. A low risk score means fewer red flags, not a reason to buy.

For `watch`: it runs until stopped and prints one line per new token (`--format json` gives
JSONL for piping into a bot). Run it in the background and summarise the alerts for the user.

## Frameworks to apply (from Spyzer's guide)

- **Bundling is supply control, not automatically good or bad.** Base the call on cluster links, top-holder %, where the funding came from, chart shape, and volume compared with market cap.
- **Canonical identity / vamping:** if several Arc tokens chase one narrative, liquidity rotates to whichever the market treats as the original. Check the name, deployer, and community.
- **Thesis before entry:** if the user is weighing a trade, ask for a two-sentence reason to buy, what would prove it wrong, and a size that leaves them able to trade normally tomorrow.
- **Do not borrow conviction:** a low score isn't a buy signal. A KOL call isn't research.
- **Only the paranoid survive:** never ask for seed phrases or private keys. Point users to verified explorer URLs only.

## Files

- [references/arc-network.md](references/arc-network.md): chain facts, endpoints, Arc-specific gotchas
- [references/bundle-detection.md](references/bundle-detection.md): every signal, how to read it, false positives
- [references/scoring.md](references/scoring.md): risk weights and bands
- [references/report-template.md](references/report-template.md): output format
- [references/suite-blueprint.md](references/suite-blueprint.md): how to grow this into a full intelligence suite
- `scripts/arc_scan.py`: scanner · `labels.example.json`: label file format

## Limits

These are heuristics from public chain data. They aren't proof of intent, and they aren't
financial advice. A careful operator can fund wallets through a CEX or a bridge and avoid
clustering. Treat "no cluster found" as "no cluster *visible*".
