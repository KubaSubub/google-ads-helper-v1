"""PMax analytics — channel breakdown + trends, asset groups, search themes,
audience performance, extensions, PMax↔Search cannibalization."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/pmax-channels")
def get_pmax_channels(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Show PMax budget distribution across Search, Display, Shopping, Video channels."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_channel_breakdown(
        client_id=client_id, date_from=start, date_to=end,
    )


@router.get("/pmax-channel-trends")
def get_pmax_channel_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Daily PMax cost/conversions per channel for trend charts."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_channel_trends(
        client_id=client_id, date_from=start, date_to=end,
    )


@router.get("/asset-group-performance")
def get_asset_group_performance(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """PMax asset group performance with ad strength and asset breakdown."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_asset_group_performance(
        client_id=client_id, date_from=start, date_to=end,
    )


@router.get("/pmax-search-themes")
def get_pmax_search_themes(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """PMax audience signals and search themes per asset group."""
    service = AnalyticsService(db)
    return service.get_pmax_search_themes(client_id=client_id)


@router.get("/audience-performance")
def get_audience_performance(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Audience segment performance with CPA anomaly flags."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_audience_performance(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/missing-extensions")
def get_missing_extensions(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Per-campaign extension compliance audit — sitelinks, callouts, structured snippets."""
    service = AnalyticsService(db)
    return service.get_missing_extensions_audit(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/extension-performance")
def get_extension_performance(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Extension performance metrics grouped by type and campaign."""
    service = AnalyticsService(db)
    return service.get_extension_performance(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/pmax-search-cannibalization")
def get_pmax_search_cannibalization(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(2, ge=1, description="Min clicks to include"),
    db: Session = Depends(get_db),
):
    """Detect search terms appearing in both PMax and Search campaigns."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_search_cannibalization(
        client_id=client_id, date_from=start, date_to=end,
        min_clicks=min_clicks,
    )
