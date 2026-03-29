"""Rules Engine — evaluate and execute automated rules (Feature F3).

Supports dynamic condition evaluation against Keyword, Campaign, and SearchTerm
models, with actions: PAUSE, ADD_NEGATIVE, ALERT.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import BigInteger, Float, Integer, and_
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.automated_rule import AutomatedRule, AutomatedRuleLog
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.search_term import SearchTerm


# ── Entity type → model mapping ───────────────────────────────────────────

ENTITY_MODELS = {
    "keyword": Keyword,
    "campaign": Campaign,
    "search_term": SearchTerm,
}

# Fields that need client_id filtering through a join
# (Keyword → AdGroup → Campaign → client_id)
_KEYWORD_CLIENT_FILTER = True
_SEARCH_TERM_CLIENT_FILTER = True


# ── Operator mapping ──────────────────────────────────────────────────────

_OPERATORS = {
    ">": lambda col, val: col > val,
    "<": lambda col, val: col < val,
    ">=": lambda col, val: col >= val,
    "<=": lambda col, val: col <= val,
    "=": lambda col, val: col == val,
    "!=": lambda col, val: col != val,
    "contains": lambda col, val: col.ilike(f"%{val}%"),
}


def _cast_value(column, value: Any) -> Any:
    """Cast the condition value to match the column type."""
    col_type = getattr(column, "type", None)
    if isinstance(col_type, (Integer, BigInteger)):
        return int(value)
    if isinstance(col_type, Float):
        return float(value)
    return value


def _build_filters(model, conditions: list[dict]) -> list:
    """Build SQLAlchemy filter expressions from conditions JSON."""
    filters = []
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("op")
        value = cond.get("value")

        if not field or not op or value is None:
            continue

        column = getattr(model, field, None)
        if column is None:
            logger.warning(f"Unknown field '{field}' for model {model.__name__}, skipping condition")
            continue

        op_fn = _OPERATORS.get(op)
        if op_fn is None:
            logger.warning(f"Unknown operator '{op}', skipping condition")
            continue

        cast_val = _cast_value(column, value)
        filters.append(op_fn(column, cast_val))

    return filters


def _get_entity_name(entity, entity_type: str) -> str:
    """Extract a human-readable name from an entity."""
    if entity_type == "keyword":
        return getattr(entity, "text", f"Keyword #{entity.id}")
    if entity_type == "campaign":
        return getattr(entity, "name", f"Campaign #{entity.id}")
    if entity_type == "search_term":
        return getattr(entity, "text", f"SearchTerm #{entity.id}")
    return f"Entity #{entity.id}"


def _get_entity_summary(entity, entity_type: str) -> dict:
    """Build a summary dict for an entity match."""
    base = {
        "id": entity.id,
        "entity_type": entity_type,
        "name": _get_entity_name(entity, entity_type),
    }
    # Add key metrics
    for field in ("status", "cost_micros", "clicks", "impressions", "conversions", "ctr"):
        val = getattr(entity, field, None)
        if val is not None:
            base[field] = val
    return base


# ── Core evaluation ───────────────────────────────────────────────────────


def evaluate_rule(rule: AutomatedRule, db: Session) -> list[dict]:
    """Evaluate a rule's conditions and return matching entities as dicts."""
    model = ENTITY_MODELS.get(rule.entity_type)
    if model is None:
        logger.error(f"Unknown entity_type '{rule.entity_type}' for rule #{rule.id}")
        return []

    filters = _build_filters(model, rule.conditions or [])
    if not filters:
        logger.warning(f"Rule #{rule.id} has no valid conditions, returning empty")
        return []

    query = db.query(model)

    # Apply client_id filtering based on entity type
    if rule.entity_type == "campaign":
        query = query.filter(Campaign.client_id == rule.client_id)
    elif rule.entity_type == "keyword":
        # Keywords are linked via AdGroup → Campaign → client_id
        from app.models.ad_group import AdGroup
        query = (
            query.join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == rule.client_id)
        )
    elif rule.entity_type == "search_term":
        query = query.join(Campaign, SearchTerm.campaign_id == Campaign.id).filter(
            Campaign.client_id == rule.client_id
        )

    query = query.filter(and_(*filters))
    entities = query.all()

    return [_get_entity_summary(e, rule.entity_type) for e in entities]


# ── Action execution ──────────────────────────────────────────────────────


