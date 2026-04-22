"""Budget pacing + dayparting suite — day-of-week, hourly, DOW×HOUR heatmap,
YoY/seasonal, offline conversion lag."""

import calendar
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, MetricDaily
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates
from app.utils.formatters import micros_to_currency

router = APIRouter()


@router.get("/budget-pacing")
def get_budget_pacing(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Filter by campaign status"),
    db: Session = Depends(get_db),
):
    """Budget pacing for all campaigns: actual vs expected spend this month.

    Returns per-campaign pacing status (on_track / underspend / overspend)
    and a projected month-end spend.
    """
    today = date.today()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    pacing_ratio = days_elapsed / days_in_month

    campaign_q = db.query(Campaign).filter(Campaign.client_id == client_id)
    if campaign_type and campaign_type != "ALL":
        campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
    if campaign_status and campaign_status != "ALL":
        campaign_q = campaign_q.filter(Campaign.status == campaign_status)
    else:
        campaign_q = campaign_q.filter(Campaign.status == "ENABLED")
    campaigns = campaign_q.all()

    results = []
    for camp in campaigns:
        budget_monthly = micros_to_currency(camp.budget_micros) * days_in_month

        actual_spend_micros = (
            db.query(func.sum(MetricDaily.cost_micros))
            .filter(
                MetricDaily.campaign_id == camp.id,
                MetricDaily.date >= month_start,
                MetricDaily.date <= today,
            )
            .scalar()
        ) or 0
        actual_spend = micros_to_currency(actual_spend_micros)

        expected_spend = budget_monthly * pacing_ratio
        projected_spend = (actual_spend / pacing_ratio) if pacing_ratio > 0 else 0

        if expected_spend == 0:
            status = "no_data"
            pct = 0
        else:
            pct = actual_spend / expected_spend
            if pct < 0.8:
                status = "underspend"
            elif pct > 1.15:
                status = "overspend"
            else:
                status = "on_track"

        results.append({
            "campaign_id": camp.id,
            "campaign_name": camp.name,
            "daily_budget_usd": round(micros_to_currency(camp.budget_micros), 2),
            "monthly_budget_usd": round(budget_monthly, 2),
            "actual_spend_usd": round(actual_spend, 2),
            "expected_spend_usd": round(expected_spend, 2),
            "projected_spend_usd": round(projected_spend, 2),
            "pacing_pct": round(pct * 100, 1),
            "status": status,
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        })

    return {
        "month": today.strftime("%Y-%m"),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "campaigns": results,
    }


@router.get("/dayparting")
def get_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Campaign performance by day of week."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_dayparting(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/hourly-dayparting")
def get_hourly_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Campaign performance by hour of day."""
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_hourly_dayparting(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/dayparting-hourly-suggestions")
def dayparting_hourly_suggestions(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90),
    include_suggestions: bool = Query(True, description="Include bid-schedule suggestions"),
    min_hour_cost_usd: float = Query(20.0, ge=0.0, description="Minimum spend per hour to warrant a suggestion"),
    db: Session = Depends(get_db),
):
    """Hour-of-day performance heatmap + bid-schedule recommendations."""
    from app.services.dayparting_service import (
        bid_schedule_suggestions,
        hourly_breakdown,
    )

    result = hourly_breakdown(db, client_id, days)
    if include_suggestions:
        result["suggestions"] = bid_schedule_suggestions(
            db, client_id, days=days, min_cost_usd=min_hour_cost_usd
        )
    return result


@router.get("/dayparting-dow-suggestions")
def dayparting_dow_suggestions(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=14, le=90, description="Lookback (>=14 to capture 2 weekly cycles)"),
    min_dow_cost: float = Query(50.0, ge=0.0, description="Minimum spend per day-of-week to warrant a suggestion"),
    db: Session = Depends(get_db),
):
    """Day-of-week performance + bid-schedule recommendations."""
    from app.services.dayparting_service import dow_bid_schedule_suggestions

    return dow_bid_schedule_suggestions(db, client_id, days=days, min_cost=min_dow_cost)


@router.get("/dayparting-heatmap")
def dayparting_heatmap(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=14, le=90),
    db: Session = Depends(get_db),
):
    """7×24 grid of (day_of_week × hour_of_day) performance for bid-schedule UI."""
    from app.services.dayparting_service import dow_hour_heatmap

    return dow_hour_heatmap(db, client_id, days=days)


@router.get("/offline-conversion-lag")
def offline_conversion_lag_endpoint(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Health + lag stats for offline conversion uploads."""
    from app.services.offline_conversion_lag_service import offline_conversion_lag
    return offline_conversion_lag(db, client_id)


@router.get("/seasonal-comparison")
def seasonal_comparison(
    client_id: int = Query(..., description="Client ID"),
    date_from: date = Query(..., description="Current window start"),
    date_to: date = Query(..., description="Current window end"),
    comparison_type: str = Query(
        "year_over_year",
        description="year_over_year or rolling (uses months offset)",
    ),
    months_offset: int = Query(3, ge=1, le=24, description="Months offset for rolling comparison"),
    db: Session = Depends(get_db),
):
    """Compare current window against same window last year (default) or N months ago."""
    from app.services.seasonal_comparison_service import (
        rolling_comparison,
        yoy_comparison,
    )

    if comparison_type == "rolling":
        return rolling_comparison(db, client_id, date_from, date_to, months=months_offset)
    return yoy_comparison(db, client_id, date_from, date_to)
