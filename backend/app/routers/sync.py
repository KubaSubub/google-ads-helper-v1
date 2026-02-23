"""Sync endpoint — trigger Google Ads data sync manually or check status."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.database import get_db
from app.models import Client
from app.services.google_ads import google_ads_service

router = APIRouter(prefix="/sync", tags=["Data Sync"])


@router.post("/trigger")
def trigger_sync(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365, description="How many days of data to fetch"),
    db: Session = Depends(get_db),
):
    """
    Manually trigger a full data sync from Google Ads API.
    This fetches campaigns, daily metrics, and search terms.
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"success": False, "message": "Client not found"}

    if not google_ads_service.is_connected:
        return {
            "success": False,
            "message": "Google Ads API not configured. Set credentials in .env file.",
            "hint": "Copy .env.example to .env and fill in your Google Ads API credentials."
        }

    date_from = date.today() - timedelta(days=days)
    date_to = date.today() - timedelta(days=1)
    cid = client.google_customer_id

    # Phase 1: Campaigns
    campaigns_synced = google_ads_service.sync_campaigns(db, cid)
    # Phase 2: Ad Groups (depends on campaigns)
    ad_groups_synced = google_ads_service.sync_ad_groups(db, cid)
    # Phase 3: Keywords (depends on ad groups)
    keywords_synced = google_ads_service.sync_keywords(db, cid)
    # Phase 4: Daily metrics (depends on campaigns)
    metrics_synced = google_ads_service.sync_daily_metrics(db, cid, date_from, date_to)
    # Phase 5: Search terms (depends on ad groups)
    terms_synced = google_ads_service.sync_search_terms(db, cid, date_from, date_to)

    return {
        "success": True,
        "campaigns_synced": campaigns_synced,
        "ad_groups_synced": ad_groups_synced,
        "keywords_synced": keywords_synced,
        "metrics_synced": metrics_synced,
        "search_terms_synced": terms_synced,
    }


@router.get("/status")
def sync_status():
    """Check if Google Ads API is connected and ready."""
    return {
        "google_ads_connected": google_ads_service.is_connected,
        "message": "Ready to sync" if google_ads_service.is_connected
                   else "Google Ads API not configured — using demo data",
    }