def _execute_pause(entity_match: dict, rule: AutomatedRule, db: Session) -> str:
    """Set the entity's status to PAUSED."""
    model = ENTITY_MODELS.get(rule.entity_type)
    if not model:
        return "error: unknown entity type"

    entity = db.query(model).filter(model.id == entity_match["id"]).first()
    if not entity:
        return "error: entity not found"

    current_status = getattr(entity, "status", None)
    if current_status == "PAUSED":
        return "skipped: already paused"

    entity.status = "PAUSED"
    return "paused"


def _execute_add_negative(entity_match: dict, rule: AutomatedRule, db: Session) -> str:
    """Add the entity's text as a negative keyword."""
    text = entity_match.get("name", "")
    if not text:
        return "error: no text to negate"

    params = rule.action_params or {}
    match_type = params.get("match_type", "PHRASE")

    # Find campaign_id for the negative keyword
    campaign_id = None
    if rule.entity_type == "search_term":
        st = db.query(SearchTerm).filter(SearchTerm.id == entity_match["id"]).first()
        if st:
            campaign_id = st.campaign_id
    elif rule.entity_type == "keyword":
        from app.models.ad_group import AdGroup
        kw = db.query(Keyword).filter(Keyword.id == entity_match["id"]).first()
        if kw:
            ag = db.query(AdGroup).filter(AdGroup.id == kw.ad_group_id).first()
            if ag:
                campaign_id = ag.campaign_id

    if not campaign_id:
        return "error: could not determine campaign"

    # Check if negative already exists
    existing = (
        db.query(NegativeKeyword)
        .filter(
            NegativeKeyword.client_id == rule.client_id,
            NegativeKeyword.campaign_id == campaign_id,
            NegativeKeyword.text == text,
        )
        .first()
    )
    if existing:
        return "skipped: negative already exists"

    neg = NegativeKeyword(
        client_id=rule.client_id,
        campaign_id=campaign_id,
        text=text,
        match_type=match_type,
        status="ENABLED",
        source="AUTOMATED_RULE",
    )
    db.add(neg)
    return "added_negative"


def _execute_alert(entity_match: dict, rule: AutomatedRule, db: Session) -> str:
    """Create an Alert record for the matched entity."""
    params = rule.action_params or {}
    severity = params.get("severity", "MEDIUM")

    alert = Alert(
        client_id=rule.client_id,
        alert_type="AUTOMATED_RULE",
        severity=severity,
        title=f"Regula '{rule.name}': {entity_match.get('name', 'N/A')}",
        description=f"Regula automatyczna #{rule.id} wykryla dopasowanie: {entity_match.get('name', '')}",
        metric_value=str(entity_match.get("cost_micros", "")),
    )
    db.add(alert)
    return "alert_created"


_ACTION_EXECUTORS = {
    "PAUSE": _execute_pause,
    "ADD_NEGATIVE": _execute_add_negative,
    "ALERT": _execute_alert,
}


def execute_rule(rule: AutomatedRule, db: Session, dry_run: bool = True) -> dict:
    """Evaluate a rule and optionally execute actions.

    Returns a dict with matches, actions taken, and per-entity results.
    """
    matches = evaluate_rule(rule, db)
    now = datetime.now(timezone.utc)

    result = {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "entity_type": rule.entity_type,
        "action_type": rule.action_type,
        "dry_run": dry_run,
        "matches_found": len(matches),
        "actions_taken": 0,
        "details": [],
    }

    executor_fn = _ACTION_EXECUTORS.get(rule.action_type)
    if not executor_fn and not dry_run:
        result["error"] = f"Unknown action_type: {rule.action_type}"
        return result

    for match in matches:
        detail = {**match, "action_result": "dry_run" if dry_run else None}

        if not dry_run and executor_fn:
            try:
                action_result = executor_fn(match, rule, db)
                detail["action_result"] = action_result
                if action_result and not action_result.startswith("error") and not action_result.startswith("skipped"):
                    result["actions_taken"] += 1
            except Exception as exc:
                detail["action_result"] = f"error: {str(exc)[:200]}"
                logger.error(f"Rule #{rule.id} action failed for entity #{match['id']}: {exc}")

        result["details"].append(detail)

    # Update rule metadata
    rule.last_run_at = now
    rule.matches_last_run = len(matches)

    # Create log entry
    log_entry = AutomatedRuleLog(
        rule_id=rule.id,
        run_at=now,
        matches_found=len(matches),
        actions_taken=result["actions_taken"],
        dry_run=dry_run,
        result=result,
    )
    db.add(log_entry)
    db.commit()

    return result
