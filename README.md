# $TOKE Explorer — explorer.mctoken.xyz

A map-first, **anonymous, verifiable** intelligence explorer for the $TOKE (McToken) Solana token —
supply map, the complete holder/airdrop directory, governance, liquidity, and live price/activity.
Every figure links to chain. No wallet is ever tied to a human identity.

- **Mint:** `AmgUMQeqW8H74trc8UkKjzZWtxBdpS496wh4GLy2mCpo` · 3 decimals · max 420,000,069
- **Data contract:** `/api/v1/*.json` — versioned, anonymous; each record carries a `cite` to chain
- **Focus modes:** *Holders + Tagged* (default) · *Ever touched* (every address that ever held or moved TOKE)
- **Classes & cohorts:** addresses are labeled (wallet / AMM / program / CEX / distributor / infra) and
  grouped into airdrop cohorts (Genesis-71 primary; subsequent airdrops secondary) — all filterable.

This repository is the **published static bundle only**. The source knowledge base (and any identity data)
is private and never included here; published datasets are anonymous by design. Not financial advice.

## Deploy (Vercel)
Static, zero-build. Import this repo in Vercel → Framework **Other**, no build command. `vercel.json`
sets caching + CORS for `/api/v1/*`. Custom domain `explorer.mctoken.xyz` is attached in Vercel → Domains.
