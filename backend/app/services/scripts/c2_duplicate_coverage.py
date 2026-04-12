"""Script C2 — Duplicate Coverage Detection.

Finds search terms that are matched by MULTIPLE locations:
  - Search ad group A + Search ad group B
  - Search ad group + PMax campaign
  - PMax campaign A + PMax campaign B

This is cannibalization — two locations bid against each other for the same query.

The user picks ONE "keeper" location in the UI; the rest get an EXACT-match
negative so they stop matching that term. EXACT is forced because PHRASE could
kill related traffic in the loser.
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
    CATEGORY_MATCH_TYPE,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)


class DuplicateCoverageScript(ScriptBase):
    id = "C2"
    name = "Duplicate Coverage (cannibalization)"
    category = CATEGORY_MATCH_TYPE
    description = (
        "Ten sam search term laczy ruch z >1 ad group lub kampanii. "
        "Wybierz ktora lokalizacje zostawic -- reszta dostanie EXACT negative."
    )
    action_type = ACTION_NEGATIVE
    default_params = {
        "min_clicks": 5,
        "min_cost_pln": 5.0,
        "show_converting": True,
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
        min_clicks = int(p.get("min_clicks", 5))
        min_cost_pln = float(p.get("min_cost_pln", 5.0))
        show_converting = bool(p.get("show_converting", True))
        brand_protection = bool(p.get("brand_protection", True))
        min_cost_micros = int(min_cost_pln * 1_000_000)

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        brand_patterns = (
            _build_brand_patterns(client, p.get("custom_brand_words"))
            if brand_protection
            else []
        )

        campaigns = {
            c.id: c
            for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()
        }
        ad_groups = {
            ag.id: ag
            for ag in db.query(AdGroup).join(Campaign).filter(Campaign.client_id == client_id).all()
        }

        # Pre-fetch active keywords per campaign for keyword protection check.
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

        # Fetch all terms (date-filtered)
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

        # Group by text_lower, collect every location (campaign_id + optional ad_group_id)
        # Each location tracks its own metrics (so user sees which one drove the traffic).
        # location_key = (campaign_id, ad_group_id)  — ad_group_id=None for PMax
        term_locations: dict[str, dict[tuple, dict]] = defaultdict(lambda: defaultdict(lambda: {
            "clicks": 0, "cost_micros": 0, "conv": 0.0, "conv_value_micros": 0,
            "keyword_text": None, "last_term_id": None,
        }))

        for t in all_terms:
            text_lower = t.text.lower().strip()
            cid = t.campaign_id
            ag_id = t.ad_group_id
            if cid is None and ag_id:
                ag = ad_groups.get(ag_id)
                if ag:
                    cid = ag.campaign_id
            if cid is None:
                continue

            camp = campaigns.get(cid)
            if not camp:
                continue
            # PMax: collapse to campaign level (ad_group_id is None in our data)
            # Search: keep ad_group_id
            loc_key = (cid, ag_id if camp.campaign_type != "PERFORMANCE_MAX" else None)

            loc = term_locations[text_lower][loc_key]
            loc["clicks"] += t.clicks or 0
            loc["cost_micros"] += t.cost_micros or 0
            loc["conv"] += t.conversions or 0
            loc["conv_value_micros"] += t.conversion_value_micros or 0
            if t.keyword_text and not loc["keyword_text"]:
                loc["keyword_text"] = t.keyword_text
            loc["last_term_id"] = t.id

        # Build items — only terms with >= 2 locations
        items: list[ScriptItem] = []
        for text_lower, locations in term_locations.items():
            if len(locations) < 2:
                continue

            total_clicks = sum(l["clicks"] for l in locations.values())
            total_cost_micros = sum(l["cost_micros"] for l in locations.values())
            total_conv = sum(l["conv"] for l in locations.values())

            if total_clicks < min_clicks:
                continue
            if total_cost_micros < min_cost_micros:
                continue
            if not show_converting and total_conv > 0:
                continue

            # Brand protection — never build cannibalization negatives on own brand.
            if brand_protection and _is_brand_term(text_lower, brand_patterns):
                continue

            # Keyword protection — if the term IS an active keyword in any
            # location, blocking it anywhere would kill positive traffic.
            blocked_by_keyword = False
            for (loc_cid, _ag_id) in locations.keys():
                if _check_keyword_conflict(text_lower, kws_per_camp.get(loc_cid, set())) == "BLOCK":
                    blocked_by_keyword = True
                    break
            if blocked_by_keyword:
                continue

            # Build location descriptors — user will pick one as keeper
            location_list = []
            for (cid, ag_id), loc in locations.items():
                camp = campaigns.get(cid)
                ag = ad_groups.get(ag_id) if ag_id else None
                is_pmax = camp.campaign_type == "PERFORMANCE_MAX" if camp else False
                cost_pln = loc["cost_micros"] / 1_000_000
                location_list.append({
                    "campaign_id": cid,
                    "ad_group_id": ag_id,
                    "campaign_name": camp.name if camp else "?",
                    "ad_group_name": ag.name if ag else None,
                    "is_pmax": is_pmax,
                    "label": (
                        f"{camp.name if camp else '?'} [PMax]"
                        if is_pmax
                        else f"{camp.name if camp else '?'} / {ag.name if ag else '?'}"
                        + (f" (kw: {loc['keyword_text']})" if loc["keyword_text"] else "")
                    ),
                    "clicks": loc["clicks"],
                    "cost_pln": round(cost_pln, 2),
                    "conversions": round(loc["conv"], 1),
                    "cvr": round((loc["conv"] / loc["clicks"] * 100) if loc["clicks"] else 0, 1),
                })
            # Sort locations by clicks desc — top is a natural keeper candidate
            location_list.sort(key=lambda l: -l["clicks"])

            # Recommended keeper: highest CVR; fallback highest clicks
            recommended_keeper = None
            with_conv = [l for l in location_list if l["conversions"] > 0]
            if with_conv:
                recommended_keeper = max(with_conv, key=lambda l: l["cvr"])
            else:
                recommended_keeper = location_list[0]

            rec_label = f"{recommended_keeper['campaign_name']}"
            if recommended_keeper.get("ad_group_name"):
                rec_label += f" / {recommended_keeper['ad_group_name']}"

            # Pick a stable item id — use the most-recent search_term.id among locations
            any_loc_key = next(iter(locations))
            item_id = locations[any_loc_key]["last_term_id"]

            cost_pln_total = total_cost_micros / 1_000_000

            items.append(ScriptItem(
                id=item_id,
                entity_name=text_lower,
                campaign_id=None,  # duplicate spans multiple
                campaign_name=f"{len(locations)} lokalizacji",
                reason=(
                    f"{len(locations)} miejsc | {total_clicks} clk | {cost_pln_total:.0f} zl | {total_conv:.0f} konw "
                    f"| rekomendacja: zostaw {rec_label[:50]}"
                ),
                metrics={
                    "total_clicks": total_clicks,
                    "total_cost_pln": round(cost_pln_total, 2),
                    "total_conversions": round(total_conv, 1),
                    "location_count": len(locations),
                    "locations": location_list,
                    "recommended_keeper": {
                        "campaign_id": recommended_keeper["campaign_id"],
                        "ad_group_id": recommended_keeper["ad_group_id"],
                    },
                },
                estimated_savings_pln=round(cost_pln_total - recommended_keeper["cost_pln"], 2),
                action_payload={
                    "text": text_lower,
                    "locations": location_list,
                    "keeper_campaign_id": None,  # user picks in UI
                    "keeper_ad_group_id": None,
                    "recommended_keeper_campaign_id": recommended_keeper["campaign_id"],
                    "recommended_keeper_ad_group_id": recommended_keeper["ad_group_id"],
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

        # Each item may create multiple negatives (one per loser location). For
        # the daily cap we use the upper bound = sum of (locations-1) per item.
        estimated_negatives = sum(
            max(0, len(i.action_payload.get("locations") or []) - 1)
            for i in items_to_apply
        )
        allowed_count, limit_error, limit_cap = self._validate_batch(
            db, client_id, "ADD_NEGATIVE", estimated_negatives
        )
        # If the cap doesn't cover everything, keep items that fit fully.
        if allowed_count < estimated_negatives:
            budget = allowed_count
            trimmed: list = []
            for itm in items_to_apply:
                losers = max(0, len(itm.action_payload.get("locations") or []) - 1)
                if losers <= budget:
                    trimmed.append(itm)
                    budget -= losers
            items_to_apply = trimmed

        overrides = item_overrides or {}

        applied = 0
        failed = 0
        errors: list[str] = []
        if limit_error:
            errors.append(limit_error)
        applied_items: list[dict] = []

        # Group mutations by (campaign_id, negative_level, ad_group_id) for batch API
        camp_batch: dict[tuple, list[tuple]] = {}
        ag_batch: dict[tuple, list[tuple]] = {}

        for item in items_to_apply:
            ap = item.action_payload
            text = ap["text"]

            override = overrides.get(str(item.id), {})
            keeper_cid = override.get("keeper_campaign_id") or ap.get("recommended_keeper_campaign_id")
            keeper_agid = override.get("keeper_ad_group_id")
            if keeper_agid is None:
                keeper_agid = ap.get("recommended_keeper_ad_group_id")

            if not keeper_cid:
                failed += 1
                errors.append(f"{text}: nie wybrano lokalizacji do zachowania")
                continue

            # Build losing locations = all except keeper
            losers = []
            for loc in ap["locations"]:
                if loc["campaign_id"] == keeper_cid and loc.get("ad_group_id") == keeper_agid:
                    continue
                losers.append(loc)

            if not losers:
                applied += 1
                applied_items.append({
                    "id": item.id, "entity_name": text,
                    "campaign_name": "brak akcji (jedna lokalizacja)", "status": "success",
                    "estimated_savings_pln": 0,
                })
                continue

            # Create negatives for each loser
            created_for_this_item = []
            skip_item = False
            for loser in losers:
                cid = loser["campaign_id"]
                ag_id = loser.get("ad_group_id")

                # Duplicate check
                dup_q = db.query(NegativeKeyword).filter(
                    NegativeKeyword.client_id == client_id,
                    NegativeKeyword.text == text,
                    NegativeKeyword.campaign_id == cid,
                    NegativeKeyword.match_type == "EXACT",
                    NegativeKeyword.status != "REMOVED",
                )
                if ag_id:
                    dup_q = dup_q.filter(NegativeKeyword.ad_group_id == ag_id)
                if dup_q.first():
                    continue  # already covered

                neg = NegativeKeyword(
                    client_id=client_id,
                    campaign_id=cid,
                    ad_group_id=ag_id,
                    criterion_kind="NEGATIVE",
                    text=text,
                    match_type="EXACT",
                    negative_scope="AD_GROUP" if ag_id else "CAMPAIGN",
                    status="ENABLED",
                    source="LOCAL_ACTION",
                )
                db.add(neg)
                db.flush()
                created_for_this_item.append((loser, neg))

                if ag_id:
                    ag_batch.setdefault((cid, "AD_GROUP", ag_id), []).append((item, neg, loser))
                else:
                    camp_batch.setdefault((cid, "CAMPAIGN", None), []).append((item, neg, loser))

        # Phase 2: flush batches to Google Ads API
        def _push_group(group: tuple, batch: list[tuple], level: str):
            nonlocal applied, failed
            cid, _, ag_id = group
            negs = [n for _, n, _ in batch]
            try:
                if level == "AD_GROUP" and ag_id:
                    ag = db.get(AdGroup, ag_id)
                    if ag:
                        google_ads_service.batch_add_ad_group_negatives(db, ag, negs)
                else:
                    camp = db.get(Campaign, cid)
                    if camp:
                        google_ads_service.batch_add_campaign_negatives(db, camp, negs)

                for itm, neg, loser in batch:
                    applied += 1
                    applied_items.append({
                        "id": itm.id, "entity_name": itm.entity_name,
                        "campaign_name": loser["label"][:60], "status": "success",
                        "estimated_savings_pln": loser["cost_pln"],
                    })
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="ad_group" if level == "AD_GROUP" else "campaign",
                        entity_id=str(ag_id or cid),
                        status="SUCCESS",
                        execution_mode="LIVE",
                        precondition_status="PASSED",
                        action_payload={
                            "action_type": "ADD_NEGATIVE",
                            "params": {"text": neg.text, "match_type": "EXACT", "negative_level": level},
                            "target": {"campaign_id": cid, "ad_group_id": ag_id},
                        },
                        context_json={
                            "source": "scripts", "script_id": self.id,
                            "reason": "duplicate_coverage",
                        },
                    ))
                db.commit()
            except Exception as exc:
                db.rollback()
                for itm, neg, loser in batch:
                    failed += 1
                    errors.append(f"{itm.entity_name} ({loser['label'][:40]}): {exc}")
                    db.add(ActionLog(
                        client_id=client_id,
                        action_type="ADD_NEGATIVE",
                        entity_type="ad_group" if level == "AD_GROUP" else "campaign",
                        entity_id=str(ag_id or cid),
                        status="FAILED",
                        execution_mode="LIVE",
                        precondition_status="PASSED",
                        action_payload={"action_type": "ADD_NEGATIVE", "params": {"text": itm.entity_name}},
                        context_json={"source": "scripts", "script_id": self.id},
                        error_message=str(exc)[:500],
                    ))
                db.commit()

        for group, batch in camp_batch.items():
            _push_group(group, batch, "CAMPAIGN")
        for group, batch in ag_batch.items():
            _push_group(group, batch, "AD_GROUP")

        return ScriptExecuteResult(
            script_id=self.id,
            applied=applied,
            failed=failed,
            errors=errors,
            applied_items=applied_items,
            circuit_breaker_limit=limit_cap,
        )
