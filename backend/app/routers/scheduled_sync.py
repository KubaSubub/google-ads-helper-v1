"""Scheduled sync endpoints — manage per-client automatic sync schedules."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.scheduled_sync import ScheduledSyncConfig

router = APIRouter(prefix="/sync/schedule", tags=["Scheduled Sync"])


class ScheduleRequest(BaseModel):
    client_id: int
    enabled: bool = True
    interval_hours: int = Field(default=6, ge=1, le=168)  # 1h to 7 days


class ScheduleResponse(BaseModel):
    id: int
    client_id: int
    enabled: bool
    interval_hours: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


def _config_to_response(config: ScheduledSyncConfig) -> dict:
    return {
        "id": config.id,
        "client_id": config.client_id,
        "enabled": config.enabled,
        "interval_hours": config.interval_hours,
        "last_run_at": config.last_run_at,
        "next_run_at": config.next_run_at,
        "created_at": config.created_at,
    }


@router.get("")
def get_schedule(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Get the sync schedule configuration for a client."""
    config = (
        db.query(ScheduledSyncConfig)
        .filter(ScheduledSyncConfig.client_id == client_id)
        .first()
    )
    if not config:
        return {
            "client_id": client_id,
            "enabled": False,
            "interval_hours": 6,
            "last_run_at": None,
            "next_run_at": None,
            "created_at": None,
        }
    return _config_to_response(config)


@router.post("")
def create_or_update_schedule(
    req: ScheduleRequest,
    db: Session = Depends(get_db),
):
    """Create or update a sync schedule for a client."""
    config = (
        db.query(ScheduledSyncConfig)
        .filter(ScheduledSyncConfig.client_id == req.client_id)
        .first()
    )

    now = datetime.now(timezone.utc)

    if config:
        config.enabled = req.enabled
        config.interval_hours = req.interval_hours
        if req.enabled and not config.next_run_at:
            config.next_run_at = now + timedelta(hours=req.interval_hours)
        elif req.enabled:
            # Recalculate next_run based on new interval from last run
            base = config.last_run_at or now
            config.next_run_at = base + timedelta(hours=req.interval_hours)
        else:
            config.next_run_at = None
    else:
        config = ScheduledSyncConfig(
            client_id=req.client_id,
            enabled=req.enabled,
            interval_hours=req.interval_hours,
            next_run_at=now + timedelta(hours=req.interval_hours) if req.enabled else None,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(
        f"Schedule {'enabled' if config.enabled else 'disabled'} for client_id={req.client_id}, "
        f"interval={config.interval_hours}h, next_run={config.next_run_at}"
    )

    return _config_to_response(config)


@router.delete("")
def disable_schedule(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Disable and remove the sync schedule for a client."""
    config = (
        db.query(ScheduledSyncConfig)
        .filter(ScheduledSyncConfig.client_id == client_id)
        .first()
    )
    if not config:
        return {"success": True, "message": "No schedule found for this client"}

    db.delete(config)
    db.commit()

    logger.info(f"Schedule deleted for client_id={client_id}")

    return {"success": True, "message": "Schedule deleted"}
