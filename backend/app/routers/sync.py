"""Sync endpoint Ă„â€šĂ‹ÂÄ‚ËĂ˘â‚¬ĹˇĂ‚Â¬Ä‚ËĂ˘â€šÂ¬ÄąÄ„ trigger Google Ads data sync manually or check status."""

from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from loguru import logger
from app.database import get_db
from app.models import (
    Client, SyncLog, Campaign, AdGroup, Keyword, KeywordDaily,
    MetricDaily, MetricSegmented, SearchTerm, ChangeEvent,
)
from app.services.google_ads import google_ads_service

router = APIRouter(prefix="/sync", tags=["Data Sync"])


def _run_phase(name: str, fn, phases: dict, critical: bool = True):
    """Execute a sync phase and record the result."""
    try:
        count = fn()
        phases[name] = {"count": count, "status": "ok"}
        return count
    except Exception as e:
        err_msg = str(e)[:500]
        logger.error(f"Phase {name} failed: {err_msg}")
        phases[name] = {"count": 0, "status": "error", "error": err_msg}
        return 0


def _sync_message_for_status(status: str, total_errors: int = 0) -> str:
    if status == "success":
        return "Synchronizacja zakonczona pomyslnie."
    if status == "partial":
        return f"Synchronizacja zakonczona czesciowo ({total_errors} bledow)."
    return "Synchronizacja nie powiodla sie."


def _phase_failure_message(phase_label: str, error: str | None = None) -> str:
    base = f"Synchronizacja przerwana: faza {phase_label} nie powiodla sie."
    if not error:
        return base

    compact_error = " ".join(str(error).split())
    if len(compact_error) > 220:
        compact_error = compact_error[:217].rstrip() + "..."
    return f"{base} {compact_error}"

def _build_sync_response(success: bool, status: str, message: str, **extra):
    payload = {"success": success, "status": status, "message": message}
    payload.update(extra)
    return payload


