"""DSA (Dynamic Search Ads) endpoints — targets, coverage, headlines, overlap."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/dsa-targets")
def get_dsa_targets(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """List DSA targets with performance metrics."""
    service = AnalyticsService(db)
    return service.get_dsa_targets(
        client_id,
        campaign_type=campaign_type,
        campaign_status=campaign_status,
    )


@router.get("/dsa-coverage")
def get_dsa_coverage(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """DSA coverage: which campaigns are DSA, target counts."""
    service = AnalyticsService(db)
    return service.get_dsa_coverage(client_id)


@router.get("/dsa-headlines")
def get_dsa_headlines(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """List DSA auto-generated headlines with performance metrics."""
    service = AnalyticsService(db)
    return service.get_dsa_headlines(
        client_id,
        days=days,
        date_from=date_from,
        date_to=date_to,
        campaign_type=campaign_type,
        campaign_status=campaign_status,
    )


@router.get("/dsa-search-overlap")
def get_dsa_search_overlap(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Find search terms that appear in both DSA and standard Search campaigns."""
    service = AnalyticsService(db)
    return service.get_dsa_search_overlap(
        client_id,
        days=days,
        date_from=date_from,
        date_to=date_to,
    )
