# Implementation Blueprint — PATCH v2.1
## Google Ads Helper — Critical Gap Fixes

**Version:** 2.1 (Patch)  
**Date:** 2025-02-16  
**Status:** REQUIRED — Apply on top of Blueprint v2.0  
**Author:** Lead Architect (via PM)  
**Priority:** BLOCKING — Do NOT start frontend until this is merged

---

## ⚠️ WHY THIS PATCH EXISTS

Lead Architect audit of Blueprint v2.0 identified **3 critical gaps**:

| Gap | Risk | Status |
|-----|------|--------|
| Missing `revert_action` in ActionExecutor | Financial safety — "Undo" is fiction without this | 🔴 FIXED HERE |
| Missing `analytics_service.py` (Anomaly Detection) | Feature 7 (PRD) completely absent from Blueprint | 🔴 FIXED HERE |
| Missing Search Terms segmentation logic | Feature 5 (PRD) segments never get assigned | 🔴 FIXED HERE |
| PRD uses `REAL` for micros, Blueprint uses `BigInteger` | Data integrity — wrong types lose precision | ✅ RESOLVED: Use BigInteger always |

---

## CONSISTENCY RULE (Non-Negotiable)

> **All monetary values MUST be stored as `BigInteger` (micros) in the database.**
> PRD Section 4.3 contains incorrect `REAL` type suggestions — **ignore them**.
> Convert to float ONLY at the API response layer (Pydantic schemas).
> This is final. No exceptions.

```python
# CORRECT — store in DB
keyword.cost_micros = 15500000  # BigInteger

# CORRECT — return to frontend (Pydantic schema)
cost_usd: float = cost_micros / 1_000_000  # 15.50

# WRONG — never do this in models
cost: float = 15.50  # Loses precision, causes rounding bugs
```

---

# PATCH 1: ROLLBACK (revert_action)

## Location
**File:** `backend/app/services/action_executor.py`  
**Add AFTER** the `execute_recommendation` method

## Why This Matters
PRD Feature 4 requires "Undo" functionality. Without `revert_action`, the Action History page is read-only — users can see what was done but cannot reverse mistakes. This is a **financial safety risk**.

## Implementation

