"""Tests for hourly dayparting service."""

from datetime import date, timedelta

import pytest

from app.models import Campaign, Client
from app.models.metric_segmented import MetricSegmented
from app.services.dayparting_service import (
    _safe_div,
    bid_schedule_suggestions,
    hourly_breakdown,
)


def test_safe_div():
    assert _safe_div(10, 5) == 2.0
    assert _safe_div(10, 0) == 0.0
    assert _safe_div(0, 5) == 0.0


def _mk(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(client_id=client.id, google_campaign_id="c1", name="camp",
                     status="ENABLED", campaign_type="SEARCH")
    db.add(camp); db.flush()
    return client, camp


def _add_segmented(db, campaign_id, hour, clicks, impressions, cost_micros,
                    conversions, conv_value_micros=0, days_back=1):
    today = date.today()
    db.add(MetricSegmented(
        campaign_id=campaign_id,
        date=today - timedelta(days=days_back),
        hour_of_day=hour,
        clicks=clicks,
        impressions=impressions,
        cost_micros=cost_micros,
        conversions=conversions,
        conversion_value_micros=conv_value_micros,
    ))


def test_hourly_breakdown_empty(db):
    client, _camp = _mk(db)
    result = hourly_breakdown(db, client.id)
    assert result["hours"] == []
    assert result["overall"]["cpa_usd"] is None


def test_hourly_breakdown_computes_per_hour_metrics(db):
    client, camp = _mk(db)
    _add_segmented(db, camp.id, hour=9, clicks=50, impressions=500,
                    cost_micros=50_000_000, conversions=5.0, conv_value_micros=250_000_000)
    _add_segmented(db, camp.id, hour=22, clicks=20, impressions=500,
                    cost_micros=40_000_000, conversions=0, conv_value_micros=0)
    db.commit()

    result = hourly_breakdown(db, client.id)
    by_hour = {h["hour"]: h for h in result["hours"]}

    assert by_hour[9]["cpa_usd"] == pytest.approx(10.0, rel=1e-3)
    assert by_hour[9]["cvr_pct"] == pytest.approx(10.0, rel=1e-3)
    assert by_hour[9]["roas"] == pytest.approx(5.0, rel=1e-3)

    # zero-conversion hour → cpa_usd = None (can't recommend bid-up)
    assert by_hour[22]["cpa_usd"] is None
    assert by_hour[22]["cvr_pct"] == 0.0


def test_hourly_breakdown_vs_overall_delta(db):
    client, camp = _mk(db)
    # overall CPA = (100+100)/(10+2) = 16.67
    _add_segmented(db, camp.id, hour=9, clicks=50, impressions=500,
                    cost_micros=100_000_000, conversions=10.0)
    _add_segmented(db, camp.id, hour=22, clicks=50, impressions=500,
                    cost_micros=100_000_000, conversions=2.0)
    db.commit()

    result = hourly_breakdown(db, client.id)
    by_hour = {h["hour"]: h for h in result["hours"]}

    # hour 9: CPA 10 vs overall 16.67 → -40%
    assert by_hour[9]["cpa_usd"] == pytest.approx(10.0, rel=1e-3)
    assert by_hour[9]["cpa_vs_overall_pct"] < -30

    # hour 22: CPA 50 vs overall 16.67 → +200%
    assert by_hour[22]["cpa_usd"] == pytest.approx(50.0, rel=1e-3)
    assert by_hour[22]["cpa_vs_overall_pct"] > 100


def test_bid_schedule_suggestion_decrease_on_high_cpa(db):
    client, camp = _mk(db)
    # overall CPA moderate
    _add_segmented(db, camp.id, hour=9, clicks=50, impressions=500,
                    cost_micros=50_000_000, conversions=5.0)
    # hour 22 bad: CPA 25 vs overall ~12 → 2× over, DECREASE
    _add_segmented(db, camp.id, hour=22, clicks=20, impressions=200,
                    cost_micros=50_000_000, conversions=2.0)
    db.commit()

    suggestions = bid_schedule_suggestions(db, client.id, min_cost_usd=10.0)
    by_hour = {s["hour"]: s for s in suggestions}
    assert 22 in by_hour
    assert by_hour[22]["suggestion_type"] == "DECREASE"
    assert by_hour[22]["bid_adjustment_pct"] < 0


def test_bid_schedule_suggestion_increase_on_low_cpa(db):
    client, camp = _mk(db)
    # overall CPA dominated by expensive hour
    _add_segmented(db, camp.id, hour=22, clicks=30, impressions=300,
                    cost_micros=60_000_000, conversions=2.0)  # CPA 30
    _add_segmented(db, camp.id, hour=9, clicks=50, impressions=500,
                    cost_micros=25_000_000, conversions=10.0)  # CPA 2.5
    db.commit()

    # overall CPA = 85/12 = 7.08; hour 9 CPA 2.5 → ratio 0.35 → INCREASE
    suggestions = bid_schedule_suggestions(db, client.id, min_cost_usd=10.0)
    by_hour = {s["hour"]: s for s in suggestions}
    assert 9 in by_hour
    assert by_hour[9]["suggestion_type"] == "INCREASE"
    assert by_hour[9]["bid_adjustment_pct"] > 0


def test_bid_schedule_zero_conv_with_spend_flags_review(db):
    client, camp = _mk(db)
    _add_segmented(db, camp.id, hour=9, clicks=100, impressions=1000,
                    cost_micros=100_000_000, conversions=10.0)
    _add_segmented(db, camp.id, hour=23, clicks=40, impressions=400,
                    cost_micros=80_000_000, conversions=0)
    db.commit()

    # min_cost_usd=10, hour 23 has $80 → flagged as REVIEW (never INCREASE)
    suggestions = bid_schedule_suggestions(db, client.id, min_cost_usd=10.0)
    by_hour = {s["hour"]: s for s in suggestions}
    assert 23 in by_hour
    assert by_hour[23]["suggestion_type"] == "REVIEW"
    assert by_hour[23]["bid_adjustment_pct"] is None


def test_bid_schedule_ignores_low_spend_hours(db):
    client, camp = _mk(db)
    _add_segmented(db, camp.id, hour=9, clicks=50, impressions=500,
                    cost_micros=50_000_000, conversions=5.0)
    # hour 3 very low spend → ignored even with bad CPA
    _add_segmented(db, camp.id, hour=3, clicks=2, impressions=20,
                    cost_micros=5_000_000, conversions=0)
    db.commit()

    suggestions = bid_schedule_suggestions(db, client.id, min_cost_usd=10.0)
    hours_surfaced = {s["hour"] for s in suggestions}
    assert 3 not in hours_surfaced
