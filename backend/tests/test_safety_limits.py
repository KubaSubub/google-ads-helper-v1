"""Tests for validate_action() circuit breaker — SAFETY_LIMITS enforcement."""

import pytest
from app.services.action_executor import validate_action, SafetyViolationError


# ---------------------------------------------------------------------------
# UPDATE_BID / SET_BID
# ---------------------------------------------------------------------------


def test_bid_change_under_50pct_passes():
    """40% increase should pass (limit is 50%)."""
    validate_action("SET_BID", current_val=1.0, new_val=1.40, context={})


def test_bid_change_over_50pct_blocked():
    """100% increase should be blocked."""
    with pytest.raises(SafetyViolationError, match="exceeds"):
        validate_action("SET_BID", current_val=1.0, new_val=2.0, context={})


def test_bid_change_exactly_50pct_passes():
    """Exactly 50% should pass (limit is >50%, not >=50%)."""
    validate_action("SET_BID", current_val=1.0, new_val=1.50, context={})


def test_bid_zero_current_blocked():
    """Cannot change bid when current is 0."""
    with pytest.raises(SafetyViolationError, match="current bid is 0"):
        validate_action("SET_BID", current_val=0, new_val=1.0, context={})


def test_bid_below_minimum_blocked():
    """Bid below $0.10 minimum should be blocked."""
    with pytest.raises(SafetyViolationError, match="below minimum"):
        validate_action("SET_BID", current_val=0.10, new_val=0.05, context={})


def test_bid_above_maximum_blocked():
    """Bid above $100 maximum should be blocked."""
    with pytest.raises(SafetyViolationError, match="above maximum"):
        validate_action("SET_BID", current_val=80.0, new_val=110.0, context={})


def test_bid_decrease_under_50pct_passes():
    """30% decrease should pass."""
    validate_action("UPDATE_BID", current_val=2.0, new_val=1.40, context={})


# ---------------------------------------------------------------------------
# INCREASE_BUDGET / SET_BUDGET
# ---------------------------------------------------------------------------


def test_budget_change_under_30pct_passes():
    """20% increase should pass (limit is 30%)."""
    validate_action("INCREASE_BUDGET", current_val=100.0, new_val=120.0, context={})


def test_budget_change_over_30pct_blocked():
    """50% increase should be blocked."""
    with pytest.raises(SafetyViolationError, match="exceeds"):
        validate_action("INCREASE_BUDGET", current_val=100.0, new_val=150.0, context={})


def test_budget_zero_current_blocked():
    """Cannot change budget when current is 0."""
    with pytest.raises(SafetyViolationError, match="current budget is 0"):
        validate_action("SET_BUDGET", current_val=0, new_val=100.0, context={})


# ---------------------------------------------------------------------------
# PAUSE_KEYWORD
# ---------------------------------------------------------------------------


def test_pause_keyword_under_limit_passes():
    """Pausing 10/100 (10%) should pass (limit is 20%)."""
    context = {
        "total_keywords_in_campaign": 100,
        "keywords_paused_today_in_campaign": 10,
    }
    validate_action("PAUSE_KEYWORD", current_val=0, new_val=0, context=context)


def test_pause_keyword_over_limit_blocked():
    """Pausing 20/100 (20%+1) should be blocked."""
    context = {
        "total_keywords_in_campaign": 100,
        "keywords_paused_today_in_campaign": 20,
    }
    with pytest.raises(SafetyViolationError, match="Already paused"):
        validate_action("PAUSE_KEYWORD", current_val=0, new_val=0, context=context)


def test_pause_keyword_empty_campaign_passes():
    """No keywords in campaign should pass (no division by zero)."""
    context = {
        "total_keywords_in_campaign": 0,
        "keywords_paused_today_in_campaign": 0,
    }
    validate_action("PAUSE_KEYWORD", current_val=0, new_val=0, context=context)


# ---------------------------------------------------------------------------
# ADD_NEGATIVE
# ---------------------------------------------------------------------------


def test_add_negative_under_limit_passes():
    """50 negatives today should pass (limit is 100)."""
    context = {"negatives_added_today": 50}
    validate_action("ADD_NEGATIVE", current_val=0, new_val=0, context=context)


def test_add_negative_at_limit_blocked():
    """100 negatives today should be blocked."""
    context = {"negatives_added_today": 100}
    with pytest.raises(SafetyViolationError, match="Daily negative limit"):
        validate_action("ADD_NEGATIVE", current_val=0, new_val=0, context=context)
