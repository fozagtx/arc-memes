# Report template

Keep it scannable and lead with the verdict. Every claim should trace back to a scanner
field or an explorer link.

```markdown
# $SYMBOL — Name
`0xTOKEN` · Arc · scanned at block N

## Verdict: HIGH (58/100)
One or two sentences: the single biggest risk, and who controls the exit.

## Why
- 3 wallets bought in one bundler tx at launch and still hold 14% ([tx](…))
- 6 early buyers share funder 0xabc… (not a known CEX)
- Deployer kept 9% and `mint()` is live with an active owner

## Supply
Top 10: 41% · max single holder: 6.2% · holders: 312
(table of top holders, flagged wallets marked ⚠️)

## Not checked
Funder tracing (explorer unreachable) · LP lock status

## What would change the call
- Bundle wallets selling down below 3% total → ELEVATED
- Owner renounces / mint removed → −12

_On-chain heuristics, not proof of intent. Not financial advice._
```

When comparing several tokens (after `discover`), use one table: token, age in blocks,
score, label, bundled %, top10 %, and a one-line note. Sort by risk ascending.
