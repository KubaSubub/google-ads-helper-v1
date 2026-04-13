"""Script A3 — Low CTR Waste.

Flags search terms that got enough impressions to judge relevance but
whose click-through rate is below a threshold. Low CTR on a query that
Google served us means the ad wasn't compelling for that user intent —
either the ad needs tuning, or the term should be excluded.

Uses the same window-matching + brand + keyword protection as A1.
"""

from datetime import date, timedelta
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
    fetch_aggregated_terms,
)
from app.services.scripts.base import (
    ACTION_NEGATIVE,
    CATEGORY_WASTE,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)


class LowCtrWasteScript(ScriptBase):
    id = "A3"
    name = "Niski CTR — wykluczenia kandydatów"
    category = CATEGORY_WASTE
    description = (
        "Search terms z wieloma wyświetleniami ale CTR poniżej progu — "
        "sygnał że zapytanie nie pasuje do reklamy. Propozycja negatywów."
    )
    action_type = ACTION_NEGATIVE
    default_params = {
        "min_impressions": 100,
        "max_ctr_pct": 0.5,
        "max_conversions": 0,
        "negative_level": "CAMPAIGN",
        "match_type": "PHRASE",
        "brand_protection": True,
        "custom_brand_words": [],
        "conversion_lag_days": 7,
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
        min_impressions = int(p.get("min_impressions", 100))
        max_ctr_pct = float(p.get("max_ctr_pct", 0.5))
        max_conv = float(p.get("max_conversions", 0))
        brand_protection = bool(p.get("brand_protection", True))
        lag_days = max(0, int(p.get("conversion_lag_days", 7)))

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = (
            _build_brand_patterns(client, p.get("custom_brand_words"))
            if brand_protection
            else []
        )

        kws_per_camp: dict[int, set[str]] = {}
        for text, cid in (
            db.query(Keyword.text, AdGroup.campaign_id)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Keyword.status == "ENABLED")
            .all()
        ):
            if text and cid is not None:
                kws_per_camp.setdefault(cid, set()).add(text.lower().strip())

        existing_neg: set[tuple] = set()
        for text, cid in (
            db.query(NegativeKeyword.text, NegativeKeyword.campaign_id)
            .filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.status != "REMOVED",
            )
            .all()
        ):
            if text and cid is not None:
                existing_neg.add((text.lower().strip(), cid))

        camp_map = {
            c.id: c.name
            for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()
        }

        agg = fetch_aggregated_terms(db, client_id, date_from, date_to)

        today = date.today()
        reference_day = date_to if date_to and date_to < today else today
        lag_cutoff = reference_day - timedelta(days=lag_days) if lag_days > 0 else None

        items: list[ScriptItem] = []
        total_savings = 0.0
        skipped_recent = 0
        warns_recent_window = 0

        for key, d in agg.items():
            text_lower, campaign_id = key
            impressions = d["impressions"]
            clicks = d["clicks"]
            if impressions < min_impressions:
                continue
            if d["conversions"] > max_conv:
                continue
            ctr = (clicks / impressions * 100) if impressions else 0.0
            if ctr > max_ctr_pct:
                continue
            if key in existing_neg:
                continue

            window_from = d.get("window_from")
            window_to = d.get("window_to")
            if lag_cutoff is not None and window_from is not None:
                if window_from > lag_cutoff:
                    skipped_recent += 1
                    continue
                if window_to is not None and window_to > lag_cutoff:
                    warns_recent_window += 1

            if brand_protection and _is_brand_term(d["text"], brand_patterns):
                continue

            camp_keywords = kws_per_camp.get(campaign_id, set())
            kw_conflict = _check_keyword_conflict(text_lower, camp_keywords)
            if kw_conflict == "BLOCK":
                continue
            effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]
            kw_note = " [EXACT — ochrona keywordu]" if kw_conflict == "EXACT" else ""

            cost_pln = d["cost_micros"] / 1_000_000
            total_savings += cost_pln

            items.append(ScriptItem(
                id=d["term_id"],
                entity_name=d["text"],
                campaign_id=campaign_id,
                campaign_name=camp_map.get(campaign_id, ""),
                reason=(
                    f"{impressions} wyśw · {clicks} kl · CTR {ctr:.2f}% · koszt ~{cost_pln:.0f} zł{kw_note}"
                ),
                metrics={
                    "clicks": clicks,
                    "impressions": impressions,
                    "cost_pln": round(cost_pln, 2),
                    "conversions": round(d["conversions"], 1),
                    "ctr": round(ctr, 2),
                },
                estimated_savings_pln=round(cost_pln, 2),
                action_payload={
                    "text": d["text"],
                    "campaign_id": campaign_id,
                    "ad_group_id": d["ad_group_id"],
                    "negative_level": p["negative_level"],
                    "match_type": effective_match,
                },
            ))

        items.sort(key=lambda x: -x.estimated_savings_pln)

        warnings: list[str] = []
        if skipped_recent:
            warnings.append(
                f"Pominięto {skipped_recent} term(ów) z oknem w całości w ostatnich {lag_days} dniach."
            )
        if warns_recent_window:
            warnings.append(
                f"{warns_recent_window} flagowanych termów ma okno sięgające ostatnich {lag_days} dni."
            )

        return ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=round(total_savings, 2),
            warnings=warnings,
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
            match_type = ap.get("match_type", "PHRASE")
            campaign_id = ap["campaign_id"]
            ad_group_id = ap.get("ad_group_id") if neg_level == "AD_GROUP" else None
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
                            "params": {"text": neg.text, "match_type": neg.match_type, "negative_level": level},
                            "target": {"campaign_id": campaign_id, "ad_group_id": ag_id},
                        },
                        context_json={"source": "scripts", "script_id": self.id, "batch_size": len(batch)},
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
