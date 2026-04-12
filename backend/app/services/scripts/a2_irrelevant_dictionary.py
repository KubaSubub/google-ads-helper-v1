"""Script A2 — Irrelevant Dictionary (multi-layer negative gap detection).

Detects search terms that match known negatives from higher layers but are
not yet excluded in the campaign where they appear.

Layers (broad → narrow):
  Layer 1: MCC shared negative keyword lists          (ownership_level='mcc')
  Layer 2: Account-level negative keyword lists       (ownership_level='account')
  Layer 5: App-level IRRELEVANT_KEYWORDS seed         (constants.py)
  → These produce HARD MATCH — selected by default in UI.

  Layer 3: Campaign-level negatives from OTHER campaigns
  Layer 4: Ad-group-level negatives from OTHER campaigns
  → These produce SOFT MATCH — only if the term actually has traffic in the
    target campaign. Unselected by default in UI, shown as yellow hint.

Brand protection: terms containing the client's brand are skipped.
"""

import re
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.negative_keyword_list import NegativeKeywordList, NegativeKeywordListItem
from app.models.search_term import SearchTerm
from app.services.scripts._helpers import (
    GENERIC_WORDS,
    _build_brand_patterns,
    _check_keyword_conflict,
    _is_brand_term,
)
from app.services.scripts.base import (
    ACTION_NEGATIVE,
    CATEGORY_WASTE,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)
from app.utils.constants import IRRELEVANT_KEYWORDS

# Re-exported for backward compatibility with modules importing from a2.
__all__ = [
    "GENERIC_WORDS",
    "_build_brand_patterns",
    "_is_brand_term",
    "_check_keyword_conflict",
    "IrrelevantDictionaryScript",
]


