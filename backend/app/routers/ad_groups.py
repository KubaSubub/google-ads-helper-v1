"""Ad Groups endpoints — list and aggregated metrics per ad group."""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdGroup, Campaign, Keyword, KeywordDaily

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