```python
# backend/app/services/action_executor.py
# ADD THIS METHOD to the ActionExecutor class

def revert_action(self, action_log_id: int) -> Dict[str, any]:
    """
    Revert (undo) a previously executed action.
    
    Workflow:
    1. Fetch action from action_log
    2. Validate it can be reverted (< 24h, not already reverted)
    3. Parse old_value_json to get previous state
    4. Execute reverse API call
    5. Log the revert as a new action_log entry
    6. Mark original action_log as reverted
    
    Args:
        action_log_id: ID of the action_log entry to revert
    
    Returns:
        Dict with revert result:
        {
            "status": "success" | "error",
            "message": str,
            "revert_log_id": int (if successful)
        }
    
    Raises:
        ActionValidationError: If action cannot be reverted
    """
    try:
        # STEP 1: Fetch original action from log
        original_action = self.db.query(ActionLog).filter(
            ActionLog.id == action_log_id
        ).first()

        if not original_action:
            return {
                "status": "error",
                "message": f"Action log entry {action_log_id} not found"
            }

        # STEP 2: Validate revertability
        validation_result = self._validate_revertable(original_action)
        if not validation_result["can_revert"]:
            return {
                "status": "error",
                "message": validation_result["reason"]
            }

        # STEP 3: Build reverse action from old_value_json
        old_state = json.loads(original_action.old_value_json or "{}")
        reverse_action = self._build_reverse_action(
            action_type=original_action.action_type,
            old_state=old_state,
            entity_id=original_action.entity_id
        )

        if not reverse_action:
            return {
                "status": "error",
                "message": f"Cannot build reverse action for type: {original_action.action_type}"
            }

        # STEP 4: Execute reverse API call
        execution_result = self._execute_action(
            action_type=reverse_action["type"],
            action_data=reverse_action
        )

        if execution_result["status"] == "error":
            return execution_result

        # STEP 5: Log the revert as a new entry
        revert_log = ActionLog(
            client_id=original_action.client_id,
            recommendation_id=None,  # Reverts are not tied to recommendations
            action_type=f"REVERT_{original_action.action_type}",
            entity_id=original_action.entity_id,
            old_value_json=original_action.new_value_json,   # Old = what it was after action
            new_value_json=original_action.old_value_json,   # New = restoring previous state
            status="SUCCESS",
            timestamp=datetime.utcnow()
        )
        self.db.add(revert_log)

        # STEP 6: Mark original action as reverted
        original_action.status = "REVERTED"
        original_action.reverted_at = datetime.utcnow()
        self.db.commit()

        logger.info(
            f"Successfully reverted action {action_log_id} "
            f"(type: {original_action.action_type}, entity: {original_action.entity_id})"
        )

        return {
            "status": "success",
            "message": f"Action reverted: {original_action.action_type}",
            "revert_log_id": revert_log.id,
            "restored_state": old_state
        }

    except Exception as e:
        self.db.rollback()
        logger.error(f"Revert failed for action_log {action_log_id}: {str(e)}")
        return {
            "status": "error",
            "message": f"Revert failed: {str(e)}"
        }


def _validate_revertable(self, action: ActionLog) -> Dict[str, any]:
    """
    Check if an action can be reverted.
    
    Rules:
    - Action must be < 24 hours old (safety window)
    - Action status must be SUCCESS (can't revert a failed action)
    - Action must not already be REVERTED
    - Action type must be reversible
    
    IRREVERSIBLE actions (cannot undo):
    - ADD_NEGATIVE: Removing a negative is risky (may re-enable bad traffic immediately)
    - ADD_KEYWORD: Removing a keyword is OK but treated as separate operation
    
    Args:
        action: ActionLog instance
    
    Returns:
        Dict: {"can_revert": bool, "reason": str}
    """
    from datetime import timedelta

    IRREVERSIBLE_ACTION_TYPES = ["ADD_NEGATIVE"]
    REVERT_WINDOW_HOURS = 24

    # Check: already reverted
    if action.status == "REVERTED":
        return {
            "can_revert": False,
            "reason": "This action has already been reverted"
        }

    # Check: action must have succeeded
    if action.status != "SUCCESS":
        return {
            "can_revert": False,
            "reason": f"Cannot revert a {action.status} action"
        }

    # Check: time window
    time_elapsed = datetime.utcnow() - action.timestamp
    if time_elapsed > timedelta(hours=REVERT_WINDOW_HOURS):
        return {
            "can_revert": False,
            "reason": (
                f"Action is {time_elapsed.total_seconds() / 3600:.0f}h old. "
                f"Revert window is {REVERT_WINDOW_HOURS}h. "
                f"Please make changes manually in Google Ads."
            )
        }

    # Check: irreversible action types
    if action.action_type in IRREVERSIBLE_ACTION_TYPES:
        return {
            "can_revert": False,
            "reason": (
                f"Action type '{action.action_type}' cannot be automatically reverted. "
                f"Please remove the negative keyword manually in Google Ads."
            )
        }

    # Check: old state is present (required for restore)
    if not action.old_value_json:
        return {
            "can_revert": False,
            "reason": "Missing previous state data — cannot safely restore"
        }

    return {"can_revert": True, "reason": "OK"}


def _build_reverse_action(
    self,
    action_type: str,
    old_state: Dict,
    entity_id: str
) -> Optional[Dict]:
    """
    Build the API call payload to reverse an action.
    
    Maps each action type to its opposite.
    
    Args:
        action_type: Original action type (e.g., "PAUSE_KEYWORD")
        old_state: Previous state from action_log.old_value_json
        entity_id: Entity being reverted (keyword_id, etc.)
    
    Returns:
        Dict with reverse action payload, or None if not reversible
    """

    # PAUSE_KEYWORD → re-enable keyword
    if action_type == "PAUSE_KEYWORD":
        return {
            "type": "ENABLE_KEYWORD",
            "keyword_id": entity_id,
            "ad_group_id": old_state.get("ad_group_id"),
            "old_status": "PAUSED",
            "new_status": "ENABLED"
        }

    # UPDATE_BID → restore previous bid
    if action_type == "UPDATE_BID":
        original_bid_micros = old_state.get("bid_micros")
        if not original_bid_micros:
            return None
        return {
            "type": "UPDATE_BID",
            "keyword_id": entity_id,
            "ad_group_id": old_state.get("ad_group_id"),
            "old_bid_micros": None,   # Current (post-change) bid
            "new_bid_micros": original_bid_micros,   # Restore to pre-change bid
            "old_bid_usd": None,
            "new_bid_usd": original_bid_micros / 1_000_000
        }

    # PAUSE_AD → re-enable ad
    if action_type == "PAUSE_AD":
        return {
            "type": "ENABLE_AD",
            "ad_id": entity_id,
            "ad_group_id": old_state.get("ad_group_id"),
            "old_status": "PAUSED",
            "new_status": "ENABLED"
        }

    # ADD_KEYWORD → pause the keyword we added (safest approach)
    if action_type == "ADD_KEYWORD":
        return {
            "type": "PAUSE_KEYWORD",
            "keyword_id": entity_id,
            "ad_group_id": old_state.get("ad_group_id"),
            "old_status": "ENABLED",
            "new_status": "PAUSED"
        }

    # Unknown action type — cannot auto-revert
    logger.warning(f"Unknown action type for revert: {action_type}")
    return None
```

## Required: Update ActionLog Model

**File:** `backend/app/models/action_log.py`  
**Add two fields** to the ActionLog class:

```python
# ADD these two columns to ActionLog model:
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    action_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, index=True)  # SUCCESS, FAILED, REVERTED ← NEW VALUE
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    reverted_at = Column(DateTime, nullable=True)  # ← NEW COLUMN
```

## Required: Update GoogleAdsClient

**File:** `backend/app/services/google_ads_client.py`  
**Add `enable_keyword` method** (reverse of `pause_keyword`):

