"""Tests for B1 — High-Converting Term Promotion."""

from app.services.scripts.b1_high_conv_promotion import HighConvPromotionScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_b1_flags_high_conv_search_term(db):
    tree = build_basic_tree(db)
    # Not an existing keyword; has conversions.
    add_search_term(
        db, tree=tree, text="nakanaka sushi",
        clicks=50, cost_pln=100, conversions=5,
    )

    script = HighConvPromotionScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_conversions": 2, "brand_protection": False},
    )

    assert any(i.entity_name == "nakanaka sushi" for i in result.items)


def test_b1_skips_terms_already_keywords(db):
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="sushi wroclaw",  # already a positive keyword
        clicks=50, cost_pln=100, conversions=5,
    )

    script = HighConvPromotionScript()
    result = script.dry_run(db, tree["client"].id, None, None, {"min_conversions": 2})

    assert not any(i.entity_name == "sushi wroclaw" for i in result.items)


def test_b1_brand_protection_respects_client_name(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(
        db, tree=tree, text="naka promocja",
        clicks=50, cost_pln=100, conversions=5,
    )

    script = HighConvPromotionScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"min_conversions": 2, "brand_protection": True},
    )
    assert not any("naka" in i.entity_name.lower() for i in result.items)


def test_b1_search_ad_groups_attached_to_result(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="new term", clicks=50, cost_pln=100, conversions=5)

    script = HighConvPromotionScript()
    result = script.dry_run(db, tree["client"].id, None, None, {"min_conversions": 2})

    assert hasattr(result, "_search_ad_groups")
    # Expect both ad groups from the two Search campaigns.
    assert len(result._search_ad_groups) >= 2
