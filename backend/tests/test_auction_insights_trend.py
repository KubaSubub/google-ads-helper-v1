"""Tests for auction insights trend analysis."""

from datetime import date, timedelta

import pytest

from app.models import AuctionInsight, Campaign, Client
from app.services.auction_insights_trend_service import (
    _label,
    _linear_slope,
    compute_trends,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_label_thresholds():
    assert _label(10.0) == "RISING_FAST"
    assert _label(5.0) == "RISING_FAST"
    assert _label(4.9) == "RISING"
    assert _label(2.0) == "RISING"
    assert _label(1.9) == "STABLE"
    assert _label(0.0) == "STABLE"
    assert _label(-1.9) == "STABLE"
    assert _label(-2.0) == "FALLING"
    assert _label(-4.9) == "FALLING"
    assert _label(-5.0) == "FALLING_FAST"
    assert _label(-10.0) == "FALLING_FAST"


def test_linear_slope_positive_trend():
    # Pure +1 per day
    pairs = [(0, 10.0), (1, 11.0), (2, 12.0), (3, 13.0)]
    assert _linear_slope(pairs) == pytest.approx(1.0, abs=1e-6)


def test_linear_slope_flat():
    pairs = [(0, 5.0), (1, 5.0), (2, 5.0)]
    assert _linear_slope(pairs) == pytest.approx(0.0)


def test_linear_slope_single_point_zero():
    assert _linear_slope([(0, 5.0)]) == 0.0
    assert _linear_slope([]) == 0.0


# ---------------------------------------------------------------------------
# Integration with DB
# ---------------------------------------------------------------------------


def _mk(db, client_name="c"):
    client = Client(name=client_name, google_customer_id=f"gc-{client_name}")
    db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id=f"c-{client_name}",
        name="S", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    return client, camp


def _add_insights(db, campaign_id, domain, values_by_day: dict):
    """values_by_day: {days_back_from_today: (impression_share, outranking_share, overlap_rate)}"""
    today = date.today()
    for days_back, (is_val, outrank, overlap) in values_by_day.items():
        db.add(AuctionInsight(
            campaign_id=campaign_id,
            date=today - timedelta(days=days_back),
            display_domain=domain,
            impression_share=is_val,
            outranking_share=outrank,
            overlap_rate=overlap,
            position_above_rate=0.0,
            top_of_page_rate=0.0,
            abs_top_of_page_rate=0.0,
        ))


def test_rising_fast_competitor_labeled_correctly(db):
    client, camp = _mk(db)
    # 14-day window: days 1-14 are current, 15-28 are previous
    # Competitor outranking grew from 10% → 20% (delta +10pp on 0-100 scale).
    current = {d: (0.5, 0.20, 0.4) for d in range(1, 15)}
    previous = {d: (0.5, 0.10, 0.4) for d in range(15, 29)}
    _add_insights(db, camp.id, "competitor.example.com", {**current, **previous})
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert len(trends) == 1
    t = trends[0]
    assert t["competitor_domain"] == "competitor.example.com"
    assert t["outranking_share_delta_pp"] == pytest.approx(10.0, abs=0.1)
    assert t["trend_label"] == "RISING_FAST"


def test_stable_competitor_labeled_stable(db):
    client, camp = _mk(db)
    current = {d: (0.5, 0.15, 0.4) for d in range(1, 15)}
    previous = {d: (0.5, 0.16, 0.4) for d in range(15, 29)}
    _add_insights(db, camp.id, "steady.example.com", {**current, **previous})
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert len(trends) == 1
    assert trends[0]["trend_label"] == "STABLE"


def test_falling_fast_competitor(db):
    client, camp = _mk(db)
    current = {d: (0.3, 0.05, 0.2) for d in range(1, 15)}
    previous = {d: (0.3, 0.15, 0.2) for d in range(15, 29)}
    _add_insights(db, camp.id, "fading.example.com", {**current, **previous})
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert len(trends) == 1
    t = trends[0]
    assert t["outranking_share_delta_pp"] == pytest.approx(-10.0, abs=0.1)
    assert t["trend_label"] == "FALLING_FAST"


def test_results_sorted_by_outranking_delta_desc(db):
    client, camp = _mk(db)
    # Competitor A: +10pp
    cur_a = {d: (0.5, 0.25, 0.4) for d in range(1, 15)}
    prev_a = {d: (0.5, 0.15, 0.4) for d in range(15, 29)}
    _add_insights(db, camp.id, "a.com", {**cur_a, **prev_a})

    # Competitor B: +3pp
    cur_b = {d: (0.4, 0.13, 0.3) for d in range(1, 15)}
    prev_b = {d: (0.4, 0.10, 0.3) for d in range(15, 29)}
    _add_insights(db, camp.id, "b.com", {**cur_b, **prev_b})

    # Competitor C: -5pp
    cur_c = {d: (0.3, 0.05, 0.2) for d in range(1, 15)}
    prev_c = {d: (0.3, 0.10, 0.2) for d in range(15, 29)}
    _add_insights(db, camp.id, "c.com", {**cur_c, **prev_c})
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert [t["competitor_domain"] for t in trends] == ["a.com", "b.com", "c.com"]


def test_no_previous_window_still_returns_current(db):
    """Brand new competitor — only current-window data — trend label = STABLE (delta 0)."""
    client, camp = _mk(db)
    current = {d: (0.2, 0.1, 0.15) for d in range(1, 15)}
    _add_insights(db, camp.id, "new.example.com", current)
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert len(trends) == 1
    t = trends[0]
    # Without previous data, current == previous → deltas ~0
    assert t["outranking_share_delta_pp"] == pytest.approx(0.0)
    assert t["trend_label"] == "STABLE"


def test_slope_reflects_trajectory_inside_window(db):
    """Within the current window, outranking grew linearly — slope should match."""
    client, camp = _mk(db)
    # Day offset vs today; outranking_share starts at 0.10 and grows by 0.01 per day
    values = {}
    for d in range(1, 15):
        # older days_back = earlier in time. Day 14 = start, Day 1 = most recent.
        # We want outranking to grow from day 14 → day 1.
        position = 14 - d  # 0 → 13
        values[d] = (0.5, 0.10 + 0.01 * position, 0.4)
    _add_insights(db, camp.id, "rising.com", values)
    db.commit()

    trends = compute_trends(db, client.id, window_days=14)
    assert len(trends) == 1
    # slope should be roughly +1pp per day (0.01 × 100)
    assert trends[0]["outranking_slope_pp_per_day"] == pytest.approx(1.0, abs=0.1)
