"""Wasted spend, account structure, search-term trends, close variants, keyword
expansion, keyword overlap, budget allocation."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/wasted-spend")
def get_wasted_spend(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Total wasted spend on keywords, search terms, and ads with 0 conversions.
    Includes period-over-period change for dashboard KPI card."""
    start, end = resolve_dates(days, date_from, date_to)
    period_len = (end - start).days
    prev_start = start - timedelta(days=period_len)
    prev_end = start - timedelta(days=1)

    service = AnalyticsService(db)
    current = service.get_wasted_spend(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )
    previous = service.get_wasted_spend(
        client_id=client_id, date_from=prev_start, date_to=prev_end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )

    prev_waste = previous.get("total_waste_usd", 0)
    cur_waste = current.get("total_waste_usd", 0)
    if prev_waste == 0:
        change_pct = 100.0 if cur_waste > 0 else 0.0
    else:
        change_pct = round((cur_waste - prev_waste) / prev_waste * 100, 1)

    current["previous_waste_usd"] = prev_waste
    current["waste_change_pct"] = change_pct
    return current


@router.get("/account-structure")
def get_account_structure(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Account structure audit: oversized ad groups, match type mixing, keyword cannibalization."""
    service = AnalyticsService(db)
    return service.get_account_structure_audit(client_id)


@router.get("/search-term-trends")
def get_search_term_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(5, ge=1, description="Min clicks to include"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Search term trend analysis: rising, declining, and new terms."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_search_term_trends(
        client_id=client_id, date_from=start, date_to=end, min_clicks=min_clicks,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/close-variants")
def get_close_variants(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Close variant analysis: search terms vs exact keywords."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_close_variant_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/keyword-expansion")
def get_keyword_expansion(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(3, ge=1, description="Min clicks for suggestion"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword expansion suggestions from high-performing search terms."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_keyword_expansion(
        client_id=client_id, date_from=start, date_to=end, min_clicks=min_clicks,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/keyword-overlap")
def get_keyword_overlap(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Find keywords that appear in multiple campaigns (same text)."""
    service = AnalyticsService(db)
    return service.get_keyword_overlap(client_id)


@router.get("/budget-allocation")
def get_budget_allocation(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Compare CPA/ROAS across campaigns and suggest budget reallocation."""
    service = AnalyticsService(db)
    return service.get_budget_allocation(
        client_id=client_id, days=days, date_from=date_from, date_to=date_to,
    )
