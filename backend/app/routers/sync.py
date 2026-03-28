"""Sync endpoint — trigger Google Ads data sync manually or check status."""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Generator, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from loguru import logger

from app.config import settings
from app.database import SessionLocal, get_db
from app.demo_guard import ensure_demo_write_allowed
from app.models import (
    Client, SyncLog, SyncCoverage, Campaign, AdGroup, Keyword, KeywordDaily,
    NegativeKeyword, MetricDaily, MetricSegmented, SearchTerm, ChangeEvent,
)
from app.services.google_ads import google_ads_service
from app.services.google_ads_debug import google_ads_debug_service
from app.services.sync_config import PHASE_REGISTRY, PHASE_ORDER, SYNC_PRESETS, GROUP_LABELS
from app.utils.sse import sse_event

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
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Trigger a full data sync from Google Ads API with per-phase error tracking."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return _build_sync_response(False, "failed", "Client not found")
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Synchronizacja danych",
    )

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

    ads_synced = 0
    if phases["ad_groups"]["status"] == "ok":
        ads_synced = _run_phase(
            "ads",
            lambda: google_ads_service.sync_ads(db, cid),
            phases,
        )
        total_synced += ads_synced
        if phases.get("ads", {}).get("status") == "error":
            total_errors += 1
    else:
        phases["ads"] = {"count": 0, "status": "skipped", "error": "ad_groups failed"}

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

    negative_keywords_synced = 0
    if phases["ad_groups"]["status"] == "ok":
        negative_keywords_synced = _run_phase(
            "negative_keywords",
            lambda: google_ads_service.sync_negative_keywords(db, cid),
            phases,
        )
        total_synced += negative_keywords_synced
        if phases["negative_keywords"]["status"] == "error":
            total_errors += 1
    else:
        phases["negative_keywords"] = {
            "count": 0,
            "status": "skipped",
            "error": "ad_groups failed",
        }

    neg_lists_synced = _run_phase(
        "negative_keyword_lists",
        lambda: google_ads_service.sync_negative_keyword_lists(db, cid),
        phases,
    )
    total_synced += neg_lists_synced
    if phases["negative_keyword_lists"]["status"] == "error":
        total_errors += 1

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

    # Phase B+C enrichment syncs (non-critical)
    conversion_actions_synced = _run_phase(
        "conversion_actions",
        lambda: google_ads_service.sync_conversion_actions(db, cid),
        phases,
        critical=False,
    )
    total_synced += conversion_actions_synced
    if phases["conversion_actions"]["status"] == "error":
        total_errors += 1

    age_metrics_synced = _run_phase(
        "age_metrics",
        lambda: google_ads_service.sync_age_metrics(db, cid, date_from, date_to),
        phases,
        critical=False,
    )
    total_synced += age_metrics_synced
    if phases["age_metrics"]["status"] == "error":
        total_errors += 1

    gender_metrics_synced = _run_phase(
        "gender_metrics",
        lambda: google_ads_service.sync_gender_metrics(db, cid, date_from, date_to),
        phases,
        critical=False,
    )
    total_synced += gender_metrics_synced
    if phases["gender_metrics"]["status"] == "error":
        total_errors += 1

    # --- Phase D: PMax, Audience, Extensions ---
    pmax_channels_synced = _run_phase(
        "pmax_channel_metrics",
        lambda: google_ads_service.sync_pmax_channel_metrics(db, cid, date_from, date_to),
        phases,
        critical=False,
    )
    total_synced += pmax_channels_synced
    if phases["pmax_channel_metrics"]["status"] == "error":
        total_errors += 1

    asset_groups_synced = _run_phase(
        "asset_groups",
        lambda: google_ads_service.sync_asset_groups(db, cid),
        phases,
        critical=False,
    )
    total_synced += asset_groups_synced
    if phases["asset_groups"]["status"] == "error":
        total_errors += 1

    asset_group_daily_synced = _run_phase(
        "asset_group_daily",
        lambda: google_ads_service.sync_asset_group_daily(db, cid, date_from, date_to),
        phases,
        critical=False,
    )
    total_synced += asset_group_daily_synced
    if phases["asset_group_daily"]["status"] == "error":
        total_errors += 1

    asset_group_assets_synced = _run_phase(
        "asset_group_assets",
        lambda: google_ads_service.sync_asset_group_assets(db, cid),
        phases,
        critical=False,
    )
    total_synced += asset_group_assets_synced
    if phases["asset_group_assets"]["status"] == "error":
        total_errors += 1

    asset_group_signals_synced = _run_phase(
        "asset_group_signals",
        lambda: google_ads_service.sync_asset_group_signals(db, cid),
        phases,
        critical=False,
    )
    total_synced += asset_group_signals_synced
    if phases["asset_group_signals"]["status"] == "error":
        total_errors += 1

    campaign_audiences_synced = _run_phase(
        "campaign_audiences",
        lambda: google_ads_service.sync_campaign_audiences(db, cid, date_from, date_to),
        phases,
        critical=False,
    )
    total_synced += campaign_audiences_synced
    if phases["campaign_audiences"]["status"] == "error":
        total_errors += 1

    campaign_assets_synced = _run_phase(
        "campaign_assets",
        lambda: google_ads_service.sync_campaign_assets(db, cid),
        phases,
        critical=False,
    )
    total_synced += campaign_assets_synced
    if phases["campaign_assets"]["status"] == "error":
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
        negative_keywords_synced=negative_keywords_synced,
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
    negative_keywords = db.query(func.count(NegativeKeyword.id)).filter(NegativeKeyword.client_id == client_id).scalar()

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
    db_path = google_ads_debug_service._sqlite_path_from_url(settings.database_url)
    legacy_path = settings.backend_dir / "data" / "google_ads_app.db"

    return {
        "client": client.name,
        "google_ads_connected": google_ads_service.is_connected,
        "campaigns": campaigns,
        "ad_groups": ad_groups,
        "keywords": keywords,
        "negative_keywords": negative_keywords,
        "keyword_metrics_last_7d": keyword_daily_7d,
        "campaign_metrics_last_7d": daily_metrics_7d,
        "device_metrics": device_metrics,
        "geo_metrics": geo_metrics,
        "search_terms": search_terms,
        "change_events": change_events,
        "db_source_path": str(db_path) if db_path else None,
        "db_legacy_path": str(legacy_path),
        "db_legacy_exists": legacy_path.exists(),
        "last_sync": last_sync.started_at.isoformat() if last_sync else None,
        "last_sync_status": last_sync.status if last_sync else None,
    }


