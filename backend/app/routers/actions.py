"""Actions endpoints — apply recommendations + revert (undo)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.action_log import ActionLog
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/actions", tags=["Actions"])


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
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "status": a.status,
                "old_value_json": a.old_value_json,
                "new_value_json": a.new_value_json,
                "error_message": a.error_message,
                "executed_at": str(a.executed_at) if a.executed_at else None,
                "reverted_at": str(a.reverted_at) if a.reverted_at else None,
            }
            for a in actions
        ],
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
