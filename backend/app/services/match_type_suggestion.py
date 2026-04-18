"""Match-type recommendation for promoting search terms to keywords.

Rules of thumb (in order — first match wins):

1. Very strong intent signal → EXACT.
   CTR > 5% AND conversions >= 3.
   The term has demonstrated commercial intent; lock it down as exact to stop
   budget leaking to loosely-related variants.

2. Solid volume + proven conversions → PHRASE.
   clicks >= 20 AND conversions >= 1.
   Enough traffic to trust the pattern; phrase lets Google match plurals / word-order
   without losing intent.

3. High volume without conversions yet → PHRASE (wider data collection).
   clicks >= 20 AND conversions == 0.
   This is a risky-but-useful case for phrase while you collect signal, but
   the caller should consider promoting only when clicks+cost warrant it.

4. Short-tail (1-2 words) with decent traffic → PHRASE.
   len(tokens) <= 2 AND clicks >= 10.
   Single-word promotions as EXACT under-match; phrase gives headroom.

5. Long-tail (>=4 words) with strong CTR → EXACT.
   len(tokens) >= 4 AND CTR >= 3%.
   Long-tail implies specific intent; EXACT is safer and cheaper.

6. Default → PHRASE.
   Balances reach and control; safer than BROAD for operators promoting terms
   they observed in their own account.

BROAD is intentionally never suggested by this helper — operators promoting a
search term they see in their own account are rarely adding BROAD; broad is
the category the term came FROM, not the category it should become.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class MatchTypeSuggestion:
    match_type: str        # EXACT | PHRASE
    rule_id: str           # which branch fired
    reason: str            # short human-readable justification
    confidence: float      # 0.0 – 1.0 (heuristic)


def _tokenize(text: str) -> list[str]:
    # Minimal tokenization — aligns with how negative_conflict_service normalises.
    return [t for t in (text or "").lower().split() if t]


def suggest_match_type(
    text: str,
    clicks: int,
    impressions: int,
    conversions: float,
) -> MatchTypeSuggestion:
    """Return a single match-type recommendation for one search term.

    Inputs are what the operator sees in the search-terms table: the term's own
    clicks / impressions / conversions across the window. CTR is computed locally
    in the same units stored on SearchTerm (percentage).
    """
    ctr_pct = (clicks / impressions * 100) if impressions else 0.0
    token_count = len(_tokenize(text))

    # 1. Strong intent
    if ctr_pct > 5.0 and conversions >= 3:
        return MatchTypeSuggestion(
            match_type="EXACT",
            rule_id="strong_intent",
            reason=(
                f"CTR {ctr_pct:.1f}% i {conversions:.0f} konwersji — silny sygnał intencji, "
                f"EXACT zablokuje budżet na wariantach"
            ),
            confidence=0.9,
        )

    # 5. Long-tail + solid CTR (checked before "2/3" because long-tail = high-signal)
    if token_count >= 4 and ctr_pct >= 3.0:
        return MatchTypeSuggestion(
            match_type="EXACT",
            rule_id="long_tail_high_ctr",
            reason=(
                f"Long-tail ({token_count} słów) z CTR {ctr_pct:.1f}% — konkretna intencja, "
                f"EXACT tańszy i bezpieczniejszy"
            ),
            confidence=0.8,
        )

    # 2. Solid volume + proven conversions
    if clicks >= 20 and conversions >= 1:
        return MatchTypeSuggestion(
            match_type="PHRASE",
            rule_id="proven_volume",
            reason=(
                f"{clicks} kliknięć + {conversions:.0f} konw. — zaufaj wzorcowi, "
                f"PHRASE złapie liczby mnogie i szyk słów"
            ),
            confidence=0.75,
        )

    # 3. High volume without conversions — still PHRASE, but flag lower confidence
    if clicks >= 20 and conversions == 0:
        return MatchTypeSuggestion(
            match_type="PHRASE",
            rule_id="high_volume_no_conv",
            reason=(
                f"{clicks} kliknięć bez konwersji — jeśli chcesz go dodać mimo wszystko, "
                f"PHRASE da dane do dalszej decyzji; rozważ zamiast tego negatyw"
            ),
            confidence=0.35,
        )

    # 4. Short-tail with decent traffic
    if token_count <= 2 and clicks >= 10:
        return MatchTypeSuggestion(
            match_type="PHRASE",
            rule_id="short_tail",
            reason=(
                f"Krótki term ({token_count} słów) z {clicks} kliknięciami — "
                f"EXACT by niedomatchował, PHRASE daje zasięg"
            ),
            confidence=0.65,
        )

    # 6. Default
    return MatchTypeSuggestion(
        match_type="PHRASE",
        rule_id="default",
        reason="Zbyt mało sygnału dla EXACT — PHRASE jako balans zasięg/kontrola",
        confidence=0.5,
    )


def suggest_for_terms(terms: Iterable) -> list[dict]:
    """Batch helper used by the router.

    Expects objects with `.id`, `.text`, `.clicks`, `.impressions`, `.conversions`.
    """
    out: list[dict] = []
    for t in terms:
        s = suggest_match_type(
            text=t.text or "",
            clicks=int(t.clicks or 0),
            impressions=int(t.impressions or 0),
            conversions=float(t.conversions or 0),
        )
        out.append({
            "search_term_id": t.id,
            "search_term_text": t.text,
            "suggested_match_type": s.match_type,
            "rule_id": s.rule_id,
            "reason": s.reason,
            "confidence": s.confidence,
        })
    return out
