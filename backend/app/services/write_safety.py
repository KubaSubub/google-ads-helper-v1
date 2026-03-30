"""Unified write-path safety layer.

Every mutation endpoint (rules, negatives, placements, bidding) MUST go through:
1. Demo guard  — ensure_demo_write_allowed()
2. Safety check — validate_action() where applicable
3. Audit log   — record_write_action()

This module provides lightweight helpers that complement the existing
ActionExecutor (used for recommendation-driven actions) so that *direct*
user-initiated writes also satisfy the same invariants.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.action_log import ActionLog


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_write_action(
    db: Session,
    *,
    client_id: int,
    action_type: str,
    entity_type: str,
    entity_id: Any,
    status: str = "SUCCESS",
    execution_mode: str = "LOCAL",
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    context: Optional[dict] = None,
    error_message: Optional[str] = None,
) -> ActionLog:
    """Create an ActionLog entry for a non-recommendation write operation."""
    log_entry = ActionLog(
        client_id=client_id,
        recommendation_id=None,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=str(entity_id or 0),
        old_value_json=json.dumps(old_value) if old_value else None,
        new_value_json=json.dumps(new_value) if new_value else None,
        status=status,
        error_message=error_message,
        execution_mode=execution_mode,
        precondition_status="PASSED" if status == "SUCCESS" else "FAILED",
        context_json=context,
        action_payload={"action_type": action_type, "source": "DIRECT_WRITE"},
    )
    db.add(log_entry)
    db.flush()
    return log_entry


def count_negatives_added_today(db: Session, client_id: int) -> int:
    """Count negative keywords added today for a given client (for daily limit)."""
    today = utcnow().date()
    return (
        db.query(ActionLog)
        .filter(
            ActionLog.client_id == client_id,
            ActionLog.action_type.in_(["ADD_NEGATIVE", "BULK_ADD_NEGATIVE", "RULE_ADD_NEGATIVE"]),
            ActionLog.status.in_(["SUCCESS", "APPLIED"]),
            func.date(ActionLog.executed_at) == today,
        )
        .count()
    )


def count_pauses_today(db: Session, client_id: int) -> int:
    """Count entities paused today for a given client."""
    today = utcnow().date()
    return (
        db.query(ActionLog)
        .filter(
            ActionLog.client_id == client_id,
            ActionLog.action_type.in_(["PAUSE_KEYWORD", "RULE_PAUSE"]),
            ActionLog.status == "SUCCESS",
            func.date(ActionLog.executed_at) == today,
        )
        .count()
    )