@router.post("/trigger")
def trigger_sync(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365, description="How many days of data to fetch"),
    db: Session = Depends(get_db),
):
    """Trigger a full data sync from Google Ads API with per-phase error tracking."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return _build_sync_response(False, "failed", "Client not found")

    diagnostics = google_ads_service.get_connection_diagnostics()
    if not diagnostics["ready"]:
        return _build_sync_response(
            False,
            "failed",
            diagnostics["reason"],
            reason=diagnostics["reason"],
            missing_credentials=diagnostics["missing_credentials"],
        )

    date_from = date.today() - timedelta(days=days)
    date_to = date.today() - timedelta(days=1)
    cid = google_ads_service.normalize_customer_id(client.google_customer_id)

    sync_log = SyncLog(client_id=client.id, days=days, status="running")
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    phases = {}
    total_synced = 0
    total_errors = 0

    campaigns_synced = _run_phase(
        "campaigns",
        lambda: google_ads_service.sync_campaigns(db, cid),
        phases,
    )
    total_synced += campaigns_synced

    if phases["campaigns"]["status"] == "error":
        total_errors += 1
        sync_log.status = "failed"
        sync_log.phases = phases
        sync_log.total_synced = total_synced
        sync_log.total_errors = total_errors
        sync_log.error_message = "Phase 1 (campaigns) failed - aborting sync"
        sync_log.finished_at = datetime.now(timezone.utc)
        db.commit()
        return _build_sync_response(
            False,
            "failed",
            _phase_failure_message("kampanii", phases["campaigns"].get("error")),
            sync_log_id=sync_log.id,
            phases=phases,
            total_synced=total_synced,
            total_errors=total_errors,
            campaigns_synced=campaigns_synced,
        )

    impression_share_synced = _run_phase(
        "impression_share",
        lambda: google_ads_service.sync_campaign_impression_share(db, cid),
        phases,
    )
    total_synced += impression_share_synced
    if phases["impression_share"]["status"] == "error":
        total_errors += 1

    ad_groups_synced = _run_phase(
        "ad_groups",
        lambda: google_ads_service.sync_ad_groups(db, cid),
        phases,
    )
    total_synced += ad_groups_synced
    if phases["ad_groups"]["status"] == "error":
        total_errors += 1

    keywords_synced = 0
    if phases["ad_groups"]["status"] == "ok":
        keywords_synced = _run_phase(
            "keywords",
            lambda: google_ads_service.sync_keywords(db, cid),
            phases,
        )
        total_synced += keywords_synced
        if phases["keywords"]["status"] == "error":
            total_errors += 1
    else:
        phases["keywords"] = {"count": 0, "status": "skipped", "error": "ad_groups failed"}

    keyword_daily_synced = 0
    if phases.get("keywords", {}).get("status") == "ok":
        keyword_daily_synced = _run_phase(
            "keyword_daily",
            lambda: google_ads_service.sync_keyword_daily(db, cid, date_from, date_to),
            phases,
        )
        total_synced += keyword_daily_synced
        if phases["keyword_daily"]["status"] == "error":
            total_errors += 1
    else:
        phases["keyword_daily"] = {
            "count": 0,
            "status": "skipped",
            "error": "keywords failed/skipped",
        }

    metrics_synced = _run_phase(
        "daily_metrics",
        lambda: google_ads_service.sync_daily_metrics(db, cid, date_from, date_to),
        phases,
    )
    total_synced += metrics_synced
    if phases["daily_metrics"]["status"] == "error":
        total_errors += 1

    device_metrics_synced = _run_phase(
        "device_metrics",
        lambda: google_ads_service.sync_device_metrics(db, cid, date_from, date_to),
        phases,
    )
    total_synced += device_metrics_synced
    if phases["device_metrics"]["status"] == "error":
        total_errors += 1

    geo_metrics_synced = _run_phase(
        "geo_metrics",
        lambda: google_ads_service.sync_geo_metrics(db, cid, date_from, date_to),
        phases,
    )
    total_synced += geo_metrics_synced
    if phases["geo_metrics"]["status"] == "error":
        total_errors += 1

    terms_synced = 0
    if phases["ad_groups"]["status"] == "ok":
        terms_synced = _run_phase(
            "search_terms",
            lambda: google_ads_service.sync_search_terms(db, cid, date_from, date_to),
            phases,
        )
        total_synced += terms_synced
        if phases["search_terms"]["status"] == "error":
            total_errors += 1
    else:
        phases["search_terms"] = {"count": 0, "status": "skipped", "error": "ad_groups failed"}

    pmax_terms_synced = _run_phase(
        "pmax_terms",
        lambda: google_ads_service.sync_pmax_search_terms(db, cid, date_from, date_to),
        phases,
    )
    total_synced += pmax_terms_synced
    if phases["pmax_terms"]["status"] == "error":
        total_errors += 1

    change_events_synced = _run_phase(
        "change_events",
        lambda: google_ads_service.sync_change_events(db, cid, client.id, days=30),
        phases,
        critical=False,
    )
    total_synced += change_events_synced
    if phases["change_events"]["status"] == "error":
        total_errors += 1

    if total_errors == 0:
        sync_log.status = "success"
    elif total_errors < len(phases):
        sync_log.status = "partial"
    else:
        sync_log.status = "failed"

    failed_phases = [
        name for name, meta in phases.items() if meta.get("status") == "error"
    ]
    sync_log.phases = phases
    sync_log.total_synced = total_synced
    sync_log.total_errors = total_errors
    sync_log.error_message = (
        None if not failed_phases else "Nieudane fazy: " + ", ".join(failed_phases)
    )
    sync_log.finished_at = datetime.now(timezone.utc)
    db.commit()

    message = _sync_message_for_status(sync_log.status, total_errors)
    return _build_sync_response(
        total_errors == 0,
        sync_log.status,
        message,
        sync_log_id=sync_log.id,
        total_synced=total_synced,
        total_errors=total_errors,
        phases=phases,
        campaigns_synced=campaigns_synced,
        ad_groups_synced=ad_groups_synced,
        keywords_synced=keywords_synced,
        keyword_daily_synced=keyword_daily_synced,
        metrics_synced=metrics_synced,
        device_metrics_synced=device_metrics_synced,
        geo_metrics_synced=geo_metrics_synced,
        search_terms_synced=terms_synced,
        pmax_terms_synced=pmax_terms_synced,
        change_events_synced=change_events_synced,
    )


@router.get("/status")
def sync_status():
    """Check if Google Ads API is connected and ready."""
    diagnostics = google_ads_service.get_connection_diagnostics()
    return {
        "google_ads_connected": diagnostics["ready"],
        "configured": diagnostics["configured"],
        "authenticated": diagnostics["authenticated"],
        "ready": diagnostics["ready"],
        "missing_credentials": diagnostics["missing_credentials"],
        "message": diagnostics["reason"],
    }


@router.get("/logs")
def get_sync_logs(
    client_id: int = Query(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent sync logs for a client."""
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.client_id == client_id)
        .order_by(SyncLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "status": log.status,
            "days": log.days,
            "phases": log.phases,
            "total_synced": log.total_synced,
            "total_errors": log.total_errors,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        }
        for log in logs
    ]


