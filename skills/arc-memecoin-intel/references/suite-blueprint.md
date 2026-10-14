# Growing this into a full Arc memecoin intelligence suite

The skill today is a **single-shot scanner and analyst**. Here's the recommended way to grow
it into a full research suite, in build order. Each layer is useful on its own.

## 1. Indexer (data foundation)
Replace per-scan `eth_getLogs` with one continuous indexer: Ponder, Envio, or a small Python
worker that writes to Postgres. Store every `Transfer`, `PairCreated`/`PoolCreated`, `Swap`,
and native USDC funding edge. Everything below then becomes a fast SQL query instead of
minutes of RPC calls, and you get true historical holder snapshots.

## 2. Wallet graph (the real moat)
Build a funding graph (who funded whom, plus who sent tokens to whom) and run
connected-components or Louvain clustering on it. Label known nodes (CEX hot wallets, bridges,
routers, lockers, launchpads) so they don't merge unrelated users. Persistent cluster IDs let
you say "this cluster bundled 4 previous launches and dumped every one". Deployer and cluster
**reputation across launches** is the single most predictive signal you can have.

## 3. Launch radar (real-time)
Subscribe to new blocks (WebSocket `eth_subscribe`). On every new pool, run the scan
automatically within seconds. Push alerts to Telegram or Discord with the verdict, and add a
watchlist that alerts when flagged wallets start selling. Arc's sub-second finality makes
this practical.

## 4. Market and attention layer
Join on-chain data with price, volume, and market-cap candles (from swap events), plus social
attention (X mentions of the ticker and contract address, Telegram growth). That covers
Spyzer's **attention arbitrage** and **vamping** checks: spot the gap between a narrative
going viral and the market repricing, and find which of several copycat tickers is the
canonical one.

## 5. Smart-money and KOL tracker
Score wallets by realized PnL across Arc memes. Follow consistently profitable early wallets,
and audit KOL calls against what their wallets actually did. This applies the guide's
"track record over followers" rule.

## 6. Research UI
A dashboard (Next.js + the indexer API) with token pages (score history, bubble map of
clusters, holder churn), wallet pages, a live launch feed, and a "compare" view for vamp
battles. Also expose the scanner as an **MCP server** so Claude can call `scan`, `cluster`,
and `wallet_history` directly instead of shelling out.

## 7. Feedback loop
Label outcomes (rugged, dumped by the bundle, survived 7d, 10x) and backtest the score
weights in `scoring.md` against them. Retune every few weeks. Without this loop the score
is an opinion. With it, it's a model.

### Suggested stack
Python or TypeScript indexer → Postgres (+ pgvector for narrative similarity) → FastAPI or tRPC →
Next.js UI · bot alerts · MCP server wrapping the same queries · this skill as the analyst layer.
