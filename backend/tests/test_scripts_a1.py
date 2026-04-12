"""Tests for A1 — Zero Conversion Waste script."""

from unittest.mock import patch

from app.models.action_log import ActionLog
from app.services.scripts.a1_zero_conv_waste import ZeroConvWasteScript
from tests.scripts_fixtures import add_search_term, build_basic_tree


def _run(db, tree, **params):
    script = ZeroConvWasteScript()
    return script.dry_run(db, tree["client"].id, None, None, params)


def test_a1_happy_path_flags_zero_conv_term(db):
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="tanie obuwie",
        clicks=20, cost_pln=50, conversions=0,
        days_ago_from=40, days_ago_to=15,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=0)

    assert result.total_matching == 1
    assert result.items[0].entity_name == "tanie obuwie"
    assert result.items[0].action_payload["match_type"] == "PHRASE"


def test_a1_brand_protection_blocks_branded_term(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(
        db, tree=tree, text="naka sushi promocja",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=40, days_ago_to=15,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, brand_protection=True, conversion_lag_days=0)
    assert result.total_matching == 0

    # Disabling brand protection should surface the branded term
    result = _run(db, tree, min_clicks=5, min_cost_pln=20, brand_protection=False, conversion_lag_days=0)
    assert result.total_matching == 1


def test_a1_keyword_protection_blocks_exact_keyword_match(db):
    tree = build_basic_tree(db)
    # "sushi wroclaw" is already an active keyword in Search A — can't negative it.
    add_search_term(
        db, tree=tree, text="sushi wroclaw",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=40, days_ago_to=15,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=0)
    assert result.total_matching == 0


def test_a1_keyword_protection_forces_exact_for_subset_match(db):
    tree = build_basic_tree(db)
    # "sushi" ⊂ "sushi wroclaw" — PHRASE negative would kill the keyword, force EXACT.
    add_search_term(
        db, tree=tree, text="sushi",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=40, days_ago_to=15,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=0)
    assert result.total_matching == 1
    assert result.items[0].action_payload["match_type"] == "EXACT"


def test_a1_conversion_lag_skips_short_recent_windows(db):
    tree = build_basic_tree(db)
    # Short window (5 days) fully inside the 7-day lag → skipped.
    add_search_term(
        db, tree=tree, text="tanie obuwie",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=5, days_ago_to=0,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=7)
    assert result.total_matching == 0
    assert result.warnings, "expected a lag skip warning"

    # Disabling lag resurfaces the term.
    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=0)
    assert result.total_matching == 1


def test_a1_conversion_lag_keeps_long_window_with_warning(db):
    tree = build_basic_tree(db)
    # 30-day window ending today: most data is old enough to trust, keep but warn.
    add_search_term(
        db, tree=tree, text="tanie obuwie",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=30, days_ago_to=0,
    )

    result = _run(db, tree, min_clicks=5, min_cost_pln=20, conversion_lag_days=7)
    assert result.total_matching == 1
    assert any("sięgające" in w for w in result.warnings)


def test_a1_execute_blocks_without_google_ads_api(db):
    tree = build_basic_tree(db)
    add_search_term(
        db, tree=tree, text="tanie obuwie",
        clicks=30, cost_pln=80, conversions=0,
        days_ago_from=40, days_ago_to=15,
    )

    from app.services.google_ads import google_ads_service
    with patch.object(type(google_ads_service), "is_connected", new=False):
        script = ZeroConvWasteScript()
        result = script.execute(
            db, tree["client"].id, None, None,
            {"min_clicks": 5, "min_cost_pln": 20, "conversion_lag_days": 0},
        )

    assert result.applied == 0
    assert result.errors
    assert "Google Ads API" in result.errors[0]


def test_a1_execute_respects_validate_batch_cap(db, monkeypatch):
    tree = build_basic_tree(db)
    for i in range(5):
        add_search_term(
            db, tree=tree, text=f"term {i}",
            clicks=10, cost_pln=25, conversions=0,
            days_ago_from=40, days_ago_to=15,
        )

    # Force MAX_NEGATIVES_PER_DAY down to 2 via monkeypatch.
    from app.services import action_executor as ae
    original = dict(ae.SAFETY_LIMITS)
    monkeypatch.setattr(ae, "SAFETY_LIMITS", {**original, "MAX_NEGATIVES_PER_DAY": 2})

    # Stub google_ads_service to look connected and swallow the batch call.
    from app.services.google_ads import google_ads_service
    with patch.object(type(google_ads_service), "is_connected", new=True):
        monkeypatch.setattr(
            google_ads_service,
            "batch_add_campaign_negatives",
            lambda db_, campaign, negs: None,
        )
        script = ZeroConvWasteScript()
        result = script.execute(
            db, tree["client"].id, None, None,
            {"min_clicks": 5, "min_cost_pln": 20, "conversion_lag_days": 0},
        )

    assert result.applied == 2
    assert any("MAX_NEGATIVES_PER_DAY" in e for e in result.errors)
    # ActionLog should record exactly 2 successes
    success_logs = db.query(ActionLog).filter(ActionLog.status == "SUCCESS").count()
    assert success_logs == 2
    # Frontend-friendly structured field must be populated.
    assert result.circuit_breaker_limit == 2
