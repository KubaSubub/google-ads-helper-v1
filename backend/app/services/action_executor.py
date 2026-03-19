"""Action Executor - validates and executes canonical recommendation actions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.demo_guard import demo_write_lock_reason, is_demo_protected_client
from app.models.action_log import ActionLog
from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.recommendation import Recommendation
from app.services.recommendation_contract import micros_to_float
from app.utils.constants import SAFETY_LIMITS
from app.utils.formatters import currency_to_micros, micros_to_currency


class SafetyViolationError(Exception):
    """Raised when action violates SAFETY_LIMITS."""


class PreconditionFailedError(Exception):
    """Raised when recommendation payload no longer matches entity state."""


REVERSIBLE_ACTIONS = {
    "PAUSE_KEYWORD": {"can_revert": True, "window_hours": 24, "strategy": "ENABLE_KEYWORD"},
    "UPDATE_BID": {"can_revert": True, "window_hours": 24, "strategy": "SET_KEYWORD_BID"},
    "ADD_KEYWORD": {"can_revert": True, "window_hours": 24, "strategy": "PAUSE_KEYWORD"},
    "INCREASE_BUDGET": {"can_revert": True, "window_hours": 24, "strategy": "SET_BUDGET"},
    "PAUSE_AD": {"can_revert": False, "window_hours": 0, "strategy": None},
    "ADD_NEGATIVE": {"can_revert": False, "window_hours": 0, "strategy": None},
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_effective_limits(client_limits: Optional[dict] = None) -> dict:
    """Merge per-client safety overrides with global defaults."""
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
    """Circuit breaker for canonical action payloads."""
    limits = get_effective_limits(client_limits)

    if action_type in {"UPDATE_BID", "SET_BID", "SET_KEYWORD_BID"}:
        if not current_val or current_val <= 0:
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

    if action_type in {"INCREASE_BUDGET", "SET_BUDGET"}:
        if not current_val or current_val <= 0:
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

    if action_type == "ADD_KEYWORD" and context.get("keyword_exists"):
        raise SafetyViolationError("Keyword already exists in the target ad group")


class ActionExecutor:
    """Executes recommendation actions with preconditions and audit logging."""

    def __init__(self, db: Session):
        self.db = db

    def apply_recommendation(
        self,
        recommendation_id: int,
        client_id: int,
        dry_run: bool = False,
        allow_demo_write: bool = False,
    ) -> dict:
        if is_demo_protected_client(self.db, client_id) and not allow_demo_write:
            return {
                "status": "blocked",
                "reason": demo_write_lock_reason("Zastosowanie rekomendacji"),
            }

        rec = (
            self.db.query(Recommendation)
            .filter(
                Recommendation.id == recommendation_id,
                Recommendation.client_id == client_id,
                Recommendation.status == "pending",
            )
            .first()
        )

        if not rec:
            return {"status": "error", "message": "Recommendation not found or already applied"}

        payload = self._normalize_action_payload(rec)
        action_type = payload.get("action_type")
        mode = "DRY_RUN" if dry_run else "LIVE"

        if not action_type or not payload.get("executable"):
            reason = "Recommendation is not executable"
            self._record_log(
                recommendation=rec,
                action_type=action_type or rec.rule_id,
                entity_type=self._log_entity_type(payload),
                entity_id=self._log_entity_id(payload),
                status="BLOCKED",
                execution_mode=mode,
                precondition_status="NOT_EXECUTABLE",
                action_payload=payload,
                context_json={"reason": reason},
                error_message=reason,
            )
            self.db.commit()
            return {"status": "blocked", "reason": reason}

        client_record = self.db.query(Client).filter(Client.id == client_id).first()
        client_limits = ((client_record.business_rules or {}).get("safety_limits") if client_record else None)

        try:
            context = self._build_context(payload, client_id)
            precondition_state = self._evaluate_preconditions(rec, payload, context)
            current_val, new_val = self._extract_values(payload, precondition_state)
            context.update(precondition_state)
            validate_action(action_type, current_val, new_val, context, client_limits)
        except (PreconditionFailedError, SafetyViolationError) as exc:
            self._record_log(
                recommendation=rec,
                action_type=action_type,
                entity_type=self._log_entity_type(payload),
                entity_id=self._log_entity_id(payload),
                status="BLOCKED",
                execution_mode=mode,
                precondition_status="FAILED",
                action_payload=payload,
                context_json=context if 'context' in locals() else {},
                old_value_json=self._json_dumps(self._build_before_state(payload, precondition_state if 'precondition_state' in locals() else {})),
                new_value_json=self._json_dumps(self._build_after_state(payload, precondition_state if 'precondition_state' in locals() else {})),
                error_message=str(exc),
            )
            self.db.commit()
            return {"status": "blocked", "reason": str(exc)}

        before_state = self._build_before_state(payload, precondition_state)
        after_state = self._build_after_state(payload, precondition_state)

        if dry_run:
            self._record_log(
                recommendation=rec,
                action_type=action_type,
                entity_type=self._log_entity_type(payload),
                entity_id=self._log_entity_id(payload),
                status="DRY_RUN",
                execution_mode="DRY_RUN",
                precondition_status="PASSED",
                action_payload=payload,
                context_json=context,
                old_value_json=self._json_dumps(before_state),
                new_value_json=self._json_dumps(after_state),
            )
            self.db.commit()
            return {
                "status": "dry_run",
                "action": payload,
                "current_val": current_val,
                "new_val": new_val,
                "before_state": before_state,
                "after_state": after_state,
                "message": "Dry run - action not applied.",
            }

        from app.services.google_ads import google_ads_service

        try:
            api_result = google_ads_service.apply_action(
                self.db,
                action_type=action_type,
                entity_id=self._log_entity_id(payload),
                params=payload.get("params") or {},
                target=payload.get("target") or {},
            )
            if api_result.get("status") != "success":
                raise RuntimeError(api_result.get("message", "API call failed"))

            if api_result.get("entity_id"):
                payload.setdefault("target", {})["entity_id"] = api_result["entity_id"]
            if api_result.get("entity_type"):
                payload.setdefault("target", {})["entity_type"] = api_result["entity_type"]

            log_entry = self._record_log(
                recommendation=rec,
                action_type=action_type,
                entity_type=api_result.get("entity_type") or self._log_entity_type(payload),
                entity_id=api_result.get("entity_id") or self._log_entity_id(payload),
                status="SUCCESS",
                execution_mode=api_result.get("mode", "LIVE"),
                precondition_status="PASSED",
                action_payload=payload,
                context_json={**context, **{k: v for k, v in api_result.items() if k not in {"status", "message"}}},
                old_value_json=self._json_dumps(before_state),
                new_value_json=self._json_dumps(after_state),
            )

            rec.status = "applied"
            rec.applied_at = utcnow().replace(tzinfo=None)
            rec.action_payload = payload
            self.db.commit()

            return {
                "status": "success",
                "action_type": action_type,
                "message": api_result.get("message", "Action applied successfully"),
                "before_state": before_state,
                "after_state": after_state,
                "action_log_id": log_entry.id if log_entry else None,
                "mode": api_result.get("mode", "LIVE"),
            }

        except Exception as exc:
            self.db.rollback()
            self._record_log(
                recommendation=rec,
                action_type=action_type,
                entity_type=self._log_entity_type(payload),
                entity_id=self._log_entity_id(payload),
                status="FAILED",
                execution_mode="LIVE",
                precondition_status="PASSED",
                action_payload=payload,
                context_json=context,
                old_value_json=self._json_dumps(before_state),
                new_value_json=self._json_dumps(after_state),
                error_message=str(exc),
            )
            self.db.commit()  # new transaction after rollback — persist FAILED log
            return {"status": "error", "message": str(exc)}

    def revert_action(self, action_log_id: int, allow_demo_write: bool = False) -> dict:
        original = self.db.query(ActionLog).filter(ActionLog.id == action_log_id).first()
        if not original:
            return {"status": "error", "message": "Action not found"}
        if is_demo_protected_client(self.db, original.client_id) and not allow_demo_write:
            return {"status": "error", "message": demo_write_lock_reason("Cofanie akcji")}

        if original.status == "REVERTED":
            return {"status": "error", "message": "Already reverted"}

        if original.status != "SUCCESS":
            return {"status": "error", "message": f"Cannot revert {original.status} action"}

        executed_at = original.executed_at or utcnow().replace(tzinfo=None)
        if executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=timezone.utc)
        if utcnow() - executed_at > timedelta(hours=24):
            return {"status": "error", "message": "Revert window (24h) expired"}

        payload = original.action_payload or {}
        revertability = payload.get("revertability") or REVERSIBLE_ACTIONS.get(original.action_type, {})
        reverse_action = revertability.get("strategy")
        if not reverse_action:
            return {"status": "error", "message": f"{original.action_type} cannot be reverted"}

        old_state = self._json_loads(original.old_value_json)
        target_entity_id = self._coerce_int(original.entity_id)

        params: dict[str, Any] = {}
        target = (payload.get("target") or {}).copy()
        if original.action_type == "UPDATE_BID":
            previous_bid = old_state.get("bid") or old_state.get("current_bid") or old_state.get("current_value")
            if previous_bid is None:
                return {"status": "error", "message": "Missing previous bid - cannot revert"}
            params["amount"] = float(previous_bid)
            params["amount_micros"] = currency_to_micros(float(previous_bid))
        elif original.action_type == "INCREASE_BUDGET":
            previous_budget = old_state.get("budget") or old_state.get("current_budget") or old_state.get("current_value")
            if previous_budget is None:
                return {"status": "error", "message": "Missing previous budget - cannot revert"}
            params["amount"] = float(previous_budget)
            params["amount_micros"] = currency_to_micros(float(previous_budget))
        elif original.action_type == "ADD_KEYWORD":
            reverse_action = "PAUSE_KEYWORD"
        elif original.action_type == "PAUSE_KEYWORD":
            reverse_action = "ENABLE_KEYWORD"

        from app.services.google_ads import google_ads_service

        try:
            result = google_ads_service.apply_action(
                self.db,
                action_type=reverse_action,
                entity_id=target_entity_id,
                params=params,
                target=target,
            )
            if result.get("status") != "success":
                raise RuntimeError(result.get("message", "Revert failed"))

            original.status = "REVERTED"
            original.reverted_at = utcnow().replace(tzinfo=None)

            self._record_log(
                recommendation=None,
                recommendation_id=original.recommendation_id,
                client_id=original.client_id,
                action_type=f"REVERT_{original.action_type}",
                entity_type=result.get("entity_type") or original.entity_type,
                entity_id=result.get("entity_id") or target_entity_id,
                status="SUCCESS",
                execution_mode=result.get("mode", "LIVE"),
                precondition_status="PASSED",
                action_payload={
                    "action_type": reverse_action,
                    "target": target,
                    "params": params,
                },
                context_json={"original_action_log_id": original.id},
                old_value_json=original.new_value_json,
                new_value_json=original.old_value_json,
            )
            self.db.commit()
            return {"status": "success", "message": f"Reverted: {original.action_type}"}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": f"Revert failed: {exc}"}

    def _normalize_action_payload(self, rec: Recommendation) -> dict:
        payload = rec.action_payload or {}
        if payload.get("action_type"):
            payload.setdefault("target", {})
            payload.setdefault("params", {})
            payload.setdefault("preconditions", {})
            payload.setdefault("revertability", REVERSIBLE_ACTIONS.get(payload["action_type"], {}))
            return payload

        fallback = self._json_loads(rec.suggested_action)
        action_type = fallback.get("action_type") or fallback.get("type") or rec.rule_id
        target = {
            "entity_type": fallback.get("entity_type") or rec.entity_type,
            "entity_id": self._coerce_int(fallback.get("entity_id")) or self._coerce_int(rec.entity_id),
            "campaign_id": fallback.get("campaign_id") or rec.campaign_id,
            "ad_group_id": fallback.get("ad_group_id") or rec.ad_group_id,
            "google_resource_name": fallback.get("google_resource_name") or rec.google_resource_name,
        }
        payload = {
            "action_type": action_type,
            "target": target,
            "params": fallback.get("params") or {},
            "preconditions": fallback.get("preconditions") or {},
            "revertability": fallback.get("revertability") or REVERSIBLE_ACTIONS.get(action_type, {}),
            "executable": fallback.get("executable", True),
            "current_value": fallback.get("current_value"),
            "new_value": fallback.get("new_value"),
        }
        if action_type == "ADD_KEYWORD" and target.get("ad_group_id"):
            payload["params"].setdefault("ad_group_id", target["ad_group_id"])
        if action_type == "ADD_NEGATIVE" and target.get("campaign_id"):
            payload["params"].setdefault("campaign_id", target["campaign_id"])
        return payload

    def _build_context(self, payload: dict, client_id: int) -> dict:
        target = payload.get("target") or {}
        action_type = payload.get("action_type")
        context: dict[str, Any] = {"client_id": client_id}
        today = utcnow().date()
        campaign_id = target.get("campaign_id")

        if action_type == "PAUSE_KEYWORD" and campaign_id:
            context["total_keywords_in_campaign"] = (
                self.db.query(Keyword)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .filter(AdGroup.campaign_id == campaign_id)
                .count()
            )
            context["keywords_paused_today_in_campaign"] = (
                self.db.query(ActionLog)
                .filter(
                    ActionLog.client_id == client_id,
                    ActionLog.action_type == "PAUSE_KEYWORD",
                    ActionLog.status == "SUCCESS",
                    func.date(ActionLog.executed_at) == today,
                )
                .count()
            )

        if action_type == "ADD_NEGATIVE":
            context["negatives_added_today"] = (
                self.db.query(ActionLog)
                .filter(
                    ActionLog.client_id == client_id,
                    ActionLog.action_type == "ADD_NEGATIVE",
                    ActionLog.status == "SUCCESS",
                    func.date(ActionLog.executed_at) == today,
                )
                .count()
            )

        if action_type == "ADD_KEYWORD":
            text = ((payload.get("params") or {}).get("text") or "").strip().lower()
            ad_group_id = target.get("ad_group_id") or (payload.get("params") or {}).get("ad_group_id")
            context["keyword_exists"] = bool(
                text
                and ad_group_id
                and self.db.query(Keyword)
                .filter(
                    Keyword.ad_group_id == ad_group_id,
                    func.lower(Keyword.text) == text,
                    Keyword.status != "REMOVED",
                )
                .first()
            )

        return context

    def _evaluate_preconditions(self, rec: Recommendation, payload: dict, context: dict) -> dict:
        target = payload.get("target") or {}
        params = payload.get("params") or {}
        preconditions = payload.get("preconditions") or {}
        entity_type = target.get("entity_type")
        entity_id = self._coerce_int(target.get("entity_id"))
        state: dict[str, Any] = {}

        if rec.expires_at:
            expires_at = rec.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < utcnow():
                raise PreconditionFailedError("Recommendation expired - regenerate before applying")

        entity = None
        if entity_type == "keyword" and entity_id:
            entity = self.db.get(Keyword, entity_id)
        elif entity_type == "ad" and entity_id:
            entity = self.db.get(Ad, entity_id)
        elif entity_type == "campaign" and entity_id:
            entity = self.db.get(Campaign, entity_id)

        if preconditions.get("entity_exists") and entity_type in {"keyword", "ad", "campaign"} and not entity:
            raise PreconditionFailedError("Target entity no longer exists")

        expected_status = preconditions.get("expected_status")
        if expected_status and entity is not None:
            actual_status = getattr(entity, "status", None)
            state["current_status"] = actual_status
            if actual_status != expected_status:
                raise PreconditionFailedError(
                    f"Expected status {expected_status}, found {actual_status or 'UNKNOWN'}"
                )

        if "current_bid_micros" in preconditions:
            if not entity or not isinstance(entity, Keyword):
                raise PreconditionFailedError("Keyword context missing for bid update")
            current_bid = int(entity.bid_micros or 0)
            state["current_bid_micros"] = current_bid
            if current_bid != int(preconditions["current_bid_micros"]):
                raise PreconditionFailedError("Current bid changed since recommendation was generated")

        if "current_budget_micros" in preconditions:
            if not entity or not isinstance(entity, Campaign):
                raise PreconditionFailedError("Campaign context missing for budget update")
            current_budget = int(entity.budget_micros or 0)
            state["current_budget_micros"] = current_budget
            if current_budget != int(preconditions["current_budget_micros"]):
                raise PreconditionFailedError("Current budget changed since recommendation was generated")

        if preconditions.get("keyword_absent"):
            ad_group_id = target.get("ad_group_id") or params.get("ad_group_id")
            text = (params.get("text") or "").strip().lower()
            existing = None
            if ad_group_id and text:
                existing = (
                    self.db.query(Keyword)
                    .filter(
                        Keyword.ad_group_id == ad_group_id,
                        func.lower(Keyword.text) == text,
                        Keyword.status != "REMOVED",
                    )
                    .first()
                )
            if existing:
                raise PreconditionFailedError("Keyword already exists in target ad group")

        if payload.get("action_type") == "ADD_NEGATIVE":
            campaign_id = target.get("campaign_id") or params.get("campaign_id")
            text = (params.get("text") or "").strip().lower()
            if not campaign_id:
                raise PreconditionFailedError("Campaign-level negative requires campaign scope")
            duplicate = (
                self.db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.campaign_id == campaign_id,
                    NegativeKeyword.negative_scope == "CAMPAIGN",
                    func.lower(NegativeKeyword.text) == text,
                    NegativeKeyword.status != "REMOVED",
                )
                .first()
            )
            if duplicate:
                raise PreconditionFailedError("Negative keyword already exists at campaign level")

        state["entity_exists"] = entity is not None or entity_type not in {"keyword", "ad", "campaign"}
        return state

    def _extract_values(self, payload: dict, precondition_state: dict) -> Tuple[float, float]:
        params = payload.get("params") or {}
        current = payload.get("current_value")
        new = payload.get("new_value")
        action_type = payload.get("action_type")

        if current is None and action_type == "UPDATE_BID":
            current = micros_to_float(precondition_state.get("current_bid_micros"))
        if new is None and action_type == "UPDATE_BID":
            new = float(params.get("amount") or micros_to_currency(params.get("amount_micros") or 0))

        if current is None and action_type == "INCREASE_BUDGET":
            current = micros_to_float(precondition_state.get("current_budget_micros"))
        if new is None and action_type == "INCREASE_BUDGET":
            new = float(params.get("amount") or micros_to_currency(params.get("amount_micros") or 0))

        return (float(current or 0), float(new or 0))

    def _build_before_state(self, payload: dict, state: dict) -> dict:
        target = payload.get("target") or {}
        action_type = payload.get("action_type")
        before: dict[str, Any] = {}

        if action_type == "PAUSE_KEYWORD":
            before["status"] = state.get("current_status", "ENABLED")
        elif action_type == "PAUSE_AD":
            before["status"] = state.get("current_status", "ENABLED")
        elif action_type == "UPDATE_BID":
            before["bid"] = round(micros_to_currency(state.get("current_bid_micros") or 0), 2)
        elif action_type == "INCREASE_BUDGET":
            before["budget"] = round(micros_to_currency(state.get("current_budget_micros") or 0), 2)
        elif action_type == "ADD_KEYWORD":
            before["keyword"] = "absent"
            before["ad_group_id"] = target.get("ad_group_id")
        elif action_type == "ADD_NEGATIVE":
            before["negative"] = "absent"
            before["campaign_id"] = target.get("campaign_id") or (payload.get("params") or {}).get("campaign_id")
        return before

    def _build_after_state(self, payload: dict, state: dict) -> dict:
        params = payload.get("params") or {}
        action_type = payload.get("action_type")
        after: dict[str, Any] = {}

        if action_type in {"PAUSE_KEYWORD", "PAUSE_AD"}:
            after["status"] = "PAUSED"
        elif action_type == "UPDATE_BID":
            amount = float(params.get("amount") or micros_to_currency(params.get("amount_micros") or 0))
            after["bid"] = round(amount, 2)
        elif action_type == "INCREASE_BUDGET":
            amount = float(params.get("amount") or micros_to_currency(params.get("amount_micros") or 0))
            after["budget"] = round(amount, 2)
        elif action_type == "ADD_KEYWORD":
            after["keyword"] = params.get("text")
            after["match_type"] = params.get("match_type")
            after["status"] = "ENABLED"
        elif action_type == "ADD_NEGATIVE":
            after["negative"] = params.get("text")
            after["match_type"] = params.get("match_type")
            after["level"] = params.get("negative_level")
        return after

    def _record_log(
        self,
        recommendation: Recommendation | None,
        action_type: str,
        entity_type: str,
        entity_id: Any,
        status: str,
        execution_mode: str,
        precondition_status: str,
        action_payload: dict,
        context_json: dict,
        old_value_json: str | None = None,
        new_value_json: str | None = None,
        error_message: str | None = None,
        recommendation_id: int | None = None,
        client_id: int | None = None,
    ) -> ActionLog:
        log_entry = ActionLog(
            client_id=client_id or (recommendation.client_id if recommendation else None),
            recommendation_id=recommendation_id if recommendation_id is not None else (recommendation.id if recommendation else None),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id or 0),
            old_value_json=old_value_json,
            new_value_json=new_value_json,
            status=status,
            error_message=error_message,
            execution_mode=execution_mode,
            precondition_status=precondition_status,
            context_json=context_json,
            action_payload=action_payload,
        )
        self.db.add(log_entry)
        self.db.flush()
        return log_entry

    def _log_entity_type(self, payload: dict) -> str:
        return ((payload.get("target") or {}).get("entity_type") or "keyword")

    def _log_entity_id(self, payload: dict) -> int:
        target = payload.get("target") or {}
        params = payload.get("params") or {}
        return (
            self._coerce_int(target.get("entity_id"))
            or self._coerce_int(target.get("campaign_id"))
            or self._coerce_int(target.get("ad_group_id"))
            or self._coerce_int(params.get("campaign_id"))
            or self._coerce_int(params.get("ad_group_id"))
            or 0
        )

    @staticmethod
    def _json_loads(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            return json.loads(value)
        except Exception:
            return {}

    @staticmethod
    def _json_dumps(value: dict | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value in (None, "", 0, "0"):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


