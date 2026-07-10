# Entity logo icons

The explorer's **Entity** column renders a small round logo icon per protocol.

This folder ships self-hosted **official brand logos as `<slug>.png`** (64×64, optimized),
with the authored `<slug>.svg` marks kept as offline fallback — no external CDN / no runtime
dependency, in keeping with the explorer's self-contained, verifiable design. Resolution
order in `entityIcon()`: official `.png` → authored `.svg` → branded monogram. The icon is
masked to a circle by the `.ent` style in `index.html`.

Official domain-provenance marks (SNS, AllDomains) live in `../domains/{sns,alldomains}.svg`
and are rendered by `domMark()` next to every `.sol` / AllDomains shortname.

## Files

| Entity   | File           |
|----------|----------------|
| Jupiter  | `jupiter.svg`  |
| Orca     | `orca.svg`     |
| Raydium  | `raydium.svg`  |
| Meteora  | `meteora.svg`  |
| Realms   | `realms.svg`   |
| Align    | `align.svg`    |

The filename is the entity name lowercased with non-alphanumerics stripped
(`entityIcon()` in `index.html` resolves `assets/entities/<slug>.svg`).

## Swapping in official artwork

Drop a replacement `<slug>.svg` (or change the extension in `entityIcon()` to `.png`
and add a `<slug>.png`) here — no other code change needed. Use a square (1:1) asset;
it's center-masked to a circle. If a file is missing or fails to load, the code falls
back to a branded monogram (first letter on the entity's brand colour from the
`ENTITY` map in `index.html`).
