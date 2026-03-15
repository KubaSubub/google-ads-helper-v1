"""History endpoints — Google Ads change history from all sources."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.change_event import ChangeEvent
from app.models.action_log import ActionLog
from app.models import Keyword, Campaign, AdGroup

router = APIRouter(prefix="/history", tags=["History"])


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _enrich_action(action: ActionLog, db: Session) -> dict:
    """Add entity_name and campaign_name to an action_log entry."""
    entity_name = None
    campaign_name = None

    try:
        if action.entity_type == "keyword" and action.entity_id:
            kw = db.query(Keyword).filter(Keyword.id == int(action.entity_id)).first()
            if kw:
                entity_name = kw.text
                ag = db.query(AdGroup).filter(AdGroup.id == kw.ad_group_id).first()
                if ag:
                    camp = db.query(Campaign).filter(Campaign.id == ag.campaign_id).first()
                    if camp:
                        campaign_name = camp.name
        elif action.entity_type == "campaign" and action.entity_id:
            camp = db.query(Campaign).filter(Campaign.id == int(action.entity_id)).first()
            if camp:
                entity_name = camp.name
                campaign_name = camp.name
    except (ValueError, TypeError):
        pass

    return {
        "entity_name": entity_name,
        "campaign_name": campaign_name,
    }


def _serialize_event(e: ChangeEvent) -> dict:
    return {
        "id": e.id,
        "client_id": e.client_id,
        "resource_name": e.resource_name,
        "change_date_time": str(e.change_date_time),
        "user_email": e.user_email,
        "client_type": e.client_type,
        "change_resource_type": e.change_resource_type,
        "change_resource_name": e.change_resource_name,
        "resource_change_operation": e.resource_change_operation,
        "changed_fields": e.changed_fields,
        "old_resource_json": e.old_resource_json,
        "new_resource_json": e.new_resource_json,
        "action_log_id": e.action_log_id,
        "entity_id": e.entity_id,
        "entity_name": e.entity_name,
        "campaign_name": e.campaign_name,
        "is_helper_action": e.action_log_id is not None,
    }


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/")
def list_change_events(
    client_id: int = Query(..., description="Client ID"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    client_type: Optional[str] = Query(None, description="Filter by client type (source)"),
    operation: Optional[str] = Query(None, description="CREATE, UPDATE, or REMOVE"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List change events from Google Ads with filters."""
    query = db.query(ChangeEvent).filter(ChangeEvent.client_id == client_id)

    if date_from:
        query = query.filter(ChangeEvent.change_date_time >= datetime.fromisoformat(date_from))
    if date_to:
        dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)
        query = query.filter(ChangeEvent.change_date_time < dt_to)
    if resource_type:
        query = query.filter(ChangeEvent.change_resource_type == resource_type)
    if user_email:
        query = query.filter(ChangeEvent.user_email == user_email)
    if client_type:
        query = query.filter(ChangeEvent.client_type == client_type)
    if operation:
        query = query.filter(ChangeEvent.resource_change_operation == operation)

    query = query.order_by(ChangeEvent.change_date_time.desc())
    total = query.count()
    events = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [_serialize_event(e) for e in events],
    }


@router.get("/unified")
def unified_timeline(
    client_id: int = Query(..., description="Client ID"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Unified timeline merging action_log + change_event by timestamp DESC."""

    # --- Action log entries ---
    action_q = db.query(ActionLog).filter(ActionLog.client_id == client_id)
    if date_from:
        action_q = action_q.filter(ActionLog.executed_at >= datetime.fromisoformat(date_from))
    if date_to:
        dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)
        action_q = action_q.filter(ActionLog.executed_at < dt_to)
    if resource_type:
        action_q = action_q.filter(ActionLog.entity_type == resource_type.lower())
    actions = action_q.all()

    # --- Change events (exclude those already linked to action_log to avoid duplicates) ---
    event_q = db.query(ChangeEvent).filter(
        ChangeEvent.client_id == client_id,
        ChangeEvent.action_log_id.is_(None),
    )
    if date_from:
        event_q = event_q.filter(ChangeEvent.change_date_time >= datetime.fromisoformat(date_from))
    if date_to:
        dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)
        event_q = event_q.filter(ChangeEvent.change_date_time < dt_to)
    if resource_type:
        event_q = event_q.filter(ChangeEvent.change_resource_type == resource_type.upper())
    events = event_q.all()

    # --- Build unified list ---
    entries = []
    now = datetime.now(timezone.utc)

    for a in actions:
        enriched = _enrich_action(a, db)
        executed_at = a.executed_at
        if executed_at and executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=timezone.utc)
        age_seconds = (now - executed_at).total_seconds() if executed_at else 999999
        entries.append({
            "source": "helper",
            "timestamp": str(a.executed_at),
            "operation": a.action_type,
            "resource_type": a.entity_type or "",
            "entity_id": a.entity_id,
            "entity_name": enriched["entity_name"],
            "campaign_name": enriched["campaign_name"],
            "user_email": None,
            "client_type": "GOOGLE_ADS_HELPER",
            "status": a.status,
            "old_value_json": a.old_value_json,
            "new_value_json": a.new_value_json,
            "changed_fields": None,
            "action_log_id": a.id,
            "change_event_id": None,
            "can_revert": (
                a.status == "SUCCESS"
                and a.action_type != "ADD_NEGATIVE"
                and age_seconds < 86400
                and a.reverted_at is None
            ),
        })

    for e in events:
        entries.append({
            "source": "external",
            "timestamp": str(e.change_date_time),
            "operation": e.resource_change_operation,
            "resource_type": e.change_resource_type or "",
            "entity_id": e.entity_id,
            "entity_name": e.entity_name,
            "campaign_name": e.campaign_name,
            "user_email": e.user_email,
            "client_type": e.client_type,
            "status": None,
            "old_value_json": e.old_resource_json,
            "new_value_json": e.new_resource_json,
            "changed_fields": e.changed_fields,
            "action_log_id": None,
            "change_event_id": e.id,
            "can_revert": False,
        })

    # Sort by timestamp DESC
    entries.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    total = len(entries)
    page = entries[offset: offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": page,
    }


@router.get("/filters")
def get_available_filters(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Return distinct filter values for the frontend dropdowns."""
    resource_types = [
        r[0] for r in db.query(ChangeEvent.change_resource_type)
        .filter(ChangeEvent.client_id == client_id)
        .distinct().all()
    ]

    user_emails = [
        r[0] for r in db.query(ChangeEvent.user_email)
        .filter(ChangeEvent.client_id == client_id, ChangeEvent.user_email.isnot(None))
        .distinct().all()
    ]

    client_types = [
        r[0] for r in db.query(ChangeEvent.client_type)
        .filter(ChangeEvent.client_id == client_id)
        .distinct().all()
    ]

    return {
        "resource_types": sorted(resource_types),
        "user_emails": sorted(user_emails),
        "client_types": sorted(client_types),
    }


