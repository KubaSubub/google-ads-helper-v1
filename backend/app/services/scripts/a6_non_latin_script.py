"""Script A6 — Non-Latin Script Detection.

Detects search terms containing characters from scripts other than the allowed
list (default: LATIN only). Useful for filtering out queries in other languages
that are clearly outside the client's target market (Cyrillic, CJK, Arabic, etc).

Each detected term becomes an EXACT match negative keyword (one negative per
term — Google Ads doesn't support character-class negatives).
"""

import unicodedata
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
    CATEGORY_WASTE,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)

# Unicode script names we care about. Names match what unicodedata.name() returns
# as the FIRST WORD of each character's name (e.g. "LATIN SMALL LETTER A" -> "LATIN").
# Order matters for display purposes in reason strings.
KNOWN_SCRIPTS = [
    "LATIN",       # English, Polish, German, French, Italian, Spanish...
    "CYRILLIC",    # Russian, Ukrainian, Bulgarian, Serbian...
    "GREEK",
    "HEBREW",
    "ARABIC",
    "CJK",         # Chinese ideographs (CJK UNIFIED IDEOGRAPH...)
    "HIRAGANA",    # Japanese syllabary
    "KATAKANA",    # Japanese syllabary
    "HANGUL",      # Korean
    "THAI",
    "DEVANAGARI",  # Hindi, Sanskrit
    "BENGALI",
    "TAMIL",
    "GEORGIAN",
    "ARMENIAN",
]


def _detect_scripts(text: str) -> dict[str, int]:
    """Return {script_name: char_count} for letters in text.
    Digits, whitespace, punctuation are ignored.
    """
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            continue
        first_word = name.split(" ", 1)[0]
        # Map to known script bucket
        if first_word in KNOWN_SCRIPTS:
            counts[first_word] = counts.get(first_word, 0) + 1
        else:
            # Some characters have complex names; try to extract script from full name
            # For now, fall back to first word (may be a script we don't know)
            counts[first_word] = counts.get(first_word, 0) + 1
    return counts


