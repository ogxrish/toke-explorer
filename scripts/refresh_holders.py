#!/usr/bin/env python3
"""
refresh_holders.py — derive fresh holders.json + holders_all.json from base_lean.json.

The external auto-refresh pipeline keeps base_lean.json (all 22k+ wallets:
balance / pct / first_seen / sns) and labels.json current, but holders.json —
the featured, enriched snapshot the Voyager, the homepage twin lenses and the
Explorer's provenance surfaces read — was a one-time backfill bundle. This
script closes that gap deterministically, using ONLY data already published
in the repo:

  fresh facts   : base_lean.json  (balance, pct, first_seen, last_seen, sns, sns_all)
  fresh labels  : labels.json     (liquidity-pool / governance / treasury / program …)
  tier badges   : badges.json     (rules parsed at runtime — never hardcoded)
  history       : previous holders_all.json / holders.json rows
                  (historical + honor badges, cohorts, curated type_basis)

New in the derived output: `first_seen` and `age_days` per row — Voyager
Protocol v1's canonical inputs (distance_km = balance × age_days).

Deterministic: output is a pure function of the input files (as_of is taken
from base_lean), so re-runs on unchanged inputs produce byte-identical files
and the CI job only commits real changes.
"""
import json, math, os, re, sys
from datetime import datetime, timezone

API = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api", "v1")
API = os.path.normpath(API)

FEATURED_MIN_BALANCE = 1_000_000  # holders.json selection: balance>=1M OR cohort OR labeled type


def load(name):
    with open(os.path.join(API, name), "r", encoding="utf-8") as f:
        return json.load(f)


def unwrap(j):
    return j["data"] if isinstance(j, dict) and "data" in j else j


def parse_tier_rules(badges_doc):
    """Parse '>=5,000,000 TOKE' style tier rules from badges.json. Highest tier wins."""
    tiers = []
    for b in unwrap(badges_doc)["badges"]:
        if b.get("kind") != "tier":
            continue
        m = re.search(r">=\s*([\d,]+(?:\.\d+)?)", b.get("rule", ""))
        if not m:
            continue
        tiers.append((float(m.group(1).replace(",", "")), b["key"]))
    tiers.sort(reverse=True)  # e.g. [(5e6,'mcwhale'), (4.2e6,'1pct-club'), (1e6,'mcmillionaire'), (1,'mcvoter')]
    return tiers


def tier_badge(balance, tiers):
    for threshold, key in tiers:
        if balance >= threshold:
            return key
    return "sub-1-toke"  # matches historical convention for dust balances


