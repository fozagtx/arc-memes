# Arc network notes

Arc is Circle's open EVM-compatible Layer 1. It's built for stablecoin finance and settles in USDC.

## Endpoints (verify before relying on them; they can change)

| | Testnet |
|---|---|
| Chain ID | `5042002` |
| RPC | `https://rpc.testnet.arc.network` |
| Explorer | `https://testnet.arcscan.app` (Blockscout: `/api/v2/...` and Etherscan-style `/api?module=...`) |
| Native gas | USDC |

For mainnet, or a provider RPC (Alchemy, QuickNode, your own node), pass `--rpc` and
`--explorer` or set `ARC_RPC_URL` and `ARC_EXPLORER_URL`. Funder tracing needs an explorer API.
Everything else needs only the RPC. Creation-block binary search needs an **archive** node. On a
pruned node the scanner falls back to the last 50k blocks and reports the history as incomplete.

## Arc-specific gotchas

- **USDC is gas.** Every new wallet has to receive USDC before it can do anything. That makes
  the *first incoming USDC* a reliable funding origin, which is good for clustering. Native USDC
  balance uses 18 decimals. The USDC ERC-20 interface uses 6. Don't mix them when you compare amounts.
- **Deterministic sub-second finality, no public mempool auction.** Classic mempool sniping
  and sandwiching are much harder. If many wallets buy in the launch block, it was probably
  arranged by the deployer or a bundler contract. Weight same-block clusters more than you would on Ethereum.
- **Gas is cheap and priced in dollars.** Spinning up dozens of wallets costs almost nothing.
  A high share of fresh wallets among early buyers matters more here.
- **Dollar-denominated pairs.** Most meme pairs are quoted in USDC or a wrapped USDC. Pass those
  addresses to `discover --quote` so the meme side is identified correctly.
- **Young ecosystem.** DEX factories, launchpads, and lockers are still settling. Don't assume a
  specific DEX. `discover` listens for the standard Uniswap V2 `PairCreated` and V3
  `PoolCreated` events from *any* factory. A custom launchpad that uses bonding curves and
  emits other events won't show up. Scan those tokens directly by address.
