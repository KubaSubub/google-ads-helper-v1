"""Tests for D3 — N-gram Audit Report (view-only)."""

from app.services.scripts.d3_ngram_audit import NgramAuditReportScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def _run(db, tree, **params):
    return NgramAuditReportScript().dry_run(db, tree["client"].id, None, None, params)


def test_d3_returns_top_ngrams_regardless_of_conversions(db):
    """D3 must keep converting n-grams too — unlike D1 which drops them."""
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="pizza delivery a", clicks=10, cost_pln=20, conversions=3)
    add_search_term(db, tree=tree, text="pizza delivery b", clicks=10, cost_pln=20, conversions=2)
    add_search_term(db, tree=tree, text="pizza delivery c", clicks=10, cost_pln=20, conversions=1)

    result = _run(db, tree, ngram_size=2, min_term_count=2)

    names = [i.entity_name for i in result.items]
    assert "pizza delivery" in names
    item = next(i for i in result.items if i.entity_name == "pizza delivery")
    assert item.metrics["conversions"] == 6
    assert item.metrics["term_count"] == 3
    assert item.metrics["campaigns_affected"] == 1


def test_d3_respects_top_n_limit(db):
    tree = build_basic_tree(db)
    for i in range(5):
        add_search_term(db, tree=tree, text=f"unique phrase alpha {i}", clicks=10, cost_pln=10 + i)

    result = _run(db, tree, ngram_size=1, top_n=2, min_term_count=5)
    assert len(result.items) <= 2


def test_d3_execute_is_noop(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="pizza delivery a", clicks=10, cost_pln=20, conversions=1)
    add_search_term(db, tree=tree, text="pizza delivery b", clicks=10, cost_pln=20, conversions=1)

    res = NgramAuditReportScript().execute(db, tree["client"].id, None, None, {})
    assert res.applied == 0
    assert res.errors  # informs it is view-only
