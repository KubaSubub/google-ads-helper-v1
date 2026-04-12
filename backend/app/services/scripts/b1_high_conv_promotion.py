"""Script B1 — High-Converting Term Promotion.

Identifies search terms that convert well but are not yet added as keywords.
Adding them as exact match keywords gives the advertiser direct bid control
and prevents the term from being lost if Google changes broad/phrase matching.

For Search campaigns: executable action (ADD_KEYWORD to the source ad group).
For PMax campaigns: informational alert only (PMax doesn't support keywords).
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.search_term import SearchTerm
from app.services.scripts._helpers import (
    _build_brand_patterns,
    _is_brand_term,
)
from app.services.scripts.base import (
    ACTION_KEYWORD,
    CATEGORY_EXPANSION,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)


class HighConvPromotionScript(ScriptBase):
    id = "B1"
    name = "Promocja top performerów do keywords"
    category = CATEGORY_EXPANSION
    description = (
        "Search terms z konwersjami, które nie są jeszcze keyword'ami — "
        "dodaj jako exact match żeby uzyskać kontrolę nad bidem."
    )
    action_type = ACTION_KEYWORD
    default_params = {
        "min_conversions": 2,
        "min_cvr_pct": 0.0,
        "max_cpa_pln": 0.0,        # 0 = no limit
        "keyword_match_type": "EXACT",
        "include_pmax_alerts": True,
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
        min_conv = float(p.get("min_conversions", 2))
        min_cvr = float(p.get("min_cvr_pct", 0))
        max_cpa = float(p.get("max_cpa_pln", 0))
        include_pmax = bool(p.get("include_pmax_alerts", True))
        brand_protection = bool(p.get("brand_protection", True))

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = _build_brand_patterns(client, p.get("custom_brand_words")) if brand_protection else []

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        camp_map = {c.id: c for c in campaigns}

        # Pre-fetch all existing keyword texts per client (any campaign/ad group)
        existing_kw_texts: set[str] = set()
        kw_rows = (
            db.query(Keyword.text)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        for (text,) in kw_rows:
            if text:
                existing_kw_texts.add(text.lower().strip())

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

        all_terms = q1.all() + q2.all()

        # Window matching: pick best sync window per (text, campaign_id)
        user_range_days = None
        if date_from and date_to:
            user_range_days = max(1, (date_to - date_from).days)

        groups: dict[tuple, list[SearchTerm]] = {}
        for t in all_terms:
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid is None:
                continue
            key = (t.text.lower().strip(), cid)
            groups.setdefault(key, []).append(t)

        best_terms: dict[tuple, SearchTerm] = {}
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
            best_terms[key] = chosen

        # Compute campaign-level avg CVR + CPA for comparison
        camp_stats: dict[int, dict] = {}
        for key, t in best_terms.items():
            cid = key[1]
            if cid not in camp_stats:
                camp_stats[cid] = {"clicks": 0, "conv": 0.0, "cost_micros": 0}
            camp_stats[cid]["clicks"] += t.clicks or 0
            camp_stats[cid]["conv"] += t.conversions or 0
            camp_stats[cid]["cost_micros"] += t.cost_micros or 0

        camp_cvr: dict[int, float] = {}
        camp_cpa: dict[int, float] = {}
        for cid, s in camp_stats.items():
            camp_cvr[cid] = (s["conv"] / s["clicks"] * 100) if s["clicks"] else 0
            cost_pln = s["cost_micros"] / 1_000_000
            camp_cpa[cid] = (cost_pln / s["conv"]) if s["conv"] else 0

        items: list[ScriptItem] = []
        seen: set[str] = set()

        for key, term in best_terms.items():
            text_lower, cid = key
            conv = term.conversions or 0
            clicks = term.clicks or 0

            if conv < min_conv:
                continue
            if text_lower in existing_kw_texts:
                continue
            if text_lower in seen:
                continue
            if brand_protection and _is_brand_term(term.text, brand_patterns):
                continue

            cvr = (conv / clicks * 100) if clicks else 0
            cost_pln = (term.cost_micros or 0) / 1_000_000
            cpa = (cost_pln / conv) if conv else 0
            conv_value_pln = (term.conversion_value_micros or 0) / 1_000_000

            if min_cvr > 0 and cvr < min_cvr:
                continue
            if max_cpa > 0 and cpa > max_cpa:
                continue

            camp = camp_map.get(cid)
            if not camp:
                continue
            is_pmax = camp.campaign_type == "PERFORMANCE_MAX"

            if is_pmax and not include_pmax:
                continue

            seen.add(text_lower)
            avg_cvr = camp_cvr.get(cid, 0)
            cvr_vs_avg = f"{cvr / avg_cvr:.1f}x" if avg_cvr else "--"
            value_note = f" | wart. {conv_value_pln:.0f} zl" if conv_value_pln > 0 else " | wart. 0 zl (micro-conv?)"
            source_note = f" | zrodlo: {camp.name}" if is_pmax else ""

            items.append(ScriptItem(
                id=term.id,
                entity_name=term.text,
                campaign_id=cid,
                campaign_name=camp.name,
                reason=(
                    f"{conv:.0f} konw | CVR {cvr:.1f}% ({cvr_vs_avg} avg) | CPA {cpa:.1f} zl{value_note}{source_note}"
                    + (" [PMax -- tylko alert]" if is_pmax else "")
                ),
                metrics={
                    "clicks": clicks,
                    "impressions": term.impressions or 0,
                    "conversions": round(conv, 1),
                    "conversion_value_pln": round(conv_value_pln, 2),
                    "cost_pln": round(cost_pln, 2),
                    "cvr": round(cvr, 1),
                    "cpa": round(cpa, 1),
                    "camp_avg_cvr": round(avg_cvr, 1),
                },
                estimated_savings_pln=round(cost_pln, 2),
                action_payload={
                    "text": term.text,
                    "campaign_id": cid,
                    "ad_group_id": None,  # user must pick in UI
                    "match_type": p["keyword_match_type"],
                    "match_source": "pmax_alert" if is_pmax else "search_action",
                    "is_pmax": is_pmax,
                },
            ))

        # Search actions first (executable), then PMax alerts
        items.sort(key=lambda x: (
            0 if x.action_payload.get("match_source") == "search_action" else 1,
            -(x.metrics.get("conversions") or 0),
        ))

        # Build list of available Search ad groups for the UI dropdown
        search_ad_groups = [
            {"id": ag.id, "name": ag.name, "campaign_name": camp_map.get(ag_camp_id, {}).name if camp_map.get(ag_camp_id) else ""}
            for ag, ag_camp_id in (
                (db.get(AdGroup, ag_id), cid)
                for cid, camp in camp_map.items()
                if camp.campaign_type == "SEARCH" and camp.status == "ENABLED"
                for ag_id in [
                    a.id for a in db.query(AdGroup).filter(AdGroup.campaign_id == cid).all()
                ]
            )
            if ag
        ]

        result = ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=0,
        )
        # Attach ad groups as extra data (ScriptResult doesn't have a field for this,
        # but the router serializes it from the script result dict)
        result._search_ad_groups = search_ad_groups
        return result

    def execute(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
        item_ids: Optional[list] = None,
        item_overrides: Optional[dict] = None,
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

        # Filter out PMax alerts — not executable
        items_to_apply = [i for i in items_to_apply if not i.action_payload.get("is_pmax")]

        allowed_count, limit_error, limit_cap = self._validate_batch(
            db, client_id, "ADD_KEYWORD", len(items_to_apply)
        )
        items_to_apply = items_to_apply[:allowed_count]

        overrides = item_overrides or {}

        applied = 0
        failed = 0
        errors: list[str] = []
        if limit_error:
            errors.append(limit_error)
        applied_items: list[dict] = []

        for item in items_to_apply:
            ap = item.action_payload
            item_override = overrides.get(str(item.id), {})
            ad_group_id = item_override.get("ad_group_id") or ap.get("ad_group_id")
            match_type = ap.get("match_type", "EXACT")

            if not ad_group_id:
                failed += 1
                errors.append(f"{item.entity_name}: wybierz docelowy ad group w podgladzie")
                continue

            # Check if keyword already exists
            existing = (
                db.query(Keyword)
                .filter(
                    Keyword.ad_group_id == ad_group_id,
                    Keyword.text == ap["text"],
                    Keyword.status != "REMOVED",
                )
                .first()
            )
            if existing:
                applied += 1
                applied_items.append({
                    "id": item.id, "entity_name": item.entity_name,
                    "campaign_name": item.campaign_name, "status": "success",
                })
                continue

            try:
                kw = Keyword(
                    ad_group_id=ad_group_id,
                    text=ap["text"],
                    match_type=match_type,
                    status="ENABLED",
                    criterion_kind="POSITIVE",
                )
                db.add(kw)
                db.flush()

                google_ads_service._mutate_add_keyword(kw, db)

                db.add(ActionLog(
                    client_id=client_id,
                    action_type="ADD_KEYWORD",
                    entity_type="ad_group",
                    entity_id=str(ad_group_id),
                    status="SUCCESS",
                    execution_mode="LIVE",
                    precondition_status="PASSED",
                    action_payload={
                        "action_type": "ADD_KEYWORD",
                        "params": {"text": ap["text"], "match_type": match_type},
                        "target": {"ad_group_id": ad_group_id, "campaign_id": ap["campaign_id"]},
                    },
                    context_json={"source": "scripts", "script_id": self.id},
                ))
                db.commit()

                applied += 1
                applied_items.append({
                    "id": item.id, "entity_name": item.entity_name,
                    "campaign_name": item.campaign_name, "status": "success",
                })
            except Exception as exc:
                db.rollback()
                failed += 1
                errors.append(f"{item.entity_name}: {exc}")
                db.add(ActionLog(
                    client_id=client_id,
                    action_type="ADD_KEYWORD",
                    entity_type="ad_group",
                    entity_id=str(ad_group_id),
                    status="FAILED",
                    execution_mode="LIVE",
                    precondition_status="PASSED",
                    action_payload={"action_type": "ADD_KEYWORD", "params": {"text": ap["text"]}},
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
