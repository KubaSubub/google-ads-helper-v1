"""Automated Rules endpoints — CRUD + dry-run + execute (Feature F3)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.automated_rule import AutomatedRule, AutomatedRuleLog
from app.services.rules_engine import evaluate_rule, execute_rule

router = APIRouter(prefix="/rules", tags=["Automated Rules"])


# ── Pydantic schemas ──────────────────────────────────────────────────────


class ConditionSchema(BaseModel):
    field: str
    op: str  # ">", "<", ">=", "<=", "=", "!=", "contains"
    value: float | int | str


class RuleCreateRequest(BaseModel):
    client_id: int
    name: str = Field(..., max_length=200)
    enabled: bool = True
    entity_type: str  # "keyword", "campaign", "search_term"
    conditions: List[ConditionSchema]
    action_type: str  # "PAUSE", "ADD_NEGATIVE", "ALERT"
    action_params: Optional[dict] = None
    check_interval_hours: int = Field(default=24, ge=1, le=720)


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    enabled: Optional[bool] = None
    entity_type: Optional[str] = None
    conditions: Optional[List[ConditionSchema]] = None
    action_type: Optional[str] = None
    action_params: Optional[dict] = None
    check_interval_hours: Optional[int] = Field(None, ge=1, le=720)


# ── Serialization helpers ─────────────────────────────────────────────────


def _serialize_rule(rule: AutomatedRule) -> dict:
    return {
        "id": rule.id,
        "client_id": rule.client_id,
        "name": rule.name,
        "enabled": rule.enabled,
        "entity_type": rule.entity_type,
        "conditions": rule.conditions,
        "action_type": rule.action_type,
        "action_params": rule.action_params,
        "check_interval_hours": rule.check_interval_hours,
        "last_run_at": rule.last_run_at,
        "matches_last_run": rule.matches_last_run,
        "created_at": rule.created_at,
    }


def _serialize_log(log: AutomatedRuleLog) -> dict:
    return {
        "id": log.id,
        "rule_id": log.rule_id,
        "run_at": log.run_at,
        "matches_found": log.matches_found,
        "actions_taken": log.actions_taken,
        "dry_run": log.dry_run,
        "result": log.result,
    }


# ── Validation ────────────────────────────────────────────────────────────

VALID_ENTITY_TYPES = {"keyword", "campaign", "search_term"}
VALID_ACTION_TYPES = {"PAUSE", "ADD_NEGATIVE", "ALERT"}
VALID_OPERATORS = {">", "<", ">=", "<=", "=", "!=", "contains"}


def _validate_rule_data(entity_type: str, action_type: str, conditions: list):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Nieprawidlowy entity_type '{entity_type}'. Dozwolone: {', '.join(VALID_ENTITY_TYPES)}",
        )
    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Nieprawidlowy action_type '{action_type}'. Dozwolone: {', '.join(VALID_ACTION_TYPES)}",
        )
    if not conditions:
        raise HTTPException(status_code=400, detail="Regula musi miec co najmniej jeden warunek")
    for cond in conditions:
        op = cond.op if hasattr(cond, "op") else cond.get("op")
        if op not in VALID_OPERATORS:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidlowy operator '{op}'. Dozwolone: {', '.join(VALID_OPERATORS)}",
            )


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/")
def list_rules(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """List all automated rules for a client."""
    rules = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.client_id == client_id)
        .order_by(AutomatedRule.created_at.desc())
        .all()
    )
    return {"rules": [_serialize_rule(r) for r in rules], "total": len(rules)}


@router.post("/")
def create_rule(
    req: RuleCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new automated rule."""
    _validate_rule_data(req.entity_type, req.action_type, req.conditions)

    rule = AutomatedRule(
        client_id=req.client_id,
        name=req.name,
        enabled=req.enabled,
        entity_type=req.entity_type,
        conditions=[c.model_dump() for c in req.conditions],
        action_type=req.action_type,
        action_params=req.action_params,
        check_interval_hours=req.check_interval_hours,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"Created automated rule #{rule.id} '{rule.name}' for client_id={rule.client_id}")
    return _serialize_rule(rule)


@router.get("/{rule_id}")
def get_rule(
    rule_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Get rule details + recent logs."""
    rule = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.id == rule_id, AutomatedRule.client_id == client_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regula nie znaleziona")

    logs = (
        db.query(AutomatedRuleLog)
        .filter(AutomatedRuleLog.rule_id == rule_id)
        .order_by(AutomatedRuleLog.run_at.desc())
        .limit(20)
        .all()
    )

    return {
        **_serialize_rule(rule),
        "logs": [_serialize_log(log) for log in logs],
    }


@router.put("/{rule_id}")
def update_rule(
    rule_id: int,
    req: RuleUpdateRequest,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Update an existing rule."""
    rule = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.id == rule_id, AutomatedRule.client_id == client_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regula nie znaleziona")

    # Validate if entity_type or action_type is being changed
    new_entity = req.entity_type or rule.entity_type
    new_action = req.action_type or rule.action_type
    new_conditions = req.conditions if req.conditions is not None else rule.conditions
    if req.entity_type or req.action_type or req.conditions is not None:
        _validate_rule_data(new_entity, new_action, new_conditions)

    if req.name is not None:
        rule.name = req.name
    if req.enabled is not None:
        rule.enabled = req.enabled
    if req.entity_type is not None:
        rule.entity_type = req.entity_type
    if req.conditions is not None:
        rule.conditions = [c.model_dump() for c in req.conditions]
    if req.action_type is not None:
        rule.action_type = req.action_type
    if req.action_params is not None:
        rule.action_params = req.action_params
    if req.check_interval_hours is not None:
        rule.check_interval_hours = req.check_interval_hours

    db.commit()
    db.refresh(rule)

    logger.info(f"Updated automated rule #{rule.id}")
    return _serialize_rule(rule)


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Delete an automated rule and all its logs."""
    rule = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.id == rule_id, AutomatedRule.client_id == client_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regula nie znaleziona")

    rule_name = rule.name
    db.delete(rule)
    db.commit()

    logger.info(f"Deleted automated rule #{rule_id} '{rule_name}'")
    return {"success": True, "message": f"Regula '{rule_name}' usunieta"}


@router.post("/{rule_id}/dry-run")
def dry_run_rule(
    rule_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Evaluate a rule without executing actions — preview matches."""
    rule = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.id == rule_id, AutomatedRule.client_id == client_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regula nie znaleziona")

    return execute_rule(rule, db, dry_run=True)


@router.post("/{rule_id}/execute")
def execute_rule_endpoint(
    rule_id: int,
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Execute a rule for real — apply actions to matching entities.

    Goes through the canonical safety pipeline: demo guard → validate_action → audit log.
    """
    rule = (
        db.query(AutomatedRule)
        .filter(AutomatedRule.id == rule_id, AutomatedRule.client_id == client_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Regula nie znaleziona")

    return execute_rule(rule, db, dry_run=False, allow_demo_write=allow_demo_write)
