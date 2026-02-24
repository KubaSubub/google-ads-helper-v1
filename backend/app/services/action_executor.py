"""Action Executor - Executes actions on Google Ads API with safety validation.

CLAUDE.md Reguła 4: EVERY write to Google Ads API MUST pass through validate_action().
CLAUDE.md Reguła 6: NEVER let exceptions crash silently.

This module handles:
- Circuit breaker (validate_action) - prevents unsafe actions
- Action execution with logging
- Revert/undo functionality (Feature 4)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.recommendation import Recommendation
from app.models.action_log import ActionLog
from app.models.keyword import Keyword
from app.models.client import Client
from app.utils.constants import SAFETY_LIMITS
from app.utils.formatters import micros_to_currency, currency_to_micros


class SafetyViolationError(Exception):
    """Raised when action violates SAFETY_LIMITS."""
    pass


def get_effective_limits(client_limits: Optional[dict] = None) -> dict:
    """Merge per-client safety overrides with global defaults.

    Client limits are stored in Client.business_rules["safety_limits"].
    Only keys that exist in SAFETY_LIMITS can be overridden.
    """
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
    """Circuit breaker - validates action safety before execution.

    CRITICAL: This function MUST be called before EVERY write to Google Ads API.

    Args:
        action_type: Type of action (UPDATE_BID, PAUSE_KEYWORD, etc.)
        current_val: Current value in USD (not micros)
        new_val: New value in USD (not micros)
        context: Additional context (campaign stats, daily counts, etc.)
        client_limits: Optional per-client safety limit overrides

    Raises:
        SafetyViolationError: If action violates safety limits
    """
    limits = get_effective_limits(client_limits)

    if action_type in ("UPDATE_BID", "SET_BID"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change bid: current bid is 0 or None")

        pct_change = abs(new_val - current_val) / current_val
        if pct_change > limits["MAX_BID_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Bid change {pct_change:.0%} exceeds {limits['MAX_BID_CHANGE_PCT']:.0%} limit. "
                f"${current_val:.2f} → ${new_val:.2f}"
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
                f"Budget change {pct_change:.0%} exceeds "
                f"{limits['MAX_BUDGET_CHANGE_PCT']:.0%} limit"
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
                f"Daily negative limit reached: "
                f"{negatives_today}/{limits['MAX_NEGATIVES_PER_DAY']}"
            )


class ActionExecutor:
    """Executes actions on Google Ads API with validation and logging."""

    def __init__(self, db: Session):
        self.db = db

    def apply_recommendation(
        self,
        recommendation_id: int,
        client_id: int,
        dry_run: bool = False
    ) -> dict:
        """Apply recommendation via Google Ads API.

        Flow:
        1. Fetch recommendation from DB
        2. Build context for validation
        3. validate_action() — circuit breaker
        4. If dry_run → return preview
        5. Execute via Google Ads API (TODO: implement API call)
        6. Log to action_log
        7. Update recommendation status

        Args:
            recommendation_id: Recommendation ID
            client_id: Client ID (for security check)
            dry_run: If True, validate but don't execute

        Returns:
            Dict with status, action details, and any errors
        """
        # 1. Fetch recommendation
        rec = self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.client_id == client_id,
            Recommendation.status == "pending"
        ).first()

        if not rec:
            return {
                "status": "error",
                "message": "Recommendation not found or already applied"
            }

        # Parse suggested action JSON
        action = json.loads(rec.suggested_action)
        action_type = action["type"]

        # 2. Build context for validation
        context = self._build_context(action, client_id)
        current_val, new_val = self._extract_values(action)

        # 3. CIRCUIT BREAKER
        try:
            validate_action(action_type, current_val, new_val, context)
        except SafetyViolationError as e:
            return {"status": "blocked", "reason": str(e)}

        # 4. DRY RUN → preview
        if dry_run:
            return {
                "status": "dry_run",
                "action": action,
                "current_val": current_val,
                "new_val": new_val,
                "message": "Dry run — action NOT applied."
            }

        # 5. EXECUTE via Google Ads API + update local DB
        try:
            from app.services.google_ads import google_ads_service
            old_value_json = json.dumps({"current_val": current_val})
            new_value_json = json.dumps({"new_val": new_val})

            # Execute via Google Ads API (also updates local DB)
            api_result = google_ads_service.apply_action(
                self.db, action_type,
                entity_id=action.get("entity_id"),
                params=action.get("params", {}),
            )
            if api_result.get("status") == "error":
                raise Exception(api_result.get("message", "API call failed"))

            # 6. LOG SUCCESS
            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=action_type,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=str(action.get("entity_id", "")),
                old_value_json=old_value_json,
                new_value_json=new_value_json,
                status="SUCCESS"
            )
            self.db.add(log_entry)

            # 7. UPDATE RECOMMENDATION
            rec.status = "applied"
            rec.applied_at = datetime.utcnow()
            self.db.commit()

            return {
                "status": "success",
                "action_type": action_type,
                "message": "Action applied successfully"
            }

        except Exception as e:
            self.db.rollback()

            # LOG FAILURE
            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=action_type,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=str(action.get("entity_id", "")),
                status="FAILED",
                error_message=str(e)
            )
            self.db.add(log_entry)
            self.db.commit()

            return {"status": "error", "message": str(e)}

    def revert_action(self, action_log_id: int) -> dict:
        """Revert/undo a previously executed action.

        Revert rules (ADR-007 + Patch v2.1):
        - Action must be < 24 hours old
        - Status must be SUCCESS (not FAILED, not REVERTED)
        - ADD_NEGATIVE is IRREVERSIBLE

        Revert mappings:
        - PAUSE_KEYWORD → ENABLE_KEYWORD
        - UPDATE_BID → restore old_bid_micros
        - ADD_KEYWORD → PAUSE the added keyword

        Args:
            action_log_id: ID of action to revert

        Returns:
            Dict with status and message
        """
        original = self.db.query(ActionLog).filter(
            ActionLog.id == action_log_id
        ).first()

        if not original:
            return {"status": "error", "message": "Action not found"}

        # Validate revertability
        if original.status == "REVERTED":
            return {"status": "error", "message": "Already reverted"}

        if original.status != "SUCCESS":
            return {"status": "error", "message": f"Cannot revert {original.status} action"}

        time_elapsed = datetime.utcnow() - original.executed_at
        if time_elapsed > timedelta(hours=24):
            return {"status": "error", "message": "Revert window (24h) expired"}

        IRREVERSIBLE = ["ADD_NEGATIVE"]
        if original.action_type in IRREVERSIBLE:
            return {"status": "error", "message": f"{original.action_type} cannot be reverted"}

        if not original.old_value_json:
            return {"status": "error", "message": "Missing previous state — cannot revert"}

        # Execute reverse via Google Ads API + local DB
        try:
            from app.services.google_ads import google_ads_service
            old_state = json.loads(original.old_value_json)

            # Revert mappings: execute reverse action
            if original.action_type == "PAUSE_KEYWORD":
                google_ads_service.apply_action(
                    self.db, "ENABLE_KEYWORD",
                    entity_id=int(original.entity_id),
                    params={},
                )
            elif original.action_type == "UPDATE_BID":
                google_ads_service.apply_action(
                    self.db, "SET_KEYWORD_BID",
                    entity_id=int(original.entity_id),
                    params={"amount": old_state.get("current_val", 0)},
                )
            elif original.action_type == "ADD_KEYWORD":
                google_ads_service.apply_action(
                    self.db, "PAUSE_KEYWORD",
                    entity_id=int(original.entity_id),
                    params={},
                )

            # Mark original as reverted
            original.status = "REVERTED"
            original.reverted_at = datetime.utcnow()

            # Log revert action
            revert_log = ActionLog(
                client_id=original.client_id,
                action_type=f"REVERT_{original.action_type}",
                entity_type=original.entity_type,
                entity_id=original.entity_id,
                old_value_json=original.new_value_json,
                new_value_json=original.old_value_json,
                status="SUCCESS"
            )
            self.db.add(revert_log)
            self.db.commit()

            return {
                "status": "success",
                "message": f"Reverted: {original.action_type}"
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": f"Revert failed: {str(e)}"}

    def _build_context(self, action: dict, client_id: int) -> dict:
        """Build context dict for validate_action().

        Counts:
        - keywords_paused_today_in_campaign
        - total_keywords_in_campaign
        - negatives_added_today

        Args:
            action: Action dict with campaign_id, etc.
            client_id: Client ID

        Returns:
            Context dict for validation
        """
        context = {}
        today = datetime.utcnow().date()

        # Count keywords paused today in same campaign
        if action.get("campaign_id"):
            context["total_keywords_in_campaign"] = self.db.query(Keyword).join(
                Keyword.ad_group
            ).filter(
                Keyword.ad_group.has(campaign_id=action["campaign_id"])
            ).count()

            context["keywords_paused_today_in_campaign"] = self.db.query(ActionLog).filter(
                ActionLog.client_id == client_id,
                ActionLog.action_type == "PAUSE_KEYWORD",
                func.date(ActionLog.executed_at) == today
            ).count()

        # Count negatives added today
        context["negatives_added_today"] = self.db.query(ActionLog).filter(
            ActionLog.client_id == client_id,
            ActionLog.action_type == "ADD_NEGATIVE",
            func.date(ActionLog.executed_at) == today
        ).count()

        return context

    def _extract_values(self, action: dict) -> Tuple[float, float]:
        """Extract current and new values from action payload.

        Args:
            action: Action dict with current_value, new_value (in USD)

        Returns:
            Tuple of (current_val, new_val) in USD
        """
        current = action.get("current_value", 0.0)
        new = action.get("new_value", 0.0)
        return (float(current), float(new))