def age_days(first_seen, asof_dt):
    if not first_seen:
        return None
    try:
        t = datetime.strptime(first_seen[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return max(0, math.floor((asof_dt - t).total_seconds() / 86400))


# labels.json category -> holders row type (existing vocabulary preserved)
CATEGORY_TYPE = {
    "liquidity-pool": "lp",
    "governance": "dao-contract",
    "dao": "dao-contract",
    "treasury": "treasury-dao",
    "program": "program",
    "distributor": "distributor",
    "project": "project",
}


def main():
    base = load("base_lean.json")
    labels = unwrap(load("labels.json")).get("assign", {})
    badges_doc = load("badges.json")
    prev_all = {r["address"]: r for r in unwrap(load("holders_all.json"))}
    prev_feat = {r["address"]: r for r in unwrap(load("holders.json"))}

    asof = base["as_of"]
    asof_dt = datetime.strptime(asof, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    tiers = parse_tier_rules(badges_doc)
    hist_badge_keys = {b["key"] for b in unwrap(badges_doc)["badges"] if b.get("kind") in ("historical", "honor")}

    rows = [r for r in base["data"] if r.get("balance", 0) > 0]
    rows.sort(key=lambda r: (-r["balance"], r["address"]))

    out_all, out_feat = [], []
    for rank, r in enumerate(rows, 1):
        addr = r["address"]
        bal = r["balance"]
        old = prev_feat.get(addr) or prev_all.get(addr) or {}
        label = labels.get(addr)

        # --- badges: recompute tier from live balance; carry historical/honor forward
        badges = [tier_badge(bal, tiers)]
        badges += [b for b in old.get("badges", []) if b in hist_badge_keys]

        # --- cohorts are historical facts about the address: carry forward verbatim
        cohorts = list(old.get("cohorts", []))

        # --- type: fresh label wins, then curated previous row, then default holder
        typ, basis, pool, pair = "holder", None, None, None
        if label:
            typ = CATEGORY_TYPE.get(label.get("category"), "holder")
            nm = label.get("name") or label.get("display") or label.get("category")
            proto = label.get("protocol")
            basis = (f"{proto} — {nm}" if proto else nm)
            if typ == "lp":
                basis += " -- liquidity, not a personal holder"
                pool = label.get("display") or nm
        if old.get("type") and old["type"] != "holder":
            # previous curation is richer (pool/pair, prose basis) — prefer it wholesale
            typ = old["type"]
            basis = old.get("type_basis") or basis
            pool = old.get("pool") or pool
            pair = old.get("pair")
        elif not basis:
            basis = old.get("type_basis") or "default -- holds TOKE; no further claim"

        sns = r.get("sns")
        domains = r.get("sns_all") or ([sns] if sns else [])
        aged = age_days(r.get("first_seen"), asof_dt)

        lean = {
            "address": addr,
            "balance": bal,
            "pct": r.get("pct"),
            "rank": rank,
            "type": typ,
            "sns": sns,
            "badges": badges,
            "cohorts": cohorts,
            "first_seen": r.get("first_seen"),
            "age_days": aged,
            "cite": {"type": "account", "ref": addr},
        }
        out_all.append(lean)

        if bal >= FEATURED_MIN_BALANCE or cohorts or typ != "holder":
            out_feat.append({
                "address": addr,
                "balance": bal,
                "pct": r.get("pct"),
                "rank": rank,
                "type": typ,
                "type_basis": basis,
                "pool": pool,
                "pair": pair,
                "sns": sns,
                "domains": domains,
                "badges": badges,
                "cohorts": cohorts,
                "first_seen": r.get("first_seen"),
                "age_days": aged,
                "cite": {"type": "account", "ref": addr},
            })

    # featured rows get their own sequential rank (matches historical convention)
    for i, r in enumerate(out_feat, 1):
        r["rank"] = i

    def envelope(prev_doc, dataset, data, notes):
        return {
            "dataset": dataset,
            "version": prev_doc.get("version", "v1"),
            "as_of": asof,
            "chain": prev_doc.get("chain", "solana-mainnet"),
            "source": {
                "derived_from": ["base_lean.json", "labels.json", "badges.json"],
                "carried_history": ["holders_all.json (badges/cohorts backfill)"],
                "pipeline": "scripts/refresh_holders.py",
                "confidence": "confirmed",
            },
            "visibility": prev_doc.get("visibility", "l2"),
            "notes": notes,
            "data": data,
        }

    doc_feat = envelope(
        load("holders.json"), "holders", out_feat,
        "Featured set: balance>=1M OR cohort OR labeled non-holder. Balances/pct/first_seen from "
        "base_lean (auto-refreshed); tier badges recomputed from badges.json rules; historical/honor "
        "badges + cohorts carried by address; types from labels.json. NEW: first_seen + age_days "
        "(Voyager Protocol v1 inputs). Anonymous.",
    )
    doc_all = envelope(
        load("holders_all.json"), "holders_all", out_all,
        "All holders (balance>0), enriched as holders.json (see its notes). Loaded on demand by the "
        "explorer's 'All holders' scope. Not bundled into data.js. NEW: first_seen + age_days.",
    )

    changed = []
    for name, doc in (("holders.json", doc_feat), ("holders_all.json", doc_all)):
        path = os.path.join(API, name)
        new = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        try:
            with open(path, "r", encoding="utf-8") as f:
                cur = f.read()
        except FileNotFoundError:
            cur = None
        if new != cur:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            changed.append(name)

    print(f"as_of={asof} rows_all={len(out_all)} rows_featured={len(out_feat)} changed={changed or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
