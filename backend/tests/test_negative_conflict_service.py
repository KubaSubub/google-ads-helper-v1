"""Tests for negative-keyword ↔ positive-keyword conflict detection."""

from datetime import date

import pytest

from app.models import AdGroup, Campaign, Client, Keyword, NegativeKeyword
from app.services.negative_conflict_service import (
    _negative_blocks_positive,
    _normalise,
    detect_conflicts,
)


# ---------------------------------------------------------------------------
# Pure helpers — no DB needed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("cheap shoes", ["cheap", "shoes"]),
        ("[cheap shoes]", ["cheap", "shoes"]),
        ('"cheap shoes"', ["cheap", "shoes"]),
        ("+cheap +shoes", ["cheap", "shoes"]),
        ("  CHEAP   SHOES  ", ["cheap", "shoes"]),
        ("", []),
    ],
)
def test_normalise_strips_match_markers(raw, expected):
    assert _normalise(raw) == expected


def test_exact_negative_blocks_only_exact_positive():
    neg = _normalise("cheap shoes")
    assert _negative_blocks_positive(neg, "EXACT", _normalise("cheap shoes")) is True
    assert _negative_blocks_positive(neg, "EXACT", _normalise("cheap running shoes")) is False


def test_phrase_negative_blocks_substring_positive():
    neg = _normalise("cheap shoes")
    assert _negative_blocks_positive(neg, "PHRASE", _normalise("cheap shoes")) is True
    # substring of tokens in order
    assert _negative_blocks_positive(neg, "PHRASE", _normalise("buy cheap shoes online")) is True
    # tokens present but not contiguous → phrase negative should NOT block
    assert _negative_blocks_positive(neg, "PHRASE", _normalise("cheap running shoes")) is False


def test_broad_negative_blocks_when_all_tokens_present_any_order():
    neg = _normalise("cheap shoes")
    assert _negative_blocks_positive(neg, "BROAD", _normalise("cheap shoes")) is True
    assert _negative_blocks_positive(neg, "BROAD", _normalise("shoes cheap online")) is True
    assert _negative_blocks_positive(neg, "BROAD", _normalise("cheap running shoes")) is True
    assert _negative_blocks_positive(neg, "BROAD", _normalise("expensive shoes")) is False


def test_empty_negative_does_not_block():
    assert _negative_blocks_positive([], "PHRASE", _normalise("cheap shoes")) is False


# ---------------------------------------------------------------------------
# Integration — actual DB
# ---------------------------------------------------------------------------


def _build_campaign(db, client, name="c1"):
    c = Campaign(
        client_id=client.id,
        google_campaign_id=f"gc-{name}",
        name=name,
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(c)
    db.flush()
    ag = AdGroup(campaign_id=c.id, google_ad_group_id=f"gag-{name}", name=f"ag-{name}", status="ENABLED")
    db.add(ag)
    db.flush()
    return c, ag


def test_campaign_scope_phrase_negative_blocks_exact_positive(db):
    """High-value case: campaign-scope phrase negative silently blocking an ad-group exact positive."""
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    camp, ag = _build_campaign(db, client)

    positive = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="k1",
        text="cheap running shoes",
        match_type="EXACT",
        status="ENABLED",
        cost_micros=120_000_000,   # $120
        conversions=4.0,
    )
    negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=camp.id,
        text="cheap shoes",
        match_type="PHRASE",
        negative_scope="CAMPAIGN",
        status="ENABLED",
    )
    db.add_all([positive, negative])
    db.commit()

    conflicts = detect_conflicts(db, client.id)
    # Phrase "cheap shoes" is NOT a contiguous substring of "cheap running shoes"
    # → this specific case does not conflict under phrase semantics.
    assert conflicts == []


def test_campaign_scope_broad_negative_blocks_exact_positive(db):
    """Broad negative 'cheap shoes' DOES block 'cheap running shoes' positive."""
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    camp, ag = _build_campaign(db, client)

    positive = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="k1",
        text="cheap running shoes",
        match_type="EXACT",
        status="ENABLED",
        cost_micros=120_000_000,
        conversions=4.0,
    )
    negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=camp.id,
        text="cheap shoes",
        match_type="BROAD",
        negative_scope="CAMPAIGN",
        status="ENABLED",
    )
    db.add_all([positive, negative])
    db.commit()

    conflicts = detect_conflicts(db, client.id)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["positive_text"] == "cheap running shoes"
    assert c["negative_text"] == "cheap shoes"
    assert c["scope"] == "campaign"
    assert c["positive_cost_usd"] == pytest.approx(120.0, rel=1e-3)
    assert c["positive_conversions"] == pytest.approx(4.0)


