"""Audience overlap / redundancy detection.

Google Ads doesn't expose per-user audience membership in API responses, so
*true* overlap (share of users in audience A who are also in audience B) is not
computable locally. This service instead flags **likely redundancy** using the
signals we do have:

1. **Same audience_type stacked in same campaign**
   — e.g. two IN_MARKET audiences both active on the same campaign usually means
     the team added them in different sessions and neither got removed.
2. **Name similarity within same type**
   — "Men 25-54 interested in running" vs "Running enthusiasts 25-54" = likely
     duplicative custom-intent audiences.
3. **Similar performance profile**
   — CVR within ±20% and CPA within ±20% over the same window is suspicious;
     if two audiences perform identically, one probably shadows the other.

Output is a list of audience-pair suggestions with a `reason` field explaining
the signal. It is intentionally a *review queue*, not an auto-apply feed.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.campaign_audience import CampaignAudienceMetric


def _token_jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two strings' lowercased word sets. 0-1."""
    ta = set((a or "").lower().split())
    tb = set((b or "").lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _safe_ratio(numer: float, denom: float) -> float:
    return (numer / denom) if denom else 0.0


def detect_audience_redundancy(
    db: Session, client_id: int, window_days: int = 30
) -> list[dict]:
    """Return likely-redundant audience pairs per campaign, highest-priority first."""
    cutoff = date.today() - timedelta(days=window_days)

    rows = (
        db.query(
            CampaignAudienceMetric,
            Campaign.name.label("campaign_name"),
            Campaign.campaign_type.label("campaign_type"),
        )
        .join(Campaign, CampaignAudienceMetric.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            CampaignAudienceMetric.date >= cutoff,
        )
        .all()
    )
    if not rows:
        return []

    # Aggregate per (campaign_id, audience_resource_name) across the window.
    agg: dict[tuple[int, str], dict] = defaultdict(
        lambda: {
            "clicks": 0, "impressions": 0, "conversions": 0.0,
            "cost_micros": 0, "conv_value_micros": 0,
            "name": None, "type": None, "campaign_name": None, "campaign_type": None,
        }
    )
    for metric, camp_name, camp_type in rows:
        key = (metric.campaign_id, metric.audience_resource_name)
        bucket = agg[key]
        bucket["clicks"] += metric.clicks or 0
        bucket["impressions"] += metric.impressions or 0
        bucket["conversions"] += float(metric.conversions or 0)
        bucket["cost_micros"] += metric.cost_micros or 0
        bucket["conv_value_micros"] += metric.conversion_value_micros or 0
        bucket["name"] = bucket["name"] or metric.audience_name
        bucket["type"] = bucket["type"] or metric.audience_type
        bucket["campaign_name"] = camp_name
        bucket["campaign_type"] = camp_type

    # Build per-campaign audience list.
    by_campaign: dict[int, list[dict]] = defaultdict(list)
    for (campaign_id, resource_name), data in agg.items():
        cost_usd = data["cost_micros"] / 1_000_000
        conv_value_usd = data["conv_value_micros"] / 1_000_000
        cvr = _safe_ratio(data["conversions"], data["clicks"]) * 100
        cpa = _safe_ratio(cost_usd, data["conversions"])
        roas = _safe_ratio(conv_value_usd, cost_usd)
        by_campaign[campaign_id].append({
            "campaign_id": campaign_id,
            "campaign_name": data["campaign_name"],
            "campaign_type": data["campaign_type"],
            "audience_resource_name": resource_name,
            "audience_name": data["name"],
            "audience_type": data["type"],
            "clicks": data["clicks"],
            "impressions": data["impressions"],
            "conversions": round(data["conversions"], 2),
            "cost_usd": round(cost_usd, 2),
            "cvr_pct": round(cvr, 2),
            "cpa_usd": round(cpa, 2),
            "roas": round(roas, 2),
        })

    findings: list[dict] = []
    for campaign_id, audiences in by_campaign.items():
        if len(audiences) < 2:
            continue
        for i in range(len(audiences)):
            for j in range(i + 1, len(audiences)):
                a, b = audiences[i], audiences[j]

                reasons: list[str] = []
                # Signal 1: same audience_type
                if a["audience_type"] and a["audience_type"] == b["audience_type"]:
                    reasons.append(f"Ten sam typ: {a['audience_type']}")

                # Signal 2: name similarity
                jaccard = _token_jaccard(a["audience_name"] or "", b["audience_name"] or "")
                if jaccard >= 0.4:
                    reasons.append(f"Podobne nazwy (Jaccard {jaccard:.2f})")

                # Signal 3: similar performance profile (both must have data)
                if a["clicks"] >= 50 and b["clicks"] >= 50:
                    cvr_close = abs(a["cvr_pct"] - b["cvr_pct"]) <= max(a["cvr_pct"], b["cvr_pct"]) * 0.2
                    cpa_close = (
                        abs(a["cpa_usd"] - b["cpa_usd"])
                        <= max(a["cpa_usd"], b["cpa_usd"], 1.0) * 0.2
                    )
                    if cvr_close and cpa_close:
                        reasons.append("CVR i CPA w obrębie 20%")

                # Need at least two signals to reduce false positives.
                if len(reasons) < 2:
                    continue

                severity = "HIGH" if len(reasons) == 3 else "MEDIUM"
                combined_cost = a["cost_usd"] + b["cost_usd"]
                findings.append({
                    "severity": severity,
                    "campaign_id": campaign_id,
                    "campaign_name": a["campaign_name"],
                    "campaign_type": a["campaign_type"],
                    "audience_a": a,
                    "audience_b": b,
                    "signals": reasons,
                    "combined_cost_usd": round(combined_cost, 2),
                    "recommendation": (
                        "Przejrzyj obie audiences — jeśli to ta sama grupa klientów "
                        "pod dwiema etykietami, zostaw jedną i zaoszczędź budżet na testach."
                    ),
                })

    findings.sort(
        key=lambda f: ({"HIGH": 0, "MEDIUM": 1}.get(f["severity"], 9), -f["combined_cost_usd"])
    )
    return findings
