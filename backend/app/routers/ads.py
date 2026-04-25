"""Ad detail endpoint — pelny RSA breakdown + comparison vs ad group averages."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ad, AdGroup

router = APIRouter(prefix="/ads", tags=["Ads"])


def _normalize_asset(entry):
    """Normalize a headlines/descriptions entry to {text, pinned_position, performance_label}."""
    if entry is None:
        return None
    if isinstance(entry, dict):
        return {
            "text": entry.get("text"),
            "pinned_position": entry.get("pinned_position"),
            "performance_label": entry.get("performance_label"),
        }
    return {"text": str(entry), "pinned_position": None, "performance_label": None}


@router.get("/{ad_id}")
def get_ad_detail(ad_id: int, db: Session = Depends(get_db)):
    """Get full ad detail with RSA assets breakdown + ad group averages for comparison.

    Returns:
        - ad: full ad metadata + headlines/descriptions with pinned_position + performance_label
        - ad_group: minimal context (id, name, campaign_id)
        - comparison: avg metrics for sibling ads in same group + diff_pct vs this ad
    """
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    ad_group = db.get(AdGroup, ad.ad_group_id)
    if not ad_group:
        raise HTTPException(status_code=404, detail="Ad group not found")

    # Sibling ads (excluding this one)
    siblings = (
        db.query(Ad)
        .filter(Ad.ad_group_id == ad.ad_group_id, Ad.id != ad.id)
        .all()
    )

    def _avg(values):
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 2) if valid else 0

    cost = (ad.cost_micros or 0) / 1_000_000
    cpa = round(cost / ad.conversions, 2) if ad.conversions else 0

    if siblings:
        sib_clicks = _avg([s.clicks or 0 for s in siblings])
        sib_impr = _avg([s.impressions or 0 for s in siblings])
        sib_cost = _avg([(s.cost_micros or 0) / 1_000_000 for s in siblings])
        sib_conv = _avg([s.conversions or 0 for s in siblings])
        sib_ctr = _avg([s.ctr or 0 for s in siblings])
        sib_cpa = _avg([
            ((s.cost_micros or 0) / 1_000_000) / s.conversions if s.conversions else 0
            for s in siblings
        ])
    else:
        sib_clicks = sib_impr = sib_cost = sib_conv = sib_ctr = sib_cpa = 0

    def _diff_pct(this_val, avg_val):
        if avg_val == 0:
            return None
        return round((this_val - avg_val) / avg_val * 100, 1)

    return {
        "ad": {
            "id": ad.id,
            "google_ad_id": ad.google_ad_id,
            "ad_group_id": ad.ad_group_id,
            "ad_type": ad.ad_type,
            "status": ad.status,
            "approval_status": ad.approval_status,
            "ad_strength": ad.ad_strength,
            "final_url": ad.final_url,
            "long_headline": ad.long_headline,
            "business_name": ad.business_name,
            "headlines": [_normalize_asset(h) for h in (ad.headlines or [])],
            "descriptions": [_normalize_asset(d) for d in (ad.descriptions or [])],
            "headlines_count": len(ad.headlines or []),
            "descriptions_count": len(ad.descriptions or []),
            "clicks": ad.clicks or 0,
            "impressions": ad.impressions or 0,
            "cost": round(cost, 2),
            "conversions": round(ad.conversions or 0.0, 2),
            "ctr": round(ad.ctr or 0.0, 2),
            "cpa": cpa,
        },
        "ad_group": {
            "id": ad_group.id,
            "name": ad_group.name,
            "campaign_id": ad_group.campaign_id,
        },
        "comparison": {
            "siblings_count": len(siblings),
            "avg": {
                "clicks": sib_clicks,
                "impressions": sib_impr,
                "cost": sib_cost,
                "conversions": sib_conv,
                "ctr": sib_ctr,
                "cpa": sib_cpa,
            },
            "diff_pct": {
                "clicks": _diff_pct(ad.clicks or 0, sib_clicks),
                "impressions": _diff_pct(ad.impressions or 0, sib_impr),
                "cost": _diff_pct(cost, sib_cost),
                "conversions": _diff_pct(ad.conversions or 0, sib_conv),
                "ctr": _diff_pct(ad.ctr or 0, sib_ctr),
                "cpa": _diff_pct(cpa, sib_cpa),
            },
        },
    }
