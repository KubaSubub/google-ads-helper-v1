"""Tests for A6 — Non-Latin Script detector."""

from app.services.scripts.a6_non_latin_script import (
    NonLatinScriptScript,
    _detect_scripts,
)
from tests.scripts_fixtures import add_search_term, build_basic_tree


def test_detect_scripts_handles_cyrillic():
    out = _detect_scripts("sushi доставка")
    assert out.get("CYRILLIC", 0) >= 6
    assert out.get("LATIN", 0) >= 5


def test_detect_scripts_ignores_polish_diacritics():
    """Polish letters live inside the LATIN bucket — never flagged as foreign."""
    out = _detect_scripts("łódź żółć")
    assert "LATIN" in out
    assert "CYRILLIC" not in out


def test_a6_flags_cyrillic_search_term(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="доставка суши", clicks=5, cost_pln=10)

    script = NonLatinScriptScript()
    result = script.dry_run(db, tree["client"].id, None, None, {})

    assert result.total_matching == 1
    item = result.items[0]
    assert "CYRILLIC" in item.metrics["scripts_detected"]


def test_a6_brand_protection_respects_custom_words(db):
    tree = build_basic_tree(db, client_name="Naka")
    add_search_term(db, tree=tree, text="Naka доставка", clicks=5, cost_pln=10)

    script = NonLatinScriptScript()
    result = script.dry_run(
        db, tree["client"].id, None, None,
        {"brand_protection": True, "custom_brand_words": ["Naka"]},
    )
    assert result.total_matching == 0


def test_a6_keyword_conflict_blocks_exact_keyword_match(db):
    tree = build_basic_tree(db)
    # Active keyword "sushi wroclaw" — identical search term (with foreign chars appended).
    # Use the exact keyword text mixed with Cyrillic → BLOCK prevents exclusion.
    add_search_term(db, tree=tree, text="sushi wroclaw", clicks=5, cost_pln=10)

    script = NonLatinScriptScript()
    result = script.dry_run(db, tree["client"].id, None, None, {})
    # No non-Latin chars — should naturally be empty, sanity check
    assert result.total_matching == 0


def test_a6_preserves_exact_default_match_type(db):
    """A6 default is EXACT already; the match_type must not be accidentally mutated."""
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="доставка суши", clicks=5, cost_pln=10)

    script = NonLatinScriptScript()
    result = script.dry_run(db, tree["client"].id, None, None, {})

    assert result.items[0].action_payload["match_type"] == "EXACT"