def test_negative_in_different_campaign_does_not_conflict(db):
    """Campaign-scope negatives only affect keywords inside the same campaign."""
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    c1, ag1 = _build_campaign(db, client, "c1")
    c2, ag2 = _build_campaign(db, client, "c2")

    positive = Keyword(
        ad_group_id=ag1.id,
        google_keyword_id="k1",
        text="running shoes",
        match_type="PHRASE",
        status="ENABLED",
        cost_micros=50_000_000,
        conversions=2.0,
    )
    negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=c2.id,   # different campaign
        text="running shoes",
        match_type="EXACT",
        negative_scope="CAMPAIGN",
        status="ENABLED",
    )
    db.add_all([positive, negative])
    db.commit()

    assert detect_conflicts(db, client.id) == []


def test_ad_group_scope_negative_only_blocks_its_ad_group(db):
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    camp, ag1 = _build_campaign(db, client, "c1")
    ag2 = AdGroup(campaign_id=camp.id, google_ad_group_id="gag-other", name="ag-other", status="ENABLED")
    db.add(ag2); db.flush()

    pos_in_blocked_ag = Keyword(
        ad_group_id=ag1.id, google_keyword_id="k1",
        text="blue running shoes", match_type="BROAD",
        status="ENABLED", cost_micros=10_000_000, conversions=1.0,
    )
    pos_in_other_ag = Keyword(
        ad_group_id=ag2.id, google_keyword_id="k2",
        text="blue running shoes", match_type="BROAD",
        status="ENABLED", cost_micros=10_000_000, conversions=1.0,
    )
    neg = NegativeKeyword(
        client_id=client.id, ad_group_id=ag1.id, campaign_id=None,
        text="blue shoes", match_type="BROAD",
        negative_scope="AD_GROUP", status="ENABLED",
    )
    db.add_all([pos_in_blocked_ag, pos_in_other_ag, neg])
    db.commit()

    conflicts = detect_conflicts(db, client.id)
    # Exactly one conflict: the positive in ag1. The one in ag2 is out of scope.
    assert len(conflicts) == 1
    assert conflicts[0]["ad_group_id"] == ag1.id


def test_conflicts_ordered_by_positive_cost_desc(db):
    """Highest-spend blocked positives appear first — matters when capping output."""
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    camp, ag = _build_campaign(db, client)

    cheap = Keyword(
        ad_group_id=ag.id, google_keyword_id="cheap",
        text="a term", match_type="BROAD",
        status="ENABLED", cost_micros=5_000_000, conversions=0,
    )
    expensive = Keyword(
        ad_group_id=ag.id, google_keyword_id="expensive",
        text="a term", match_type="BROAD",
        status="ENABLED", cost_micros=500_000_000, conversions=10.0,
    )
    neg = NegativeKeyword(
        client_id=client.id, campaign_id=camp.id,
        text="a term", match_type="BROAD",
        negative_scope="CAMPAIGN", status="ENABLED",
    )
    db.add_all([cheap, expensive, neg])
    db.commit()

    conflicts = detect_conflicts(db, client.id)
    assert [c["positive_keyword_id"] for c in conflicts] == [expensive.id, cheap.id]


def test_disabled_positive_or_disabled_negative_not_reported(db):
    client = Client(name="c", google_customer_id="1"); db.add(client); db.flush()
    camp, ag = _build_campaign(db, client)

    disabled_pos = Keyword(
        ad_group_id=ag.id, google_keyword_id="p",
        text="cheap shoes", match_type="EXACT",
        status="PAUSED", cost_micros=1_000_000, conversions=0,
    )
    neg = NegativeKeyword(
        client_id=client.id, campaign_id=camp.id,
        text="cheap shoes", match_type="EXACT",
        negative_scope="CAMPAIGN", status="ENABLED",
    )
    db.add_all([disabled_pos, neg]); db.commit()
    assert detect_conflicts(db, client.id) == []

    disabled_pos.status = "ENABLED"
    neg.status = "REMOVED"
    db.commit()
    assert detect_conflicts(db, client.id) == []
