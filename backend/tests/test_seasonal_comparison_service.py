"""Tests for seasonal / YoY comparison service."""

from datetime import date, timedelta

import pytest

from app.models import Campaign, Client, MetricDaily
from app.services.seasonal_comparison_service import (
    _delta_label,
    _delta_pct,
    rolling_comparison,
    yoy_comparison,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_delta_pct():
    assert _delta_pct(110, 100) == 10.0
    assert _delta_pct(80, 100) == -20.0
    assert _delta_pct(100, 0) is None


def test_delta_label_higher_is_better():
    assert _delta_label(10.0, higher_is_better=True) == "BETTER"
    assert _delta_label(-10.0, higher_is_better=True) == "WORSE"
    assert _delta_label(2.0, higher_is_better=True) == "FLAT"
    assert _delta_label(None, higher_is_better=True) == "NO_BASELINE"


def test_delta_label_lower_is_better():
    assert _delta_label(10.0, higher_is_better=False) == "WORSE"
    assert _delta_label(-10.0, higher_is_better=False) == "BETTER"


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


def _mk(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(client_id=client.id, google_campaign_id="c1", name="camp",
                     status="ENABLED", campaign_type="SEARCH")
    db.add(camp); db.flush()
    return client, camp


def _add_metric(db, campaign_id, d, clicks=10, cost_micros=10_000_000,
                 conversions=1.0, conv_value_micros=30_000_000, impressions=500):
    db.add(MetricDaily(
        campaign_id=campaign_id, date=d,
        clicks=clicks, impressions=impressions,
        cost_micros=cost_micros, conversions=conversions,
        conversion_value_micros=conv_value_micros,
    ))


def test_yoy_comparison_detects_growth(db):
    client, camp = _mk(db)
    # Current window — 10 days of today-offset
    today = date(2026, 4, 18)
    for i in range(7):
        _add_metric(db, camp.id, today - timedelta(days=i), clicks=100, cost_micros=100_000_000)

    # Previous window same dates last year, lower volume
    prev_from = today.replace(year=2025) - timedelta(days=6)
    for i in range(7):
        _add_metric(db, camp.id, prev_from + timedelta(days=i), clicks=50, cost_micros=50_000_000)
    db.commit()

    result = yoy_comparison(
        db, client.id,
        date_from=today - timedelta(days=6),
        date_to=today,
    )
    assert result["comparison_type"] == "year_over_year"
    assert result["current"]["clicks"] == 700
    assert result["previous"]["clicks"] == 350
    assert result["deltas"]["clicks"] == 100.0
    assert result["labels"]["clicks"] == "BETTER"


def test_rolling_comparison_offsets_months(db):
    client, camp = _mk(db)
    today = date(2026, 4, 18)
    for i in range(5):
        _add_metric(db, camp.id, today - timedelta(days=i), clicks=100, cost_micros=100_000_000)

    # 3 months ago (~90 days)
    prev_base = today - timedelta(days=90)
    for i in range(5):
        _add_metric(db, camp.id, prev_base - timedelta(days=i), clicks=80, cost_micros=80_000_000)
    db.commit()

    result = rolling_comparison(
        db, client.id,
        date_from=today - timedelta(days=4), date_to=today,
        months=3,
    )
    assert result["comparison_type"] == "rolling"
    assert result["period"]["offset_months"] == 3
    assert result["current"]["clicks"] == 500
    assert result["previous"]["clicks"] == 400


def test_empty_previous_window_no_baseline(db):
    client, camp = _mk(db)
    today = date(2026, 4, 18)
    for i in range(3):
        _add_metric(db, camp.id, today - timedelta(days=i), clicks=50)
    db.commit()

    result = yoy_comparison(
        db, client.id,
        date_from=today - timedelta(days=2), date_to=today,
    )
    # Previous is all zeros → delta is NO_BASELINE since previous=0 triggers None
    assert result["previous"]["clicks"] == 0
    assert result["deltas"]["clicks"] is None
    assert result["labels"]["clicks"] == "NO_BASELINE"


def test_cost_delta_lower_is_better(db):
    """Cost going down = BETTER (unlike clicks/conversions which are higher-is-better)."""
    client, camp = _mk(db)
    today = date(2026, 4, 18)
    # Current: lower cost
    _add_metric(db, camp.id, today, clicks=50, cost_micros=50_000_000)
    # Previous year: higher cost
    prev = today.replace(year=2025)
    _add_metric(db, camp.id, prev, clicks=50, cost_micros=100_000_000)
    db.commit()

    result = yoy_comparison(db, client.id, date_from=today, date_to=today)
    assert result["deltas"]["cost_usd"] < 0  # cost went down
    assert result["labels"]["cost_usd"] == "BETTER"


def test_flat_delta_labeled_flat(db):
    client, camp = _mk(db)
    today = date(2026, 4, 18)
    _add_metric(db, camp.id, today, clicks=100, cost_micros=100_000_000)
    prev = today.replace(year=2025)
    _add_metric(db, camp.id, prev, clicks=102, cost_micros=102_000_000)  # ~+2%
    db.commit()

    result = yoy_comparison(db, client.id, date_from=today, date_to=today)
    assert result["labels"]["clicks"] == "FLAT"
