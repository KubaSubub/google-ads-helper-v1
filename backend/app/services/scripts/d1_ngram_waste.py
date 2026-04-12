"""Script D1 — N-gram Waste Analysis.

Splits all search terms into n-grams (1/2/3/4 words), aggregates metrics
cross-term per n-gram, and identifies waste patterns — n-grams that appear
in many search terms but produce zero conversions.

One negative for an n-gram blocks all terms containing it, which makes this
much more efficient than per-term negatives (A1).

Results are grouped by n-gram size so the UI can render tabs (1-gram, 2-gram, ...).
"""

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.search_term import SearchTerm
from app.services.scripts._helpers import (
    _build_brand_patterns,
    _check_keyword_conflict,
    _is_brand_term,
)
from app.services.scripts.base import (
    ACTION_NEGATIVE,
    CATEGORY_NGRAM,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)

STOP_WORDS = frozenset({
    "i", "w", "na", "z", "do", "dla", "od", "po", "o", "u", "a", "e",
    "the", "is", "in", "of", "to", "for", "and", "or", "me", "my",
    "near", "we", "it", "at", "by", "an", "no", "so", "up", "if", "be",
    "nie", "co", "jak", "czy", "ze", "sie", "ale", "ten", "ta", "te",
})


def _generate_ngrams(words: list[str], n: int) -> list[str]:
    """Generate n-grams from a list of words."""
    if len(words) < n:
        return []
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