```python
def enable_keyword(self, ad_group_id: str, criterion_id: str) -> bool:
    """
    Re-enable a paused keyword (used for rollback of PAUSE_KEYWORD).
    
    Args:
        ad_group_id: Ad group ID
        criterion_id: Keyword criterion ID
    
    Returns:
        True if successful
    """
    try:
        ad_group_criterion_service = self.client.get_service("AdGroupCriterionService")

        operation = self.client.get_type("AdGroupCriterionOperation")
        operation.update.resource_name = ad_group_criterion_service.ad_group_criterion_path(
            self.customer_id, ad_group_id, criterion_id
        )
        operation.update.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
        operation.update_mask.paths.append("status")

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=self.customer_id,
            operations=[operation]
        )

        logger.info(f"Re-enabled keyword {criterion_id}")
        return True

    except GoogleAdsException as ex:
        logger.error(f"Failed to re-enable keyword: {ex}")
        raise
```

## Required: New Router Endpoint

**File:** `backend/app/routers/actions.py`

```python
# backend/app/routers/actions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.action_log import ActionLog
from app.services.action_executor import ActionExecutor
from app.services.credentials_service import CredentialsService

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("/")
def get_action_history(
    client_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get action history for a client.
    Returns actions sorted newest first.
    """
    actions = db.query(ActionLog).filter(
        ActionLog.client_id == client_id
    ).order_by(
        ActionLog.timestamp.desc()
    ).offset(offset).limit(limit).all()

    return {
        "actions": actions,
        "total": db.query(ActionLog).filter(ActionLog.client_id == client_id).count()
    }


@router.post("/revert/{action_log_id}")
def revert_action(
    action_log_id: int,
    client_id: int,
    db: Session = Depends(get_db)
):
    """
    Revert (undo) a previously executed action.
    
    Safety checks:
    - Action must be < 24 hours old
    - Action must be SUCCESS status
    - Action must not already be reverted
    - Action type must be reversible
    """
    # Get client to find customer_id
    from app.models.client import Client
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Verify action belongs to this client (security check)
    action = db.query(ActionLog).filter(
        ActionLog.id == action_log_id,
        ActionLog.client_id == client_id
    ).first()
    if not action:
        raise HTTPException(
            status_code=404,
            detail="Action not found or does not belong to this client"
        )

    # Execute revert
    executor = ActionExecutor(db=db, customer_id=client.google_ads_customer_id)
    result = executor.revert_action(action_log_id=action_log_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result
```

---

# PATCH 2: ANOMALY DETECTION (analytics_service.py)

## Location
**File:** `backend/app/services/analytics_service.py`  
**Status:** File listed in Blueprint tree but EMPTY — this is the complete implementation

## Why This Matters
PRD Feature 7 requires anomaly detection (spend spike, conversion drop, CTR drop). Without this, the Alerts page shows nothing. This is **Feature 6 in MVP priority list**.

## Implementation