@router.get("/debug/keywords")
def sync_debug_keywords(
    client_id: int = Query(...),
    search: list[str] | None = Query(default=None),
    include_removed: bool = Query(True),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Compare raw keyword_view rows with matching local SQLite rows for one client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"error": "Client not found"}

    try:
        return google_ads_debug_service.search_keyword_sources(
            db=db,
            client_id=client.id,
            search_terms=search,
            include_removed=include_removed,
            limit=limit,
        )
    except Exception as e:
        err_msg = google_ads_service._format_google_ads_error(e)
        logger.error(f"Keyword source debug failed for client {client_id}: {err_msg}")
        return {
            "error": err_msg,
            "client_id": client.id,
            "client_name": client.name,
            "customer_id": google_ads_service.normalize_customer_id(client.google_customer_id),
            "search_terms": [term.strip() for term in (search or []) if term and term.strip()],
        }

@router.get("/debug/keyword-source-of-truth")
def sync_debug_keyword_source_of_truth(
    client_id: int = Query(...),
    criterion_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    """Return authoritative Google Ads vs SQLite view for a single keyword criterion."""
    try:
        return google_ads_debug_service.build_keyword_source_of_truth(
            db=db,
            client_id=client_id,
            criterion_id=criterion_id,
        )
    except Exception as e:
        err_msg = google_ads_service._format_google_ads_error(e)
        logger.error(f"Keyword source-of-truth debug failed for client {client_id}, criterion {criterion_id}: {err_msg}")
        return {
            "error": err_msg,
            "client_id": client_id,
            "criterion_id": str(criterion_id),
        }


@router.post("/phase/{phase_name}")
def sync_single_phase(
    phase_name: str,
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Run a single sync phase for debugging. Available phases:
    campaigns, impression_share, ad_groups, keywords, keyword_daily,
    daily_metrics, device_metrics, geo_metrics, search_terms, pmax_terms,
    change_events, conversion_actions, age_metrics, gender_metrics,
    pmax_channel_metrics, asset_groups, asset_group_daily, asset_group_assets,
    asset_group_signals, campaign_audiences, campaign_assets
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"success": False, "error": "Client not found"}
    ensure_demo_write_allowed(
        db,
        client.id,
        allow_demo_write=allow_demo_write,
        operation="Uruchamianie fazy synchronizacji",
    )

    if not google_ads_service.is_connected:
        return {"success": False, "error": "Google Ads API not connected"}

    date_from = date.today() - timedelta(days=days)
    date_to = date.today() - timedelta(days=1)
    cid = google_ads_service.normalize_customer_id(client.google_customer_id)

    phase_map = {
        "campaigns": lambda: google_ads_service.sync_campaigns(db, cid),
        "impression_share": lambda: google_ads_service.sync_campaign_impression_share(db, cid),
        "ad_groups": lambda: google_ads_service.sync_ad_groups(db, cid),
        "ads": lambda: google_ads_service.sync_ads(db, cid),
        "keywords": lambda: google_ads_service.sync_keywords(db, cid),
        "negative_keywords": lambda: google_ads_service.sync_negative_keywords(db, cid),
        "negative_keyword_lists": lambda: google_ads_service.sync_negative_keyword_lists(db, cid),
        "keyword_daily": lambda: google_ads_service.sync_keyword_daily(db, cid, date_from, date_to),
        "daily_metrics": lambda: google_ads_service.sync_daily_metrics(db, cid, date_from, date_to),
        "device_metrics": lambda: google_ads_service.sync_device_metrics(db, cid, date_from, date_to),
        "geo_metrics": lambda: google_ads_service.sync_geo_metrics(db, cid, date_from, date_to),
        "search_terms": lambda: google_ads_service.sync_search_terms(db, cid, date_from, date_to),
        "pmax_terms": lambda: google_ads_service.sync_pmax_search_terms(db, cid, date_from, date_to),
        "auction_insights": lambda: google_ads_service.sync_auction_insights(db, cid, date_from, date_to),
        "change_events": lambda: google_ads_service.sync_change_events(db, cid, client.id, days=days),
        "conversion_actions": lambda: google_ads_service.sync_conversion_actions(db, cid),
        "age_metrics": lambda: google_ads_service.sync_age_metrics(db, cid, date_from, date_to),
        "gender_metrics": lambda: google_ads_service.sync_gender_metrics(db, cid, date_from, date_to),
        "parental_metrics": lambda: google_ads_service.sync_parental_status_metrics(db, cid, date_from, date_to),
        "income_metrics": lambda: google_ads_service.sync_income_range_metrics(db, cid, date_from, date_to),
        "placement_metrics": lambda: google_ads_service.sync_placement_metrics(db, cid, date_from, date_to),
        "bid_modifiers": lambda: google_ads_service.sync_bid_modifiers(db, cid),
        "bidding_strategies": lambda: google_ads_service.sync_bidding_strategies(db, cid),
        "shared_budgets": lambda: google_ads_service.sync_shared_budgets(db, cid),
        "audiences": lambda: google_ads_service.sync_audiences(db, cid),
        "topic_metrics": lambda: google_ads_service.sync_topic_metrics(db, cid, date_from, date_to),
        "google_recommendations": lambda: google_ads_service.sync_google_recommendations(db, cid),
        "conversion_value_rules": lambda: google_ads_service.sync_conversion_value_rules(db, cid),
        # Phase D
        "pmax_channel_metrics": lambda: google_ads_service.sync_pmax_channel_metrics(db, cid, date_from, date_to),
        "asset_groups": lambda: google_ads_service.sync_asset_groups(db, cid),
        "asset_group_daily": lambda: google_ads_service.sync_asset_group_daily(db, cid, date_from, date_to),
        "asset_group_assets": lambda: google_ads_service.sync_asset_group_assets(db, cid),
        "asset_group_signals": lambda: google_ads_service.sync_asset_group_signals(db, cid),
        "campaign_audiences": lambda: google_ads_service.sync_campaign_audiences(db, cid, date_from, date_to),
        "campaign_assets": lambda: google_ads_service.sync_campaign_assets(db, cid),
    }

    if phase_name not in phase_map:
        return {"success": False, "error": f"Unknown phase '{phase_name}'", "available": list(phase_map.keys())}

    try:
        count = phase_map[phase_name]()
        return {"success": True, "phase": phase_name, "count": count}
    except Exception as e:
        return {"success": False, "phase": phase_name, "error": str(e)[:500]}


@router.get("/data-coverage")
def get_data_coverage(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Return date range of synced data and last sync info for a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return {"error": "Client not found"}

    campaign_ids = db.query(Campaign.id).filter(Campaign.client_id == client_id)

    min_date = (
        db.query(func.min(MetricDaily.date))
        .filter(MetricDaily.campaign_id.in_(campaign_ids))
        .scalar()
    )
    max_date = (
        db.query(func.max(MetricDaily.date))
        .filter(MetricDaily.campaign_id.in_(campaign_ids))
        .scalar()
    )

    last_sync = (
        db.query(SyncLog)
        .filter(SyncLog.client_id == client_id, SyncLog.status.in_(["success", "partial"]))
        .order_by(SyncLog.finished_at.desc())
        .first()
    )

    return {
        "client_id": client_id,
        "data_from": min_date.isoformat() if min_date else None,
        "data_to": max_date.isoformat() if max_date else None,
        "last_sync_at": last_sync.finished_at.isoformat() if last_sync and last_sync.finished_at else None,
        "last_sync_days": last_sync.days if last_sync else None,
        "last_sync_status": last_sync.status if last_sync else None,
    }


# ═══════════════════════════════════════════════════════════════════
# New endpoints: presets, per-resource coverage, SSE trigger-stream
# ═══════════════════════════════════════════════════════════════════


@router.get("/presets")
def get_sync_presets():
    """Return sync presets and phase registry for the configuration modal."""
    phases_info = {
        k: {
            "label": v["label"],
            "group": v["group"],
            "max_days": v["max_days"],
            "pattern": v["pattern"],
        }
        for k, v in PHASE_REGISTRY.items()
    }
    presets_info = {
        k: {
            "label": v["label"],
            "description": v["description"],
            "mode": v["mode"],
            "days": v.get("days"),
        }
        for k, v in SYNC_PRESETS.items()
    }
    return {
        "presets": presets_info,
        "phases": phases_info,
        "groups": GROUP_LABELS,
        "phase_order": PHASE_ORDER,
    }


@router.get("/coverage")
def get_sync_coverage(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Return per-resource sync coverage for a client."""
    coverages = (
        db.query(SyncCoverage)
        .filter(SyncCoverage.client_id == client_id)
        .all()
    )
    result = {}
    for c in coverages:
        result[c.resource_type] = {
            "data_from": c.data_from.isoformat() if c.data_from else None,
            "data_to": c.data_to.isoformat() if c.data_to else None,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "last_status": c.last_status,
            "max_days": PHASE_REGISTRY.get(c.resource_type, {}).get("max_days"),
        }
    return result


# ─── Incremental date resolution ──────────────────────────────────


def _resolve_dates_for_phase(
    phase_name: str,
    mode: str,
    coverage: Optional[SyncCoverage],
    user_date_from: Optional[date] = None,
    user_date_to: Optional[date] = None,
    fixed_days: Optional[int] = None,
) -> tuple[Optional[date], Optional[date]]:
    """Compute (date_from, date_to) for a metric phase based on mode and coverage."""
    meta = PHASE_REGISTRY.get(phase_name, {})
    max_days = meta.get("max_days")
    yesterday = date.today() - timedelta(days=1)

    # date_to is always yesterday (today may be incomplete)
    effective_to = user_date_to or yesterday

    if mode == "fixed" and fixed_days:
        effective_from = date.today() - timedelta(days=fixed_days)
    elif mode == "incremental" and coverage and coverage.data_to:
        # Start from day after last synced data
        effective_from = coverage.data_to + timedelta(days=1)
        if effective_from > effective_to:
            # Already up to date
            return None, None
    else:
        # Full sync — go back as far as API allows
        if max_days:
            effective_from = date.today() - timedelta(days=max_days)
        else:
            effective_from = date.today() - timedelta(days=365)

    # User override
    if user_date_from:
        effective_from = user_date_from

    # Clamp to API limit
    if max_days:
        earliest_allowed = date.today() - timedelta(days=max_days)
        if effective_from < earliest_allowed:
            effective_from = earliest_allowed

    return effective_from, effective_to


def _upsert_coverage(
    db: Session,
    client_id: int,
    resource_type: str,
    phase_date_from: Optional[date],
    phase_date_to: Optional[date],
    status: str = "ok",
):
    """Update or create SyncCoverage record after a sync phase."""
    existing = (
        db.query(SyncCoverage)
        .filter(
            SyncCoverage.client_id == client_id,
            SyncCoverage.resource_type == resource_type,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if existing:
        if phase_date_from and (not existing.data_from or phase_date_from < existing.data_from):
            existing.data_from = phase_date_from
        if phase_date_to and (not existing.data_to or phase_date_to > existing.data_to):
            existing.data_to = phase_date_to
        existing.last_sync_at = now
        existing.last_status = status
    else:
        db.add(SyncCoverage(
            client_id=client_id,
            resource_type=resource_type,
            data_from=phase_date_from,
            data_to=phase_date_to,
            last_sync_at=now,
            last_status=status,
        ))
    db.commit()


# ─── Phase executor mapping ───────────────────────────────────────


def _build_phase_executor(cid: str, db: Session, date_from: date, date_to: date, client_id: int):
    """Return a dict mapping phase_name -> callable returning row count."""
    return {
        "campaigns":            lambda: google_ads_service.sync_campaigns(db, cid),
        "impression_share":     lambda: google_ads_service.sync_campaign_impression_share(db, cid),
        "ad_groups":            lambda: google_ads_service.sync_ad_groups(db, cid),
        "ads":                  lambda: google_ads_service.sync_ads(db, cid),
        "product_groups":       lambda: google_ads_service.sync_product_groups(db, cid),
        "keywords":             lambda: google_ads_service.sync_keywords(db, cid),
        "negative_keywords":    lambda: google_ads_service.sync_negative_keywords(db, cid),
        "negative_keyword_lists": lambda: google_ads_service.sync_negative_keyword_lists(db, cid),
        "keyword_daily":        lambda: google_ads_service.sync_keyword_daily(db, cid, date_from, date_to),
        "daily_metrics":        lambda: google_ads_service.sync_daily_metrics(db, cid, date_from, date_to),
        "search_terms":         lambda: google_ads_service.sync_search_terms(db, cid, date_from, date_to),
        "pmax_terms":           lambda: google_ads_service.sync_pmax_search_terms(db, cid, date_from, date_to),
        "device_metrics":       lambda: google_ads_service.sync_device_metrics(db, cid, date_from, date_to),
        "geo_metrics":          lambda: google_ads_service.sync_geo_metrics(db, cid, date_from, date_to),
        "auction_insights":     lambda: google_ads_service.sync_auction_insights(db, cid, date_from, date_to),
        "change_events":        lambda: google_ads_service.sync_change_events(db, cid, client_id, days=28),
        "conversion_actions":   lambda: google_ads_service.sync_conversion_actions(db, cid),
        "age_metrics":          lambda: google_ads_service.sync_age_metrics(db, cid, date_from, date_to),
        "gender_metrics":       lambda: google_ads_service.sync_gender_metrics(db, cid, date_from, date_to),
        "pmax_channel_metrics": lambda: google_ads_service.sync_pmax_channel_metrics(db, cid, date_from, date_to),
        "asset_groups":         lambda: google_ads_service.sync_asset_groups(db, cid),
        "asset_group_daily":    lambda: google_ads_service.sync_asset_group_daily(db, cid, date_from, date_to),
        "asset_group_assets":   lambda: google_ads_service.sync_asset_group_assets(db, cid),
        "asset_group_signals":  lambda: google_ads_service.sync_asset_group_signals(db, cid),
        "parental_metrics":     lambda: google_ads_service.sync_parental_status_metrics(db, cid, date_from, date_to),
        "income_metrics":       lambda: google_ads_service.sync_income_range_metrics(db, cid, date_from, date_to),
        "placement_metrics":    lambda: google_ads_service.sync_placement_metrics(db, cid, date_from, date_to),
        "bid_modifiers":        lambda: google_ads_service.sync_bid_modifiers(db, cid),
        "bidding_strategies":   lambda: google_ads_service.sync_bidding_strategies(db, cid),
        "shared_budgets":       lambda: google_ads_service.sync_shared_budgets(db, cid),
        "audiences":            lambda: google_ads_service.sync_audiences(db, cid),
        "topic_metrics":        lambda: google_ads_service.sync_topic_metrics(db, cid, date_from, date_to),
        "google_recommendations": lambda: google_ads_service.sync_google_recommendations(db, cid),
        "conversion_value_rules": lambda: google_ads_service.sync_conversion_value_rules(db, cid),
        "campaign_audiences":   lambda: google_ads_service.sync_campaign_audiences(db, cid, date_from, date_to),
        "campaign_assets":      lambda: google_ads_service.sync_campaign_assets(db, cid),
    }


# ─── SSE streaming sync endpoint ─────────────────────────────────


def _sse(event: str, data: dict) -> str:
    return sse_event(event, json.dumps(data, default=str))


@router.post("/trigger-stream")
def trigger_sync_stream(
    request: Request,
    client_id: int = Query(...),
    preset: Optional[str] = Query(None),
    phases_filter: Optional[str] = Query(None, alias="phases", description="Comma-separated phase names"),
    date_from_param: Optional[date] = Query(None, alias="date_from"),
    date_to_param: Optional[date] = Query(None, alias="date_to"),
    allow_demo_write: bool = Query(False),
):
    """Trigger sync with SSE progress streaming.

    Returns a Server-Sent Events stream with per-phase progress updates.
    """

    def generate() -> Generator[str, None, None]:
        db = SessionLocal()
        try:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                yield _sse("error", {"message": "Client not found"})
                return

            try:
                ensure_demo_write_allowed(db, client.id, allow_demo_write=allow_demo_write, operation="Sync")
            except Exception as e:
                yield _sse("error", {"message": str(e)})
                return

            diagnostics = google_ads_service.get_connection_diagnostics()
            if not diagnostics["ready"]:
                yield _sse("error", {"message": diagnostics["reason"]})
                return

            cid = google_ads_service.normalize_customer_id(client.google_customer_id)

            # Resolve preset config
            preset_config = SYNC_PRESETS.get(preset or "incremental", SYNC_PRESETS["incremental"])
            mode = preset_config["mode"]
            fixed_days = preset_config.get("days")

            # Determine which phases to run
            if phases_filter:
                requested_phases = [p.strip() for p in phases_filter.split(",") if p.strip() in PHASE_REGISTRY]
            else:
                requested_phases = preset_config["phases"]

            # Load existing coverage for incremental logic
            coverages = {
                c.resource_type: c
                for c in db.query(SyncCoverage).filter(SyncCoverage.client_id == client_id).all()
            }

            # Create sync log
            sync_log = SyncLog(client_id=client.id, days=0, status="running")
            db.add(sync_log)
            db.commit()
            db.refresh(sync_log)

            total_phases = len(requested_phases)
            total_synced = 0
            total_errors = 0
            phase_results = {}
            failed_phases = set()
            import time
            start_time = time.time()

            yield _sse("sync_start", {
                "sync_log_id": sync_log.id,
                "total_phases": total_phases,
                "mode": mode,
                "phases": requested_phases,
            })

            for idx, phase_name in enumerate(requested_phases):
                # Check if client disconnected
                if hasattr(request, '_disconnected') and request._disconnected:
                    break

                meta = PHASE_REGISTRY.get(phase_name, {})
                dep = meta.get("depends_on")

                # Check dependency
                if dep and dep in failed_phases:
                    phase_results[phase_name] = {"count": 0, "status": "skipped", "reason": f"{dep} nie powiodło się"}
                    yield _sse("phase_skip", {
                        "phase": phase_name,
                        "index": idx + 1,
                        "total": total_phases,
                        "label": meta.get("label", phase_name),
                        "reason": f"Zależność {dep} nie powiodła się",
                    })
                    continue

                # Resolve dates for this specific phase
                if meta.get("pattern") == "B":
                    phase_from, phase_to = _resolve_dates_for_phase(
                        phase_name, mode, coverages.get(phase_name),
                        date_from_param, date_to_param, fixed_days,
                    )
                    if phase_from is None and phase_to is None:
                        # Already up to date
                        phase_results[phase_name] = {"count": 0, "status": "skipped", "reason": "Dane aktualne"}
                        yield _sse("phase_skip", {
                            "phase": phase_name,
                            "index": idx + 1,
                            "total": total_phases,
                            "label": meta.get("label", phase_name),
                            "reason": "Dane aktualne",
                        })
                        continue
                elif meta.get("pattern") == "C":
                    # Change events — always last 28 days
                    phase_from = date.today() - timedelta(days=28)
                    phase_to = date.today() - timedelta(days=1)
                else:
                    # Pattern A — structural, no dates
                    phase_from = None
                    phase_to = None

                yield _sse("phase_start", {
                    "phase": phase_name,
                    "index": idx + 1,
                    "total": total_phases,
                    "label": meta.get("label", phase_name),
                    "date_from": str(phase_from) if phase_from else None,
                    "date_to": str(phase_to) if phase_to else None,
                })

                # Build executor with resolved dates
                executor = _build_phase_executor(
                    cid, db,
                    phase_from or (date.today() - timedelta(days=30)),
                    phase_to or (date.today() - timedelta(days=1)),
                    client.id,
                )

                try:
                    fn = executor.get(phase_name)
                    if not fn:
                        raise RuntimeError(f"Unknown phase: {phase_name}")
                    count = fn()
                    phase_results[phase_name] = {"count": count, "status": "ok"}
                    total_synced += count

                    # Update coverage
                    _upsert_coverage(db, client.id, phase_name, phase_from, phase_to, "ok")

                    yield _sse("phase_done", {
                        "phase": phase_name,
                        "index": idx + 1,
                        "total": total_phases,
                        "count": count,
                        "status": "ok",
                    })

                except Exception as e:
                    err_msg = str(e)[:500]
                    logger.error(f"SSE sync phase {phase_name} failed: {err_msg}")
                    phase_results[phase_name] = {"count": 0, "status": "error", "error": err_msg}
                    total_errors += 1
                    if meta.get("critical"):
                        failed_phases.add(phase_name)

                    _upsert_coverage(db, client.id, phase_name, phase_from, phase_to, "error")

                    yield _sse("phase_error", {
                        "phase": phase_name,
                        "index": idx + 1,
                        "total": total_phases,
                        "error": err_msg,
                        "critical": meta.get("critical", False),
                    })

                    # Abort on critical failure
                    if meta.get("critical"):
                        failed_phases.add(phase_name)

                # Emit progress
                elapsed = time.time() - start_time
                done_count = idx + 1
                if done_count > 0 and done_count < total_phases:
                    avg_per_phase = elapsed / done_count
                    eta_seconds = int(avg_per_phase * (total_phases - done_count))
                else:
                    eta_seconds = 0

                yield _sse("progress", {
                    "percent": int(done_count / total_phases * 100),
                    "done": done_count,
                    "total": total_phases,
                    "eta_seconds": eta_seconds,
                    "elapsed_seconds": int(elapsed),
                })

            # Finalize sync log
            elapsed_total = time.time() - start_time
            if total_errors == 0:
                sync_log.status = "success"
            elif total_errors < len(phase_results):
                sync_log.status = "partial"
            else:
                sync_log.status = "failed"

            sync_log.phases = phase_results
            sync_log.total_synced = total_synced
            sync_log.total_errors = total_errors
            sync_log.finished_at = datetime.now(timezone.utc)
            db.commit()

            yield _sse("done", {
                "status": sync_log.status,
                "total_synced": total_synced,
                "total_errors": total_errors,
                "sync_log_id": sync_log.id,
                "elapsed_seconds": int(elapsed_total),
                "phases": phase_results,
            })

        except Exception as exc:
            logger.exception("SSE sync stream error")
            yield _sse("error", {"message": str(exc)[:500]})
        finally:
            db.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


