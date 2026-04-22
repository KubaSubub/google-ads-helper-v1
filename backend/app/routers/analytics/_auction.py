"""Auction Insights — competitor visibility snapshot + rolling-window trend."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Client
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/auction-insights")
def auction_insights(
    client_id: int = Query(...),
    campaign_id: int = Query(None, description="Filter by campaign"),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Auction insights — competitor visibility metrics."""
    from app.models.auction_insight import AuctionInsight

    start, end = resolve_dates(days, date_from, date_to)

    query = (
        db.query(
            AuctionInsight.display_domain,
            func.avg(AuctionInsight.impression_share).label("avg_impression_share"),
            func.avg(AuctionInsight.overlap_rate).label("avg_overlap_rate"),
            func.avg(AuctionInsight.position_above_rate).label("avg_position_above_rate"),
            func.avg(AuctionInsight.outranking_share).label("avg_outranking_share"),
            func.avg(AuctionInsight.top_of_page_rate).label("avg_top_of_page_rate"),
            func.avg(AuctionInsight.abs_top_of_page_rate).label("avg_abs_top_of_page_rate"),
            func.count(AuctionInsight.id).label("data_points"),
        )
        .join(Campaign, AuctionInsight.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            AuctionInsight.date >= start,
            AuctionInsight.date <= end,
        )
    )

    if campaign_id:
        query = query.filter(AuctionInsight.campaign_id == campaign_id)

    results = (
        query
        .group_by(AuctionInsight.display_domain)
        .order_by(func.avg(AuctionInsight.impression_share).desc())
        .all()
    )

    client = db.get(Client, client_id)
    your_domain = None
    if client and client.website:
        your_domain = client.website.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

    competitors = []
    for row in results:
        domain = row.display_domain
        is_self = (your_domain and domain and your_domain in domain) or False
        competitors.append({
            "display_domain": domain,
            "is_self": is_self,
            "impression_share": round((row.avg_impression_share or 0) * 100, 1),
            "overlap_rate": round((row.avg_overlap_rate or 0) * 100, 1),
            "position_above_rate": round((row.avg_position_above_rate or 0) * 100, 1),
            "outranking_share": round((row.avg_outranking_share or 0) * 100, 1),
            "top_of_page_rate": round((row.avg_top_of_page_rate or 0) * 100, 1),
            "abs_top_of_page_rate": round((row.avg_abs_top_of_page_rate or 0) * 100, 1),
            "data_points": row.data_points,
        })

    trend_query = (
        db.query(
            AuctionInsight.date,
            AuctionInsight.display_domain,
            func.avg(AuctionInsight.impression_share).label("impression_share"),
            func.avg(AuctionInsight.outranking_share).label("outranking_share"),
        )
        .join(Campaign, AuctionInsight.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            AuctionInsight.date >= start,
            AuctionInsight.date <= end,
        )
    )
    if campaign_id:
        trend_query = trend_query.filter(AuctionInsight.campaign_id == campaign_id)

    top_domains = [c["display_domain"] for c in competitors[:5]]
    trend_rows = (
        trend_query
        .filter(AuctionInsight.display_domain.in_(top_domains))
        .group_by(AuctionInsight.date, AuctionInsight.display_domain)
        .order_by(AuctionInsight.date)
        .all()
    )

    trends = {}
    for row in trend_rows:
        domain = row.display_domain
        if domain not in trends:
            trends[domain] = []
        trends[domain].append({
            "date": str(row.date),
            "impression_share": round((row.impression_share or 0) * 100, 1),
            "outranking_share": round((row.outranking_share or 0) * 100, 1),
        })

    return {
        "competitors": competitors,
        "trends": trends,
        "period": {"from": str(start), "to": str(end)},
        "total_competitors": len(competitors),
    }


@router.get("/auction-insights-trend")
def auction_insights_trend(
    client_id: int = Query(...),
    window_days: int = Query(14, ge=7, le=60, description="Length of the current window; previous window has the same length"),
    min_outranking_delta_pp: float = Query(
        0.0,
        description="Filter to competitors whose outranking_share delta >= this many percentage points",
    ),
    trend_label: str = Query(
        "ALL",
        description="Filter by trend_label: RISING_FAST, RISING, STABLE, FALLING, FALLING_FAST, ALL",
    ),
    db: Session = Depends(get_db),
):
    """Per-competitor Auction Insights trend over a rolling window."""
    from app.services.auction_insights_trend_service import compute_trends

    items = compute_trends(db, client_id, window_days=window_days)
    if trend_label != "ALL":
        items = [i for i in items if i["trend_label"] == trend_label.upper()]
    items = [i for i in items if i["outranking_share_delta_pp"] >= min_outranking_delta_pp]

    return {
        "window_days": window_days,
        "total": len(items),
        "items": items,
    }