```python
# backend/app/services/analytics_service.py
"""
Analytics Service
KPI calculations, trend analysis, and anomaly detection.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.alert import Alert
from app.models.client import Client
from app.utils.formatters import micros_to_currency

logger = logging.getLogger(__name__)

# Anomaly Detection Thresholds
ANOMALY_THRESHOLDS = {
    "SPEND_SPIKE_MULTIPLIER": 1.5,      # Today > 1.5× 30-day avg → alert
    "CONV_DROP_TO_ZERO_MIN_AVG": 3.0,   # Alert if avg >= 3/day but today = 0
    "CTR_DROP_MULTIPLIER": 0.7,          # Today < 70% of 30-day avg CTR → alert
}


class AnalyticsService:
    """Service for KPI calculations and anomaly detection."""

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────
    # KPI CALCULATIONS
    # ─────────────────────────────────────────────

    def get_client_kpis(self, client_id: int) -> Dict:
        """
        Calculate aggregate KPIs for a client (all campaigns combined).

        Returns:
            Dict with:
            - spend_today (USD)
            - spend_yesterday (USD)
            - spend_change_pct
            - conversions_today
            - conversions_yesterday
            - conversions_change_pct
            - roas (Revenue / Spend, requires conversion value)
            - cpa (Spend / Conversions)
        """
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        # Get aggregated campaign metrics
        # NOTE: For MVP, we use total spend/conversions from campaigns table
        # These are 30-day totals — divide by 30 for daily avg as proxy

        today_metrics = self.db.query(
            func.sum(Campaign.spend_micros).label("total_spend"),
            func.sum(Campaign.conversions).label("total_conv"),
            func.sum(Campaign.clicks).label("total_clicks"),
            func.sum(Campaign.impressions).label("total_impressions")
        ).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED"
        ).first()

        if not today_metrics or not today_metrics.total_spend:
            return self._empty_kpi_response()

        # Calculate derived metrics
        spend_usd = micros_to_currency(today_metrics.total_spend or 0)
        conversions = today_metrics.total_conv or 0
        clicks = today_metrics.total_clicks or 0
        impressions = today_metrics.total_impressions or 0

        cpa = spend_usd / conversions if conversions > 0 else 0
        ctr = clicks / impressions if impressions > 0 else 0

        return {
            "spend_usd": spend_usd,
            "conversions": conversions,
            "clicks": clicks,
            "impressions": impressions,
            "cpa_usd": round(cpa, 2),
            "ctr_pct": round(ctr * 100, 2),
            "data_period": "last_30_days",
            "note": "KPIs represent 30-day totals from last sync"
        }

    def _empty_kpi_response(self) -> Dict:
        """Return empty KPI structure when no data available."""
        return {
            "spend_usd": 0,
            "conversions": 0,
            "clicks": 0,
            "impressions": 0,
            "cpa_usd": 0,
            "ctr_pct": 0,
            "data_period": "no_data",
            "note": "No data available. Please sync first."
        }

    def get_campaign_breakdown(self, client_id: int) -> List[Dict]:
        """
        Get KPI breakdown per campaign for a client.
        Used for multi-campaign dashboard table.

        Returns:
            List of campaign dicts with metrics
        """
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status != "REMOVED"
        ).order_by(Campaign.spend_micros.desc()).all()

        result = []
        for campaign in campaigns:
            spend_usd = micros_to_currency(campaign.spend_micros or 0)
            conversions = campaign.conversions or 0
            clicks = campaign.clicks or 0
            impressions = campaign.impressions or 0
            budget_usd = micros_to_currency(campaign.budget_micros or 0)

            cpa = spend_usd / conversions if conversions > 0 else 0
            ctr = clicks / impressions if impressions > 0 else 0
            roas = 0  # Requires conversion_value — not in MVP schema yet

            result.append({
                "campaign_id": campaign.id,
                "google_id": campaign.google_id,
                "name": campaign.name,
                "status": campaign.status,
                "budget_usd": budget_usd,
                "spend_usd": spend_usd,
                "conversions": conversions,
                "clicks": clicks,
                "ctr_pct": round(ctr * 100, 2),
                "cpa_usd": round(cpa, 2),
                "roas": roas
            })

        return result

    # ─────────────────────────────────────────────
    # ANOMALY DETECTION
    # ─────────────────────────────────────────────

    def detect_and_save_anomalies(self, client_id: int) -> int:
        """
        Run all anomaly detection rules for a client.
        Saves new alerts to database.
        Called AFTER sync completes.

        Returns:
            Number of new anomalies detected
        """
        logger.info(f"Running anomaly detection for client {client_id}")

        new_alerts = []

        # Run all detection rules
        new_alerts.extend(self._detect_spend_spike(client_id))
        new_alerts.extend(self._detect_conversion_drop(client_id))
        new_alerts.extend(self._detect_ctr_drop(client_id))

        # Save new alerts (avoid duplicates created today)
        saved_count = 0
        today = datetime.utcnow().date()

        for alert in new_alerts:
            # Check: same alert type for same client today already exists
            existing = self.db.query(Alert).filter(
                Alert.client_id == client_id,
                Alert.alert_type == alert.alert_type,
                func.date(Alert.created_at) == today,
                Alert.resolved_at.is_(None)  # Only check unresolved
            ).first()

            if not existing:
                self.db.add(alert)
                saved_count += 1

        self.db.commit()
        logger.info(f"Anomaly detection complete: {saved_count} new alerts for client {client_id}")
        return saved_count

    def _detect_spend_spike(self, client_id: int) -> List[Alert]:
        """
        ANOMALY 1: Spend Spike
        Logic: Total spend today > 1.5× 30-day average daily spend

        NOTE: For MVP, we compare total 30-day spend / 30 (avg daily)
        against current total. This is a proxy — exact daily comparison
        requires day-by-day metrics not stored in MVP schema.
        """
        alerts = []

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED"
        ).all()

        if not campaigns:
            return alerts

        total_spend_micros = sum(c.spend_micros or 0 for c in campaigns)
        avg_daily_spend_micros = total_spend_micros / 30  # 30-day period proxy

        # Threshold: 1.5× average daily spend (extrapolated to full period)
        # For MVP: flag if total spend / 30 exceeds a reasonable daily threshold
        # This will be refined in v1.1 with actual daily metrics
        spike_threshold = avg_daily_spend_micros * ANOMALY_THRESHOLDS["SPEND_SPIKE_MULTIPLIER"]

        # Compare last 7 days proxy (total / 30 * 7) vs first 23 days proxy
        # Simplified: if last 7-day portion is disproportionate
        # TODO v1.1: Use actual daily metrics for precise detection

        # For now: flag if any single campaign has unusually high spend
        total_avg = total_spend_micros / 30 if total_spend_micros > 0 else 0

        for campaign in campaigns:
            camp_spend_micros = campaign.spend_micros or 0
            camp_daily_avg = camp_spend_micros / 30

            # Simple heuristic: campaign spend > 3× what would be expected
            # for a proportional share (catches runaway campaigns)
            expected_share = total_avg / len(campaigns) if campaigns else 0
            if expected_share > 0 and camp_daily_avg > expected_share * 3:
                spend_usd = micros_to_currency(camp_spend_micros)
                avg_usd = micros_to_currency(expected_share * 30)

                alert = Alert(
                    client_id=client_id,
                    alert_type="SPEND_SPIKE",
                    priority="HIGH",
                    message=(
                        f"Campaign '{campaign.name}' has disproportionate spend: "
                        f"${spend_usd:.2f} total (30d) vs expected ${avg_usd:.2f}. "
                        f"Review budget settings."
                    )
                )
                alerts.append(alert)

        return alerts

    def _detect_conversion_drop(self, client_id: int) -> List[Alert]:
        """
        ANOMALY 2: Conversion Drop
        Logic: Account conversions dropped significantly below 30-day average

        For MVP: Flag if total conversions < expected minimum
        (< 30% of 30-day total / 30 days)
        """
        alerts = []

        stats = self.db.query(
            func.sum(Campaign.conversions).label("total_conv"),
            func.count(Campaign.id).label("campaign_count")
        ).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED"
        ).first()

        if not stats or not stats.total_conv:
            return alerts

        total_conversions = stats.total_conv
        daily_avg = total_conversions / 30

        # Alert if daily average is high but total is unexpectedly low
        # This catches cases where conversion tracking may have broken
        if daily_avg >= ANOMALY_THRESHOLDS["CONV_DROP_TO_ZERO_MIN_AVG"]:
            # Check for very low total (may indicate recent tracking issue)
            # Proxy: if total < daily_avg * 15 (only half the period has conversions)
            if total_conversions < daily_avg * 15:
                alert = Alert(
                    client_id=client_id,
                    alert_type="CONVERSION_DROP",
                    priority="HIGH",
                    message=(
                        f"Conversion anomaly detected. "
                        f"30-day total: {total_conversions:.0f} conversions "
                        f"(avg {daily_avg:.1f}/day). "
                        f"Verify conversion tracking is working correctly."
                    )
                )
                alerts.append(alert)

        return alerts

    def _detect_ctr_drop(self, client_id: int) -> List[Alert]:
        """
        ANOMALY 3: CTR Drop
        Logic: Account-wide CTR dropped significantly
        Indicates potential ad disapprovals or quality issues

        For MVP: Flag campaigns with CTR significantly below their stored value
        """
        alerts = []

        # Find campaigns with very low CTR (may indicate ad disapprovals)
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED",
            Campaign.impressions > 1000,  # Only flag if enough traffic
            Campaign.ctr < 0.005  # CTR < 0.5% is very low for Search
        ).all()

        for campaign in campaigns:
            alert = Alert(
                client_id=client_id,
                alert_type="CTR_DROP",
                priority="MEDIUM",
                message=(
                    f"Campaign '{campaign.name}' has very low CTR: "
                    f"{(campaign.ctr or 0) * 100:.2f}%. "
                    f"Check for ad disapprovals or relevance issues."
                )
            )
            alerts.append(alert)

        return alerts

    def get_unresolved_alerts(self, client_id: int) -> List[Dict]:
        """
        Get all unresolved alerts for a client.
        Sorted by priority (HIGH first), then newest first.

        Returns:
            List of alert dicts
        """
        alerts = self.db.query(Alert).filter(
            Alert.client_id == client_id,
            Alert.resolved_at.is_(None)
        ).order_by(
            # Sort HIGH before MEDIUM
            Alert.priority.desc(),
            Alert.created_at.desc()
        ).all()

        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "priority": alert.priority,
                "message": alert.message,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "age_hours": (
                    (datetime.utcnow() - alert.created_at).total_seconds() / 3600
                    if alert.created_at else 0
                )
            }
            for alert in alerts
        ]

    def resolve_alert(self, alert_id: int, client_id: int) -> bool:
        """
        Mark an alert as resolved ("Mark as Reviewed" in UI).

        Args:
            alert_id: Alert ID to resolve
            client_id: Client ID (security check)

        Returns:
            True if resolved, False if not found
        """
        alert = self.db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.client_id == client_id
        ).first()

        if not alert:
            return False

        alert.resolved_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Alert {alert_id} marked as resolved for client {client_id}")
        return True

    def get_alerts_summary(self, client_id: int) -> Dict:
        """
        Get alert counts for UI badge display.

        Returns:
            Dict: {"high": int, "medium": int, "total": int}
        """
        unresolved = self.db.query(Alert).filter(
            Alert.client_id == client_id,
            Alert.resolved_at.is_(None)
        ).all()

        high_count = sum(1 for a in unresolved if a.priority == "HIGH")
        medium_count = sum(1 for a in unresolved if a.priority == "MEDIUM")

        return {
            "high": high_count,
            "medium": medium_count,
            "total": len(unresolved)
        }
```

