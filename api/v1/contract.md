# TOKE Explorer — Public Data Contract (v1)

The versioned interface between the KB and the explorer. The front-end knows **only** this contract,
so the backend can be static JSON now and a live TOKE API later with no UI change.

**Three rules every record obeys:**
1. **Anonymous.** Addresses only. No name, handle, or wallet↔human mapping. Ever. (Enforced by `redaction_gate.py`.)
2. **Verifiable.** Every figure carries a `cite` → a tx / account / program ref (or a `method` for computed values).
3. **Tiered.** Every dataset + field carries a `visibility` of `l1` | `l2` | `l3`. `l4` is never emitted.

Base path: `/api/v1/`. All amounts are TOKE in decimal (3 dp) unless suffixed `_g` (g = 0.001 TOKE).

---

## Common envelope

Every dataset file:

```json
{
  "dataset": "holders",
  "version": "v1",
  "as_of": "2026-05-30T00:00:00Z",
  "chain": "solana-mainnet",
  "source": { "kb_files": ["01-token/onchain-ledger/snapshots/holders_20260530.json"],
              "pipeline": "snapshot_holders.py", "confidence": "confirmed" },
  "visibility": "l2",
  "notes": "…",
  "data": [ /* records */ ]
}
```

### The `cite` object (provenance, attached to figures)

```json
"cite": {
  "type": "account|tx|program|token|computed",
  "ref": "<address | signature | mint>",        // omitted when type=computed
  "method": "sum(balances where last_touch>1yr)", // present when type=computed
  "inputs": ["holders@2026-05-30"],                // dataset refs feeding a computed value
  "confidence": "confirmed|corroborated|single_source|inferred"
}
```

The client turns `{type, ref}` into a deep-link using the user-selected explorer (Solscan default, XRAY,
official). For `type:"computed"`, the UI shows `method` + `inputs` in a tooltip instead of a link.

---

## Datasets

### 1. `token.json` — canonical facts  ·  `l1` (facts) + `l2` (derived)
mint, name, decimals, `max_supply`, `current_supply`, `burned` + `burned_pct`(l2), authorities
(mint/freeze/update + mutable-metadata), `lp_locked_pct`, `holders_count`, `pools[]` (ref). Each authority/
supply field carries a `cite{type:"token"|"account"}`. Source: `01-token/token.json`.

### 2. `oracle.json` — price  ·  `l2`
`liquidity_weighted_price_usd`, `total_pool_liquidity_usd`, `implied_mcap_usd`, per-pool `{dex,quote,pair,priceUsd,liquidityUsd, cite{type:"account",ref:pair}}`, `method:"liquidity-weighted VWAP across pools"`. Source: `analysis/oracle_*.json` + live Dexscreener. **Thin-liquidity caveat** carried in `notes`.

### 3. `pools.json` — material pools  ·  `l1`
Array of `{dex, pair(ref), quote, created, liquidity_usd, price_usd, label}`. The 3 material pools (Meteora SOL/USDC, Raydium SOL). **DePIN LP pairs (TOKE-HNT/IOT) excluded** per owner.

### 4. `liquidity.json` — flagship  ·  `l1` (reserves) + `l2` (derived)
Per-pool reserves + depth points; **LP holders anonymous + ranked** `[{address, lp_kind:"raydium-lp|meteora-pos", share_pct, cite}]`; LP concentration; reserves-over-time series; a `true_liquidity_vs_fdv` block (`liquidity_usd`, `mcap_usd`, ratio). Slippage curve points (`l2`, `method`). Source: pools + snapshots/`lp_holders_*`, `meteora_cnft_*` (owner-run DAS for Meteora positions).

### 5. `supply.json` — disposition + concentration  ·  `l2`
Buckets `[{key, label, wallets, toke, pct, cite{computed}}]`: active_lt1yr, dormant_gt1yr, untouched_genesis, dust_lt1, routing_infra, burned. Plus `concentration:{top10_pct, top25_pct}`. This feeds the **Map**. Source: `analysis/illiquid_supply.json` + snapshot.

### 6. `holders.json` — the tracked set (leaderboard)  ·  `l1` (balance) + `l2` (badges/type)
The centerpiece. One record per **featured** wallet (scope: **≥1M TOKE ∪ cohorts**, §3.5):

```json
{
  "address": "Cn4PFe…ZoAjm",
  "rank": 5,
  "balance": 18398710.048,
  "pct": 4.3838,
  "cite": { "type": "account", "ref": "Cn4PFe…ZoAjm" },
  "type": "community|treasury|market-maker|lp|gov-escrow|routing",   // l2 classification
  "sns": "supertoke.sol",            // ONLY public SNS labels; null otherwise. NOT a human name.
  "badges": ["mcwhale","born-mcwhale","dank"],                       // l2/l3
  "cohorts": ["genesis-71","500k","voter-2026"],                    // l2 (chain-derived only)
  "first_active": "2023-06-22", "last_active": "2025-11-25",        // l1
  "age_days": 1074,
  "rank_delta_24h": 0, "rank_delta_7d": -1, "balance_delta_7d": 0,  // l2
  "pnl_realized_usd": 2867,          // l2, OPTIONAL, OFF by default in UI; omitted if disabled
  "epithet_ref": "ep_genesis_hodler" // l3 → resolved via lore.json/epithets; address-keyed, no name
}
```

