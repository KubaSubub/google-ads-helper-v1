"""Script D3 — N-gram Audit Report (view-only).

Same n-gram aggregation logic as D1, but surfaces the **top N** n-grams
regardless of conversion state, with no negative-keyword action attached.
Useful as a strategic read: "which words dominate my search-term spend,
good or bad, across campaigns?".

Unlike D1 (which filters to zero-conv waste), D3 keeps n-grams with
conversions so the specialist can spot both waste candidates and high-ROI
winners in the same view.
"""

from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.search_term import SearchTerm
from app.services.scripts.base import (
    ACTION_ALERT,
    CATEGORY_NGRAM,
    MATCH_SOURCE_AUDIT,
    ScriptBase,
    ScriptItem,
    ScriptResult,
)
from app.services.scripts.d1_ngram_waste import STOP_WORDS, _generate_ngrams


class NgramAuditReportScript(ScriptBase):
    id = "D3"
    name = "N-gram Audit (raport poglądowy)"
    category = CATEGORY_NGRAM
    description = (
        "Zestawienie top n-gramów w search termach — kliknięcia, koszt, konwersje, "
        "liczba kampanii. Raport bez akcji; służy do analizy wzorców zapytań."
    )
    action_type = ACTION_ALERT
    default_params = {
        "top_n": 20,
        "ngram_size": 2,  # 1, 2, 3 or 4
        "min_term_count": 2,
    }
    # Hard ceiling to keep top_n from exploding memory on huge accounts.
    _TOP_N_MAX = 500

    def dry_run(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
    ) -> ScriptResult:
        p = {**self.default_params, **(params or {})}
        top_n = max(1, min(self._TOP_N_MAX, int(p.get("top_n", 20))))
        ngram_size = int(p.get("ngram_size", 2))
        if ngram_size not in (1, 2, 3, 4):
            ngram_size = 2
        min_term_count = max(1, int(p.get("min_term_count", 2)))

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

        # Dedup by (text, campaign) — the same term showing up in two
        # campaigns must contribute both rows, otherwise n-gram aggregates
        # under-count cost/conv_value.
        per_campaign: dict[tuple, SearchTerm] = {}
        for t in all_terms:
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid is None:
                continue
            key = (t.text.lower().strip(), cid)
            if key not in per_campaign or (t.cost_micros or 0) > (per_campaign[key].cost_micros or 0):
                per_campaign[key] = t

        stats: dict[str, dict] = defaultdict(lambda: {
            "clicks": 0, "cost_micros": 0, "conv": 0.0, "conv_value_micros": 0,
            "terms": set(), "campaign_ids": set(),
        })

        for (text_lower, cid), term in per_campaign.items():
            words = [w for w in text_lower.split() if len(w) >= 3 and w not in STOP_WORDS]
            for ngram in _generate_ngrams(words, ngram_size):
                s = stats[ngram]
                s["clicks"] += term.clicks or 0
                s["cost_micros"] += term.cost_micros or 0
                s["conv"] += term.conversions or 0
                s["conv_value_micros"] += term.conversion_value_micros or 0
                s["terms"].add(text_lower)
                s["campaign_ids"].add(cid)

        rows = [
            (ngram, s) for ngram, s in stats.items()
            if len(s["terms"]) >= min_term_count
        ]
        rows.sort(key=lambda r: -r[1]["cost_micros"])
        rows = rows[:top_n]

        items: list[ScriptItem] = []
        for ngram, s in rows:
            cost_pln = s["cost_micros"] / 1_000_000
            conv_value_pln = s["conv_value_micros"] / 1_000_000
            cpa = (cost_pln / s["conv"]) if s["conv"] else 0.0
            items.append(ScriptItem(
                id=f"{ngram_size}:{ngram}",
                entity_name=ngram,
                campaign_id=None,
                campaign_name=f"{len(s['campaign_ids'])} kamp",
                reason=(
                    f"{len(s['terms'])} termów · {s['clicks']} clk · {cost_pln:.0f} zł · "
                    f"{s['conv']:.1f} konw"
                ),
                metrics={
                    "ngram_size": ngram_size,
                    "term_count": len(s["terms"]),
                    "campaigns_affected": len(s["campaign_ids"]),
                    "clicks": s["clicks"],
                    "cost_pln": round(cost_pln, 2),
                    "conversions": round(s["conv"], 1),
                    "conversion_value_pln": round(conv_value_pln, 2),
                    "cpa_pln": round(cpa, 1),
                },
                estimated_savings_pln=0.0,
                # Non-actionable — tagged `audit` so ScriptsPage routes this
                # into the read-only alert bucket.
                action_payload={"match_source": MATCH_SOURCE_AUDIT, "text": ngram, "ngram_size": ngram_size},
            ))

        return ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=0.0,
        )

    def execute(self, db, client_id, date_from, date_to, params=None, item_ids=None):
        # Audit-only script — no mutation path.
        from app.services.scripts.base import ScriptExecuteResult
        return ScriptExecuteResult(
            script_id=self.id,
            errors=["D3 to raport poglądowy — nie wykonuje akcji."],
        )