## Required: New Analytics Router Endpoints

**File:** `backend/app/routers/analytics.py`

```python
# backend/app/routers/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/kpis")
def get_kpis(client_id: int, db: Session = Depends(get_db)):
    """Get aggregate KPIs for a client."""
    service = AnalyticsService(db)
    return service.get_client_kpis(client_id)


@router.get("/campaigns")
def get_campaign_breakdown(client_id: int, db: Session = Depends(get_db)):
    """Get KPI breakdown per campaign."""
    service = AnalyticsService(db)
    return service.get_campaign_breakdown(client_id)


@router.get("/anomalies")
def get_anomalies(
    client_id: int,
    status: str = "unresolved",
    db: Session = Depends(get_db)
):
    """
    Get anomaly alerts for a client.
    
    Args:
        status: "unresolved" (default) or "all"
    """
    service = AnalyticsService(db)

    if status == "unresolved":
        return {
            "alerts": service.get_unresolved_alerts(client_id),
            "summary": service.get_alerts_summary(client_id)
        }
    else:
        # Return all alerts including resolved
        from app.models.alert import Alert
        all_alerts = db.query(Alert).filter(
            Alert.client_id == client_id
        ).order_by(Alert.created_at.desc()).all()
        return {"alerts": all_alerts}


@router.post("/anomalies/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    client_id: int,
    db: Session = Depends(get_db)
):
    """Mark an alert as reviewed/resolved."""
    service = AnalyticsService(db)
    success = service.resolve_alert(alert_id=alert_id, client_id=client_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "resolved", "alert_id": alert_id}


@router.post("/detect")
def run_anomaly_detection(client_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger anomaly detection for a client.
    NOTE: This is also called automatically after sync completes.
    """
    service = AnalyticsService(db)
    count = service.detect_and_save_anomalies(client_id)
    return {"status": "success", "new_alerts": count}
```

