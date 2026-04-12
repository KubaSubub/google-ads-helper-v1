"""Tests for _helpers.py — brand + keyword protection primitives."""

import re

from app.models import Client
from app.services.scripts._helpers import (
    _build_brand_patterns,
    _check_keyword_conflict,
    _is_brand_term,
)


def _make_client(name: str) -> Client:
    return Client(name=name, google_customer_id="x")


def test_build_brand_patterns_strips_generic_words():
    """'Sushi Naka Naka' should only pattern-match 'Naka' — 'Sushi' is generic."""
    client = _make_client("Sushi Naka Naka")
    patterns = _build_brand_patterns(client, None)

    assert len(patterns) == 1
    assert all(isinstance(p, re.Pattern) for p in patterns)
    assert patterns[0].search("naka delivery")
    assert not patterns[0].search("sushi lunch")


def test_build_brand_patterns_fallback_uses_last_word_if_all_generic():
    """When every token is generic, fall back to the last word so we still protect something."""
    client = _make_client("Pizza Bar")
    patterns = _build_brand_patterns(client, None)

    assert len(patterns) == 1
    assert patterns[0].search("Bar open")


def test_build_brand_patterns_uses_custom_words_when_provided():
    """Custom list wins over client.name parsing."""
    client = _make_client("Irrelevant Name")
    patterns = _build_brand_patterns(client, ["ACME", "widgets"])

    assert len(patterns) == 2
    assert patterns[0].search("buy ACME")
    assert patterns[1].search("widgets 2025")


def test_is_brand_term_respects_word_boundaries():
    client = _make_client("Naka")
    patterns = _build_brand_patterns(client, None)

    assert _is_brand_term("naka delivery", patterns) is True
    assert _is_brand_term("NAKA sushi", patterns) is True
    # Word boundary must prevent matching 'banakamura' as containing 'naka'
    assert _is_brand_term("banakamura", patterns) is False


def test_check_keyword_conflict_exact_match_is_block():
    kws = {"buty sportowe", "obuwie damskie"}
    assert _check_keyword_conflict("buty sportowe", kws) == "BLOCK"


def test_check_keyword_conflict_subset_is_exact():
    """'buty' ⊂ 'buty sportowe' → PHRASE negative would kill the keyword → force EXACT."""
    kws = {"buty sportowe"}
    assert _check_keyword_conflict("buty", kws) == "EXACT"


def test_check_keyword_conflict_multi_word_subset_is_exact():
    kws = {"buty sportowe damskie"}
    assert _check_keyword_conflict("buty damskie", kws) == "EXACT"


def test_check_keyword_conflict_reverse_subset_is_exact():
    """Negative ⊃ keyword — PHRASE negative would still kill the shorter keyword."""
    kws = {"buty"}
    assert _check_keyword_conflict("tanie buty sportowe", kws) == "EXACT"


def test_check_keyword_conflict_none_when_no_overlap():
    kws = {"buty sportowe"}
    assert _check_keyword_conflict("szafa ikea", kws) is None


def test_check_keyword_conflict_empty_term_returns_none():
    kws = {"buty sportowe"}
    assert _check_keyword_conflict("", kws) is None


def test_build_brand_patterns_accepts_two_char_brand():
    """Short brand tokens like 'LG' or 'AB' must survive the length filter."""
    client = _make_client("LG Electronics")
    patterns = _build_brand_patterns(client, None)
    assert any(p.search("LG tv") for p in patterns)