**Never** contains a name/handle. `sns` only carries *publicly resolvable* domains (treasuries), which are
public labels, not identities. The full 13,003 holders are **not** here — they live in `supply.json`
aggregates and are reachable via on-demand lookup.

### 7. `cohorts.json` — cohort taxonomy  ·  `l2` + the L4→L2 bridge
`[{key, label, rule, members:[address…], count, aggregate:{toke,pct}, cite}]` for genesis-71, born-mcwhale,
500k, lp, voter-{2024,2025,2026}, nft-taste, nft-mcvote, dank. `rule` states the on-chain predicate (so it's
reproducible). **Bridge field** `identity_mapped_pct` (e.g. 34.4) is the *only* L4-derived value — a number,
never a roster. Clusters that were identity-informed (e.g. "LP Cabal") are **excluded** unless reconstructable
from L1 alone.

### 8. `flows.json` — curated flow stories  ·  `l1` (txs) + `l3` (framing)
`[{key, title, blurb(l3), nodes:[{id,label,address?}], edges:[{from,to,amount,cite{type:"tx",ref:sig}}]}]`:
genesis-fingerprint, mcvault-unlock, escrow-cycle, lp-pooling (anonymous). Every edge cites a signature.

### 9. `governance.json` — proposals & votes  ·  `l1` + `l2`
`proposals:[{id(ref), title, date, state, turnout_pct, result, cite{type:"account",ref:proposal}}]`;
`mcvotes:[{year, theme, yes_pct, quorum, outcome}]`; `rolls:[{proposal, address, weight, direction, cite{tx}}]`
(anonymous); `tip4_dividend:{payouts, method}`. Source: `analysis/governance.json`, `realms_audit.json`.

### 10. `badges.json` — badge system  ·  `l2` (thresholds) + `l3` (culture)
`[{key, glyph, label, rule, max_possible, current_count, kind:"tier|historical|honor"}]` — mcwhale, 1pct-club,
mcmillionaire, mcvoter, born-mcwhale ⭐, dank 🌿. Counts are computed; assignment is per-wallet in `holders.json`.

### 11. `lore.json` — narrative + epithets  ·  `l3`
`saga` (McVault, Moonman, Idiot Dev, Wheel of TOKE blurbs), `hall_of_fame:[{exhibit, title, status, link}]`,
`epithets:{ "<address>": {alias, blurb, cite?} }` — **address-keyed, zero names**, sourced from `curated/epithets.json`.

### 12. `health.json` — integrity posture  ·  `l1` + `l2`
`authorities`, `lp_locked_pct`, `top10_pct`, `flags:[{key,severity,detail,cite}]`, `score` + `grade` (method
stated). Powers the embeddable badge. Source: `token.json` + rugcheck capture.

### 13. `activity.json` — recent on-chain activity  ·  `l1`
Most-recent N `[{sig(ref), ts, type:"swap|transfer|vote|lp", from, to, amount, cite{type:"tx",ref:sig}}]`.
Pre-baked tail + refreshed live client-side (Dexscreener/Helius). Anonymous addresses.

### 14. `base_all.json` — the COMPLETE BASE  ·  `l2`  ·  ON-DEMAND
Every address that ever touched TOKE (~22.6k). One row per address:
`{address, balance, pct, rank|null, type, class, class_label, class_source, sns, badges, cohorts, holder, tagged, recv, legs}`.
Flags drive the front-end **focus modes** (no server round-trip): **default** = `holder || tagged`
(current holders + any cohort-tagged wallet — the primary view); **ever-touched** = all rows.
Large (~6 MB) so it is fetched lazily and never bundled into `data.js`. Built by `build_base.py`.

### 15. `cohorts.json` — cohort catalog  ·  `config`
`{ "<cohort key>": {label, tier:"primary|secondary|badge", date, count} }`. Genesis-71 = **primary**;
the subsequent airdrops (MOBILE, POLLEN, Pixel, McDegens, DeWiCats, Hot Heads, DePIN Happy Hour, Entropy,
DePioneers) = **secondary**; DANK/Voter = badges. Drives the cohort filter + cohort cards (live counts).

### 16. `classes.json` — classification catalog  ·  `config`
`{ "<class>": {label, count} }` for the classification filter (wallet / amm / cex / program / distributor /
treasury / project / dao / bot / infra / flagged). Per-address class lives in `base_all.json`.

---

## Downstream correction surfaces (edit → re-run `build/refresh.sh`)
The base is data-driven, so tags and accuracy can be corrected without touching code or architecture:
- **`curated/address-labels.json`** — per-address `class` + `label` (`source: curated` always wins over the
  build-time heuristic). Promote any auto-classified address by adding it here.
- **`curated/airdrop_recipients.json`** — verified recipient sets per cohort (rename/add keys here).
- **`01-token/onchain-ledger/analysis/airdrops_audit.json`** — human source of truth for airdrop
  amounts/dates/verdicts; `build_base.py`'s `COHORT_META` mirrors its labels/tiers/dates.
- Cohort membership, classification, and focus-mode definitions all flow from these files into
  `base_all.json` on rebuild — no front-end change required.

---

## Versioning
`/api/v1/` is frozen once M1 ships; breaking changes → `/api/v2/`. Each file's `as_of` + `source.confidence`
drive the UI's freshness + "confirmed vs inferred" treatment. A top-level `index.json` lists datasets,
their `as_of`, and the `contract_version`.