class IrrelevantDictionaryScript(ScriptBase):
    id = "A2"
    name = "Luki w wykluczeniach (słownik + cross-campaign)"
    category = CATEGORY_WASTE
    description = (
        "Wykrywa search terms pasujące do negatywów z list MCC/konta/IRRELEVANT "
        "lub z innych kampanii — ale niepokryte w kampanii gdzie generują ruch."
    )
    action_type = ACTION_NEGATIVE
    default_params = {
        "min_clicks": 0,
        "min_cost_pln": 0.0,
        "brand_protection": True,
        "custom_brand_words": [],
        "include_soft": True,        # show cross-campaign suggestions
        "soft_min_clicks": 1,        # soft matches require at least 1 click
        "negative_level": "CAMPAIGN",
        "match_type": "PHRASE",
    }

    def _build_global_patterns(self, db: Session, client_id: int) -> list[tuple[str, str, re.Pattern]]:
        """Build (word, source_label, pattern) tuples from layers 1, 2, 5."""
        patterns: list[tuple[str, str, re.Pattern]] = []
        seen: set[str] = set()

        def _add(text: str, source: str):
            key = text.lower().strip()
            if key in seen or len(key) < 2:
                return
            seen.add(key)
            patterns.append((
                text.strip(),
                source,
                re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE),
            ))

        # Layer 5: app-level seed
        for kw in IRRELEVANT_KEYWORDS:
            _add(kw, "IRRELEVANT_KEYWORDS")

        # Layer 1: MCC lists
        mcc_lists = (
            db.query(NegativeKeywordList)
            .filter(
                NegativeKeywordList.ownership_level == "mcc",
                NegativeKeywordList.status == "ENABLED",
            )
            .all()
        )
        for lst in mcc_lists:
            items = db.query(NegativeKeywordListItem).filter(NegativeKeywordListItem.list_id == lst.id).all()
            for item in items:
                _add(item.text, f"MCC: {lst.name}")

        # Layer 2: account lists for this client
        acct_lists = (
            db.query(NegativeKeywordList)
            .filter(
                NegativeKeywordList.client_id == client_id,
                NegativeKeywordList.ownership_level == "account",
                NegativeKeywordList.status == "ENABLED",
            )
            .all()
        )
        for lst in acct_lists:
            items = db.query(NegativeKeywordListItem).filter(NegativeKeywordListItem.list_id == lst.id).all()
            for item in items:
                _add(item.text, f"Lista: {lst.name}")

        return patterns

    def dry_run(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
    ) -> ScriptResult:
        p = {**self.default_params, **(params or {})}
        min_clicks = int(p.get("min_clicks", 0))
        min_cost_pln = float(p.get("min_cost_pln", 0.0))
        brand_protection = bool(p.get("brand_protection", True))
        include_soft = bool(p.get("include_soft", True))
        soft_min_clicks = int(p.get("soft_min_clicks", 1))
        min_cost_micros = int(min_cost_pln * 1_000_000)

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = _build_brand_patterns(client, p.get("custom_brand_words")) if brand_protection else []
        global_patterns = self._build_global_patterns(db, client_id)

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        camp_name_map = {c.id: c.name for c in campaigns}

        # Pre-fetch ALL existing negatives per campaign (one query, not N)
        all_negs = (
            db.query(NegativeKeyword.text, NegativeKeyword.campaign_id)
            .filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.status != "REMOVED",
            )
            .all()
        )
        existing_per_camp: dict[int, set[str]] = {}
        for text, cid in all_negs:
            if text and cid is not None:
                existing_per_camp.setdefault(cid, set()).add(text.lower().strip())

        # Pre-build cross-campaign negative lookup: {neg_text_lower: source_campaign_name}
        # Built ONCE, then per-campaign we exclude that campaign's own negs.
        all_cross_negs: dict[str, dict[str, int]] = {}  # neg_text -> {camp_name, camp_id}
        if include_soft:
            for text, cid in all_negs:
                if not text:
                    continue
                key = text.lower().strip()
                word_count = len(key.split())
                if word_count == 1 and len(key) < 8:
                    continue
                if key not in all_cross_negs:
                    all_cross_negs[key] = {"name": camp_name_map.get(cid, ""), "camp_id": cid}

        # Pre-fetch ALL search terms for this client in date range (one query batch)
        all_terms_q1 = (
            db.query(SearchTerm)
            .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
        )
        all_terms_q2 = (
            db.query(SearchTerm)
            .filter(SearchTerm.campaign_id.isnot(None), SearchTerm.ad_group_id.is_(None))
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
        )
        if date_from:
            all_terms_q1 = all_terms_q1.filter(SearchTerm.date_to >= date_from)
            all_terms_q2 = all_terms_q2.filter(SearchTerm.date_to >= date_from)
        if date_to:
            all_terms_q1 = all_terms_q1.filter(SearchTerm.date_from <= date_to)
            all_terms_q2 = all_terms_q2.filter(SearchTerm.date_from <= date_to)
        all_terms_raw = all_terms_q1.all() + all_terms_q2.all()

        # Group terms by campaign, dedup by text (keep highest cost)
        terms_by_camp: dict[int, dict[str, SearchTerm]] = {}
        for t in all_terms_raw:
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid is None:
                continue
            key = t.text.lower().strip()
            bucket = terms_by_camp.setdefault(cid, {})
            if key not in bucket or (t.cost_micros or 0) > (bucket[key].cost_micros or 0):
                bucket[key] = t

        # Pre-fetch keywords per campaign — for keyword protection check
        all_kws = (
            db.query(Keyword.text, AdGroup.campaign_id)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Keyword.status == "ENABLED")
            .all()
        )
        kws_per_camp: dict[int, set[str]] = {}
        for text, cid in all_kws:
            if text:
                kws_per_camp.setdefault(cid, set()).add(text.lower().strip())

        items: list[ScriptItem] = []
        seen_keys: set[tuple] = set()

        for campaign in campaigns:
            existing_negs = existing_per_camp.get(campaign.id, set())
            term_map = terms_by_camp.get(campaign.id, {})
            camp_keywords = kws_per_camp.get(campaign.id, set())

            # HARD MATCH — layers 1, 2, 5
            for text_lower, term in term_map.items():
                if text_lower in existing_negs:
                    continue
                dedup_key = (text_lower, campaign.id)
                if dedup_key in seen_keys:
                    continue
                if brand_protection and _is_brand_term(term.text, brand_patterns):
                    continue

                clicks = term.clicks or 0
                cost_micros = term.cost_micros or 0
                if clicks < min_clicks or cost_micros < min_cost_micros:
                    continue

                # Keyword protection: skip or force EXACT
                kw_conflict = _check_keyword_conflict(text_lower, camp_keywords)
                if kw_conflict == "BLOCK":
                    continue

                for word, source, pattern in global_patterns:
                    if pattern.search(term.text):
                        cost_pln = cost_micros / 1_000_000
                        effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]
                        kw_note = " [wymuszony EXACT — ochrona keywordu]" if kw_conflict == "EXACT" else ""
                        seen_keys.add(dedup_key)
                        items.append(ScriptItem(
                            id=term.id,
                            entity_name=term.text,
                            campaign_id=campaign.id,
                            campaign_name=campaign.name,
                            reason=f'"{word}" ({source}){kw_note}',
                            metrics={
                                "clicks": clicks,
                                "impressions": term.impressions or 0,
                                "cost_pln": round(cost_pln, 2),
                                "conversions": round(term.conversions or 0, 1),
                            },
                            estimated_savings_pln=round(cost_pln, 2),
                            action_payload={
                                "text": term.text,
                                "campaign_id": campaign.id,
                                "ad_group_id": term.ad_group_id,
                                "negative_level": p["negative_level"],
                                "match_type": effective_match,
                                "match_source": "hard",
                                "matched_word": word,
                                "matched_source": source,
                            },
                        ))
                        break

            # SOFT MATCH — layers 3, 4 (cross-campaign)
            # Use substring check instead of per-negative regex compilation.
            if include_soft:
                for text_lower, term in term_map.items():
                    if text_lower in existing_negs:
                        continue
                    dedup_key = (text_lower, campaign.id)
                    if dedup_key in seen_keys:
                        continue
                    if brand_protection and _is_brand_term(term.text, brand_patterns):
                        continue

                    clicks = term.clicks or 0
                    if clicks < soft_min_clicks:
                        continue

                    # Keyword protection
                    kw_conflict = _check_keyword_conflict(text_lower, camp_keywords)
                    if kw_conflict == "BLOCK":
                        continue

                    term_words = set(text_lower.split())
                    matched_neg = None
                    matched_source = None
                    for neg_key, neg_info in all_cross_negs.items():
                        if neg_info["camp_id"] == campaign.id:
                            continue
                        neg_words = neg_key.split()
                        if all(w in term_words for w in neg_words):
                            matched_neg = neg_key
                            matched_source = neg_info["name"]
                            break

                    if matched_neg:
                        cost_pln = (term.cost_micros or 0) / 1_000_000
                        effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]
                        kw_note = " [EXACT — ochrona keywordu]" if kw_conflict == "EXACT" else ""
                        seen_keys.add(dedup_key)
                        items.append(ScriptItem(
                            id=term.id,
                            entity_name=term.text,
                            campaign_id=campaign.id,
                            campaign_name=campaign.name,
                            reason=f'Wykluczone w: {matched_source}{kw_note}',
                            metrics={
                                "clicks": clicks,
                                "impressions": term.impressions or 0,
                                "cost_pln": round(cost_pln, 2),
                                "conversions": round(term.conversions or 0, 1),
                            },
                            estimated_savings_pln=round(cost_pln, 2),
                            action_payload={
                                "text": term.text,
                                "campaign_id": campaign.id,
                                "ad_group_id": term.ad_group_id,
                                "negative_level": p["negative_level"],
                                "match_type": effective_match,
                                "match_source": "soft",
                                "matched_word": matched_neg,
                                "matched_source": f"Kampania: {matched_source}",
                            },
                        ))

        # Sort: hard first, then soft; within each group by cost desc
        items.sort(key=lambda x: (
            0 if x.action_payload.get("match_source") == "hard" else 1,
            -x.estimated_savings_pln,
        ))

        total_savings = sum(i.estimated_savings_pln for i in items)
        return ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=round(total_savings, 2),
        )

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
                errors=["Google Ads API nie jest połączone. Nie można wykonać skryptu."],
            )

        preview = self.dry_run(db, client_id, date_from, date_to, params)

        items_to_apply = preview.items
        if item_ids is not None:
            selected = {str(i) for i in item_ids}
            items_to_apply = [i for i in preview.items if str(i.id) in selected]

        # Circuit breaker: cap at MAX_NEGATIVES_PER_DAY across all scripts.
        allowed_count, limit_error, limit_cap = self._validate_batch(
            db, client_id, "ADD_NEGATIVE", len(items_to_apply)
        )
        trimmed_items = items_to_apply[:allowed_count]

        applied = 0
        failed = 0
        errors: list[str] = []
        if limit_error:
            errors.append(limit_error)
        applied_items: list[dict] = []

        # Group by (campaign_id, level, ad_group_id) so AD_GROUP negatives
        # go to batch_add_ad_group_negatives and CAMPAIGN-level negatives go
        # to batch_add_campaign_negatives — was a P0 bug where everything was
        # forced to campaign level.
        groups: dict[tuple, list[tuple]] = {}
        for item in trimmed_items:
            ap = item.action_payload
            neg_level = ap.get("negative_level", "CAMPAIGN")
            match_type = ap.get("match_type", "PHRASE")
            campaign_id = ap["campaign_id"]
            ad_group_id = ap.get("ad_group_id") if neg_level == "AD_GROUP" else None

            # Fallback: PMax terms do not have an ad_group — degrade to
            # CAMPAIGN scope so DB + API state stay consistent.
            if neg_level == "AD_GROUP" and not ad_group_id:
                neg_level = "CAMPAIGN"

            dup_q = db.query(NegativeKeyword).filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.text == ap["text"],
                NegativeKeyword.campaign_id == campaign_id,
                NegativeKeyword.match_type == match_type,
                NegativeKeyword.status != "REMOVED",
            )
            if neg_level == "AD_GROUP" and ad_group_id:
                dup_q = dup_q.filter(NegativeKeyword.ad_group_id == ad_group_id)
            if dup_q.first():
                applied += 1
                applied_items.append({
                    "id": item.id, "entity_name": item.entity_name,
                    "campaign_name": item.campaign_name, "status": "success",
                    "estimated_savings_pln": item.estimated_savings_pln,
                })
                continue

            neg = NegativeKeyword(
                client_id=client_id,
                campaign_id=campaign_id,
                ad_group_id=ad_group_id,
                criterion_kind="NEGATIVE",
                text=ap["text"],
                match_type=match_type,
                negative_scope=neg_level,
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg)
            db.flush()

            group_key = (campaign_id, neg_level, ad_group_id)
            groups.setdefault(group_key, []).append((item, neg))

        for (campaign_id, level, ag_id), batch in groups.items():
            negs_in_batch = [neg for _, neg in batch]
            try:
                if level == "AD_GROUP" and ag_id:
                    ad_group = db.get(AdGroup, ag_id)
                    if ad_group:
                        google_ads_service.batch_add_ad_group_negatives(db, ad_group, negs_in_batch)
                else:
                    campaign = db.get(Campaign, campaign_id)
                    if campaign:
                        google_ads_service.batch_add_campaign_negatives(db, campaign, negs_in_batch)

                for itm, neg in batch:
                    applied += 1
                    applied_items.append({
                        "id": itm.id, "entity_name": itm.entity_name,
                        "campaign_name": itm.campaign_name, "status": "success",
                        "estimated_savings_pln": itm.estimated_savings_pln,
                    })
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="ad_group" if level == "AD_GROUP" else "campaign",
                        entity_id=str(ag_id or campaign_id),
                        status="SUCCESS",
                        execution_mode="LIVE",
                        precondition_status="PASSED",
                        action_payload={
                            "action_type": "ADD_NEGATIVE",
                            "params": {
                                "text": neg.text,
                                "match_type": neg.match_type,
                                "negative_level": level,
                            },
                            "target": {"campaign_id": campaign_id, "ad_group_id": ag_id},
                        },
                        context_json={
                            "source": "scripts", "script_id": self.id,
                            "match_source": itm.action_payload.get("match_source"),
                            "matched_word": itm.action_payload.get("matched_word"),
                        },
                    ))
                db.commit()
            except Exception as exc:
                db.rollback()
                for itm, neg in batch:
                    failed += 1
                    errors.append(f"{itm.entity_name}: {exc}")
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="ad_group" if level == "AD_GROUP" else "campaign",
                        entity_id=str(ag_id or campaign_id),
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
