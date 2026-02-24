"""Actions endpoints — apply recommendations + revert (undo)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.action_log import ActionLog
from app.models.keyword import Keyword
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/actions", tags=["Actions"])


def _enrich_action(a: ActionLog, db: Session) -> dict:
    """Add entity_name and campaign_name context to action log entry."""
    result = {
        "id": a.id,
        "action_type": a.action_type,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "entity_name": None,
        "campaign_name": None,
        "status": a.status,
        "old_value_json": a.old_value_json,
        "new_value_json": a.new_value_json,
        "error_message": a.error_message,
        "executed_at": str(a.executed_at) if a.executed_at else None,
        "reverted_at": str(a.reverted_at) if a.reverted_at else None,
    }

    try:
        entity_id = int(a.entity_id) if a.entity_id else None
    except (ValueError, TypeError):
        return result

    if not entity_id:
        return result

    if a.entity_type == "keyword":
        kw = db.query(Keyword).get(entity_id)
        if kw:
            result["entity_name"] = kw.text
            ag = db.query(AdGroup).get(kw.ad_group_id) if kw.ad_group_id else None
            if ag:
                camp = db.query(Campaign).get(ag.campaign_id) if ag.campaign_id else None
                if camp:
                    result["campaign_name"] = camp.name
    elif a.entity_type == "campaign":
        camp = db.query(Campaign).get(entity_id)
        if camp:
            result["entity_name"] = camp.name
            result["campaign_name"] = camp.name

    return result


@router.get("/")
def list_actions(
    client_id: int = Query(..., description="Client ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List action history for a client (chronological, newest first)."""
    query = db.query(ActionLog).filter(
        ActionLog.client_id == client_id
    ).order_by(ActionLog.executed_at.desc())

    total = query.count()
    actions = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "actions": [_enrich_action(a, db) for a in actions],
    }


@router.post("/revert/{action_log_id}")
def revert_action(
    action_log_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Revert (undo) a previously executed action.

    Rules:
    - Action must be < 24h old
    - Status must be SUCCESS
    - ADD_NEGATIVE is irreversible
    """
    # Verify client ownership
    action = db.query(ActionLog).filter(
        ActionLog.id == action_log_id,
        ActionLog.client_id == client_id,
    ).first()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    executor = ActionExecutor(db)
    result = executor.revert_action(action_log_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result
