"""Tests for A2 — Irrelevant Dictionary script.

Focus: AD_GROUP branching fix (P0), hard-match detection, keyword protection.
"""

from unittest.mock import patch

from app.models.action_log import ActionLog
from app.models.negative_keyword import NegativeKeyword
from app.services.scripts.a2_irrelevant_dictionary import IrrelevantDictionaryScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_a2_hard_match_from_irrelevant_seed(db):
    """IRRELEVANT_KEYWORDS seed 'darmowe' triggers hard match."""
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="darmowe sushi",
        clicks=10, cost_pln=30, conversions=0,
    )

    script = IrrelevantDictionaryScript()
    result = script.dry_run(db, tree["client"].id, None, None, {})

    assert result.total_matching >= 1
    hard = [i for i in result.items if i.action_payload.get("match_source") == "hard"]
    assert hard, "expected at least one hard match"
    assert hard[0].action_payload["ad_group_id"] == tree["ad_groups"]["a"].id


def test_a2_brand_protection_skips_branded_term(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(
        db, tree=tree, text="darmowe naka",
        clicks=10, cost_pln=30, conversions=0,
    )

    script = IrrelevantDictionaryScript()
    result = script.dry_run(db, tree["client"].id, None, None, {"brand_protection": True})

    brand_hits = [i for i in result.items if "naka" in i.entity_name.lower()]
    assert not brand_hits


def test_a2_execute_branches_to_ad_group_negatives(db, monkeypatch):
    """P0 fix: when negative_level=AD_GROUP execute must call batch_add_ad_group_negatives."""
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="darmowe sushi",
        clicks=10, cost_pln=30, conversions=0,
    )

    calls = {"ag": 0, "camp": 0, "ag_ids": []}

    def fake_ad_group(db_, ad_group, negs):
        calls["ag"] += 1
        calls["ag_ids"].append(ad_group.id)

    def fake_campaign(db_, campaign, negs):
        calls["camp"] += 1

    from app.services.google_ads import google_ads_service
    monkeypatch.setattr(google_ads_service, "batch_add_ad_group_negatives", fake_ad_group)
    monkeypatch.setattr(google_ads_service, "batch_add_campaign_negatives", fake_campaign)

    with patch.object(type(google_ads_service), "is_connected", new=True):
        script = IrrelevantDictionaryScript()
        result = script.execute(
            db, tree["client"].id, None, None,
            {"negative_level": "AD_GROUP"},
        )

    assert result.applied >= 1
    assert calls["ag"] >= 1, "AD_GROUP level must route to batch_add_ad_group_negatives"
    assert calls["camp"] == 0

    neg = db.query(NegativeKeyword).filter(NegativeKeyword.negative_scope == "AD_GROUP").first()
    assert neg is not None
    assert neg.ad_group_id == tree["ad_groups"]["a"].id


def test_a2_execute_uses_campaign_batch_for_campaign_level(db, monkeypatch):
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="darmowe sushi",
        clicks=10, cost_pln=30, conversions=0,
    )

    calls = {"ag": 0, "camp": 0}

    from app.services.google_ads import google_ads_service
    monkeypatch.setattr(
        google_ads_service, "batch_add_ad_group_negatives",
        lambda *_a, **_k: calls.__setitem__("ag", calls["ag"] + 1),
    )
    monkeypatch.setattr(
        google_ads_service, "batch_add_campaign_negatives",
        lambda *_a, **_k: calls.__setitem__("camp", calls["camp"] + 1),
    )

    with patch.object(type(google_ads_service), "is_connected", new=True):
        script = IrrelevantDictionaryScript()
        script.execute(db, tree["client"].id, None, None, {"negative_level": "CAMPAIGN"})

    assert calls["camp"] >= 1
    assert calls["ag"] == 0


def test_a2_execute_requires_google_ads_connection(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="darmowe sushi", clicks=10, cost_pln=30)

    from app.services.google_ads import google_ads_service
    with patch.object(type(google_ads_service), "is_connected", new=False):
        script = IrrelevantDictionaryScript()
        result = script.execute(db, tree["client"].id, None, None, {})

    assert result.applied == 0
    assert result.errors
