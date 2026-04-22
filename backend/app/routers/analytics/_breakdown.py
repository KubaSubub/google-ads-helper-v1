"""Segment breakdowns — device, geo, demographics, impression share."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.analytics._legacy import TREND_METRICS
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/impression-share")
def get_impression_share(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Daily impression share trends for SEARCH campaigns."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_impression_share_trends(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


@router.get("/device-breakdown")
def get_device_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by device (Mobile/Desktop/Tablet)."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_device_breakdown(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


@router.get("/geo-breakdown")
def get_geo_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    limit: int = Query(20, ge=1, le=50, description="Max cities"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by city/geography."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_geo_breakdown(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id, limit=limit,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


@router.get("/trends-by-device")
def get_trends_by_device(
    client_id: int = Query(..., description="Client ID"),
    metric: str = Query("clicks", description="Single metric to split by device"),
    days: int = Query(30, ge=7, le=365),
    date_from: date = Query(None),
    date_to: date = Query(None),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    campaign_ids: str = Query(None, description="Comma-separated campaign IDs"),
    db: Session = Depends(get_db),
):
    """Daily time-series for a single metric, split across device segments."""
    start, end = resolve_dates(days, date_from, date_to)
    max_span = timedelta(days=365)
    if end - start > max_span:
        start = end - max_span

    if metric not in TREND_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    id_filter: list[int] | None = None
    if campaign_ids:
        try:
            id_filter = [int(x) for x in campaign_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    service = AnalyticsService(db)
    return service.get_trends_by_device(
        client_id=client_id,
        metric=metric,
        date_from=start,
        date_to=end,
        campaign_ids=id_filter,
        campaign_type=campaign_type,
        campaign_status=campaign_status,
    )


@router.get("/demographics")
def get_demographics(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Aggregate metrics by age range and gender, flag CPA anomalies."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_demographic_breakdown(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )
