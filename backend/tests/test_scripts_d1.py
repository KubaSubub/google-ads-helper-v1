"""Tests for D1 — N-gram Waste script (P0 cross-campaign fix)."""

from unittest.mock import patch

from app.models.negative_keyword import NegativeKeyword
from app.services.scripts.d1_ngram_waste import NgramWasteScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_d1_dry_run_exposes_all_campaign_ids(db):
    """P0 fix: action_payload.campaign_ids must list every campaign the n-gram touched."""
    tree = build_basic_tree(db)
    # Same "tanie" n-gram appears in 3+ terms across both campaigns.
    add_search_term(db, tree=tree, text="tanie jedzenie a1", clicks=10, cost_pln=15, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="tanie jedzenie a2", clicks=10, cost_pln=15, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="tanie jedzenie b1", clicks=10, cost_pln=15, campaign_key="b", ad_group_key="b")

    script = NgramWasteScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_term_count": 3, "min_total_cost_pln": 10},
    )

    unigrams = [i for i in result.items if i.metrics.get("ngram_size") == 1]
    tanie = next((i for i in unigrams if i.entity_name == "tanie"), None)
    assert tanie is not None, "expected n-gram 'tanie' to be flagged"
    camp_ids = tanie.action_payload.get("campaign_ids")
    assert camp_ids and len(camp_ids) == 2
    assert set(camp_ids) == {tree["campaigns"]["a"].id, tree["campaigns"]["b"].id}
    assert tanie.metrics["campaign_count"] == 2


def test_d1_execute_pushes_negative_to_every_campaign(db, monkeypatch):
    """P0 fix: execute must create one NegativeKeyword per campaign, not just one."""
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="tanie jedzenie a1", clicks=10, cost_pln=15, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="tanie jedzenie a2", clicks=10, cost_pln=15, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="tanie jedzenie b1", clicks=10, cost_pln=15, campaign_key="b", ad_group_key="b")

    pushed_campaign_ids: list[int] = []

    def fake_batch(db_, campaign, negs):
        pushed_campaign_ids.append(campaign.id)

    from app.services.google_ads import google_ads_service
    monkeypatch.setattr(google_ads_service, "batch_add_campaign_negatives", fake_batch)

    with patch.object(type(google_ads_service), "is_connected", new=True):
        script = NgramWasteScript()
        result = script.execute(
            db, tree["client"].id, None, None,
            {"min_term_count": 3, "min_total_cost_pln": 10},
            item_ids=["1:tanie"],
        )

    # One DB row per campaign for the n-gram "tanie"
    negs = db.query(NegativeKeyword).filter(NegativeKeyword.text == "tanie").all()
    assert len(negs) == 2
    assert {n.campaign_id for n in negs} == {tree["campaigns"]["a"].id, tree["campaigns"]["b"].id}

    assert result.applied >= 2
    assert set(pushed_campaign_ids) == {tree["campaigns"]["a"].id, tree["campaigns"]["b"].id}


def test_d1_keyword_protection_blocks_matching_keyword(db):
    """N-gram identical to an active keyword should never surface."""
    tree = build_basic_tree(db)
    # "sushi wroclaw" is already a keyword in Search A — do not flag unigrams that collide.
    for i in range(3):
        add_search_term(
            db, tree=tree, text=f"sushi wroclaw fragment {i}",
            clicks=10, cost_pln=15,
        )

    script = NgramWasteScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_term_count": 3, "min_total_cost_pln": 10},
    )

    items_text = {i.entity_name for i in result.items}
    assert "sushi wroclaw" not in items_text, "full keyword must be BLOCK-skipped"


def test_d1_execute_requires_api_connection(db):
    tree = build_basic_tree(db)
    for i in range(3):
        add_search_term(db, tree=tree, text=f"tanie obuwie {i}", clicks=10, cost_pln=15)

    from app.services.google_ads import google_ads_service
    with patch.object(type(google_ads_service), "is_connected", new=False):
        script = NgramWasteScript()
        result = script.execute(db, tree["client"].id, None, None, {})

    assert result.applied == 0
    assert result.errors
