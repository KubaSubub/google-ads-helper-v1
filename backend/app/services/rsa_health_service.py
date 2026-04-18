"""RSA (Responsive Search Ad) health report.

Aggregates per-ad-group RSA state from the local cache — doesn't need a new
Google Ads API sync. Uses what we already store: `Ad.ad_strength`, `Ad.headlines`,
`Ad.descriptions`, and the ad's own performance metrics.

Output per ad group (SEARCH campaigns only):
    - RSA count, count by ad_strength, weakest ad
    - Total headlines / descriptions across all RSAs (signals asset diversity)
    - Whether the ad group has at least one EXCELLENT/GOOD RSA
    - Flag for "single-RSA ad group" (no A/B testing happening)
    - Recommendation text keyed by state

A full asset-level report (per-headline CTR, per-asset performance label) needs
`ad_group_ad_asset_view` which this service does NOT sync — leave that for a
later sync pass.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign


_STRENGTH_ORDER = {
    "EXCELLENT": 5,
    "GOOD": 4,
    "AVERAGE": 3,
    "POOR": 2,
    "UNRATED": 1,
    None: 0,
}


def _headline_count(ad: Ad) -> int:
    return len(ad.headlines) if ad.headlines else 0


def _description_count(ad: Ad) -> int:
    return len(ad.descriptions) if ad.descriptions else 0


def ad_group_rsa_report(db: Session, client_id: int) -> list[dict]:
    """Return one row per SEARCH ad group summarising its RSA state."""
    rows = (
        db.query(Ad, AdGroup, Campaign)
        .join(AdGroup, Ad.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
            Ad.status == "ENABLED",
        )
        .all()
    )
    if not rows:
        return []

    # group by ad_group
    groups: dict[int, dict] = {}
    for ad, ag, camp in rows:
        g = groups.setdefault(ag.id, {
            "ad_group_id": ag.id,
            "ad_group_name": ag.name,
            "campaign_id": camp.id,
            "campaign_name": camp.name,
            "ads": [],
        })
        g["ads"].append(ad)

    out: list[dict] = []
    for g in groups.values():
        ads = g["ads"]
        strengths = [a.ad_strength for a in ads]
        strength_counts = dict(Counter(strengths))
        max_strength_order = max((_STRENGTH_ORDER.get(s, 0) for s in strengths), default=0)
        has_good_or_better = max_strength_order >= _STRENGTH_ORDER["GOOD"]
        weakest_idx = min(
            range(len(ads)),
            key=lambda i: _STRENGTH_ORDER.get(ads[i].ad_strength, 0),
        )
        weakest = ads[weakest_idx]

        total_headlines = sum(_headline_count(a) for a in ads)
        total_descriptions = sum(_description_count(a) for a in ads)
        single_rsa = len(ads) == 1

        # Recommendation logic — cascades from worst problem to lightest.
        if single_rsa:
            severity = "MEDIUM"
            recommendation = (
                "Tylko 1 RSA w ad group — brak A/B testu. Dodaj co najmniej jedną "
                "drugą RSA z innymi headline'ami, żeby Google mógł porównać."
            )
        elif not has_good_or_better:
            severity = "HIGH"
            recommendation = (
                "Żaden RSA w tym ad group nie ma ad_strength >= GOOD. Uzupełnij "
                "brakujące headline'y/descriptions w najsłabszym RSA — zwykle "
                "potrzeba 10+ headlines i 4 descriptions."
            )
        elif any(a.ad_strength == "POOR" for a in ads):
            severity = "MEDIUM"
            recommendation = (
                "Jeden z RSA ma ad_strength POOR. Dodaj brakujące assety albo "
                "zastąp ten RSA nową wersją."
            )
        elif total_headlines < len(ads) * 8:  # heuristic — RSAs often underfilled
            severity = "LOW"
            recommendation = (
                "Średnia liczba headlines na RSA poniżej 8. Google rekomenduje 10+ "
                "dla pełnego pokrycia."
            )
        else:
            severity = "OK"
            recommendation = "Ad group wygląda zdrowo — RSAs rotują i mają wystarczająco assetów."

        out.append({
            "ad_group_id": g["ad_group_id"],
            "ad_group_name": g["ad_group_name"],
            "campaign_id": g["campaign_id"],
            "campaign_name": g["campaign_name"],
            "rsa_count": len(ads),
            "single_rsa": single_rsa,
            "strength_distribution": strength_counts,
            "has_good_or_better": has_good_or_better,
            "weakest_ad_id": weakest.id,
            "weakest_ad_strength": weakest.ad_strength,
            "weakest_ad_headlines": _headline_count(weakest),
            "weakest_ad_descriptions": _description_count(weakest),
            "total_headlines": total_headlines,
            "total_descriptions": total_descriptions,
            "avg_headlines_per_rsa": round(total_headlines / len(ads), 1),
            "avg_descriptions_per_rsa": round(total_descriptions / len(ads), 1),
            "severity": severity,
            "recommendation": recommendation,
        })

    # Sort by severity (HIGH > MEDIUM > LOW > OK) then by RSA count asc.
    severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "OK": 0}
    out.sort(key=lambda r: (-severity_rank.get(r["severity"], 0), r["rsa_count"]))
    return out
