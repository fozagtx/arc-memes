# Arc Memecoin Intel

Agent skill for memecoin research on [Arc](https://www.arc.network/), Circle's USDC-gas L1. It scans tokens on-chain, finds bundled supply (bundler txs, coordinated launch blocks, shared-funder clusters, deployer pre-distribution), scores the risk 0–100, and writes a research report. It uses the frameworks from [spyzer-memecoin-skill](https://github.com/fozagtx/spyzer-memecoin-skill).

This is educational tooling only. It is not financial advice.

## What's included

- `skills/arc-memecoin-intel/SKILL.md`: the skill entrypoint and workflow
- `skills/arc-memecoin-intel/scripts/arc_scan.py`: a stdlib-only scanner with `discover`, `scan`, and `wallet` commands
- `skills/arc-memecoin-intel/references/`: Arc network notes, bundle signals, scoring, the report template, and the full-suite blueprint
- `scripts/install.sh` / `scripts/verify.sh`: install into Claude, Codex, or generic agent skill folders

## Install (one line)

```bash
curl -fsSL https://raw.githubusercontent.com/fozagtx/arc-memes/main/scripts/install.sh | bash
```

That clones the repo, copies the skill into `~/.claude/skills/arc-memecoin-intel`, and cleans up. Restart Claude Code and ask *"use arc-memecoin-intel to scan 0x…"*. The agent runs the scanner for you. You never have to touch Python yourself.

Other agents: `... | bash -s -- codex`, `... | bash -s -- all`, or `... | bash -s -- --dest /your/skills/arc-memecoin-intel`.

**Or with git clone:**

```bash
git clone https://github.com/fozagtx/arc-memes.git
cd arc-memes && ./scripts/install.sh            # claude | codex | agents | all
```

**Requirements:** `git`, plus Python 3 for the scanner. Python 3 comes preinstalled on macOS and Linux, and the scanner needs no `pip install` because it uses only the standard library. On Windows, use WSL or install Python from python.org.

## Use the scanner directly

```bash
cd skills/arc-memecoin-intel
python3 scripts/arc_scan.py discover --mints --scan 5
python3 scripts/arc_scan.py watch --mints
python3 scripts/arc_scan.py scan 0xTOKEN
python3 scripts/arc_scan.py --format json scan 0xTOKEN
python3 scripts/arc_scan.py wallet 0xWALLET
```

Set `ARC_RPC_URL` and `ARC_EXPLORER_URL` (or pass `--rpc` / `--explorer`) for mainnet or your own node. The defaults point to Arc testnet and Arcscan.

## Ask your agent

```text
Use arc-memecoin-intel to scan 0x... and tell me if it's bundled.
Find new memecoins launched on Arc today and rank them by risk.
Who funded the top 5 early buyers of 0x...?
How should we grow this into a full Arc memecoin intelligence suite?
```
