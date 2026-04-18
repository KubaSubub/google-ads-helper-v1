"""Landing page diagnostics from locally-stored data.

We don't call PageSpeed Insights or crawl the LP here — that's a future
integration with its own API key and rate limits. What we *can* do:

1. Aggregate keyword performance by `final_url`.
2. Flag LPs where many keywords have landing_page_quality = BELOW_AVERAGE
   (using `historical_landing_page_quality` on Keyword).
3. Flag LPs where the overall conversion rate is materially lower than the
   account average (LP-side problem, not keyword-side).
4. Surface LPs with multiple ad groups pointing at them (brand consolidation /
   message-match mismatch risk).
5. Flag long / noisy tracking templates that might be breaking the redirect chain.

Output: one row per final_url, with enough signal for an operator to prioritise
which pages to hand to the design / UX team.
"""

from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.keyword import Keyword


_QUERY_STRING_RX = re.compile(r"\?.*$")
_TRACKING_PARAM_RX = re.compile(r"\{[^}]+\}")


def _normalise_url(raw: str) -> str:
    """Strip query params — we care about the LP, not the tracking."""
    if not raw:
        return ""
    return _QUERY_STRING_RX.sub("", raw.strip().rstrip("/")).lower()


def _count_tracking_params(raw: str) -> int:
    if not raw:
        return 0
    return len(_TRACKING_PARAM_RX.findall(raw))


def landing_page_report(db: Session, client_id: int) -> list[dict]:
    """Return per-LP aggregate performance + flags, ordered by cost desc."""
    rows = (
        db.query(Keyword, AdGroup, Campaign)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
            Keyword.status == "ENABLED",
            Keyword.final_url.isnot(None),
        )
        .all()
    )
    if not rows:
        return []

    # Aggregate per normalised URL
    groups: dict[str, dict] = defaultdict(lambda: {
        "original_urls": set(),
        "keyword_count": 0,
        "ad_group_ids": set(),
        "campaign_ids": set(),
        "clicks": 0,
        "impressions": 0,
        "cost_micros": 0,
        "conversions": 0.0,
        "conv_value_micros": 0,
        "below_avg_lp_count": 0,
        "above_avg_lp_count": 0,
        "missing_lp_rating": 0,
        "max_tracking_params": 0,
    })
    account_total_cost = 0
    account_total_conv = 0.0

    for kw, ag, camp in rows:
        url = _normalise_url(kw.final_url)
        if not url:
            continue
        g = groups[url]
        g["original_urls"].add(kw.final_url)
        g["keyword_count"] += 1
        g["ad_group_ids"].add(ag.id)
        g["campaign_ids"].add(camp.id)
        g["clicks"] += kw.clicks or 0
        g["impressions"] += kw.impressions or 0
        g["cost_micros"] += kw.cost_micros or 0
        g["conversions"] += float(kw.conversions or 0)
        g["conv_value_micros"] += kw.conversion_value_micros or 0

        lp_rating = kw.historical_landing_page_quality
        if lp_rating is None or lp_rating == 0:
            g["missing_lp_rating"] += 1
        elif lp_rating == 1:
            g["below_avg_lp_count"] += 1
        elif lp_rating == 3:
            g["above_avg_lp_count"] += 1

        g["max_tracking_params"] = max(
            g["max_tracking_params"], _count_tracking_params(kw.final_url or "")
        )

        account_total_cost += kw.cost_micros or 0
        account_total_conv += float(kw.conversions or 0)

    account_cvr = (account_total_conv / (account_total_cost or 1)) if account_total_cost else 0

    out: list[dict] = []
    for url, g in groups.items():
        cost_usd = g["cost_micros"] / 1_000_000
        conv_value_usd = g["conv_value_micros"] / 1_000_000
        cvr = (g["conversions"] / g["clicks"] * 100) if g["clicks"] else 0
        cpa = (cost_usd / g["conversions"]) if g["conversions"] > 0 else None
        roas = (conv_value_usd / cost_usd) if cost_usd else 0

        # Flags
        flags: list[str] = []
        # Flag 1: majority of keywords marked BELOW_AVERAGE for LP experience
        rated_count = g["keyword_count"] - g["missing_lp_rating"]
        if rated_count > 0 and g["below_avg_lp_count"] / rated_count >= 0.5:
            flags.append("LP_EXPERIENCE_BELOW_AVERAGE")
        # Flag 2: CVR materially below account average (only if volume is meaningful)
        if g["clicks"] >= 100 and account_cvr > 0 and (g["conversions"] / g["clicks"]) < account_cvr * 0.5:
            flags.append("CVR_HALF_OF_ACCOUNT_AVG")
        # Flag 3: used by multiple ad groups (message-match risk)
        if len(g["ad_group_ids"]) >= 3:
            flags.append(f"SHARED_BY_{len(g['ad_group_ids'])}_AD_GROUPS")
        # Flag 4: tracking template complexity
        if g["max_tracking_params"] >= 4:
            flags.append(f"TRACKING_TEMPLATE_{g['max_tracking_params']}_PARAMS")

        severity = "LOW"
        if "LP_EXPERIENCE_BELOW_AVERAGE" in flags or "CVR_HALF_OF_ACCOUNT_AVG" in flags:
            severity = "HIGH" if cost_usd >= 100 else "MEDIUM"
        elif flags:
            severity = "LOW"

        out.append({
            "url": url,
            "original_urls_sample": sorted(g["original_urls"])[:3],
            "keyword_count": g["keyword_count"],
            "ad_group_count": len(g["ad_group_ids"]),
            "campaign_count": len(g["campaign_ids"]),
            "clicks": g["clicks"],
            "impressions": g["impressions"],
            "cost_usd": round(cost_usd, 2),
            "conversions": round(g["conversions"], 2),
            "conversion_value_usd": round(conv_value_usd, 2),
            "cvr_pct": round(cvr, 2),
            "cpa_usd": round(cpa, 2) if cpa is not None else None,
            "roas": round(roas, 2),
            "below_average_lp_count": g["below_avg_lp_count"],
            "above_average_lp_count": g["above_avg_lp_count"],
            "missing_lp_rating": g["missing_lp_rating"],
            "flags": flags,
            "severity": severity,
        })

    out.sort(key=lambda r: r["cost_usd"], reverse=True)
    return out