@router.get("/debug")
def sync_debug(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Quick diagnostic: row counts per resource + last sync info."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"error": "Client not found"}

    seven_days_ago = date.today() - timedelta(days=7)

    # Row counts
    campaigns = db.query(func.count(Campaign.id)).filter(Campaign.client_id == client_id).scalar()
    ad_groups = db.query(func.count(AdGroup.id)).join(Campaign).filter(Campaign.client_id == client_id).scalar()
    keywords = db.query(func.count(Keyword.id)).join(AdGroup).join(Campaign).filter(Campaign.client_id == client_id).scalar()

    keyword_daily_7d = (
        db.query(func.count(KeywordDaily.id))
        .join(Keyword).join(AdGroup).join(Campaign)
        .filter(Campaign.client_id == client_id, KeywordDaily.date >= seven_days_ago)
        .scalar()
    )

    daily_metrics_7d = (
        db.query(func.count(MetricDaily.id))
        .join(Campaign)
        .filter(Campaign.client_id == client_id, MetricDaily.date >= seven_days_ago)
        .scalar()
    )

    device_metrics = (
        db.query(func.count(MetricSegmented.id))
        .join(Campaign)
        .filter(Campaign.client_id == client_id, MetricSegmented.device.isnot(None))
        .scalar()
    )

    geo_metrics = (
        db.query(func.count(MetricSegmented.id))
        .join(Campaign)
        .filter(Campaign.client_id == client_id, MetricSegmented.geo_city.isnot(None))
        .scalar()
    )

    search_terms = db.query(func.count(SearchTerm.id)).filter(
        SearchTerm.campaign_id.in_(
            db.query(Campaign.id).filter(Campaign.client_id == client_id)
        )
    ).scalar()

    change_events = db.query(func.count(ChangeEvent.id)).filter(ChangeEvent.client_id == client_id).scalar()

    # Last sync
    last_sync = (
        db.query(SyncLog)
        .filter(SyncLog.client_id == client_id)
        .order_by(SyncLog.started_at.desc())
        .first()
    )

    return {
        "client": client.name,
        "google_ads_connected": google_ads_service.is_connected,
        "campaigns": campaigns,
        "ad_groups": ad_groups,
        "keywords": keywords,
        "keyword_metrics_last_7d": keyword_daily_7d,
        "campaign_metrics_last_7d": daily_metrics_7d,
        "device_metrics": device_metrics,
        "geo_metrics": geo_metrics,
        "search_terms": search_terms,
        "change_events": change_events,
        "last_sync": last_sync.started_at.isoformat() if last_sync else None,
        "last_sync_status": last_sync.status if last_sync else None,
    }


@router.post("/phase/{phase_name}")
def sync_single_phase(
    phase_name: str,
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Run a single sync phase for debugging. Available phases:
    campaigns, impression_share, ad_groups, keywords, keyword_daily,
    daily_metrics, device_metrics, geo_metrics, search_terms, pmax_terms, change_events
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"success": False, "error": "Client not found"}

    if not google_ads_service.is_connected:
        return {"success": False, "error": "Google Ads API not connected"}

    date_from = date.today() - timedelta(days=days)
    date_to = date.today() - timedelta(days=1)
    cid = google_ads_service.normalize_customer_id(client.google_customer_id)

    phase_map = {
        "campaigns": lambda: google_ads_service.sync_campaigns(db, cid),
        "impression_share": lambda: google_ads_service.sync_campaign_impression_share(db, cid),
        "ad_groups": lambda: google_ads_service.sync_ad_groups(db, cid),
        "keywords": lambda: google_ads_service.sync_keywords(db, cid),
        "keyword_daily": lambda: google_ads_service.sync_keyword_daily(db, cid, date_from, date_to),
        "daily_metrics": lambda: google_ads_service.sync_daily_metrics(db, cid, date_from, date_to),
        "device_metrics": lambda: google_ads_service.sync_device_metrics(db, cid, date_from, date_to),
        "geo_metrics": lambda: google_ads_service.sync_geo_metrics(db, cid, date_from, date_to),
        "search_terms": lambda: google_ads_service.sync_search_terms(db, cid, date_from, date_to),
        "pmax_terms": lambda: google_ads_service.sync_pmax_search_terms(db, cid, date_from, date_to),
        "change_events": lambda: google_ads_service.sync_change_events(db, cid, client.id, days=days),
    }

    if phase_name not in phase_map:
        return {"success": False, "error": f"Unknown phase '{phase_name}'", "available": list(phase_map.keys())}

    try:
        count = phase_map[phase_name]()
        return {"success": True, "phase": phase_name, "count": count}
    except Exception as e:
        return {"success": False, "phase": phase_name, "error": str(e)[:500]}

