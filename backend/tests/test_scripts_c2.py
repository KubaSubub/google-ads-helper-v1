"""Tests for C2 — Duplicate Coverage (cannibalization)."""

from app.services.scripts.c2_duplicate_coverage import DuplicateCoverageScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_c2_detects_cross_campaign_duplicate(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="dostawa", clicks=30, cost_pln=60, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="dostawa", clicks=20, cost_pln=40, campaign_key="b", ad_group_key="b")

    script = DuplicateCoverageScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_clicks": 5, "min_cost_pln": 5},
    )

    assert any(i.entity_name == "dostawa" for i in result.items)
    item = next(i for i in result.items if i.entity_name == "dostawa")
    assert item.metrics["location_count"] == 2
    assert item.action_payload["recommended_keeper_campaign_id"] in (
        tree["campaigns"]["a"].id,
        tree["campaigns"]["b"].id,
    )


def test_c2_brand_protection_skips_branded_duplicate(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(db, tree=tree, text="naka dostawa", clicks=30, cost_pln=60, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="naka dostawa", clicks=20, cost_pln=40, campaign_key="b", ad_group_key="b")

    script = DuplicateCoverageScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_clicks": 5, "min_cost_pln": 5, "brand_protection": True},
    )
    assert not any("naka" in i.entity_name.lower() for i in result.items)


def test_c2_keyword_conflict_blocks_duplicate_when_term_is_keyword(db):
    tree = build_basic_tree(db)
    # "dostawa sushi" is already a keyword in Search B — BLOCK the duplicate.
    add_search_term(db, tree=tree, text="dostawa sushi", clicks=30, cost_pln=60, campaign_key="a", ad_group_key="a")
    add_search_term(db, tree=tree, text="dostawa sushi", clicks=20, cost_pln=40, campaign_key="b", ad_group_key="b")

    script = DuplicateCoverageScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_clicks": 5, "min_cost_pln": 5},
    )
    assert not any(i.entity_name == "dostawa sushi" for i in result.items)
