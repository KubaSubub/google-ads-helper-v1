"""Tests for audience overlap / redundancy detection."""

from datetime import date, timedelta

import pytest

from app.models import Campaign, Client
from app.models.campaign_audience import CampaignAudienceMetric
from app.services.audience_overlap_service import (
    _safe_ratio,
    _token_jaccard,
    detect_audience_redundancy,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_token_jaccard_identical_is_1():
    assert _token_jaccard("running shoes marathon", "running shoes marathon") == 1.0


def test_token_jaccard_disjoint_is_0():
    assert _token_jaccard("apple banana", "cherry date") == 0.0


def test_token_jaccard_partial():
    # {"running","shoes"} vs {"running","boots"} → intersection 1, union 3 → 1/3
    assert _token_jaccard("running shoes", "running boots") == pytest.approx(1 / 3)


def test_token_jaccard_empty_inputs():
    assert _token_jaccard("", "foo") == 0.0
    assert _token_jaccard("foo", "") == 0.0
    assert _token_jaccard("", "") == 0.0


def test_safe_ratio():
    assert _safe_ratio(10, 5) == 2.0
    assert _safe_ratio(0, 10) == 0.0
    assert _safe_ratio(10, 0) == 0.0


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


def _mk(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="camp", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    return client, camp


def _add_audience_metric(db, campaign_id, resource, name, aud_type,
                        clicks, impressions, conversions, cost_micros, conv_value_micros=0, days_back=5):
    today = date.today()
    db.add(CampaignAudienceMetric(
        campaign_id=campaign_id,
        audience_resource_name=resource,
        audience_name=name,
        audience_type=aud_type,
        date=today - timedelta(days=days_back),
        clicks=clicks,
        impressions=impressions,
        conversions=conversions,
        cost_micros=cost_micros,
        conversion_value_micros=conv_value_micros,
    ))


def test_same_type_similar_names_similar_perf_triggers_high(db):
    """Three signals align → HIGH severity."""
    client, camp = _mk(db)
    _add_audience_metric(db, camp.id, "res1", "Running enthusiasts 25-54",
                          "IN_MARKET", clicks=100, impressions=1000,
                          conversions=10.0, cost_micros=100_000_000, conv_value_micros=500_000_000)
    _add_audience_metric(db, camp.id, "res2", "Running enthusiasts 25 54",
                          "IN_MARKET", clicks=100, impressions=1000,
                          conversions=10.0, cost_micros=100_000_000, conv_value_micros=500_000_000)
    db.commit()

    findings = detect_audience_redundancy(db, client.id, window_days=30)
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == "HIGH"
    assert len(f["signals"]) == 3


def test_same_type_dissimilar_names_no_match(db):
    """Only 1 signal (same type) → doesn't fire."""
    client, camp = _mk(db)
    _add_audience_metric(db, camp.id, "res1", "Runners",
                          "IN_MARKET", clicks=100, impressions=1000,
                          conversions=10.0, cost_micros=100_000_000)
    _add_audience_metric(db, camp.id, "res2", "Skiing enthusiasts",
                          "IN_MARKET", clicks=50, impressions=500,
                          conversions=2.0, cost_micros=80_000_000)
    db.commit()

    assert detect_audience_redundancy(db, client.id) == []


def test_different_type_same_name_no_match(db):
    """Name similar but different type — not redundant (different targeting)."""
    client, camp = _mk(db)
    _add_audience_metric(db, camp.id, "res1", "Running shoes buyers",
                          "IN_MARKET", clicks=100, impressions=1000,
                          conversions=10.0, cost_micros=100_000_000)
    _add_audience_metric(db, camp.id, "res2", "Running shoes buyers",
                          "REMARKETING", clicks=100, impressions=1000,
                          conversions=10.0, cost_micros=100_000_000)
    db.commit()

    # Name match + similar perf = 2 signals but different type so type-signal not present.
    findings = detect_audience_redundancy(db, client.id)
    # jaccard identical = name signal, similar perf = perf signal → 2 signals MEDIUM
    assert len(findings) == 1
    assert findings[0]["severity"] == "MEDIUM"


def test_cross_campaign_no_redundancy(db):
    """Redundancy is per-campaign — same audience in two campaigns is fine."""
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    c1 = Campaign(client_id=client.id, google_campaign_id="c1", name="a", status="ENABLED", campaign_type="SEARCH")
    c2 = Campaign(client_id=client.id, google_campaign_id="c2", name="b", status="ENABLED", campaign_type="SEARCH")
    db.add_all([c1, c2]); db.flush()

    _add_audience_metric(db, c1.id, "res1", "Runners", "IN_MARKET",
                          clicks=100, impressions=1000, conversions=10.0, cost_micros=50_000_000)
    _add_audience_metric(db, c2.id, "res2", "Runners", "IN_MARKET",
                          clicks=100, impressions=1000, conversions=10.0, cost_micros=50_000_000)
    db.commit()

    assert detect_audience_redundancy(db, client.id) == []


def test_findings_sorted_high_first_then_by_cost(db):
    """HIGH (3 signals) should surface before MEDIUM (2 signals)."""
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    c1 = Campaign(client_id=client.id, google_campaign_id="c1", name="camp1", status="ENABLED", campaign_type="SEARCH")
    c2 = Campaign(client_id=client.id, google_campaign_id="c2", name="camp2", status="ENABLED", campaign_type="SEARCH")
    db.add_all([c1, c2]); db.flush()

    # MEDIUM pair on c1, big spend
    _add_audience_metric(db, c1.id, "m1", "Marathon runners", "IN_MARKET",
                          clicks=200, impressions=2000, conversions=20.0,
                          cost_micros=1_000_000_000, conv_value_micros=3_000_000_000)
    _add_audience_metric(db, c1.id, "m2", "Trail runners", "IN_MARKET",
                          clicks=50, impressions=500, conversions=2.0,
                          cost_micros=200_000_000, conv_value_micros=400_000_000)

    # HIGH pair on c2 (3 signals): same type + high name similarity + similar perf
    _add_audience_metric(db, c2.id, "h1", "Runners 25-54", "IN_MARKET",
                          clicks=100, impressions=1000, conversions=10.0,
                          cost_micros=50_000_000, conv_value_micros=250_000_000)
    _add_audience_metric(db, c2.id, "h2", "Runners 25-54 premium", "IN_MARKET",
                          clicks=100, impressions=1000, conversions=10.0,
                          cost_micros=50_000_000, conv_value_micros=250_000_000)
    db.commit()

    findings = detect_audience_redundancy(db, client.id)
    # HIGH should be first regardless of cost
    assert findings[0]["severity"] == "HIGH"
