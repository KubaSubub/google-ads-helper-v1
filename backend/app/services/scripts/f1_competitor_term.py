"""Script F1 — Competitor Term Detection (alert-only).

Scans search terms for mentions of competitor brand names declared in
`Client.ai_context.competitors` (or via `custom_competitor_words` param).
The script does NOT auto-negate — competitor terms can be legitimately
converting, so the specialist decides per-term.

Report fields per match: term, campaign, clicks, cost, conversions —
letting the user triage "bleeding money on competitor brand" vs
"great hijack, keep it".
"""

import re
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.search_term import SearchTerm
from app.services.scripts.base import (
    ACTION_ALERT,
    CATEGORY_BRAND,
    MATCH_SOURCE_COMPETITOR,
    ScriptBase,
    ScriptExecuteResult,
    ScriptItem,
    ScriptResult,
)


def _build_competitor_patterns(words: list[str]) -> list[tuple[str, re.Pattern]]:
    """Return (display_word, compiled_pattern) tuples, deduped + length-filtered."""
    seen: set[str] = set()
    out: list[tuple[str, re.Pattern]] = []
    for w in words or []:
        key = (w or "").strip().lower()
        if not key or key in seen or len(key) < 2:
            continue
        seen.add(key)
        out.append((w.strip(), re.compile(r"\b" + re.escape(w.strip()) + r"\b", re.IGNORECASE)))
    return out


class CompetitorTermScript(ScriptBase):
    id = "F1"
    name = "Wyszukiwania pod konkurencję (alert)"
    category = CATEGORY_BRAND
    description = (
        "Wykrywa search termy zawierające nazwy konkurentów — alert do decyzji, "
        "czy zablokować (przepalają budżet) czy zostawić (skuteczny hijack)."
    )
    action_type = ACTION_ALERT
    default_params = {
        "custom_competitor_words": [],
        "min_clicks": 1,
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
        min_clicks = int(p.get("min_clicks", 1))

        client = db.get(Client, client_id)
        if not client:
            return ScriptResult(script_id=self.id, total_matching=0, items=[])

        competitors: list[str] = []
        custom = p.get("custom_competitor_words") or []
        if isinstance(custom, str):
            custom = [c.strip() for c in custom.split(",") if c.strip()]
        if isinstance(custom, list):
            competitors.extend([c for c in custom if isinstance(c, str) and c])

        # Client.competitors is the canonical source (top-level JSON column).
        stored = getattr(client, "competitors", None) or []
        if isinstance(stored, list):
            competitors.extend([c for c in stored if isinstance(c, str) and c])
        elif isinstance(stored, str):
            competitors.extend([c.strip() for c in stored.split(",") if c.strip()])

        patterns = _build_competitor_patterns(competitors)
        if not patterns:
            return ScriptResult(
                script_id=self.id,
                total_matching=0,
                items=[],
                warnings=[
                    "Brak listy konkurentów — dodaj `custom_competitor_words` w params "
                    "lub uzupełnij `Client.ai_context.competitors`."
                ],
            )

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

        camp_map = {c.id: c.name for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()}

        # Dedup by (text, campaign) keeping highest cost window
        seen: dict[tuple, SearchTerm] = {}
        for t in all_terms:
            cid = t.campaign_id
            if cid is None and t.ad_group_id:
                ag = db.get(AdGroup, t.ad_group_id)
                cid = ag.campaign_id if ag else None
            if cid is None:
                continue
            key = (t.text.lower().strip(), cid)
            if key not in seen or (t.cost_micros or 0) > (seen[key].cost_micros or 0):
                seen[key] = t

        items: list[ScriptItem] = []
        for (text_lower, cid), term in seen.items():
            if (term.clicks or 0) < min_clicks:
                continue
            matched = next((label for label, pat in patterns if pat.search(term.text)), None)
            if not matched:
                continue
            cost_pln = (term.cost_micros or 0) / 1_000_000
            items.append(ScriptItem(
                id=term.id,
                entity_name=term.text,
                campaign_id=cid,
                campaign_name=camp_map.get(cid, ""),
                reason=(
                    f"Konkurent: {matched} · {term.clicks or 0} kl · "
                    f"{cost_pln:.0f} zł · {term.conversions or 0:.1f} konw"
                ),
                metrics={
                    "clicks": term.clicks or 0,
                    "impressions": term.impressions or 0,
                    "cost_pln": round(cost_pln, 2),
                    "conversions": round(term.conversions or 0, 1),
                    "matched_competitor": matched,
                },
                estimated_savings_pln=0.0,
                action_payload={
                    "match_source": MATCH_SOURCE_COMPETITOR,
                    "text": term.text,
                    "competitor": matched,
                },
            ))

        items.sort(key=lambda x: -x.metrics["cost_pln"])

        return ScriptResult(
            script_id=self.id,
            total_matching=len(items),
            items=items,
            estimated_savings_pln=0.0,
        )

    def execute(self, db, client_id, date_from, date_to, params=None, item_ids=None):
        # Alert-only — no mutations.
        from app.services.scripts.base import ScriptExecuteResult
        return ScriptExecuteResult(
            script_id=self.id,
            errors=["F1 to alert — decyzję podejmuje specjalista manualnie."],
        )