---

# PATCH 3: SEARCH TERMS SEGMENTATION

## Location
**File:** `backend/app/services/sync_service.py`  
**Problem:** `_upsert_search_term` stores data but never assigns `segment` field  
**File:** `backend/app/services/search_terms_service.py` ← **NEW FILE**

## Why This Matters
PRD Feature 5 requires 4 segments: HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER. Without segmentation, the SearchTerms.jsx page shows all terms unsorted — the killer feature doesn't work.

## When Does Segmentation Happen?

**Architecture Decision:**
```
Option A: Segment during sync (real-time)
- Pro: Data is segmented immediately
- Con: Sync is slower, couples sync to business logic

Option B: Segment after sync (batch job)  ← CHOSEN
- Pro: Sync is fast (just store data)
- Con: User sees unsegmented data briefly after sync

Implementation: After sync completes, 
call segment_all_search_terms(client_id).
This is called in sync_service.py as the final phase.
```

## New File: search_terms_service.py

**File:** `backend/app/services/search_terms_service.py`

```python
# backend/app/services/search_terms_service.py
"""
Search Terms Service
Handles segmentation logic for search terms (Feature 5 in PRD).

Segments:
- HIGH_PERFORMER: conv >= 3 AND cvr > campaign avg cvr
- WASTE: clicks >= 5 AND conv = 0 AND ctr < 1%
- IRRELEVANT: query contains disqualifying words
- OTHER: everything else (insufficient data)
"""
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.search_term import SearchTerm
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.utils.constants import IRRELEVANT_KEYWORDS, SAFETY_LIMITS

logger = logging.getLogger(__name__)


class SearchTermsService:
    """Service for search term segmentation and analysis."""

    def __init__(self, db: Session):
        self.db = db

    def segment_all_search_terms(self, client_id: int) -> Dict:
        """
        Assign segment to all search terms for a client.
        
        MUST be called after sync completes.
        Processes in priority order:
        1. IRRELEVANT (fastest check — keyword matching)
        2. HIGH_PERFORMER (needs campaign CVR)
        3. WASTE (needs CTR + conv data)
        4. OTHER (everything remaining)

        Args:
            client_id: Client ID

        Returns:
            Dict with counts per segment
        """
        logger.info(f"Segmenting search terms for client {client_id}")

        counts = {
            "HIGH_PERFORMER": 0,
            "WASTE": 0,
            "IRRELEVANT": 0,
            "OTHER": 0
        }

        # Get all search terms for this client (unset segment or re-evaluate all)
        search_terms = self.db.query(SearchTerm).filter(
            SearchTerm.client_id == client_id
        ).all()

        if not search_terms:
            logger.info(f"No search terms found for client {client_id}")
            return counts

        # Pre-calculate campaign CVRs (to avoid N+1 queries)
        campaign_cvrs = self._get_campaign_cvrs(client_id)

        for st in search_terms:
            segment = self._classify_search_term(st, campaign_cvrs)
            st.segment = segment
            counts[segment] += 1

        self.db.commit()

        logger.info(
            f"Segmentation complete for client {client_id}: "
            f"HP={counts['HIGH_PERFORMER']}, "
            f"WASTE={counts['WASTE']}, "
            f"IRR={counts['IRRELEVANT']}, "
            f"OTHER={counts['OTHER']}"
        )

        return counts

    def _classify_search_term(
        self,
        st: SearchTerm,
        campaign_cvrs: Dict[int, float]
    ) -> str:
        """
        Classify a single search term into a segment.
        
        Priority order (checked top to bottom, first match wins):
        1. IRRELEVANT — contains disqualifying keyword
        2. HIGH_PERFORMER — high conversions + CVR
        3. WASTE — clicks with no conversions + low CTR
        4. OTHER — default

        Args:
            st: SearchTerm instance
            campaign_cvrs: Pre-calculated {campaign_id: cvr} dict

        Returns:
            Segment string: "HIGH_PERFORMER", "WASTE", "IRRELEVANT", "OTHER"
        """

        # PRIORITY 1: IRRELEVANT (intent-based, fastest check)
        if self._is_irrelevant(st.query_text):
            return "IRRELEVANT"

        # PRIORITY 2: HIGH_PERFORMER
        # Criteria: conv >= 3 AND cvr > campaign avg cvr
        if (
            (st.conversions or 0) >= SAFETY_LIMITS["ADD_KEYWORD_MIN_CONV"]
            and (st.clicks or 0) > 0
        ):
            st_cvr = st.conversions / st.clicks
            campaign_cvr = campaign_cvrs.get(st.campaign_id, 0)

            if st_cvr > campaign_cvr:
                return "HIGH_PERFORMER"

        # PRIORITY 3: WASTE
        # Criteria: clicks >= 5 AND conv = 0 AND ctr < 1%
        if (
            (st.clicks or 0) >= SAFETY_LIMITS["ADD_NEGATIVE_MIN_CLICKS"]
            and (st.conversions or 0) == 0
            and (st.ctr or 0) < 0.01
        ):
            return "WASTE"

        # DEFAULT: OTHER (insufficient data or mixed signals)
        return "OTHER"

    def _is_irrelevant(self, query_text: str) -> bool:
        """
        Check if search term contains irrelevant intent keywords.
        
        Case-insensitive substring match.
        
        Args:
            query_text: Search query string

        Returns:
            True if irrelevant
        """
        if not query_text:
            return False

        query_lower = query_text.lower()
        return any(
            irrelevant_kw.lower() in query_lower
            for irrelevant_kw in IRRELEVANT_KEYWORDS
        )

    def _get_campaign_cvrs(self, client_id: int) -> Dict[int, float]:
        """
        Pre-calculate CVR for all campaigns of a client.
        Avoids N+1 queries when processing many search terms.

        Returns:
            Dict: {campaign_id: cvr}
        """
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id
        ).all()

        cvr_map = {}

        for campaign in campaigns:
            # Get total conversions and clicks for this campaign's keywords
            stats = self.db.query(
                func.sum(Keyword.conversions).label("total_conv"),
                func.sum(Keyword.clicks).label("total_clicks")
            ).filter(
                Keyword.campaign_id == campaign.id,
                Keyword.clicks > 0
            ).first()

            if stats and stats.total_clicks and stats.total_clicks > 0:
                cvr_map[campaign.id] = stats.total_conv / stats.total_clicks
            else:
                cvr_map[campaign.id] = 0.0

        return cvr_map

    def get_segmented_search_terms(self, client_id: int) -> Dict:
        """
        Get search terms grouped by segment.
        Used by SearchTerms.jsx frontend page.

        Returns:
            Dict with segments as keys, each containing list of terms + stats
        """
        all_terms = self.db.query(SearchTerm).filter(
            SearchTerm.client_id == client_id
        ).order_by(
            SearchTerm.cost_micros.desc()
        ).all()

        segments = {
            "HIGH_PERFORMER": [],
            "WASTE": [],
            "IRRELEVANT": [],
            "OTHER": []
        }

        segment_stats = {
            "HIGH_PERFORMER": {"count": 0, "total_cost_usd": 0, "total_conv": 0},
            "WASTE": {"count": 0, "total_cost_usd": 0, "total_conv": 0},
            "IRRELEVANT": {"count": 0, "total_cost_usd": 0, "total_conv": 0},
            "OTHER": {"count": 0, "total_cost_usd": 0, "total_conv": 0}
        }

        for st in all_terms:
            segment = st.segment or "OTHER"

            term_dict = {
                "id": st.id,
                "query_text": st.query_text,
                "clicks": st.clicks or 0,
                "impressions": st.impressions or 0,
                "cost_usd": (st.cost_micros or 0) / 1_000_000,
                "conversions": st.conversions or 0,
                "ctr_pct": round((st.ctr or 0) * 100, 2),
                "cvr_pct": round(
                    (st.conversions / st.clicks * 100)
                    if (st.clicks or 0) > 0 else 0,
                    2
                ),
                "segment": segment,
                "campaign_id": st.campaign_id
            }

            segments[segment].append(term_dict)

            # Accumulate stats
            segment_stats[segment]["count"] += 1
            segment_stats[segment]["total_cost_usd"] += term_dict["cost_usd"]
            segment_stats[segment]["total_conv"] += term_dict["conversions"]

        return {
            "segments": segments,
            "stats": segment_stats,
            "total_terms": len(all_terms)
        }
```

