"""Campaign endpoints — list, detail, metrics."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.database import get_db
from app.models import Campaign, MetricDaily, AdGroup
from app.schemas import CampaignResponse, MetricDailyResponse, PaginatedResponse

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("/", response_model=PaginatedResponse)
def list_campaigns(
    client_id: int = Query(..., description="Filter by client ID"),
    status: str = Query(None, description="Filter by status: ENABLED, PAUSED, REMOVED"),
    campaign_type: str = Query(None, description="Filter by type: SEARCH, DISPLAY, etc."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List campaigns for a client with filtering and pagination."""
    query = db.query(Campaign).filter(Campaign.client_id == client_id)

    if status:
        query = query.filter(Campaign.status == status.upper())
    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type.upper())

    total = query.count()
    items = query.order_by(Campaign.name).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[CampaignResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a single campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/metrics", response_model=list[MetricDailyResponse])
def get_campaign_metrics(
    campaign_id: int,
    date_from: date = Query(None, description="Start date (default: 30 days ago)"),
    date_to: date = Query(None, description="End date (default: today)"),
    db: Session = Depends(get_db),
):
    """Get daily metrics for a campaign within a date range."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    metrics = (
        db.query(MetricDaily)
        .filter(
            MetricDaily.campaign_id == campaign_id,
            MetricDaily.date >= date_from,
            MetricDaily.date <= date_to,
        )
        .order_by(MetricDaily.date)
        .all()
    )
    return metrics


@router.get("/{campaign_id}/kpis")
def get_campaign_kpis(
    campaign_id: int,
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """
    Get aggregated KPIs for a campaign for the current period vs the previous period.
    Returns: current values, previous values, and percentage change.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    today = date.today()
    current_start = today - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    def _aggregate(start: date, end: date) -> dict:
        metrics = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id == campaign_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        if not metrics:
            return {"clicks": 0, "impressions": 0, "cost": 0, "conversions": 0, "ctr": 0, "roas": 0}

        total_clicks = sum(m.clicks or 0 for m in metrics)
        total_impressions = sum(m.impressions or 0 for m in metrics)
        total_cost_micros = sum(m.cost_micros or 0 for m in metrics)
        total_conversions = sum(m.conversions or 0 for m in metrics)
        total_cost_usd = total_cost_micros / 1_000_000

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost": round(total_cost_usd, 2),
            "conversions": total_conversions,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": round((total_conversions / total_cost_usd) if total_cost_usd else 0, 2),
        }

    current = _aggregate(current_start, today)
    previous = _aggregate(previous_start, current_start - timedelta(days=1))

    def _pct_change(curr, prev):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round((curr - prev) / prev * 100, 1)

    change = {k: _pct_change(current[k], previous[k]) for k in current}

    return {
        "current": current,
        "previous": previous,
        "change_pct": change,
        "period_days": days,
    }
