# Bundle detection

A **bundle** is one actor controlling supply through many wallets. Spyzer calls it
"hidden gravity": whoever holds enough supply decides when the chart falls. No single signal
proves a bundle, so the scanner stacks them.

| Signal (JSON key) | How it's computed | Strength | False positives |
|---|---|---|---|
| `shared_tx_groups` | one tx contains pool → wallet transfers to ≥2 different wallets | **Very strong.** A bundler contract buying for many wallets at once | aggregators/routers that split output (rare for memes); check the tx |
| `same_block_groups` | ≥`--min-cluster` distinct wallets bought within the launch window, same block | Strong on Arc (no mempool race) | very hyped launch with many real buyers; compare with funder data |
| `funder_clusters` | early buyers whose first USDC came from the same address | Strong | CEX hot wallets and bridges fund thousands of unrelated users. **If the funder is a known exchange or bridge, discount it** |
| `deployer_seeded` | tokens sent from the mint/deployer to wallets other than the pool | Medium–strong | disclosed team/marketing/vesting wallets, airdrops; ask whether it was disclosed |
| `fresh_wallet_ratio` | share of traced early buyers with nonce ≤ 3 | Supporting | new users onboarding to Arc. On a young chain many real users are fresh |
| `top10_pct`, `max_holder_pct` | current balances excluding pools, burn, and the token contract | Context | CEX or locker contracts holding for many users; check what the address is |

**The number that matters most is `bundled_supply_pct`.** It's what the flagged wallets hold
*now*. A bundle that already sold out is history. A bundle still holding 30% is the dump risk.

## Reading intent (Spyzer)

Bundles aren't automatically malicious. A team can use one to stabilize supply. Lean benign if:
it was disclosed, the tokens are locked or vesting, the wallets haven't sold into strength, and
the deployer has a public track record. Lean malicious if: the wallets are fresh, all funded by
one source in the same minutes, sold early into retail buys, the chart is too clean or full of
bot candles, or volume is far out of line with market cap.

## Manual follow-ups when the stakes are high

1. Open the `shared_tx_groups` tx on Arcscan. Is the `to` a known router or a custom contract?
2. For each funder cluster, run `wallet <funder>`. Is the funder itself funded by the deployer?
3. Compare the bundled wallets' sells with the chart. Did they sell into retail candles?
4. Check whether the LP tokens are locked or burned (look at who holds the pool's LP token).
