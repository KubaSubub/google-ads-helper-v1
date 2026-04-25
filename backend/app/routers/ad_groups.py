"""Ad Groups endpoints — list and aggregated metrics per ad group."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ad, AdGroup, Campaign, Keyword, KeywordDaily

router = APIRouter(prefix="/ad_groups", tags=["Ad Groups"])


@router.get("/")
def list_ad_groups(
    campaign_id: int = Query(..., description="Filter by campaign"),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """List ad groups for a campaign with aggregated KPI over date range.

    Aggregation source: KeywordDaily (keyword_id -> keyword.ad_group_id).
    Metrics aggregated per ad_group: clicks, impressions, cost_micros, conversions, conversion_value_micros.
    Derived: CTR, CPC, CPA, ROAS, conversion_rate.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to - timedelta(days=30)

    ad_groups = (
        db.query(AdGroup)
        .filter(AdGroup.campaign_id == campaign_id)
        .order_by(AdGroup.name)
        .all()
    )

    # Aggregate KeywordDaily joined via Keyword to ad_group_id.
    agg_rows = (
        db.query(
            Keyword.ad_group_id.label("ad_group_id"),
            func.coalesce(func.sum(KeywordDaily.clicks), 0).label("clicks"),
            func.coalesce(func.sum(KeywordDaily.impressions), 0).label("impressions"),
            func.coalesce(func.sum(KeywordDaily.cost_micros), 0).label("cost_micros"),
            func.coalesce(func.sum(KeywordDaily.conversions), 0.0).label("conversions"),
            func.coalesce(func.sum(KeywordDaily.conversion_value_micros), 0).label("conversion_value_micros"),
        )
        .join(Keyword, Keyword.id == KeywordDaily.keyword_id)
        .join(AdGroup, AdGroup.id == Keyword.ad_group_id)
        .filter(AdGroup.campaign_id == campaign_id)
        .filter(KeywordDaily.date >= date_from)
        .filter(KeywordDaily.date <= date_to)
        .group_by(Keyword.ad_group_id)
        .all()
    )
    metrics_map = {row.ad_group_id: row for row in agg_rows}

    items = []
    for ag in ad_groups:
        m = metrics_map.get(ag.id)
        clicks = int(m.clicks) if m else 0
        impressions = int(m.impressions) if m else 0
        cost_micros = int(m.cost_micros) if m else 0
        conversions = float(m.conversions) if m else 0.0
        conv_value_micros = int(m.conversion_value_micros) if m else 0

        cost = cost_micros / 1_000_000
        conv_value = conv_value_micros / 1_000_000

        items.append({
            "id": ag.id,
            "google_ad_group_id": ag.google_ad_group_id,
            "name": ag.name,
            "status": ag.status,
            "bid_micros": ag.bid_micros,
            "clicks": clicks,
            "impressions": impressions,
            "cost": round(cost, 2),
            "conversions": round(conversions, 2),
            "conversion_value": round(conv_value, 2),
            "ctr": round((clicks / impressions * 100) if impressions else 0, 2),
            "cpc": round((cost / clicks) if clicks else 0, 2),
            "cpa": round((cost / conversions) if conversions else 0, 2),
            "roas": round((conv_value / cost) if cost else 0, 2),
            "conversion_rate": round((conversions / clicks * 100) if clicks else 0, 2),
        })

    return {
        "campaign_id": campaign_id,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "total": len(items),
        "items": items,
    }


def _headline_text(headline_entry) -> str | None:
    """Extract text from a headline entry (string or dict with 'text' key)."""
    if not headline_entry:
        return None
    if isinstance(headline_entry, dict):
        return headline_entry.get("text")
    return str(headline_entry)


@router.get("/{ad_group_id}/ads")
def list_ads_in_group(
    ad_group_id: int,
    db: Session = Depends(get_db),
):
    """List ads in a single ad group with snapshot metrics + RSA preview.

    Returns ad_type, status, ad_strength, approval_status, headline_1/2 (RSA preview),
    final_url, and snapshot metrics (clicks, impressions, cost, conversions, CTR).
    """
    ad_group = db.query(AdGroup).filter(AdGroup.id == ad_group_id).first()
    if not ad_group:
        raise HTTPException(status_code=404, detail="Ad group not found")

    ads = (
        db.query(Ad)
        .filter(Ad.ad_group_id == ad_group_id)
        .order_by(Ad.clicks.desc().nullslast(), Ad.id)
        .all()
    )

    items = []
    for ad in ads:
        cost = (ad.cost_micros or 0) / 1_000_000
        items.append({
            "id": ad.id,
            "google_ad_id": ad.google_ad_id,
            "ad_type": ad.ad_type,
            "status": ad.status,
            "approval_status": ad.approval_status,
            "ad_strength": ad.ad_strength,
            "final_url": ad.final_url,
            "headline_1": _headline_text(ad.headlines[0] if ad.headlines else None),
            "headline_2": _headline_text(ad.headlines[1] if ad.headlines and len(ad.headlines) > 1 else None),
            "headlines_count": len(ad.headlines or []),
            "descriptions_count": len(ad.descriptions or []),
            "clicks": ad.clicks or 0,
            "impressions": ad.impressions or 0,
            "cost": round(cost, 2),
            "conversions": round(ad.conversions or 0.0, 2),
            "ctr": round(ad.ctr or 0.0, 2),
        })

    return {
        "ad_group_id": ad_group_id,
        "ad_group_name": ad_group.name,
        "campaign_id": ad_group.campaign_id,
        "total": len(items),
        "items": items,
    }
