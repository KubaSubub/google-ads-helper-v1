"""Bidding strategy endpoints — advisor, smart-bidding health, target-vs-actual,
bid-strategy impact + report, learning status, portfolio health, ad-group health."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/bidding-advisor")
def get_bidding_advisor(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Conversion lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Bidding strategy recommendations based on conversion volume."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_bidding_advisor(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/smart-bidding-health")
def get_smart_bidding_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Smart Bidding campaigns conversion volume health check."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_smart_bidding_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/bid-strategy-impact")
def get_bid_strategy_impact(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(90, ge=30, le=180, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Bid strategy change impact — 14-day before/after comparison."""
    service = AnalyticsService(db)
    return service.get_bid_strategy_change_impact(client_id=client_id, days=days)


@router.get("/ad-group-health")
def get_ad_group_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Ad group structural health: ad count, keyword count, zero-conv groups."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_ad_group_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/target-vs-actual")
def get_target_vs_actual(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Compare Smart Bidding targets with actual CPA/ROAS."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_target_vs_actual(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/bid-strategy-report")
def get_bid_strategy_report(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    campaign_id: int = Query(None, description="Filter to specific campaign"),
    db: Session = Depends(get_db),
):
    """Daily time series of target vs actual CPA/ROAS per campaign."""
    service = AnalyticsService(db)
    return service.get_bid_strategy_performance_report(
        client_id=client_id, days=days, campaign_id=campaign_id,
    )


@router.get("/learning-status")
def get_learning_status(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Detect campaigns in Smart Bidding learning period."""
    service = AnalyticsService(db)
    return service.get_learning_status(client_id=client_id)


@router.get("/portfolio-health")
def get_portfolio_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Analyze health of portfolio bid strategies."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_portfolio_strategy_health(
        client_id=client_id, date_from=start, date_to=end,
    )
