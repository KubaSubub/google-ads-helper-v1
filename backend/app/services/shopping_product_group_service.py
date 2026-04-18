"""Shopping product-group performance + feed quality heuristics (local-only).

Full Shopping optimisation needs Merchant Center integration (feed diagnostics,
disapprovals, image quality). This service uses only what's already in our DB
— the product_groups table synced from Google Ads API — to surface the
high-impact patterns a PPC operator would spot in a weekly review.

Surfaces:

1. **Zero-conversion UNIT-level groups with material spend** → candidates for
   bid down or exclusion.
2. **High-ROAS units vs low-ROAS units in same subdivision** → bid reshuffle.
3. **UNIT groups with 0 impressions despite non-zero bid** → likely feed issue
   (product not serving — could be disapproved, missing price, missing image).
4. **Subdivision without any UNIT children** → incomplete structure.
5. **Top UNITs by cost without conversions in 30d** → Pareto losers.

Output is per-group (filtered to UNIT partition_type when relevant) sorted by
severity and cost.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.product_group import ProductGroup


def _safe_div(num: float, den: float) -> float:
    return (num / den) if den else 0.0


def product_group_report(db: Session, client_id: int) -> list[dict]:
    """Return Shopping product-group findings with severity + recommendation."""
    rows = (
        db.query(ProductGroup, Campaign)
        .join(Campaign, ProductGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SHOPPING",
            ProductGroup.status == "ENABLED",
        )
        .all()
    )
    if not rows:
        return []

    # Compute ROAS baselines per campaign for comparison.
    per_campaign: dict[int, list[ProductGroup]] = defaultdict(list)
    campaign_lookup: dict[int, Campaign] = {}
    for pg, camp in rows:
        per_campaign[camp.id].append(pg)
        campaign_lookup[camp.id] = camp

    campaign_avg_roas: dict[int, float] = {}
    for camp_id, pgs in per_campaign.items():
        total_cost = sum((p.cost_micros or 0) for p in pgs) / 1_000_000
        total_value = sum((p.conversion_value_micros or 0) for p in pgs) / 1_000_000
        campaign_avg_roas[camp_id] = _safe_div(total_value, total_cost)

    # Identify subdivisions without UNIT children.
    child_count_by_parent: dict[str, int] = defaultdict(int)
    for pg, _camp in rows:
        if pg.parent_criterion_id:
            child_count_by_parent[pg.parent_criterion_id] += 1

    findings: list[dict] = []
    for pg, camp in rows:
        cost_usd = (pg.cost_micros or 0) / 1_000_000
        conv_value_usd = (pg.conversion_value_micros or 0) / 1_000_000
        conversions = float(pg.conversions or 0)
        impressions = pg.impressions or 0
        clicks = pg.clicks or 0
        bid_usd = (pg.bid_micros or 0) / 1_000_000
        roas = _safe_div(conv_value_usd, cost_usd)
        cpa = _safe_div(cost_usd, conversions) if conversions > 0 else None
        cvr = _safe_div(conversions, clicks) * 100

        flags: list[str] = []
        severity = "LOW"
        recommendation = ""

        # UNIT-level checks (actionable — subdivisions are just tree nodes)
        if pg.partition_type == "UNIT":
            # 1. Zero-impression UNIT with a bid → likely feed issue
            if impressions == 0 and (pg.bid_micros or 0) > 0:
                flags.append("ZERO_IMPRESSIONS_WITH_BID")
                severity = "HIGH"
                recommendation = (
                    "UNIT ma bid ale 0 wyświetleń — prawdopodobnie problem z feedem "
                    "(produkt disapproved, brak zdjęcia, brak ceny, brak GTIN). "
                    "Sprawdź Merchant Center → Diagnostics."
                )

            # 2. Zero-conversion UNIT with material spend
            elif conversions == 0 and cost_usd >= 25:
                flags.append("ZERO_CONV_WITH_SPEND")
                severity = "HIGH" if cost_usd >= 100 else "MEDIUM"
                recommendation = (
                    f"UNIT wydał ${cost_usd:.2f} bez konwersji. Zmniejsz bid lub wyklucz "
                    "(dodaj UNIT z bidem 0 dla tej gałęzi)."
                )

            # 3. Very low ROAS vs campaign avg
            elif cost_usd >= 25 and campaign_avg_roas[camp.id] > 0 and roas < campaign_avg_roas[camp.id] * 0.5:
                flags.append("LOW_ROAS_VS_CAMPAIGN")
                severity = "MEDIUM"
                recommendation = (
                    f"ROAS {roas:.2f}× to mniej niż połowa średniej kampanii "
                    f"({campaign_avg_roas[camp.id]:.2f}×). Zmniejsz bid o 25-50%."
                )

            # 4. High-ROAS underserved (low IS signal from low impressions given high CVR)
            elif cost_usd >= 25 and roas >= campaign_avg_roas[camp.id] * 2 and campaign_avg_roas[camp.id] > 0:
                flags.append("HIGH_ROAS_UNDERSERVED")
                severity = "MEDIUM"
                recommendation = (
                    f"ROAS {roas:.2f}× to 2× średnia kampanii ({campaign_avg_roas[camp.id]:.2f}×). "
                    "Zwiększ bid o 20-30% i skaluj."
                )

        # 5. Subdivision without UNIT children (orphan node)
        if pg.partition_type == "SUBDIVISION" and child_count_by_parent.get(pg.google_criterion_id, 0) == 0:
            flags.append("SUBDIVISION_WITHOUT_CHILDREN")
            severity = "LOW"
            recommendation = (
                "Subdivision bez dzieci — wypełnij rozdziałami UNIT lub usuń."
            )

        if not flags:
            continue

        findings.append({
            "product_group_id": pg.id,
            "campaign_id": pg.campaign_id,
            "campaign_name": campaign_lookup[pg.campaign_id].name,
            "case_value": pg.case_value,
            "case_value_type": pg.case_value_type,
            "partition_type": pg.partition_type,
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": round(cost_usd, 2),
            "conversions": round(conversions, 2),
            "conversion_value_usd": round(conv_value_usd, 2),
            "bid_usd": round(bid_usd, 2),
            "cvr_pct": round(cvr, 2),
            "cpa_usd": round(cpa, 2) if cpa is not None else None,
            "roas": round(roas, 2),
            "campaign_avg_roas": round(campaign_avg_roas[camp.id], 2),
            "flags": flags,
            "severity": severity,
            "recommendation": recommendation,
        })

    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: (severity_rank[f["severity"]], -f["cost_usd"]))
    return findings