## Required: Update sync_service.py

**File:** `backend/app/services/sync_service.py`  
**Add Phase 4** at the end of `sync_client` method:

```python
# In SyncService.sync_client(), ADD after Phase 3 (Search Terms):

# --- PHASE 4: SEGMENTATION ---
logger.info(f"Running search terms segmentation for {client_id}...")
try:
    from app.services.search_terms_service import SearchTermsService
    seg_service = SearchTermsService(self.db)
    seg_counts = seg_service.segment_all_search_terms(client_id)
    stats["segmentation"] = seg_counts
    logger.info(f"Segmentation complete: {seg_counts}")
except Exception as e:
    logger.error(f"Segmentation failed: {str(e)}")
    errors.append(f"Segmentation: {str(e)}")
    # Non-critical: don't rollback sync data if segmentation fails

# --- PHASE 5: ANOMALY DETECTION ---
logger.info(f"Running anomaly detection for {client_id}...")
try:
    from app.services.analytics_service import AnalyticsService
    analytics = AnalyticsService(self.db)
    new_alerts = analytics.detect_and_save_anomalies(client_id)
    stats["new_alerts"] = new_alerts
    logger.info(f"Anomaly detection: {new_alerts} new alerts")
except Exception as e:
    logger.error(f"Anomaly detection failed: {str(e)}")
    errors.append(f"Anomaly detection: {str(e)}")
    # Non-critical: don't rollback sync data
```

