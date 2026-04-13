"""Shared helpers for optimization scripts — brand + keyword protection +
search-term aggregation with sync-window matching.

Keeps protection and fetch logic in one place so every script can reuse it
without duplicating code. A2 keeps re-exporting the protection symbols for
backward compatibility with D1/B1 that imported them from there.
"""

import re
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.search_term import SearchTerm


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


def fetch_aggregated_terms(
    db: Session,
    client_id: int,
    date_from: Optional[date],
    date_to: Optional[date],
) -> dict[tuple, dict]:
    """Aggregate SearchTerm rows into a (text_lower, campaign_id) → stats map.

    Handles the sync-window matching logic:
    - If the user picked a date range, pick the candidate window whose
      length is closest to the user's range (tiebreaker: most recent).
    - Otherwise use the most recently updated window per key.

    Shared by A1 and A3; kept in one place so a future change to window
    logic (e.g. switching to lateral joins) updates both scripts at once.
    """
    q1 = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    q2 = (
        db.query(SearchTerm)
        .filter(SearchTerm.campaign_id.isnot(None), SearchTerm.ad_group_id.is_(None))
        .join(Campaign, SearchTerm.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if date_from:
        q1 = q1.filter(SearchTerm.date_to >= date_from)
        q2 = q2.filter(SearchTerm.date_to >= date_from)
    if date_to:
        q1 = q1.filter(SearchTerm.date_from <= date_to)
        q2 = q2.filter(SearchTerm.date_from <= date_to)
    rows = q1.all() + q2.all()

    groups: dict[tuple, list] = {}
    for row in rows:
        campaign_id = row.campaign_id
        ad_group_id = row.ad_group_id
        if campaign_id is None and ad_group_id:
            ag = db.get(AdGroup, ad_group_id)
            if ag:
                campaign_id = ag.campaign_id
        if campaign_id is None:
            continue
        key = (row.text.lower().strip(), campaign_id)
        groups.setdefault(key, []).append(row)

    user_range_days = None
    if date_from and date_to:
        user_range_days = max(1, (date_to - date_from).days)

    agg: dict[tuple, dict] = {}
    for key, candidates in groups.items():
        if user_range_days is not None:
            chosen = min(
                candidates,
                key=lambda r: (
                    abs((r.date_to - r.date_from).days - user_range_days),
                    -r.date_to.toordinal(),
                ),
            )
        else:
            chosen = max(candidates, key=lambda r: r.date_to)
        agg[key] = {
            "term_id": chosen.id,
            "text": chosen.text,
            "campaign_id": key[1],
            "ad_group_id": chosen.ad_group_id,
            "clicks": chosen.clicks or 0,
            "impressions": chosen.impressions or 0,
            "cost_micros": chosen.cost_micros or 0,
            "conversions": chosen.conversions or 0,
            "window_from": chosen.date_from,
            "window_to": chosen.date_to,
        }
    return agg
