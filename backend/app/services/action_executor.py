"""Action Executor - executes validated actions and handles revert flow."""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.action_log import ActionLog
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.recommendation import Recommendation
from app.services.action_types import ActionType, map_action_type
from app.utils.constants import SAFETY_LIMITS
from app.utils.formatters import micros_to_currency


class SafetyViolationError(Exception):
    """Raised when action violates SAFETY_LIMITS."""


def get_effective_limits(client_limits: Optional[dict] = None) -> dict:
    limits = dict(SAFETY_LIMITS)
    if client_limits:
        for key in SAFETY_LIMITS:
            if key in client_limits and client_limits[key] is not None:
                limits[key] = client_limits[key]
    return limits


def validate_action(
    action_type: str,
    current_val: float,
    new_val: float,
    context: dict,
    client_limits: Optional[dict] = None,
) -> None:
    limits = get_effective_limits(client_limits)

    if action_type in ("UPDATE_BID", "SET_BID", "SET_KEYWORD_BID"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change bid: current bid is 0 or None")

        pct_change = abs(new_val - current_val) / current_val
        if pct_change > limits["MAX_BID_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Bid change {pct_change:.0%} exceeds {limits['MAX_BID_CHANGE_PCT']:.0%} limit. "
                f"${current_val:.2f} -> ${new_val:.2f}"
            )

        if new_val < limits["MIN_BID_USD"]:
            raise SafetyViolationError(
                f"New bid ${new_val:.2f} below minimum ${limits['MIN_BID_USD']:.2f}"
            )

        if new_val > limits["MAX_BID_USD"]:
            raise SafetyViolationError(
                f"New bid ${new_val:.2f} above maximum ${limits['MAX_BID_USD']:.2f}"
            )

    if action_type in ("INCREASE_BUDGET", "SET_BUDGET"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change budget: current budget is 0 or None")

        pct_change = abs(new_val - current_val) / current_val
        if pct_change > limits["MAX_BUDGET_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Budget change {pct_change:.0%} exceeds {limits['MAX_BUDGET_CHANGE_PCT']:.0%} limit"
            )

    if action_type == "PAUSE_KEYWORD":
        total = context.get("total_keywords_in_campaign", 0)
        paused_today = context.get("keywords_paused_today_in_campaign", 0)
        if total > 0 and (paused_today + 1) / total > limits["MAX_KEYWORD_PAUSE_PCT"]:
            raise SafetyViolationError(
                f"Already paused {paused_today}/{total} keywords today. "
                f"Limit: {limits['MAX_KEYWORD_PAUSE_PCT']:.0%}"
            )

    if action_type == "ADD_NEGATIVE":
        negatives_today = context.get("negatives_added_today", 0)
        if negatives_today >= limits["MAX_NEGATIVES_PER_DAY"]:
            raise SafetyViolationError(
                f"Daily negative limit reached: {negatives_today}/{limits['MAX_NEGATIVES_PER_DAY']}"
            )


class ActionExecutor:
    """Executes actions on Google Ads API with validation and logging."""

    def __init__(self, db: Session):
        self.db = db

    def apply_recommendation(self, recommendation_id: int, client_id: int, dry_run: bool = False) -> dict:
        rec = self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.client_id == client_id,
            Recommendation.status == "pending",
        ).first()

        if not rec:
            return {"status": "error", "message": "Recommendation not found or already applied"}

        action = json.loads(rec.suggested_action)

        try:
            canonical_action_type, action = self._normalize_action(action)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        context = self._build_context(action, client_id)
        current_val, new_val = self._extract_values(action)
        client_limits = self._get_client_limits(client_id)

        try:
            validate_action(canonical_action_type.value, current_val, new_val, context, client_limits)
        except SafetyViolationError as e:
            return {"status": "blocked", "reason": str(e)}

        if dry_run:
            return {
                "status": "dry_run",
                "action": action,
                "canonical_action_type": canonical_action_type.value,
                "current_val": current_val,
                "new_val": new_val,
                "message": "Dry run - action NOT applied.",
            }

        try:
            from app.services.google_ads import google_ads_service

            old_value_json = json.dumps({"current_val": current_val})
            new_value_json = json.dumps({"new_val": new_val})

            api_result = google_ads_service.apply_action(
                self.db,
                canonical_action_type.value,
                entity_id=action.get("entity_id"),
                params=action.get("params", {}),
                client_id=client_id,
            )
            if api_result.get("status") == "error":
                raise Exception(api_result.get("message", "API call failed"))

            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=canonical_action_type.value,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=str(action.get("entity_id", "")),
                old_value_json=old_value_json,
                new_value_json=new_value_json,
                status="SUCCESS",
            )
            self.db.add(log_entry)

            rec.status = "applied"
            rec.applied_at = datetime.utcnow()
            self.db.commit()

            return {
                "status": "success",
                "action_type": canonical_action_type.value,
                "message": "Action applied successfully",
            }

        except Exception as e:
            self.db.rollback()
            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=canonical_action_type.value,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=str(action.get("entity_id", "")),
                status="FAILED",
                error_message=str(e),
            )
            self.db.add(log_entry)
            self.db.commit()
            return {"status": "error", "message": str(e)}

    def revert_action(self, action_log_id: int) -> dict:
        original = self.db.query(ActionLog).filter(ActionLog.id == action_log_id).first()

        if not original:
            return {"status": "error", "message": "Action not found"}
        if original.status == "REVERTED":
            return {"status": "error", "message": "Already reverted"}
        if original.status != "SUCCESS":
            return {"status": "error", "message": f"Cannot revert {original.status} action"}

        time_elapsed = datetime.utcnow() - original.executed_at
        if time_elapsed > timedelta(hours=24):
            return {"status": "error", "message": "Revert window (24h) expired"}

        if original.action_type in ["ADD_NEGATIVE"]:
            return {"status": "error", "message": f"{original.action_type} cannot be reverted"}

        if not original.old_value_json:
            return {"status": "error", "message": "Missing previous state - cannot revert"}

        try:
            from app.services.google_ads import google_ads_service

            old_state = json.loads(original.old_value_json)

            if original.action_type == ActionType.PAUSE_KEYWORD.value:
                google_ads_service.apply_action(
                    self.db, ActionType.ENABLE_KEYWORD.value, entity_id=int(original.entity_id), params={}, client_id=original.client_id
                )
            elif original.action_type == ActionType.UPDATE_BID.value:
                google_ads_service.apply_action(
                    self.db,
                    ActionType.SET_KEYWORD_BID.value,
                    entity_id=int(original.entity_id),
                    params={"amount": old_state.get("current_val", 0)},
                    client_id=original.client_id,
                )
            elif original.action_type == ActionType.ADD_KEYWORD.value:
                google_ads_service.apply_action(
                    self.db, ActionType.PAUSE_KEYWORD.value, entity_id=int(original.entity_id), params={}, client_id=original.client_id
                )

            original.status = "REVERTED"
            original.reverted_at = datetime.utcnow()

            revert_log = ActionLog(
                client_id=original.client_id,
                action_type=f"REVERT_{original.action_type}",
                entity_type=original.entity_type,
                entity_id=original.entity_id,
                old_value_json=original.new_value_json,
                new_value_json=original.old_value_json,
                status="SUCCESS",
            )
            self.db.add(revert_log)
            self.db.commit()
            return {"status": "success", "message": f"Reverted: {original.action_type}"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Revert failed: {str(e)}"}

    def _get_client_limits(self, client_id: int) -> Optional[dict]:
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client or not client.business_rules:
            return None
        return (client.business_rules or {}).get("safety_limits")

    def _normalize_action(self, action: Dict) -> Tuple[ActionType, Dict]:
        action_type_raw = action.get("type")
        canonical = map_action_type(action_type_raw)

        params = action.get("params", {}) or {}
        entity_id = action.get("entity_id")

        if canonical == ActionType.UPDATE_BID and action_type_raw in ("INCREASE_BID", "DECREASE_BID"):
            keyword = self.db.query(Keyword).filter(Keyword.id == entity_id).first()
            if not keyword:
                raise ValueError(f"Keyword {entity_id} not found")

            current_bid = micros_to_currency(keyword.bid_micros)
            if current_bid <= 0:
                raise ValueError("Cannot apply bid change: current bid is 0")

            change_pct = float(params.get("change_pct", 20)) / 100.0
            if action_type_raw == "DECREASE_BID":
                new_bid = current_bid * (1 - change_pct)
            else:
                new_bid = current_bid * (1 + change_pct)

            action["params"] = {"amount": round(new_bid, 2)}

        action["type"] = canonical.value
        return canonical, action

    def _build_context(self, action: dict, client_id: int) -> dict:
        context = {}
        today = datetime.utcnow().date()

        if action.get("campaign_id"):
            context["total_keywords_in_campaign"] = self.db.query(Keyword).join(Keyword.ad_group).filter(
                Keyword.ad_group.has(campaign_id=action["campaign_id"])
            ).count()

            context["keywords_paused_today_in_campaign"] = self.db.query(ActionLog).filter(
                ActionLog.client_id == client_id,
                ActionLog.action_type == "PAUSE_KEYWORD",
                func.date(ActionLog.executed_at) == today,
            ).count()

        context["negatives_added_today"] = self.db.query(ActionLog).filter(
            ActionLog.client_id == client_id,
            ActionLog.action_type == "ADD_NEGATIVE",
            func.date(ActionLog.executed_at) == today,
        ).count()

        return context

    def _extract_values(self, action: dict) -> Tuple[float, float]:
        action_type = action.get("type")
        params = action.get("params", {}) or {}
        entity_id = action.get("entity_id")

        if action_type in (ActionType.UPDATE_BID.value, ActionType.SET_KEYWORD_BID.value):
            keyword = self.db.query(Keyword).filter(Keyword.id == entity_id).first()
            current = micros_to_currency(keyword.bid_micros) if keyword else 0.0
            new = float(params.get("amount", 0.0))
            return (float(current), float(new))

        current = action.get("current_value", 0.0)
        new = action.get("new_value", 0.0)
        return (float(current), float(new))
