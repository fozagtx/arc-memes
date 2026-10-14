# Risk scoring

Implemented in `score()` in `scripts/arc_scan.py`. The points add up and the total is capped at 100.
**Higher means more dangerous.**

| Signal | Points |
|---|---|
| Bundled supply still held ≥20% / ≥8% / >0% | 30 / 18 / 8 |
| Any multi-recipient buy tx (`shared_tx_groups`) | 15 |
| Shared-funder clusters among early buyers | 12 |
| `mint()` present, owner not renounced | 12 |
| Coordinated launch block(s) | 10 |
| Deployer pre-distributed ≥10% of supply | 10 |
| Top-10 holders ≥50% / ≥30% | 15 / 8 |
| Deployer still holds ≥5% | 8 |
| `pause()` present, owner not renounced | 6 |
| ≥50% of traced early buyers are fresh wallets | 6 |
| <50% of V2 LP burned and no labelled locker holds it | 8 |
| Bundle actively distributing (sold 20–90%, still holding some) | 6 |
| Single holder ≥3.5% | 5 |
| No liquidity pool detected | 5 |

| Band | Score | Meaning |
|---|---|---|
| LOW | 0–24 | Few red flags visible. Still a memecoin |
| ELEVATED | 25–44 | Real concerns. Size small, watch flagged wallets |
| HIGH | 45–69 | Insiders likely control the exit. Avoid unless you have a specific edge |
| CRITICAL | 70–100 | Classic farm setup. Treat as a rug in waiting |

You can move the band by **one step** if you state a reason the data supports (for example,
"funder is a CEX hot wallet" moves it down, or "bundle wallets are actively selling" moves it
up). Unknown signals (`not_computed`) add no points. Name them in the report so a missing
check never looks like a clean one.
