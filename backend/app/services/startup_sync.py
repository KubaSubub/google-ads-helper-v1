"""Startup sync — runs once on application boot in a background asyncio task.

Per ADR-020:
- Silent discover (MCC → DB) so new managed accounts are picked up automatically.
- For each client:
    * existing (has any SyncCoverage.data_to)  → incremental (from data_to+1 to yesterday per phase)
    * new (no coverage)                        → fixed 30 days
- Does NOT block startup. UI becomes available immediately; clients dopinają się
  po kolei with sync_logs stream, which the MCC Overview already reflects via
  its freshness badges and row-level syncing state.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.client import Client
from app.models.sync_coverage import SyncCoverage
from app.models.sync_log import SyncLog
from app.services.google_ads import google_ads_service
from app.services.sync_config import PHASE_ORDER, PHASE_REGISTRY, SYNC_PRESETS
from app.routers.sync import _build_phase_executor, _resolve_dates_for_phase


def _discover_silently(db: Session) -> int:
    """Upsert clients from MCC. Returns number added. Never raises."""
    try:
        accounts = google_ads_service.discover_accounts()
    except Exception as exc:
        logger.warning(f"Startup discover skipped: {exc}")
        return 0

    added = 0
    for account in accounts or []:
        currency = (account.get("currency_code") or "").strip().upper() or None
        existing = db.query(Client).filter(
            Client.google_customer_id == account["customer_id"]
        ).first()
        if existing:
            if currency and existing.currency != currency:
                existing.currency = currency
            continue
        db.add(Client(
            name=account["name"],
            google_customer_id=account["customer_id"],
            currency=currency or "PLN",
        ))
        added += 1

    db.commit()
    if added:
        logger.info(f"Startup discover: added {added} new client(s)")
    return added


def _has_any_coverage(db: Session, client_id: int) -> bool:
    return (
        db.query(SyncCoverage)
        .filter(SyncCoverage.client_id == client_id, SyncCoverage.data_to.isnot(None))
        .first()
        is not None
    )


def _run_client_sync(db: Session, client: Client) -> dict:
    """Run all phases for a single client.

    Existing client → mode='incremental' (per-phase from data_to+1 to yesterday).
    New client      → mode='fixed' with fixed_days=30.
    """
    diagnostics = google_ads_service.get_connection_diagnostics()
    if not diagnostics["ready"]:
        return {"status": "skipped", "reason": diagnostics["reason"]}

    # Skip clients whose google_customer_id is not a valid 10-digit Google Ads ID
    # (e.g. seed/demo placeholders like "123-456-7890"). The API call would rage
    # with UNAUTHENTICATED on every phase. We never auto-delete — just skip.
    normalized_raw = "".join(ch for ch in (client.google_customer_id or "") if ch.isdigit())
    if len(normalized_raw) != 10 or normalized_raw.startswith(("1234567", "0000")):
        return {"status": "skipped", "reason": f"Pomijam — customer_id '{client.google_customer_id}' nie wyglada na realny (demo/seed)."}

    cid = google_ads_service.normalize_customer_id(client.google_customer_id)
    is_new = not _has_any_coverage(db, client.id)
    mode = "fixed" if is_new else "incremental"
    fixed_days = 30 if is_new else None

    coverages = {
        c.resource_type: c
        for c in db.query(SyncCoverage).filter(SyncCoverage.client_id == client.id).all()
    }

    sync_log = SyncLog(client_id=client.id, days=fixed_days or 0, status="running")
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    total_synced = 0
    total_errors = 0
    phases: dict[str, dict] = {}
    failed_phases: set[str] = set()

    for phase_name in PHASE_ORDER:
        meta = PHASE_REGISTRY.get(phase_name, {})
        dep = meta.get("depends_on")
        if dep and dep in failed_phases:
            phases[phase_name] = {"count": 0, "status": "skipped", "reason": f"{dep} failed"}
            continue

        if meta.get("pattern") == "B":
            phase_from, phase_to = _resolve_dates_for_phase(
                phase_name, mode, coverages.get(phase_name),
                None, None, fixed_days,
            )
            if phase_from is None and phase_to is None:
                phases[phase_name] = {"count": 0, "status": "skipped", "reason": "up to date"}
                continue
        elif meta.get("pattern") == "C":
            phase_from = date.today() - timedelta(days=28)
            phase_to = date.today() - timedelta(days=1)
        else:
            phase_from = None
            phase_to = None

        executor = _build_phase_executor(
            cid, db,
            phase_from or (date.today() - timedelta(days=30)),
            phase_to or (date.today() - timedelta(days=1)),
            client.id,
        )
        fn = executor.get(phase_name)
        if not fn:
            continue

        try:
            count = fn()
            phases[phase_name] = {"count": count, "status": "ok"}
            total_synced += count
        except Exception as e:
            err = str(e)[:500]
            logger.error(f"Startup sync phase {phase_name} failed for client {client.id}: {err}")
            phases[phase_name] = {"count": 0, "status": "error", "error": err}
            total_errors += 1
            if meta.get("critical"):
                failed_phases.add(phase_name)

    if total_errors == 0:
        sync_log.status = "success"
    elif total_synced > 0:
        sync_log.status = "partial"
    else:
        sync_log.status = "failed"
    sync_log.phases = phases
    sync_log.total_synced = total_synced
    sync_log.total_errors = total_errors
    sync_log.finished_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": sync_log.status,
        "client_id": client.id,
        "total_synced": total_synced,
        "total_errors": total_errors,
        "mode": mode,
    }


def _run_all_clients() -> None:
    db = SessionLocal()
    try:
        _discover_silently(db)
        clients = db.query(Client).all()
        logger.info(f"Startup sync: {len(clients)} client(s) to process")
        for client in clients:
            try:
                result = _run_client_sync(db, client)
                logger.info(f"Startup sync client={client.id} {client.name}: {result}")
            except Exception as exc:
                logger.error(f"Startup sync failed for client={client.id}: {exc}")
    finally:
        db.close()


async def run_startup_sync_in_background() -> None:
    """Fire-and-forget entrypoint called from FastAPI lifespan.

    The sync runs in a thread so it does not block the asyncio event loop and
    does not stall request handling. Failure is logged, never raised.
    """
    try:
        await asyncio.to_thread(_run_all_clients)
    except Exception as exc:
        logger.error(f"Startup sync background task crashed: {exc}")