class NonLatinScriptScript(ScriptBase):
    id = "A6"
    name = "Wykrywacz hasel w obcych alfabetach"
    category = CATEGORY_WASTE
    description = (
        "Wykrywa search terms zawierajace znaki spoza dozwolonych pism "
        "(np. cyrylica, CJK, arabski) i proponuje wykluczenie jako EXACT negatives."
    )
    action_type = ACTION_NEGATIVE
    default_params = {
        "allowed_scripts": ["LATIN"],
        "min_foreign_chars": 2,
        "negative_level": "CAMPAIGN",
        "match_type": "EXACT",
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

        # Normalize allowed_scripts — may come as string or list
        raw_allowed = p.get("allowed_scripts", ["LATIN"])
        if isinstance(raw_allowed, str):
            raw_allowed = [s.strip() for s in raw_allowed.split(",") if s.strip()]
        allowed = {s.upper() for s in raw_allowed}
        min_foreign = int(p.get("min_foreign_chars", 2))
        brand_protection = bool(p.get("brand_protection", True))

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = (
            _build_brand_patterns(client, p.get("custom_brand_words"))
            if brand_protection
            else []
        )

        # Pre-fetch active keywords per campaign for keyword protection.
        kws_per_camp: dict[int, set[str]] = {}
        kw_rows = (
            db.query(Keyword.text, AdGroup.campaign_id)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Keyword.status == "ENABLED")
            .all()
        )
        for text, cid in kw_rows:
            if text and cid is not None:
                kws_per_camp.setdefault(cid, set()).add(text.lower().strip())

        # Pre-fetch existing negatives (by campaign)
        existing_per_camp: dict[int, set[str]] = {}
        neg_rows = (
            db.query(NegativeKeyword.text, NegativeKeyword.campaign_id)
            .filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.status != "REMOVED",
            )
            .all()
        )
        for text, cid in neg_rows:
            if text and cid is not None:
                existing_per_camp.setdefault(cid, set()).add(text.lower().strip())

        # Pre-fetch search terms (date-filtered)
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
        all_terms = q1.all() + q2.all()

        camp_map = {c.id: c for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()}

        # Dedup by (text_lower, campaign_id) — pick row with most recent window
        seen: dict[tuple, SearchTerm] = {}
        for t in all_terms:
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid is None:
                continue
            key = (t.text.lower().strip(), cid)
            if key not in seen or (t.date_to and seen[key].date_to and t.date_to > seen[key].date_to):
                seen[key] = t

        items: list[ScriptItem] = []
        for (text_lower, cid), term in seen.items():
            if cid in existing_per_camp and text_lower in existing_per_camp[cid]:
                continue

            scripts_found = _detect_scripts(term.text)
            if not scripts_found:
                continue

            # Count foreign letters (anything not in allowed set)
            foreign_counts = {s: n for s, n in scripts_found.items() if s not in allowed}
            foreign_total = sum(foreign_counts.values())
            if foreign_total < min_foreign:
                continue

            camp = camp_map.get(cid)
            if not camp:
                continue

            # Brand protection (edge case: non-latin branded names)
            if brand_protection and _is_brand_term(term.text, brand_patterns):
                continue

            # Keyword protection — BLOCK skips, EXACT forces match_type=EXACT
            # even though A6 already defaults to EXACT (future-proof against
            # user overrides to PHRASE/BROAD).
            camp_keywords = kws_per_camp.get(cid, set())
            kw_conflict = _check_keyword_conflict(text_lower, camp_keywords)
            if kw_conflict == "BLOCK":
                continue
            effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]

            cost_pln = (term.cost_micros or 0) / 1_000_000
            scripts_label = ", ".join(sorted(foreign_counts.keys()))

            items.append(ScriptItem(
                id=term.id,
                entity_name=term.text,
                campaign_id=cid,
                campaign_name=camp.name,
                reason=(
                    f"{foreign_total} znakow obcych ({scripts_label}) | "
                    f"{term.clicks or 0} clk | {cost_pln:.0f} zl | "
                    f"{term.conversions or 0:.0f} konw"
                ),
                metrics={
                    "clicks": term.clicks or 0,
                    "impressions": term.impressions or 0,
                    "cost_pln": round(cost_pln, 2),
                    "conversions": round(term.conversions or 0, 1),
                    "foreign_chars": foreign_total,
                    "scripts_detected": foreign_counts,
                },
                estimated_savings_pln=round(cost_pln, 2),
                action_payload={
                    "text": term.text,
                    "campaign_id": cid,
                    "ad_group_id": term.ad_group_id,
                    "negative_level": p["negative_level"],
                    "match_type": effective_match,
                    "scripts_detected": foreign_counts,
                },
            ))

        items.sort(key=lambda x: -x.estimated_savings_pln)

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
                errors=["Google Ads API nie jest polaczone. Nie mozna wykonac skryptu."],
            )

        preview = self.dry_run(db, client_id, date_from, date_to, params)

        items_to_apply = preview.items
        if item_ids is not None:
            selected = {str(i) for i in item_ids}
            items_to_apply = [i for i in preview.items if str(i.id) in selected]

        allowed_count, limit_error, limit_cap = self._validate_batch(
            db, client_id, "ADD_NEGATIVE", len(items_to_apply)
        )
        items_to_apply = items_to_apply[:allowed_count]

        applied = 0
        failed = 0
        errors: list[str] = []
        if limit_error:
            errors.append(limit_error)
        applied_items: list[dict] = []

        groups: dict[tuple, list[tuple]] = {}

        for item in items_to_apply:
            ap = item.action_payload
            neg_level = ap.get("negative_level", "CAMPAIGN")
            match_type = ap.get("match_type", "EXACT")
            campaign_id = ap["campaign_id"]
            ad_group_id = ap.get("ad_group_id") if neg_level == "AD_GROUP" else None

            # Fallback: PMax terms (or any term without an ad_group) can't be
            # negated at AD_GROUP scope — drop to CAMPAIGN to keep state consistent.
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

            groups.setdefault((campaign_id, neg_level, ad_group_id), []).append((item, neg))

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
                            "scripts_detected": itm.action_payload.get("scripts_detected"),
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
