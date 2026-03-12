"""Shared recommendation contract helpers.

Keeps recommendation business types separate from executable action payloads.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any


PLAYBOOK_RULES = "PLAYBOOK_RULES"
GOOGLE_ADS_API = "GOOGLE_ADS_API"
HYBRID = "HYBRID"
ANALYTICS = "ANALYTICS"

ACTION = "ACTION"
INSIGHT_ONLY = "INSIGHT_ONLY"
BLOCKED_BY_CONTEXT = "BLOCKED_BY_CONTEXT"

ROLE_MISMATCH = "ROLE_MISMATCH"
DONOR_PROTECTED_HIGH = "DONOR_PROTECTED_HIGH"
DONOR_PROTECTED_MEDIUM = "DONOR_PROTECTED_MEDIUM"
DESTINATION_NO_HEADROOM = "DESTINATION_NO_HEADROOM"
ROAS_ONLY_SIGNAL = "ROAS_ONLY_SIGNAL"
UNKNOWN_ROLE = "UNKNOWN_ROLE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

FIXED_REASON_CODES = {
    ROLE_MISMATCH,
    DONOR_PROTECTED_HIGH,
    DONOR_PROTECTED_MEDIUM,
    DESTINATION_NO_HEADROOM,
    ROAS_ONLY_SIGNAL,
    UNKNOWN_ROLE,
    INSUFFICIENT_DATA,
}

NON_EXECUTABLE_TYPES = {
    "QS_ALERT",
    "IS_RANK_ALERT",
    "WASTED_SPEND_ALERT",
    "PMAX_CANNIBALIZATION",
    "DEVICE_ANOMALY",
    "GEO_ANOMALY",
    "BUDGET_PACING",
    "ANALYTICS_ALERT",
}

RISK_BASELINES = {
    "PAUSE_KEYWORD": 0.25,
    "UPDATE_BID": 0.45,
    "ADD_KEYWORD": 0.35,
    "ADD_NEGATIVE": 0.55,
    "PAUSE_AD": 0.45,
    "INCREASE_BUDGET": 0.50,
    "REALLOCATE_BUDGET": 0.75,
    "NGRAM_NEGATIVE": 0.95,
    "REVIEW_ONLY": 0.20,
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def micros_to_float(micros: Any) -> float:
    return round((micros or 0) / 1_000_000, 6)


def float_to_micros(value: Any) -> int:
    return int(round(float(value or 0) * 1_000_000))


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def hash_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    if not text:
        return "none"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def normalize_reason_codes(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized = []
    for value in values:
        code = str(value or "").strip().upper()
        if code in FIXED_REASON_CODES and code not in normalized:
            normalized.append(code)
    return normalized


def build_stable_key(rec: dict, client_id: int) -> str:
    source = rec.get("source") or PLAYBOOK_RULES
    campaign_id = rec.get("campaign_id") or 0
    ad_group_id = rec.get("ad_group_id") or 0
    entity_id = rec.get("entity_id") or 0
    google_resource_name = rec.get("google_resource_name") or ""
    text_hash = hash_text(rec.get("entity_name") or google_resource_name)
    return "|".join(
        [
            str(rec.get("type") or ""),
            source,
            str(client_id),
            str(campaign_id),
            str(ad_group_id),
            str(entity_id),
            text_hash,
        ]
    )


def default_expires_at(rec: dict) -> datetime:
    now = utcnow()
    source = rec.get("source") or PLAYBOOK_RULES
    action_type = (rec.get("action_payload") or {}).get("action_type")

    if source == GOOGLE_ADS_API:
        return now + timedelta(minutes=30)
    if action_type in {"UPDATE_BID", "INCREASE_BUDGET"}:
        return now + timedelta(days=1)
    if action_type in {"ADD_KEYWORD", "ADD_NEGATIVE", "PAUSE_KEYWORD", "PAUSE_AD"}:
        return now + timedelta(days=3)
    return now + timedelta(days=7)


def estimate_impact_micros(rec: dict) -> int:
    meta = rec.get("metadata") or {}
    rec_type = rec.get("type")

    if meta.get("impact_micros") is not None:
        return int(meta["impact_micros"])

    spend_micros = float_to_micros(meta.get("spend"))
    cost_micros = float_to_micros(meta.get("cost"))
    budget_micros = int(meta.get("current_budget_micros") or 0)

    if rec_type in {"PAUSE_KEYWORD", "ADD_NEGATIVE", "NGRAM_NEGATIVE", "WASTED_SPEND_ALERT"}:
        return max(spend_micros, cost_micros)
    if rec_type == "PAUSE_AD":
        return max(cost_micros, spend_micros)
    if rec_type == "ADD_KEYWORD":
        conversions = float(meta.get("conversions") or 0)
        cvr = float(meta.get("cvr") or 0)
        base = max(cost_micros, float_to_micros(conversions * max(cvr, 1)))
        return int(base * 0.35)
    if rec_type in {"INCREASE_BID", "DECREASE_BID"}:
        current_bid_micros = int(meta.get("current_bid_micros") or 0)
        pct = abs(float(meta.get("bid_change_pct") or 20)) / 100
        return int(max(current_bid_micros, cost_micros, spend_micros) * max(pct, 0.1))
    if rec_type == "REALLOCATE_BUDGET":
        return float_to_micros(meta.get("move_amount"))
    if rec_type == "IS_BUDGET_ALERT":
        lost_is_pct = float(meta.get("lost_is_pct") or 0) / 100
        candidate = int(budget_micros * max(lost_is_pct, 0.1))
        return max(candidate, int(cost_micros * 0.25))
    return max(cost_micros, spend_micros, 0)


def compute_confidence_score(rec: dict, lookback_days: int = 30) -> float:
    meta = rec.get("metadata") or {}
    score = 0.0

    clicks = float(meta.get("clicks") or 0)
    conversions = float(meta.get("conversions") or 0)
    impressions = float(meta.get("impressions") or 0)
    term_count = float(meta.get("term_count") or 0)

    if clicks >= 50:
        score += 0.35
    elif clicks >= 20:
        score += 0.25
    elif clicks >= 10:
        score += 0.15

    if conversions >= 5:
        score += 0.35
    elif conversions >= 3:
        score += 0.25
    elif conversions > 0:
        score += 0.15

    if impressions >= 1000:
        score += 0.15
    elif impressions >= 100:
        score += 0.10

    if term_count >= 5:
        score += 0.10

    if lookback_days >= 30:
        score += 0.15
    elif lookback_days >= 14:
        score += 0.10
    else:
        score += 0.05

    return round(clamp(score), 2)


def compute_risk_score(rec: dict) -> float:
    meta = rec.get("metadata") or {}
    context = rec.get("context") or meta.get("context") or {}
    action_type = (rec.get("action_payload") or {}).get("action_type") or "REVIEW_ONLY"
    score = RISK_BASELINES.get(action_type, 0.3)

    negative_level = meta.get("negative_level")
    if negative_level == "ACCOUNT":
        score += 0.25
    elif negative_level == "AD_GROUP":
        score += 0.10

    search_term_source = meta.get("search_term_source")
    if search_term_source == "PMAX":
        score += 0.20

    change_pct = abs(float(meta.get("bid_change_pct") or meta.get("budget_change_pct") or 0))
    if change_pct >= 30:
        score += 0.15
    elif change_pct >= 20:
        score += 0.10

    blocked = normalize_reason_codes(rec.get("blocked_reasons") or context.get("blocked_reasons"))
    downgraded = normalize_reason_codes(rec.get("downgrade_reasons") or context.get("downgrade_reasons"))
    all_codes = set(blocked + downgraded)

    if rec.get("context_outcome") == BLOCKED_BY_CONTEXT:
        score += 0.20
    elif rec.get("context_outcome") == INSIGHT_ONLY:
        score += 0.10

    if UNKNOWN_ROLE in all_codes or ROLE_MISMATCH in all_codes:
        score += 0.15
    if DONOR_PROTECTED_HIGH in all_codes:
        score += 0.15
    elif DONOR_PROTECTED_MEDIUM in all_codes:
        score += 0.10
    if DESTINATION_NO_HEADROOM in all_codes:
        score += 0.10
    if ROAS_ONLY_SIGNAL in all_codes:
        score += 0.10
    if INSUFFICIENT_DATA in all_codes:
        score += 0.10

    if rec.get("type") == "NGRAM_NEGATIVE":
        score += 0.25

    return round(clamp(score), 2)


def compute_priority(rec: dict) -> tuple[str, float]:
    impact_score = round(clamp((rec.get("impact_micros") or 0) / 150_000_000), 2)
    confidence_score = float(rec.get("confidence_score") or 0)
    risk_score = float(rec.get("risk_score") or 0)
    composite = round(
        impact_score * 0.5 + confidence_score * 0.3 + (1 - risk_score) * 0.2,
        2,
    )

    if composite >= 0.67:
        return ("HIGH", composite)
    if composite >= 0.42:
        return ("MEDIUM", composite)
    return ("LOW", composite)


def build_action_payload(rec: dict) -> dict:
    meta = rec.get("metadata") or {}
    rec_type = rec.get("type")
    context_outcome = rec.get("context_outcome") or ACTION
    action_type = None
    executable = False
    params: dict[str, Any] = {}
    current_value = None
    new_value = None
    revertability = {"can_revert": False, "window_hours": 24, "strategy": None}

    target = {
        "entity_type": rec.get("entity_type"),
        "entity_id": rec.get("entity_id"),
        "campaign_id": rec.get("campaign_id"),
        "ad_group_id": rec.get("ad_group_id"),
        "google_resource_name": rec.get("google_resource_name"),
    }
    preconditions: dict[str, Any] = {"entity_exists": True}

    if rec_type == "PAUSE_KEYWORD":
        action_type = "PAUSE_KEYWORD"
        executable = bool(rec.get("entity_id"))
        preconditions["expected_status"] = "ENABLED"
        revertability = {"can_revert": True, "window_hours": 24, "strategy": "ENABLE_KEYWORD"}

    elif rec_type in {"INCREASE_BID", "DECREASE_BID"}:
        action_type = "UPDATE_BID"
        current_bid_micros = int(meta.get("current_bid_micros") or 0)
        change_pct = float(meta.get("bid_change_pct") or (20 if rec_type == "INCREASE_BID" else -20))
        if rec_type == "DECREASE_BID" and change_pct > 0:
            change_pct *= -1
        new_bid_micros = int(round(current_bid_micros * (1 + (change_pct / 100))))
        current_value = micros_to_float(current_bid_micros)
        new_value = micros_to_float(new_bid_micros)
        params = {
            "amount": new_value,
            "amount_micros": new_bid_micros,
            "change_pct": change_pct,
        }
        preconditions["current_bid_micros"] = current_bid_micros
        executable = bool(rec.get("entity_id") and current_bid_micros > 0)
        revertability = {"can_revert": True, "window_hours": 24, "strategy": "SET_KEYWORD_BID"}

    elif rec_type == "ADD_KEYWORD":
        action_type = "ADD_KEYWORD"
        params = {
            "text": rec.get("entity_name"),
            "match_type": meta.get("match_type", "EXACT"),
            "source": meta.get("search_term_source", "SEARCH"),
            "ad_group_id": rec.get("ad_group_id"),
        }
        preconditions["keyword_absent"] = True
        executable = bool(rec.get("ad_group_id") and meta.get("search_term_source", "SEARCH") == "SEARCH")
        revertability = {"can_revert": True, "window_hours": 24, "strategy": "PAUSE_KEYWORD"}

    elif rec_type == "ADD_NEGATIVE":
        action_type = "ADD_NEGATIVE"
        params = {
            "text": rec.get("entity_name"),
            "match_type": meta.get("negative_match_type", "PHRASE"),
            "negative_level": meta.get("negative_level", "CAMPAIGN"),
            "campaign_id": rec.get("campaign_id"),
        }
        executable = bool(params["negative_level"] == "CAMPAIGN" and rec.get("campaign_id"))
        revertability = {"can_revert": False, "window_hours": 0, "strategy": None}

    elif rec_type == "PAUSE_AD":
        action_type = "PAUSE_AD"
        executable = bool(rec.get("entity_id"))
        preconditions["expected_status"] = "ENABLED"

    elif rec_type == "IS_BUDGET_ALERT" and meta.get("budget_action") == "INCREASE_BUDGET" and context_outcome == ACTION:
        action_type = "INCREASE_BUDGET"
        current_budget_micros = int(meta.get("current_budget_micros") or 0)
        change_pct = float(meta.get("budget_change_pct") or 20)
        new_budget_micros = int(round(current_budget_micros * (1 + change_pct / 100)))
        current_value = micros_to_float(current_budget_micros)
        new_value = micros_to_float(new_budget_micros)
        params = {
            "amount": new_value,
            "amount_micros": new_budget_micros,
            "change_pct": change_pct,
        }
        preconditions["current_budget_micros"] = current_budget_micros
        executable = bool(rec.get("entity_id") and current_budget_micros > 0)
        revertability = {"can_revert": True, "window_hours": 24, "strategy": "SET_BUDGET"}

    elif rec_type == "REALLOCATE_BUDGET":
        action_type = "REALLOCATE_BUDGET"
        params = {
            "move_amount": meta.get("move_amount", 0),
            "from_campaign_id": meta.get("from_campaign_id"),
            "to_campaign_id": meta.get("to_campaign_id"),
        }
        executable = False

    elif rec_type in NON_EXECUTABLE_TYPES or rec.get("source") in {GOOGLE_ADS_API, ANALYTICS}:
        action_type = None
        executable = False

    return {
        "action_type": action_type,
        "target": target,
        "params": params,
        "preconditions": preconditions,
        "revertability": revertability,
        "executable": executable,
        "current_value": current_value,
        "new_value": new_value,
    }
