"""Tests for keyword cannibalization detection."""

import pytest

from app.models import AdGroup, Campaign, Client, Keyword
from app.services.keyword_cannibalization_service import (
    _normalise,
    detect_cannibalization,
)


def _mk(db, client_name="c") -> tuple[Client, Campaign, AdGroup, AdGroup]:
    client = Client(name=client_name, google_customer_id=f"gc-{client_name}")
    db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id,
        google_campaign_id=f"c-{client_name}",
        name="Search camp",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(camp); db.flush()
    ag1 = AdGroup(campaign_id=camp.id, google_ad_group_id=f"ag1-{client_name}", name="ag1", status="ENABLED")
    ag2 = AdGroup(campaign_id=camp.id, google_ad_group_id=f"ag2-{client_name}", name="ag2", status="ENABLED")
    db.add_all([ag1, ag2]); db.flush()
    return client, camp, ag1, ag2


def test_normalise_lowercases_and_collapses():
    assert _normalise("  CHEAP   Shoes  ") == "cheap shoes"
    assert _normalise("[cheap shoes]") == "cheap shoes"
    assert _normalise("") == ""
    assert _normalise(None) == ""


def test_duplicate_exact_in_same_ad_group_is_high(db):
    client, camp, ag1, _ag2 = _mk(db)
    a = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=80_000_000, conversions=2.0, clicks=40,
    )
    b = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k2", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=60_000_000, conversions=1.0, clicks=30,
    )
    db.add_all([a, b]); db.commit()

    findings = detect_cannibalization(db, client.id)
    assert len(findings) == 1
    f = findings[0]
    assert f["kind"] == "DUPLICATE_EXACT_IN_AD_GROUP"
    assert f["severity"] == "HIGH"
    assert f["combined_cost_usd"] == pytest.approx(140.0, rel=1e-3)
    assert f["combined_conversions"] == pytest.approx(3.0)
    assert f["combined_clicks"] == 70


def test_exact_vs_phrase_in_same_ad_group_is_medium(db):
    client, camp, ag1, _ag2 = _mk(db)
    a = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=50_000_000, conversions=2.0, clicks=25,
    )
    b = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k2", text="running shoes",
        match_type="PHRASE", status="ENABLED", cost_micros=70_000_000, conversions=1.0, clicks=35,
    )
    db.add_all([a, b]); db.commit()

    findings = detect_cannibalization(db, client.id)
    assert len(findings) == 1
    assert findings[0]["kind"] == "EXACT_VS_PHRASE_SAME_AD_GROUP"
    assert findings[0]["severity"] == "MEDIUM"


def test_cross_ad_group_same_text_is_medium(db):
    client, camp, ag1, ag2 = _mk(db)
    a = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=100_000_000, conversions=2.0, clicks=50,
    )
    b = Keyword(
        ad_group_id=ag2.id, google_keyword_id="k2", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=80_000_000, conversions=1.0, clicks=40,
    )
    db.add_all([a, b]); db.commit()

    findings = detect_cannibalization(db, client.id)
    assert len(findings) == 1
    assert findings[0]["kind"] == "CROSS_AD_GROUP_SAME_TEXT"
    assert findings[0]["scope"] == "campaign"


def test_findings_ordered_by_combined_cost(db):
    client, camp, ag1, _ag2 = _mk(db)
    # Pair 1 — cheap
    a = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1", text="cheap term",
        match_type="EXACT", status="ENABLED", cost_micros=5_000_000, conversions=0, clicks=3,
    )
    b = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k2", text="cheap term",
        match_type="EXACT", status="ENABLED", cost_micros=10_000_000, conversions=0, clicks=5,
    )
    # Pair 2 — expensive
    c = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k3", text="expensive term",
        match_type="EXACT", status="ENABLED", cost_micros=300_000_000, conversions=5, clicks=150,
    )
    d = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k4", text="expensive term",
        match_type="EXACT", status="ENABLED", cost_micros=400_000_000, conversions=7, clicks=200,
    )
    db.add_all([a, b, c, d]); db.commit()

    findings = detect_cannibalization(db, client.id)
    assert len(findings) == 2
    assert findings[0]["normalised_text"] == "expensive term"
    assert findings[1]["normalised_text"] == "cheap term"


def test_paused_keyword_not_flagged(db):
    client, camp, ag1, _ag2 = _mk(db)
    a = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1", text="running shoes",
        match_type="EXACT", status="ENABLED", cost_micros=10_000_000, conversions=0, clicks=5,
    )
    b = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k2", text="running shoes",
        match_type="EXACT", status="PAUSED", cost_micros=20_000_000, conversions=0, clicks=10,
    )
    db.add_all([a, b]); db.commit()
    assert detect_cannibalization(db, client.id) == []


def test_non_search_campaign_is_skipped(db):
    """Cannibalization doesn't apply to PMax / DISPLAY / VIDEO — no keyword-level auction picking."""
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    camp = Campaign(
        client_id=client.id, google_campaign_id="c",
        name="PMax", status="ENABLED", campaign_type="PERFORMANCE_MAX",
    )
    db.add(camp); db.flush()
    ag = AdGroup(campaign_id=camp.id, google_ad_group_id="ag", name="ag", status="ENABLED")
    db.add(ag); db.flush()

    # Even in the unlikely case that PMax had a keyword row, we shouldn't flag it.
    a = Keyword(
        ad_group_id=ag.id, google_keyword_id="k1", text="t",
        match_type="EXACT", status="ENABLED", cost_micros=10_000_000, conversions=0, clicks=1,
    )
    b = Keyword(
        ad_group_id=ag.id, google_keyword_id="k2", text="t",
        match_type="EXACT", status="ENABLED", cost_micros=20_000_000, conversions=0, clicks=2,
    )
    db.add_all([a, b]); db.commit()
    assert detect_cannibalization(db, client.id) == []
