"""Keyword cannibalization detection.

Two positive keywords cannibalize each other when they target the same (or heavily
overlapping) search intent but live in different places. Budget is split between
them, Google picks one for each auction, and the operator rarely notices because
per-keyword metrics look "fine" individually.

This service flags three flavours of cannibalization:

1. DUPLICATE_EXACT_IN_AD_GROUP —
   Two EXACT-match keywords with identical normalised text in the same ad group.
   Almost always a data-entry accident; metric split is 50/50 random.

2. EXACT_VS_PHRASE_SAME_AD_GROUP —
   An EXACT-match and a PHRASE-match with identical normalised text in the same
   ad group. The PHRASE steals volume that should go to the EXACT bid.

3. CROSS_AD_GROUP_SAME_TEXT —
   Two enabled keywords with identical normalised text in different ad groups
   of the same SEARCH campaign (or across SEARCH campaigns on the same client).
   Google routes the query to whichever keyword's ad-rank wins — the operator
   loses control of intent-to-ad-group mapping.

Impact is computed from combined cost and conversions so callers can surface
high-spend cannibalization first.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.keyword import Keyword


def _normalise(text: str) -> str:
    # Lowercased, whitespace-collapsed. Match-type markers ([], "", +) are not
    # part of the stored text in our Keyword.text field, but be safe anyway.
    if not text:
        return ""
    cleaned = text.lower().strip()
    for ch in '[]"+':
        cleaned = cleaned.replace(ch, " ")
    return " ".join(cleaned.split())


def _fetch_keywords(db: Session, client_id: int) -> list[dict]:
    rows = (
        db.query(
            Keyword.id,
            Keyword.text,
            Keyword.match_type,
            Keyword.cost_micros,
            Keyword.conversions,
            Keyword.clicks,
            AdGroup.id.label("ad_group_id"),
            AdGroup.name.label("ad_group_name"),
            Campaign.id.label("campaign_id"),
            Campaign.name.label("campaign_name"),
            Campaign.campaign_type.label("campaign_type"),
        )
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED",
            Keyword.status == "ENABLED",
            Campaign.campaign_type == "SEARCH",  # cannibalization is only meaningful on SEARCH
        )
        .all()
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "normalised": _normalise(r.text),
            "match_type": (r.match_type or "").upper(),
            "cost_usd": (r.cost_micros or 0) / 1_000_000,
            "conversions": float(r.conversions or 0),
            "clicks": int(r.clicks or 0),
            "ad_group_id": r.ad_group_id,
            "ad_group_name": r.ad_group_name,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
        }
        for r in rows
        if r.text  # skip empty text (sync artefacts)
    ]


def detect_cannibalization(db: Session, client_id: int) -> list[dict]:
    """Return cannibalization findings, ordered by combined cost descending."""
    keywords = _fetch_keywords(db, client_id)
    if len(keywords) < 2:
        return []

    # Index by (ad_group_id, normalised) and (campaign_id, normalised) to catch
    # both intra-ad-group duplicates and cross-ad-group same-text.
    by_ag_text: dict[tuple[int, str], list[dict]] = defaultdict(list)
    by_camp_text: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for k in keywords:
        by_ag_text[(k["ad_group_id"], k["normalised"])].append(k)
        by_camp_text[(k["campaign_id"], k["normalised"])].append(k)

    findings: list[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    def _pair_key(a_id: int, b_id: int) -> tuple[int, int]:
        return (min(a_id, b_id), max(a_id, b_id))

    def _combined(a: dict, b: dict) -> tuple[float, float, int]:
        return (
            a["cost_usd"] + b["cost_usd"],
            a["conversions"] + b["conversions"],
            a["clicks"] + b["clicks"],
        )

    # 1 + 2. Same ad group, identical normalised text.
    for (ag_id, norm), group in by_ag_text.items():
        if len(group) < 2 or not norm:
            continue
        # Pair up every combination inside the group.
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                pk = _pair_key(a["id"], b["id"])
                if pk in seen_pairs:
                    continue
                seen_pairs.add(pk)

                if a["match_type"] == b["match_type"] == "EXACT":
                    kind = "DUPLICATE_EXACT_IN_AD_GROUP"
                    severity = "HIGH"
                    recommendation = (
                        "Usuń jeden z duplikatów. Identyczne exact match w tym "
                        "samym ad group dzielą bid 50/50 losowo."
                    )
                elif {a["match_type"], b["match_type"]} == {"EXACT", "PHRASE"}:
                    kind = "EXACT_VS_PHRASE_SAME_AD_GROUP"
                    severity = "MEDIUM"
                    recommendation = (
                        "Dodaj PHRASE z tą frazą jako exact-negative, aby zmusić "
                        "ruch do EXACT keyword w tym samym ad group."
                    )
                else:
                    kind = "SAME_TEXT_SAME_AD_GROUP"
                    severity = "LOW"
                    recommendation = (
                        "Przejrzyj keywords o tej samej frazie w jednym ad group — "
                        "często wynik pomyłki przy duplikowaniu kampanii."
                    )

                cost, conv, clicks = _combined(a, b)
                findings.append({
                    "kind": kind,
                    "severity": severity,
                    "scope": "ad_group",
                    "ad_group_id": ag_id,
                    "ad_group_name": a["ad_group_name"],
                    "campaign_id": a["campaign_id"],
                    "campaign_name": a["campaign_name"],
                    "normalised_text": norm,
                    "keyword_a_id": a["id"],
                    "keyword_a_text": a["text"],
                    "keyword_a_match_type": a["match_type"],
                    "keyword_a_cost_usd": a["cost_usd"],
                    "keyword_a_conversions": a["conversions"],
                    "keyword_b_id": b["id"],
                    "keyword_b_text": b["text"],
                    "keyword_b_match_type": b["match_type"],
                    "keyword_b_cost_usd": b["cost_usd"],
                    "keyword_b_conversions": b["conversions"],
                    "combined_cost_usd": round(cost, 2),
                    "combined_conversions": round(conv, 2),
                    "combined_clicks": clicks,
                    "recommendation": recommendation,
                })

    # 3. Cross-ad-group / cross-campaign within same campaign (more severe than cross-campaign).
    for (camp_id, norm), group in by_camp_text.items():
        if len(group) < 2 or not norm:
            continue
        # Skip pairs already reported at ad-group scope.
        ag_ids = {k["ad_group_id"] for k in group}
        if len(ag_ids) == 1:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["ad_group_id"] == b["ad_group_id"]:
                    continue
                pk = _pair_key(a["id"], b["id"])
                if pk in seen_pairs:
                    continue
                seen_pairs.add(pk)

                cost, conv, clicks = _combined(a, b)
                findings.append({
                    "kind": "CROSS_AD_GROUP_SAME_TEXT",
                    "severity": "MEDIUM",
                    "scope": "campaign",
                    "ad_group_id": None,
                    "ad_group_name": None,
                    "campaign_id": camp_id,
                    "campaign_name": a["campaign_name"],
                    "normalised_text": norm,
                    "keyword_a_id": a["id"],
                    "keyword_a_text": a["text"],
                    "keyword_a_match_type": a["match_type"],
                    "keyword_a_cost_usd": a["cost_usd"],
                    "keyword_a_conversions": a["conversions"],
                    "keyword_a_ad_group_id": a["ad_group_id"],
                    "keyword_a_ad_group_name": a["ad_group_name"],
                    "keyword_b_id": b["id"],
                    "keyword_b_text": b["text"],
                    "keyword_b_match_type": b["match_type"],
                    "keyword_b_cost_usd": b["cost_usd"],
                    "keyword_b_conversions": b["conversions"],
                    "keyword_b_ad_group_id": b["ad_group_id"],
                    "keyword_b_ad_group_name": b["ad_group_name"],
                    "combined_cost_usd": round(cost, 2),
                    "combined_conversions": round(conv, 2),
                    "combined_clicks": clicks,
                    "recommendation": (
                        "Ta sama fraza w dwóch różnych ad groups tej samej kampanii — "
                        "Google wybiera jedno losowo. Usuń z jednego ad group i dodaj "
                        "negative-exact by skierować ruch tylko do właściwego miejsca."
                    ),
                })

    findings.sort(key=lambda f: (f["combined_cost_usd"], f["combined_conversions"]), reverse=True)
    return findings
