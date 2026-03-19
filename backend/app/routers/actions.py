"""Actions endpoints - audit trail and revert handling."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.demo_guard import ensure_demo_write_allowed
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

    # Batch-load entities to avoid N+1 queries
    kw_ids = set()
    camp_ids = set()
    for a in actions:
        try:
            eid = int(a.entity_id) if a.entity_id else None
        except (ValueError, TypeError):
            continue
        if eid and a.entity_type == "keyword":
            kw_ids.add(eid)
        elif eid and a.entity_type == "campaign":
            camp_ids.add(eid)

    kw_map = {}
    ag_map = {}
    if kw_ids:
        keywords = db.query(Keyword).filter(Keyword.id.in_(kw_ids)).all()
        kw_map = {k.id: k for k in keywords}
        ag_ids = {k.ad_group_id for k in keywords if k.ad_group_id}
        if ag_ids:
            ad_groups = db.query(AdGroup).filter(AdGroup.id.in_(ag_ids)).all()
            ag_map = {ag.id: ag for ag in ad_groups}
            camp_ids.update(ag.campaign_id for ag in ad_groups if ag.campaign_id)

    camp_map = {}
    if camp_ids:
        campaigns = db.query(Campaign).filter(Campaign.id.in_(camp_ids)).all()
        camp_map = {c.id: c for c in campaigns}

    def _enrich_batch(action: ActionLog) -> dict:
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
            eid = int(action.entity_id) if action.entity_id else None
        except (ValueError, TypeError):
            return result
        if not eid:
            return result
        if action.entity_type == "keyword":
            kw = kw_map.get(eid)
            if kw:
                result["entity_name"] = kw.text
                ag = ag_map.get(kw.ad_group_id)
                if ag:
                    camp = camp_map.get(ag.campaign_id)
                    if camp:
                        result["campaign_name"] = camp.name
        elif action.entity_type == "campaign":
            camp = camp_map.get(eid)
            if camp:
                result["entity_name"] = camp.name
                result["campaign_name"] = camp.name
        return result

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "actions": [_enrich_batch(action) for action in actions],
    }


@router.post("/revert/{action_log_id}")
def revert_action(
    action_log_id: int,
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Revert a previously executed action when the action is reversible."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Cofanie akcji",
    )

    action = (
        db.query(ActionLog)
        .filter(ActionLog.id == action_log_id, ActionLog.client_id == client_id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    executor = ActionExecutor(db)
    result = executor.revert_action(action_log_id, allow_demo_write=allow_demo_write)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

