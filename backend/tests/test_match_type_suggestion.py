"""Tests for match-type recommendation heuristic."""

import pytest

from app.services.match_type_suggestion import suggest_match_type


def test_strong_intent_ctr_and_convs_triggers_exact():
    s = suggest_match_type(
        text="buy running shoes online",
        clicks=100,
        impressions=1000,    # CTR = 10%
        conversions=5,
    )
    assert s.match_type == "EXACT"
    assert s.rule_id == "strong_intent"
    assert s.confidence >= 0.8


def test_long_tail_with_high_ctr_triggers_exact():
    # 4 tokens, CTR 5%
    s = suggest_match_type(
        text="best running shoes for marathon",
        clicks=50,
        impressions=1000,
        conversions=1,
    )
    assert s.match_type == "EXACT"
    assert s.rule_id == "long_tail_high_ctr"


def test_proven_volume_and_convs_triggers_phrase():
    # clicks >= 20, conv >= 1, CTR moderate (not strong intent), tokens=3
    s = suggest_match_type(
        text="running shoes sale",
        clicks=30,
        impressions=3000,   # CTR 1% — not strong intent
        conversions=2,
    )
    assert s.match_type == "PHRASE"
    assert s.rule_id == "proven_volume"


def test_high_volume_no_conv_still_phrase_low_confidence():
    s = suggest_match_type(
        text="running shoes",
        clicks=30,
        impressions=5000,   # CTR 0.6%, zero conversions
        conversions=0,
    )
    assert s.match_type == "PHRASE"
    assert s.rule_id == "high_volume_no_conv"
    assert s.confidence < 0.5


def test_short_tail_decent_traffic_phrase():
    s = suggest_match_type(
        text="shoes",
        clicks=15,
        impressions=2000,
        conversions=0,
    )
    assert s.match_type == "PHRASE"
    assert s.rule_id == "short_tail"


def test_insufficient_signal_defaults_to_phrase():
    s = suggest_match_type(
        text="very specific brand sneaker model",
        clicks=3,
        impressions=200,
        conversions=0,
    )
    assert s.match_type == "PHRASE"
    assert s.rule_id == "default"


def test_never_suggests_broad():
    """BROAD should never appear in suggestions — operators promote OUT of broad, not into it."""
    for text, clicks, impr, conv in [
        ("shoes", 1000, 10000, 50),
        ("running", 50, 500, 0),
        ("marathon shoes best rated", 100, 1000, 10),
    ]:
        assert suggest_match_type(text, clicks, impr, conv).match_type in ("EXACT", "PHRASE")


def test_zero_impressions_does_not_crash():
    s = suggest_match_type("term", clicks=0, impressions=0, conversions=0)
    assert s.match_type == "PHRASE"
    assert s.rule_id == "default"
