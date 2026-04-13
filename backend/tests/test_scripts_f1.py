"""Tests for F1 — Competitor Term Detection (alert-only)."""

from app.services.scripts.f1_competitor_term import CompetitorTermScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_f1_flags_term_containing_competitor(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="allegro dostawa", clicks=5, cost_pln=8)

    result = CompetitorTermScript().dry_run(
        db, tree["client"].id, None, None,
        {"custom_competitor_words": ["allegro"], "min_clicks": 1},
    )

    assert result.total_matching == 1
    assert result.items[0].entity_name == "allegro dostawa"
    assert result.items[0].metrics["matched_competitor"].lower() == "allegro"


def test_f1_without_competitors_returns_warning(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="cokolwiek", clicks=5, cost_pln=8)

    result = CompetitorTermScript().dry_run(db, tree["client"].id, None, None, {})
    assert result.total_matching == 0
    assert result.warnings


def test_f1_respects_word_boundary(db):
    tree = build_basic_tree(db)
    # 'all' must NOT match 'allegro' (competitor word is 'allegro', full token).
    add_search_term(db, tree=tree, text="all inclusive", clicks=5, cost_pln=8)

    result = CompetitorTermScript().dry_run(
        db, tree["client"].id, None, None,
        {"custom_competitor_words": ["allegro"]},
    )
    assert result.total_matching == 0


def test_f1_execute_is_alert_only(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="allegro test", clicks=5, cost_pln=8)

    res = CompetitorTermScript().execute(db, tree["client"].id, None, None, {})
    assert res.applied == 0
    assert res.errors
