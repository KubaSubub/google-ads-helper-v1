"""Simple asyncio-based background scheduler for periodic Google Ads sync.

No external packages — uses only Python's built-in asyncio.
Checks the DB every 60 seconds for enabled schedules that are due.
"""

import asyncio
from datetime import datetime, timedelta, timezone, date

from loguru import logger

from app.database import SessionLocal
from app.models.scheduled_sync import ScheduledSyncConfig
from app.models.client import Client
from app.models.sync_log import SyncLog
from app.models.alert import Alert
from app.services.google_ads import google_ads_service

CHECK_INTERVAL_SECONDS = 60

_scheduler_task: asyncio.Task | None = None


def _run_sync_for_client(client_id: int, days: int = 30) -> dict:
    """Run a full sync for a client, returning summary info.

    This mirrors the logic in routers/sync.py trigger_sync but runs
    in a background context (no HTTP request).
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"success": False, "error": "Client not found"}

        diagnostics = google_ads_service.get_connection_diagnostics()
        if not diagnostics["ready"]:
            return {"success": False, "error": diagnostics["reason"]}

        date_from = date.today() - timedelta(days=days)
        date_to = date.today() - timedelta(days=1)
        cid = google_ads_service.normalize_customer_id(client.google_customer_id)

        sync_log = SyncLog(client_id=client.id, days=days, status="running")
        db.add(sync_log)
        db.commit()
        db.refresh(sync_log)

        total_synced = 0
        total_errors = 0
        phases = {}

        # Run phases — simplified version of sync.py trigger_sync
        phase_defs = [
            ("campaigns", lambda: google_ads_service.sync_campaigns(db, cid), True),
            ("impression_share", lambda: google_ads_service.sync_campaign_impression_share(db, cid), False),
            ("ad_groups", lambda: google_ads_service.sync_ad_groups(db, cid), False),
            ("ads", lambda: google_ads_service.sync_ads(db, cid), False),
            ("keywords", lambda: google_ads_service.sync_keywords(db, cid), False),
            ("negative_keywords", lambda: google_ads_service.sync_negative_keywords(db, cid), False),
            ("negative_keyword_lists", lambda: google_ads_service.sync_negative_keyword_lists(db, cid), False),
            ("keyword_daily", lambda: google_ads_service.sync_keyword_daily(db, cid, date_from, date_to), False),
            ("daily_metrics", lambda: google_ads_service.sync_daily_metrics(db, cid, date_from, date_to), False),
            ("device_metrics", lambda: google_ads_service.sync_device_metrics(db, cid, date_from, date_to), False),
            ("geo_metrics", lambda: google_ads_service.sync_geo_metrics(db, cid, date_from, date_to), False),
            ("search_terms", lambda: google_ads_service.sync_search_terms(db, cid, date_from, date_to), False),
            ("pmax_terms", lambda: google_ads_service.sync_pmax_search_terms(db, cid, date_from, date_to), False),
            ("change_events", lambda: google_ads_service.sync_change_events(db, cid, client.id, days=30), False),
        ]

        abort = False
        for phase_name, phase_fn, critical in phase_defs:
            if abort:
                phases[phase_name] = {"count": 0, "status": "skipped", "error": "earlier critical phase failed"}
                continue
            try:
                count = phase_fn()
                phases[phase_name] = {"count": count, "status": "ok"}
                total_synced += count
            except Exception as e:
                err_msg = str(e)[:500]
                logger.error(f"Scheduled sync phase {phase_name} failed for client {client_id}: {err_msg}")
                phases[phase_name] = {"count": 0, "status": "error", "error": err_msg}
                total_errors += 1
                if critical:
                    abort = True

        # Determine overall status
        if total_errors == 0:
            sync_log.status = "success"
        elif total_errors < len(phases):
            sync_log.status = "partial"
        else:
            sync_log.status = "failed"

        failed_phases = [name for name, meta in phases.items() if meta.get("status") == "error"]
        sync_log.phases = phases
        sync_log.total_synced = total_synced
        sync_log.total_errors = total_errors
        sync_log.error_message = (
            None if not failed_phases else "Nieudane fazy: " + ", ".join(failed_phases)
        )
        sync_log.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "success": total_errors == 0,
            "status": sync_log.status,
            "sync_log_id": sync_log.id,
            "total_synced": total_synced,
            "total_errors": total_errors,
        }
    except Exception as e:
        logger.error(f"Scheduled sync failed for client {client_id}: {e}")
        return {"success": False, "error": str(e)[:500]}
    finally:
        db.close()


def _create_sync_alert(client_id: int, sync_result: dict):
    """Create an Alert after a scheduled sync completes."""
    db = SessionLocal()
    try:
        status = sync_result.get("status", "failed")
        total_synced = sync_result.get("total_synced", 0)
        total_errors = sync_result.get("total_errors", 0)

        if status == "success":
            severity = "LOW"
            title = "Zaplanowana synchronizacja zakonczona pomyslnie"
            description = f"Zsynchronizowano {total_synced} rekordow bez bledow."
        elif status == "partial":
            severity = "MEDIUM"
            title = "Zaplanowana synchronizacja zakonczona czesciowo"
            description = f"Zsynchronizowano {total_synced} rekordow, {total_errors} bledow."
        else:
            severity = "HIGH"
            title = "Zaplanowana synchronizacja nie powiodla sie"
            error = sync_result.get("error", "Nieznany blad")
            description = f"Blad: {error}"

        alert = Alert(
            client_id=client_id,
            alert_type="SCHEDULED_SYNC_COMPLETE",
            severity=severity,
            title=title,
            description=description,
            metric_value=f"Synced: {total_synced}, Errors: {total_errors}",
        )
        db.add(alert)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create sync alert for client {client_id}: {e}")
    finally:
        db.close()


def _check_and_run_due_syncs():
    """Check DB for enabled schedules that are due and run them."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_configs = (
            db.query(ScheduledSyncConfig)
            .filter(
                ScheduledSyncConfig.enabled == True,  # noqa: E712
                (ScheduledSyncConfig.next_run_at <= now) | (ScheduledSyncConfig.next_run_at == None),  # noqa: E711
            )
            .all()
        )

        for config in due_configs:
            logger.info(f"Scheduled sync triggered for client_id={config.client_id}")

            # Run the sync
            result = _run_sync_for_client(config.client_id)

            # Update schedule timestamps
            config.last_run_at = now
            config.next_run_at = now + timedelta(hours=config.interval_hours)
            db.commit()

            # Create alert
            _create_sync_alert(config.client_id, result)

            logger.info(
                f"Scheduled sync for client_id={config.client_id} completed: "
                f"status={result.get('status', 'unknown')}"
            )
    except Exception as e:
        logger.error(f"Scheduler check failed: {e}")
    finally:
        db.close()


async def _scheduler_loop():
    """Main scheduler loop — checks every CHECK_INTERVAL_SECONDS."""
    logger.info(f"Background scheduler started (check interval: {CHECK_INTERVAL_SECONDS}s)")
    while True:
        try:
            await asyncio.to_thread(_check_and_run_due_syncs)
        except asyncio.CancelledError:
            logger.info("Background scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler():
    """Start the background scheduler task. Call from lifespan."""
    global _scheduler_task
    loop = asyncio.get_event_loop()
    _scheduler_task = loop.create_task(_scheduler_loop())
    logger.info("Scheduler task created")
    return _scheduler_task


def stop_scheduler():
    """Cancel the background scheduler task. Call from lifespan shutdown."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Scheduler task cancelled")
    _scheduler_task = None
