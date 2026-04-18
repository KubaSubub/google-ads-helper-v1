"""Negative-keyword conflict detection.

A negative keyword silently blocks a positive keyword when:
- the positive is in the same scope (same campaign, same ad group, or under the same
  campaign-scoped negative) as the negative, and
- the negative's matched form catches the positive's text.

Google Ads does not warn about these conflicts in the primary UI; accounts accumulate
them over months/years and real revenue gets filtered out without anyone noticing.

Match-semantics rules applied here (subset — covers the common cases a PPC operator
actually sees; does not try to replicate Google's entire match engine):

    BROAD negative    -> blocks positives where every significant word of the
                         positive is present (in any order) in the negative's set.
                         (This mirrors how BROAD negatives actually filter queries.)
    PHRASE negative   -> blocks positives that contain the negative as a contiguous
                         substring of words.
    EXACT negative    -> blocks positives whose normalised text equals the negative's.

Normalisation: lowercase, strip leading match-type markers ("+" / brackets / quotes),
collapse whitespace, split on spaces.
"""

from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword


_MATCH_MARKERS_RX = re.compile(r"[\[\]\"+]")
_WHITESPACE_RX = re.compile(r"\s+")


def _normalise(text: str) -> list[str]:
    cleaned = _MATCH_MARKERS_RX.sub(" ", (text or "").lower()).strip()
    cleaned = _WHITESPACE_RX.sub(" ", cleaned)
    return cleaned.split(" ") if cleaned else []


def _negative_blocks_positive(
    neg_tokens: list[str], neg_match: str, pos_tokens: list[str]
) -> bool:
    if not neg_tokens or not pos_tokens:
        return False
    neg_match = (neg_match or "").upper()

    if neg_match == "EXACT":
        return neg_tokens == pos_tokens

    if neg_match == "PHRASE":
        # contiguous substring of tokens
        n, p = len(neg_tokens), len(pos_tokens)
        if n > p:
            return False
        for i in range(p - n + 1):
            if pos_tokens[i : i + n] == neg_tokens:
                return True
        return False

    # BROAD (and anything unexpected — be conservative and use BROAD semantics)
    return all(t in pos_tokens for t in neg_tokens)


def _fetch_positives(db: Session, client_id: int) -> list[dict]:
    """Return enabled positive keywords with their campaign/ad_group context."""
    rows = (
        db.query(
            Keyword.id,
            Keyword.text,
            Keyword.match_type,
            Keyword.cost_micros,
            Keyword.conversions,
            AdGroup.id.label("ad_group_id"),
            AdGroup.name.label("ad_group_name"),
            Campaign.id.label("campaign_id"),
            Campaign.name.label("campaign_name"),
        )
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Keyword.status == "ENABLED",
            Campaign.status == "ENABLED",
        )
        .all()
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "tokens": _normalise(r.text),
            "match_type": r.match_type,
            "cost_usd": (r.cost_micros or 0) / 1_000_000,
            "conversions": float(r.conversions or 0),
            "ad_group_id": r.ad_group_id,
            "ad_group_name": r.ad_group_name,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
        }
        for r in rows
    ]


def _fetch_negatives(db: Session, client_id: int) -> list[dict]:
    rows = (
        db.query(NegativeKeyword)
        .filter(
            NegativeKeyword.client_id == client_id,
            NegativeKeyword.status == "ENABLED",
        )
        .all()
    )
    out: list[dict] = []
    for n in rows:
        scope = (n.negative_scope or "CAMPAIGN").upper()
        out.append({
            "id": n.id,
            "text": n.text,
            "tokens": _normalise(n.text),
            "match_type": n.match_type or "PHRASE",
            "scope": scope,
            "scope_id": n.campaign_id if scope == "CAMPAIGN" else n.ad_group_id,
            "ad_group_id": n.ad_group_id,
            "campaign_id": n.campaign_id,
        })
    return out


def _scope_match(neg: dict, pos: dict) -> tuple[bool, str, int | None, str]:
    """Return (in_scope, scope_label, scope_id, scope_name).

    A negative conflicts with a positive only when the negative's scope contains
    the positive. Account-level negatives (LIST_* / ACCOUNT scopes) are omitted
    from this audit — they're managed separately and rarely cause surprise
    conflicts; covering them requires list-membership joins outside v1 scope.
    """
    scope = neg["scope"]
    if scope == "AD_GROUP":
        if neg["ad_group_id"] is not None and neg["ad_group_id"] == pos["ad_group_id"]:
            return True, "ad group", pos["ad_group_id"], pos["ad_group_name"]
        return False, "", None, ""
    if scope == "CAMPAIGN":
        if neg["campaign_id"] is not None and neg["campaign_id"] == pos["campaign_id"]:
            return True, "campaign", pos["campaign_id"], pos["campaign_name"]
        return False, "", None, ""
    return False, "", None, ""


def detect_conflicts(db: Session, client_id: int) -> list[dict]:
    """Return a list of negative↔positive conflicts, ordered by positive cost desc.

    The cap on the upstream caller ensures noise doesn't drown signal — a high-spend
    positive being silently blocked is the conflict that matters.
    """
    positives = _fetch_positives(db, client_id)
    negatives = _fetch_negatives(db, client_id)
    if not positives or not negatives:
        return []

    conflicts: list[dict] = []
    for neg in negatives:
        for pos in positives:
            in_scope, scope_label, scope_id, scope_name = _scope_match(neg, pos)
            if not in_scope:
                continue
            if not _negative_blocks_positive(neg["tokens"], neg["match_type"], pos["tokens"]):
                continue
            conflicts.append({
                "negative_id": neg["id"],
                "negative_text": neg["text"],
                "negative_match_type": neg["match_type"],
                "positive_keyword_id": pos["id"],
                "positive_text": pos["text"],
                "positive_match_type": pos["match_type"],
                "campaign_id": pos["campaign_id"],
                "campaign_name": pos["campaign_name"],
                "ad_group_id": pos["ad_group_id"],
                "ad_group_name": pos["ad_group_name"],
                "scope": scope_label,
                "scope_id": scope_id,
                "scope_name": scope_name,
                "positive_cost_usd": pos["cost_usd"],
                "positive_conversions": pos["conversions"],
                "conflict_kind": (
                    "exact_match" if neg["match_type"] == "EXACT"
                    else "phrase_substring" if neg["match_type"] == "PHRASE"
                    else "broad_tokens"
                ),
            })

    # Order: highest-spend positives first — that's where the money is being blocked.
    conflicts.sort(key=lambda c: (c["positive_cost_usd"], c["positive_conversions"]), reverse=True)
    return conflicts
