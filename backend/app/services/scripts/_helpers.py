"""Shared helpers for optimization scripts — brand + keyword protection.

Keeps brand/keyword protection logic in one place so every script can
reuse it without duplicating code. A2 keeps re-exporting these symbols
for backward compatibility with D1/B1 that imported them from there.
"""

import re

from app.models.client import Client


# Generic industry words that should NOT be treated as brand tokens.
# E.g. "Sushi Naka Naka" → only "Naka" becomes a brand pattern; "Sushi"
# is filtered out because it matches any restaurant targeting sushi queries.
GENERIC_WORDS = {
    "sushi", "pizza", "burger", "kebab", "ramen", "restaurant", "restauracja",
    "bar", "bistro", "cafe", "sklep", "shop", "store", "studio", "salon",
    "centrum", "center", "agency", "agencja", "firma", "company", "group",
    "service", "services", "serwis", "uslugi", "market", "food", "catering",
}


def _build_brand_patterns(
    client: Client, custom_brand_words: list[str] | None
) -> list[re.Pattern]:
    """Build regex patterns for brand protection.

    Uses only words from the client name that are NOT generic industry terms.
    E.g. "Sushi Naka Naka" -> ["Naka"] (not "Sushi" which is generic).
    """
    words = list(custom_brand_words or [])
    if not words and client.name:
        parts = client.name.split()
        filler = {
            "sp", "zoo", "sp.", "z", "o.o.", "sa", "s.a.", "ltd", "gmbh",
            "the", "i", "w", "na",
        }
        unique = [
            w for w in parts
            if len(w) >= 2 and w.lower() not in GENERIC_WORDS and w.lower() not in filler
        ]
        words = unique if unique else parts[-1:]
    seen = set()
    patterns: list[re.Pattern] = []
    for w in words:
        key = w.lower()
        # Allow 2+ character brand tokens (e.g. "AB", "LG", "3M") but still
        # reject single characters to avoid regex churn on every word.
        if key in seen or len(key) < 2:
            continue
        seen.add(key)
        patterns.append(re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE))
    return patterns


def _is_brand_term(text: str, brand_patterns: list[re.Pattern]) -> bool:
    """Return True if any brand pattern matches the term."""
    return any(p.search(text) for p in brand_patterns)


def _check_keyword_conflict(
    term_lower: str, campaign_keywords: set[str]
) -> str | None:
    """Check if adding ``term_lower`` as a negative conflicts with existing keywords.

    Returns:
        None       — no conflict, any match type is safe
        "BLOCK"    — term == keyword, never exclude (would kill the keyword)
        "EXACT"    — any word-set overlap with an existing keyword forces EXACT
                     match type, because a PHRASE negative containing those
                     words (or contained by them) would still kill the broader
                     or overlapping keyword.
    """
    if term_lower in campaign_keywords:
        return "BLOCK"
    term_words = set(term_lower.split())
    if not term_words:
        return None
    for kw in campaign_keywords:
        kw_words = set(kw.split())
        if not kw_words:
            continue
        # Forward subset: negative words ⊆ keyword words — a PHRASE negative
        # made of term_words would fully match the keyword and kill it.
        if term_words.issubset(kw_words):
            return "EXACT"
        # Reverse subset: keyword words ⊆ negative words — a PHRASE negative
        # containing the keyword would also kill it (the keyword text appears
        # contiguously inside the negative).
        if kw_words.issubset(term_words):
            return "EXACT"
    return None
