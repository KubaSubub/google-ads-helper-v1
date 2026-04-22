"""Campaign + client comparison, industry benchmarks."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/campaign-comparison")
def get_campaign_comparison(
    client_id: int = Query(..., description="Client ID"),
    campaign_ids: str = Query(..., description="Comma-separated campaign IDs (e.g. 1,2,3)"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of selected campaigns."""
    try:
        ids = [int(x.strip()) for x in campaign_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    if not ids:
        raise HTTPException(status_code=400, detail="At least one campaign_id is required")
    if len(ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 campaigns for comparison")

    service = AnalyticsService(db)
    return service.get_campaign_comparison(
        client_id=client_id,
        campaign_ids=ids,
        days=days,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/benchmarks")
def get_benchmarks(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Compare client metrics against industry benchmarks."""
    service = AnalyticsService(db)
    return service.get_benchmarks(client_id=client_id, days=days)


@router.get("/client-comparison")
def get_client_comparison(
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """MCC view: compare ALL clients' KPIs side-by-side."""
    service = AnalyticsService(db)
    return service.get_client_comparison(days=days)
