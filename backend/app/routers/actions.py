"""Actions endpoints - audit trail and revert handling."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.action_log import ActionLog
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/actions", tags=["Actions"])


def _enrich_action(action: ActionLog, db: Session) -> dict:
    """Add entity_name and campaign_name context to an action log entry."""
    result = {
        "id": action.id,
        "recommendation_id": action.recommendation_id,
        "action_type": action.action_type,
        "entity_type": action.entity_type,
        "entity_id": action.entity_id,
        "entity_name": None,
        "campaign_name": None,
        "status": action.status,
        "execution_mode": action.execution_mode,
        "precondition_status": action.precondition_status,
        "old_value_json": action.old_value_json,
        "new_value_json": action.new_value_json,
        "error_message": action.error_message,
        "context_json": action.context_json,
        "action_payload": action.action_payload,
        "executed_at": str(action.executed_at) if action.executed_at else None,
        "reverted_at": str(action.reverted_at) if action.reverted_at else None,
    }

    try:
        entity_id = int(action.entity_id) if action.entity_id else None
    except (ValueError, TypeError):
        return result

    if not entity_id:
        return result

    if action.entity_type == "keyword":
        keyword = db.get(Keyword, entity_id)
        if keyword:
            result["entity_name"] = keyword.text
            ad_group = db.get(AdGroup, keyword.ad_group_id) if keyword.ad_group_id else None
            if ad_group:
                campaign = db.get(Campaign, ad_group.campaign_id) if ad_group.campaign_id else None
                if campaign:
                    result["campaign_name"] = campaign.name
    elif action.entity_type == "campaign":
        campaign = db.get(Campaign, entity_id)
        if campaign:
            result["entity_name"] = campaign.name
            result["campaign_name"] = campaign.name

    return result


@router.get("/")
def list_actions(
    client_id: int = Query(..., description="Client ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List action history for a client (newest first)."""
    query = (
        db.query(ActionLog)
        .filter(ActionLog.client_id == client_id)
        .order_by(ActionLog.executed_at.desc())
    )

    total = query.count()
    actions = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "actions": [_enrich_action(action, db) for action in actions],
    }


@router.post("/revert/{action_log_id}")
def revert_action(
    action_log_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Revert a previously executed action when the action is reversible."""
    action = (
        db.query(ActionLog)
        .filter(ActionLog.id == action_log_id, ActionLog.client_id == client_id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    executor = ActionExecutor(db)
    result = executor.revert_action(action_log_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