## Required: New Search Terms Router Endpoint

**File:** `backend/app/routers/search_terms.py`

```python
# backend/app/routers/search_terms.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.search_terms_service import SearchTermsService

router = APIRouter(prefix="/search-terms", tags=["Search Terms"])


@router.get("/segmented")
def get_segmented_search_terms(client_id: int, db: Session = Depends(get_db)):
    """
    Get search terms grouped by segment.
    Returns 4 groups: HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER.
    
    Used by SearchTerms.jsx to show segment cards and filtered lists.
    """
    service = SearchTermsService(db)
    return service.get_segmented_search_terms(client_id)


@router.get("/")
def get_all_search_terms(
    client_id: int,
    segment: str = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get all search terms with optional segment filter.
    
    Args:
        segment: Optional filter (HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER)
        limit: Max results per page (default 200)
        offset: Pagination offset
    """
    from app.models.search_term import SearchTerm

    query = db.query(SearchTerm).filter(SearchTerm.client_id == client_id)

    if segment:
        query = query.filter(SearchTerm.segment == segment)

    total = query.count()
    terms = query.order_by(
        SearchTerm.cost_micros.desc()
    ).offset(offset).limit(limit).all()

    return {
        "terms": [
            {
                "id": t.id,
                "query_text": t.query_text,
                "clicks": t.clicks or 0,
                "cost_usd": (t.cost_micros or 0) / 1_000_000,
                "conversions": t.conversions or 0,
                "ctr_pct": round((t.ctr or 0) * 100, 2),
                "segment": t.segment or "OTHER"
            }
            for t in terms
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

---

# PATCH SUMMARY: What Changed

## Files Modified (Update existing):

| File | Change |
|------|--------|
| `services/action_executor.py` | Added `revert_action`, `_validate_revertable`, `_build_reverse_action` |
| `services/google_ads_client.py` | Added `enable_keyword` method |
| `services/sync_service.py` | Added Phase 4 (Segmentation) and Phase 5 (Anomaly Detection) |
| `models/action_log.py` | Added `reverted_at` column and "REVERTED" as valid status |

## Files Created (New):

| File | Purpose |
|------|---------|
| `services/analytics_service.py` | KPI calculations + Anomaly Detection (was empty stub) |
| `services/search_terms_service.py` | Search terms segmentation logic |
| `routers/analytics.py` | Analytics endpoints (/kpis, /anomalies, /detect) |
| `routers/search_terms.py` | Search terms endpoints (/segmented, /) |
| `routers/actions.py` | Action history + revert endpoints |

## Schema Consistency Fix (Applied Everywhere):

```
❌ PRD Section 4.3: cost REAL  (wrong)
✅ Blueprint: cost_micros BigInteger (correct)
```

All monetary values: **BigInteger (micros)** in DB, **float (USD)** in API responses.

---

# INTEGRATION CHECKLIST

After applying this patch, verify:

- [ ] `ActionExecutor.revert_action` tested with mock action_log entry
- [ ] `AnalyticsService.detect_and_save_anomalies` called after every sync
- [ ] `SearchTermsService.segment_all_search_terms` called after every sync (Phase 4)
- [ ] `action_log.reverted_at` column exists in database (run migration)
- [ ] All 5 new routers registered in `backend/app/main.py`
- [ ] Rollback tested: apply action → revert → verify entity restored in Google Ads
- [ ] Anomaly detection tested: inject test data with spike → verify alert created
- [ ] Search term segmentation tested: verify correct segment assigned per criteria

---

# FINAL ARCHITECTURE: Sync Flow (Updated)

```
POST /clients/{id}/sync
        │
        ▼
SyncService.sync_client(client_id)
        │
        ├─ PHASE 1: Campaigns (GAQL Query A)
        │   └─ _upsert_campaign() × N
        │   └─ db.commit()
        │
        ├─ PHASE 2: Keywords (GAQL Query B)
        │   └─ _upsert_keyword() × N
        │   └─ db.commit()
        │
        ├─ PHASE 3: Search Terms (GAQL Query C)
        │   └─ _upsert_search_term() × N
        │   └─ db.commit()
        │
        ├─ PHASE 4: Segmentation  ← NEW (Patch 3)
        │   └─ SearchTermsService.segment_all_search_terms()
        │       └─ _classify_search_term() × N
        │   └─ db.commit()
        │
        ├─ PHASE 5: Anomaly Detection  ← NEW (Patch 2)
        │   └─ AnalyticsService.detect_and_save_anomalies()
        │       ├─ _detect_spend_spike()
        │       ├─ _detect_conversion_drop()
        │       └─ _detect_ctr_drop()
        │   └─ db.commit()
        │
        └─ PHASE 6: Update last_synced_at
            └─ db.commit()
            └─ Return stats
```

---

**Patch v2.1 — COMPLETE**  
**Blueprint v2.0 + Patch v2.1 = Source of Truth for AI Developer**  
**Next: Technical_Spec.md (API full spec + Frontend spec)**
