"""Script A1 — Zero Conversion Waste.

Identifies search terms that spent money but produced no conversions in the
user-selected lookback window. Adds them as campaign (or ad-group) negatives.

This is the most common daily optimization task for a Google Ads specialist.
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
)
from app.services.scripts.base import (
    ACTION_NEGATIVE,
    CATEGORY_WASTE,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)


class ZeroConvWasteScript(ScriptBase):
    id = "A1"
    name = "Zero konwersji przy wysokim koszcie"
    category = CATEGORY_WASTE
    description = (
        "Wyszukiwane hasła które wygenerowały kliknięcia i koszt ale 0 konwersji "
        "w wybranym okresie — dodaj jako negatywy żeby zatrzymać marnotrawstwo."
    )
    action_type = ACTION_NEGATIVE
    default_params = {
        "min_clicks": 5,
        "min_cost_pln": 20.0,
        "min_impressions": 0,
        "negative_level": "CAMPAIGN",   # CAMPAIGN or AD_GROUP
        "match_type": "PHRASE",         # EXACT / PHRASE / BROAD
        "brand_protection": True,
        "custom_brand_words": [],
        "conversion_lag_days": 7,       # drop windows whose end-date is within N days of today
    }

    # ──────────────────────────────────────────────────────────────────────
    # Core: fetch search terms matching the thresholds.
    # ──────────────────────────────────────────────────────────────────────
    # Why this is non-trivial: the `search_terms` table stores cumulative
    # metrics per sync window (date_from..date_to). A client can have MANY
    # overlapping windows from different sync runs (e.g. 10-day snapshot,
    # 30-day snapshot, 90-day snapshot, 180-day historical). Summing them
    # would double-count. Picking all overlapping rows would return the
    # same result for any date filter — defeating the whole point of the
    # date picker.
    #
    # Our approach: for each (text, campaign_id) group, pick the single
    # sync window whose *length* is closest to the user's range length.
    # Tiebreaker: most recent date_to. This matches user intent —
    # "ostatnie 30 dni" uses the 30-day snapshot, "od początku" uses the
    # longest available window.
    # ──────────────────────────────────────────────────────────────────────
    def _fetch_aggregated_terms(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
    ) -> dict:
        # Search campaigns: join via ad_group
        q1 = (
            db.query(SearchTerm)
            .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
        )
        # PMax: linked directly to campaign
        q2 = (
            db.query(SearchTerm)
            .filter(
                SearchTerm.campaign_id.isnot(None),
                SearchTerm.ad_group_id.is_(None),
            )
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
        )

        # Overlap filter (coarse) — drop rows whose window is entirely
        # outside the user range. We still may have multiple candidates per
        # (text, campaign) which we disambiguate below.
        if date_from:
            q1 = q1.filter(SearchTerm.date_to >= date_from)
            q2 = q2.filter(SearchTerm.date_to >= date_from)
        if date_to:
            q1 = q1.filter(SearchTerm.date_from <= date_to)
            q2 = q2.filter(SearchTerm.date_from <= date_to)

        rows = q1.all() + q2.all()

        # Group candidate rows by (text_lower, campaign_id)
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

        # Pick best-matching window per group
        user_range_days = None
        if date_from and date_to:
            user_range_days = max(1, (date_to - date_from).days)

        agg: dict[tuple, dict] = {}
        for key, candidates in groups.items():
            if user_range_days is not None:
                # Primary: smallest |window_length - user_range|
                # Secondary: most recent date_to (negated for min ordering)
                chosen = min(
                    candidates,
                    key=lambda r: (
                        abs((r.date_to - r.date_from).days - user_range_days),
                        -r.date_to.toordinal(),
                    ),
                )
            else:
                # No user range — use most recent sync window
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

    # ──────────────────────────────────────────────────────────────────────
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
        min_cost_pln = float(p.get("min_cost_pln", 20.0))
        min_impressions = int(p.get("min_impressions", 0))
        min_cost_micros = int(min_cost_pln * 1_000_000)
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

        agg = self._fetch_aggregated_terms(db, client_id, date_from, date_to)

        # Already-excluded set — skip terms already covered by a negative.
        # Key: (text_lower, campaign_id) — same shape as agg keys.
        existing_neg = set()
        neg_rows = (
            db.query(NegativeKeyword.text, NegativeKeyword.campaign_id)
            .filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.status != "REMOVED",
            )
            .all()
        )
        for text, camp_id in neg_rows:
            if text and camp_id is not None:
                existing_neg.add((text.lower().strip(), camp_id))

        # Campaign name lookup
        camp_map = {
            c.id: c.name
            for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()
        }

        items: list[ScriptItem] = []
        total_savings = 0.0
        skipped_recent = 0

        # Conversion lag cutoff — windows that lie ENTIRELY inside the last
        # lag_days are too fresh to trust as zero-conversion. Windows that
        # merely extend into that period (e.g. 30-day snapshot ending today)
        # still carry enough pre-lag data to be decisive, so we surface them
        # but attach a warning instead of silently dropping.
        today = date.today()
        reference_day = date_to if date_to and date_to < today else today
        lag_cutoff = reference_day - timedelta(days=lag_days) if lag_days > 0 else None
        warns_recent_window = 0

        for key, d in agg.items():
            text_lower, campaign_id = key
            # Threshold filter
            if d["conversions"] > 0:
                continue
            if d["clicks"] < min_clicks:
                continue
            if d["cost_micros"] < min_cost_micros:
                continue
            if d["impressions"] < min_impressions:
                continue
            # Skip if already excluded
            if key in existing_neg:
                continue

            # Conversion lag guard: only drop rows whose ENTIRE sync window
            # falls inside the lag period. Rows with a longer window that
            # merely touch the lag period are kept — the bulk of their data
            # is old enough to trust.
            window_from = d.get("window_from")
            window_to = d.get("window_to")
            if lag_cutoff is not None and window_from is not None:
                if window_from > lag_cutoff:
                    skipped_recent += 1
                    continue
                if window_to is not None and window_to > lag_cutoff:
                    warns_recent_window += 1

            # Brand protection
            if brand_protection and _is_brand_term(d["text"], brand_patterns):
                continue

            # Keyword protection — would a negative kill an active keyword?
            camp_keywords = kws_per_camp.get(campaign_id, set())
            kw_conflict = _check_keyword_conflict(text_lower, camp_keywords)
            if kw_conflict == "BLOCK":
                continue
            effective_match = "EXACT" if kw_conflict == "EXACT" else p["match_type"]
            kw_note = " [EXACT — ochrona keywordu]" if kw_conflict == "EXACT" else ""

            cost_pln = d["cost_micros"] / 1_000_000
            total_savings += cost_pln
            ctr = (d["clicks"] / d["impressions"] * 100) if d["impressions"] else 0.0

            items.append(
                ScriptItem(
                    id=d["term_id"],
                    entity_name=d["text"],
                    campaign_id=d["campaign_id"],
                    campaign_name=camp_map.get(d["campaign_id"], ""),
                    reason=(
                        f"{d['clicks']} kliknięć · 0 konwersji · koszt ~{cost_pln:.0f} zł{kw_note}"
                    ),
                    metrics={
                        "clicks": d["clicks"],
                        "impressions": d["impressions"],
                        "cost_pln": round(cost_pln, 2),
                        "conversions": round(d["conversions"], 1),
                        "ctr": round(ctr, 2),
                    },
                    estimated_savings_pln=round(cost_pln, 2),
                    action_payload={
                        "text": d["text"],
                        "campaign_id": d["campaign_id"],
                        "ad_group_id": d["ad_group_id"],
                        "negative_level": p["negative_level"],
                        "match_type": effective_match,
                    },
                )
            )

        # Sort by savings descending — user sees biggest wins first
        items.sort(key=lambda x: x.estimated_savings_pln, reverse=True)

        warnings: list[str] = []
        if skipped_recent:
            warnings.append(
                f"Pominięto {skipped_recent} term(ów) z oknem w całości w ostatnich {lag_days} dniach — "
                "conversion lag może zniekształcić 'zero konwersji'."
            )
        if warns_recent_window:
            warnings.append(
                f"{warns_recent_window} flagowanych termów ma okno sięgające ostatnich {lag_days} dni — "
                "część danych może jeszcze nie uwzględniać konwersji."
            )

        return ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=round(total_savings, 2),
            warnings=warnings,
        )

    # ──────────────────────────────────────────────────────────────────────
    def execute(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
        item_ids: Optional[list] = None,
    ) -> ScriptExecuteResult:
        """Apply negatives: write to DB → push to Google Ads API → log in ActionHistory.

        HARD REQUIREMENT: Google Ads API must be connected. No LOCAL_ONLY mode —
        writing to local DB without pushing to Google creates ghost state where
        the app thinks negatives exist but the account doesn't have them.
        """
        from app.models.action_log import ActionLog
        from app.services.google_ads import google_ads_service

        if not google_ads_service.is_connected:
            return ScriptExecuteResult(
                script_id=self.id,
                applied=0,
                failed=0,
                errors=["Google Ads API nie jest połączone. Nie można wykonać skryptu — "
                        "zmiany muszą trafić na konto Google Ads, nie tylko do lokalnej bazy."],
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

        # Phase 1: create NegativeKeyword rows in DB, group by (campaign_id, level)
        groups: dict[tuple, list[tuple]] = {}  # (campaign_id, level, ag_id) -> [(item, neg)]

        for item in items_to_apply:
            ap = item.action_payload
            neg_level = ap.get("negative_level", "CAMPAIGN")
            match_type = ap.get("match_type", "PHRASE")
            campaign_id = ap["campaign_id"]
            ad_group_id = ap.get("ad_group_id") if neg_level == "AD_GROUP" else None

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
                negative_scope="AD_GROUP" if neg_level == "AD_GROUP" else "CAMPAIGN",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg)
            db.flush()

            group_key = (campaign_id, neg_level, ad_group_id)
            groups.setdefault(group_key, []).append((item, neg))

        # Phase 2: batch push to Google Ads API (always LIVE — checked above)
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
                        entity_type="campaign" if level == "CAMPAIGN" else "ad_group",
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
                        entity_type="campaign" if level == "CAMPAIGN" else "ad_group",
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