class NgramWasteScript(ScriptBase):
    id = "D1"
    name = "N-gram Waste (analiza slów i fraz)"
    category = CATEGORY_NGRAM
    description = (
        "Rozbija search terms na 1/2/3/4-gramy, agreguje metryki cross-term "
        "i znajduje slowa/frazy generujace koszt bez konwersji."
    )
    action_type = ACTION_NEGATIVE
    # D1 operates on aggregated cross-term n-grams; ad-group scope does not
    # map cleanly (an n-gram can span ad groups). Negatives are always
    # CAMPAIGN-level — param is kept for shape compatibility but constant.
    default_params = {
        "min_term_count": 3,
        "min_total_cost_pln": 10.0,
        "max_conversions": 0,
        "negative_level": "CAMPAIGN",
        "match_type": "PHRASE",
        "brand_protection": True,
        "custom_brand_words": [],
    }

    def dry_run(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
    ) -> ScriptResult:
        p = {**self.default_params, **(params or {})}
        min_term_count = int(p.get("min_term_count", 3))
        min_cost_pln = float(p.get("min_total_cost_pln", 10.0))
        max_conv = float(p.get("max_conversions", 0))
        brand_protection = bool(p.get("brand_protection", True))

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = _build_brand_patterns(client, p.get("custom_brand_words")) if brand_protection else []

        # Pre-fetch keywords for keyword protection
        all_kws = (
            db.query(Keyword.text, AdGroup.campaign_id)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Keyword.status == "ENABLED")
            .all()
        )
        all_kw_texts: set[str] = set()
        kws_per_camp: dict[int, set[str]] = {}
        for text, cid in all_kws:
            if text:
                t = text.lower().strip()
                all_kw_texts.add(t)
                kws_per_camp.setdefault(cid, set()).add(t)

        # Pre-fetch existing negatives
        existing_neg_texts: set[str] = set()
        neg_rows = (
            db.query(NegativeKeyword.text)
            .filter(NegativeKeyword.client_id == client_id, NegativeKeyword.status != "REMOVED")
            .all()
        )
        for (text,) in neg_rows:
            if text:
                existing_neg_texts.add(text.lower().strip())

        # Pre-fetch all search terms (date-filtered)
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

        all_terms_raw = q1.all() + q2.all()

        # Dedup by text (pick highest cost)
        term_map: dict[str, SearchTerm] = {}
        for t in all_terms_raw:
            key = t.text.lower().strip()
            if key not in term_map or (t.cost_micros or 0) > (term_map[key].cost_micros or 0):
                term_map[key] = t

        # Resolve campaign_id for each term
        term_campaigns: dict[str, set[int]] = {}
        for t in all_terms_raw:
            key = t.text.lower().strip()
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid:
                term_campaigns.setdefault(key, set()).add(cid)

        camp_map = {c.id: c for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()}

        # Aggregate n-grams (1 through 4)
        # ngram_stats[n][ngram_text] = {clicks, cost_micros, conv, conv_value, terms: set}
        ngram_stats: dict[int, dict[str, dict]] = {n: defaultdict(lambda: {
            "clicks": 0, "cost_micros": 0, "conv": 0.0, "conv_value_micros": 0,
            "terms": set(), "campaign_ids": set(),
        }) for n in range(1, 5)}

        for text_lower, term in term_map.items():
            words = [w for w in text_lower.split() if len(w) >= 3 and w not in STOP_WORDS]
            cids = term_campaigns.get(text_lower, set())

            for n in range(1, 5):
                for ngram in _generate_ngrams(words, n):
                    s = ngram_stats[n][ngram]
                    s["clicks"] += term.clicks or 0
                    s["cost_micros"] += term.cost_micros or 0
                    s["conv"] += term.conversions or 0
                    s["conv_value_micros"] += term.conversion_value_micros or 0
                    s["terms"].add(text_lower)
                    s["campaign_ids"].update(cids)

        # Build items grouped by n-gram size
        items: list[ScriptItem] = []
        min_cost_micros = int(min_cost_pln * 1_000_000)

        for n in range(1, 5):
            for ngram, s in ngram_stats[n].items():
                if s["conv"] > max_conv:
                    continue
                if len(s["terms"]) < min_term_count:
                    continue
                if s["cost_micros"] < min_cost_micros:
                    continue
                if ngram in existing_neg_texts:
                    continue
                if brand_protection and _is_brand_term(ngram, brand_patterns):
                    continue

                # Keyword protection — check across all campaigns where this ngram appears
                kw_conflict = None
                for cid in s["campaign_ids"]:
                    camp_kws = kws_per_camp.get(cid, set())
                    conflict = _check_keyword_conflict(ngram, camp_kws)
                    if conflict == "BLOCK":
                        kw_conflict = "BLOCK"
                        break
                    if conflict == "EXACT":
                        kw_conflict = "EXACT"
                if kw_conflict == "BLOCK":
                    continue

                cost_pln = s["cost_micros"] / 1_000_000
                conv_value_pln = s["conv_value_micros"] / 1_000_000
                effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]
                kw_note = " [EXACT -- ochrona keywordu]" if kw_conflict == "EXACT" else ""

                # P0 fix: push negative to EVERY campaign where the n-gram
                # generates waste, not just a single (non-deterministic) pick.
                campaign_ids = sorted(s["campaign_ids"]) if s["campaign_ids"] else []
                first_camp_id = campaign_ids[0] if campaign_ids else None

                example_terms = sorted(s["terms"], key=lambda t: -(term_map[t].cost_micros or 0))[:3]

                items.append(ScriptItem(
                    id=f"{n}:{ngram}",
                    entity_name=ngram,
                    campaign_id=first_camp_id,
                    campaign_name=", ".join(
                        camp_map[c].name for c in campaign_ids if c in camp_map
                    )[:60],
                    reason=(
                        f"{len(s['terms'])} termow | {s['clicks']} clk | {cost_pln:.0f} zl "
                        f"| 0 konw | {len(campaign_ids)} kamp{kw_note}"
                    ),
                    metrics={
                        "ngram_size": n,
                        "term_count": len(s["terms"]),
                        "clicks": s["clicks"],
                        "cost_pln": round(cost_pln, 2),
                        "conversions": round(s["conv"], 1),
                        "conversion_value_pln": round(conv_value_pln, 2),
                        "example_terms": example_terms,
                        "campaign_count": len(campaign_ids),
                    },
                    estimated_savings_pln=round(cost_pln, 2),
                    action_payload={
                        "text": ngram,
                        "campaign_id": first_camp_id,
                        "campaign_ids": campaign_ids,
                        "negative_level": p["negative_level"],
                        "match_type": effective_match,
                        "ngram_size": n,
                    },
                ))

        items.sort(key=lambda x: (
            x.metrics.get("ngram_size", 1),
            -x.estimated_savings_pln,
        ))

        total_savings = sum(i.estimated_savings_pln for i in items)
        result = ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=round(total_savings, 2),
        )
        return result

    def execute(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
        item_ids: Optional[list] = None,
    ) -> ScriptExecuteResult:
        from app.models.action_log import ActionLog
        from app.services.google_ads import google_ads_service

        if not google_ads_service.is_connected:
            return ScriptExecuteResult(
                script_id=self.id,
                errors=["Google Ads API nie jest polaczone. Nie mozna wykonac skryptu."],
            )

        preview = self.dry_run(db, client_id, date_from, date_to, params)

        items_to_apply = preview.items
        if item_ids is not None:
            selected = {str(i) for i in item_ids}
            items_to_apply = [i for i in preview.items if str(i.id) in selected]

        # Expand each item to (item, campaign_id) pairs — D1 pushes a separate
        # negative into EVERY campaign where the n-gram wastes spend. This is
        # the P0 fix for the "one random campaign" bug.
        expanded: list[tuple[ScriptItem, int]] = []
        for item in items_to_apply:
            ap = item.action_payload
            cids = ap.get("campaign_ids") or ([ap["campaign_id"]] if ap.get("campaign_id") else [])
            if not cids:
                continue
            for cid in cids:
                expanded.append((item, cid))

        # Circuit breaker over the EXPANDED count — each (ngram, campaign)
        # pair counts as one negative against the daily cap. Sort by savings
        # first so the cap keeps the highest-impact pairs.
        expanded.sort(key=lambda pair: -pair[0].estimated_savings_pln)
        allowed_count, limit_error, limit_cap = self._validate_batch(
            db, client_id, "ADD_NEGATIVE", len(expanded)
        )
        expanded = expanded[:allowed_count]

        applied = 0
        failed = 0
        errors: list[str] = []
        if limit_error:
            errors.append(limit_error)
        applied_items: list[dict] = []

        # Group by (campaign_id, level) — all CAMPAIGN level for D1, but
        # future-proof shape. Each pair becomes its own NegativeKeyword row.
        groups: dict[tuple, list[tuple]] = {}

        for item, campaign_id in expanded:
            ap = item.action_payload
            # D1 is always campaign-level by design — see default_params note.
            neg_level = "CAMPAIGN"
            match_type = ap.get("match_type", "PHRASE")

            dup_q = db.query(NegativeKeyword).filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.text == ap["text"],
                NegativeKeyword.campaign_id == campaign_id,
                NegativeKeyword.match_type == match_type,
                NegativeKeyword.status != "REMOVED",
            )
            if dup_q.first():
                applied += 1
                applied_items.append({
                    "id": item.id, "entity_name": item.entity_name,
                    "campaign_name": item.campaign_name, "status": "success",
                    "estimated_savings_pln": 0,
                })
                continue

            neg = NegativeKeyword(
                client_id=client_id,
                campaign_id=campaign_id,
                criterion_kind="NEGATIVE",
                text=ap["text"],
                match_type=match_type,
                negative_scope=neg_level,
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg)
            db.flush()

            group_key = (campaign_id, neg_level, None)
            groups.setdefault(group_key, []).append((item, neg))

        for (campaign_id, level, _), batch in groups.items():
            negs_in_batch = [neg for _, neg in batch]
            try:
                campaign = db.get(Campaign, campaign_id)
                if campaign:
                    google_ads_service.batch_add_campaign_negatives(db, campaign, negs_in_batch)

                for itm, neg in batch:
                    applied += 1
                    applied_items.append({
                        "id": itm.id, "entity_name": itm.entity_name,
                        "campaign_name": campaign.name if campaign else itm.campaign_name,
                        "status": "success",
                        "estimated_savings_pln": 0,
                    })
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="campaign",
                        entity_id=str(campaign_id),
                        status="SUCCESS",
                        execution_mode="LIVE",
                        precondition_status="PASSED",
                        action_payload={
                            "action_type": "ADD_NEGATIVE",
                            "params": {
                                "text": neg.text,
                                "match_type": neg.match_type,
                                "ngram_size": itm.action_payload.get("ngram_size"),
                            },
                            "target": {"campaign_id": campaign_id},
                        },
                        context_json={"source": "scripts", "script_id": self.id},
                    ))
                db.commit()
            except Exception as exc:
                db.rollback()
                for itm, neg in batch:
                    failed += 1
                    errors.append(f"{itm.entity_name} @ camp {campaign_id}: {exc}")
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="campaign",
                        entity_id=str(campaign_id),
                        status="FAILED",
                        execution_mode="LIVE",
                        precondition_status="PASSED",
                        action_payload={"action_type": "ADD_NEGATIVE", "params": {"text": itm.entity_name}},
                        context_json={"source": "scripts", "script_id": self.id},
                        error_message=str(exc)[:500],
                    ))
                db.commit()

        return ScriptExecuteResult(
            script_id=self.id,
            applied=applied,
            failed=failed,
            errors=errors,
            applied_items=applied_items,
            circuit_breaker_limit=limit_cap,
        )
