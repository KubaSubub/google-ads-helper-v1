"""Tests for A3 — Low CTR Waste."""

from app.services.scripts.a3_low_ctr_waste import LowCtrWasteScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def _run(db, tree, **params):
    # Conversion lag off by default in tests so fresh seeded rows surface.
    params.setdefault("conversion_lag_days", 0)
    return LowCtrWasteScript().dry_run(db, tree["client"].id, None, None, params)


def test_a3_flags_term_below_ctr_threshold(db):
    tree = build_basic_tree(db)
    # 150 impressions, 1 click → CTR ≈ 0.67% above 0.5 default, keep above threshold.
    # Use 0 clicks for 150 imps → CTR 0%.
    add_search_term(
        db, tree=tree, text="zamienniki sushi",
        clicks=0, cost_pln=5,
        days_ago_from=40, days_ago_to=15,
    )
    # Force impressions up
    tree_ref = tree
    from app.models.search_term import SearchTerm
    term = db.query(SearchTerm).filter(SearchTerm.text == "zamienniki sushi").first()
    term.impressions = 200
    db.commit()

    result = _run(db, tree_ref, min_impressions=100, max_ctr_pct=0.5)
    assert result.total_matching == 1


def test_a3_ignores_term_below_min_impressions(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="niski wolumen", clicks=0, cost_pln=1)
    from app.models.search_term import SearchTerm
    term = db.query(SearchTerm).filter(SearchTerm.text == "niski wolumen").first()
    term.impressions = 50
    db.commit()

    result = _run(db, tree, min_impressions=100, max_ctr_pct=0.5)
    assert result.total_matching == 0


def test_a3_ignores_high_ctr_term(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="sushi popularne", clicks=20, cost_pln=40)
    from app.models.search_term import SearchTerm
    term = db.query(SearchTerm).filter(SearchTerm.text == "sushi popularne").first()
    term.impressions = 200  # CTR = 10%
    db.commit()

    result = _run(db, tree, min_impressions=100, max_ctr_pct=0.5)
    assert result.total_matching == 0


def test_a3_brand_protection_blocks_branded_term(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(db, tree=tree, text="naka restaurant city", clicks=0, cost_pln=5)
    from app.models.search_term import SearchTerm
    term = db.query(SearchTerm).filter(SearchTerm.text == "naka restaurant city").first()
    term.impressions = 300
    db.commit()

    result = _run(db, tree, min_impressions=100, max_ctr_pct=0.5, brand_protection=True)
    assert result.total_matching == 0
