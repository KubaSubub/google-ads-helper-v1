"""Agent Service — report generation via Claude Code headless mode.

Gathers data from existing services, builds a rich prompt,
and invokes `claude -p` as a subprocess to generate reports.
"""

import asyncio
import json
import logging
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.keyword_daily import KeywordDaily
from app.models.metric_daily import MetricDaily
from app.models.recommendation import Recommendation
from app.models.search_term import SearchTerm
from app.models.ad_group import AdGroup
from app.models.change_event import ChangeEvent
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency

logger = logging.getLogger(__name__)


def _parse_changed_fields(raw) -> list:
    """Parse changed_fields from DB — may be JSON string or already a list."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _find_claude_binary() -> str | None:
    """Find the claude CLI binary, accounting for Windows .cmd wrappers."""
    # 1. Try shutil.which (respects PATH + PATHEXT on Windows)
    found = shutil.which("claude")
    if found:
        return found

    # 2. Common npm global install locations on Windows
    if sys.platform == "win32":
        candidates = [
            Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
            Path.home() / "AppData" / "Roaming" / "npm" / "claude",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    return None

SYSTEM_PROMPT = """\
Jestes ekspertem Google Ads analizujacym dane klienta.

ZASADY:
- Dane sa dostarczone ponizej w formacie JSON — analizuj TYLKO te dane.
- Nigdy nie zmyslaj metryk ani danych.
- Odpowiadaj po polsku.
- Formatuj raporty w markdown: uzyj tabel, podgrubien, list.
- Kwoty podawaj w walucie klienta (PLN/USD) z dokladnoscia do 2 miejsc po przecinku.
- Procenty podawaj z 1 miejscem po przecinku.
- Jesli dane sa puste lub brak danych — poinformuj jasno zamiast zmyslac.
- Zakonczenie raportu: podaj 3-5 konkretnych rekomendacji dzialania.
"""

# Maps report_type -> which data sections to gather
REPORT_DATA_MAP = {
    "weekly": ["kpis", "campaigns", "alerts", "recommendations", "health"],
    "campaigns": ["campaigns_detail", "budget_pacing"],
    "keywords": ["keywords"],
    "search_terms": ["search_terms"],
    "budget": ["budget_pacing", "wasted_spend"],
    "alerts": ["alerts", "health"],
    "freeform": ["kpis", "campaigns", "alerts"],
    "monthly": [
        "month_comparison", "campaigns_detail", "change_history",
        "change_impact", "budget_pacing", "wasted_spend", "alerts", "health",
    ],
}

MONTHLY_PROMPT = """\
Przygotuj kompletny raport miesieczny Google Ads.

STRUKTURA DANYCH (nie duplikuj, nie sumuj ponownie):
- `month_comparison` = zagregowane KPI calego konta (current vs previous) — to jest zrodlo prawdy dla sumarycznych metryk
- `campaigns_detail` = metryki per kampania z deltami vs poprzedni okres — NIE sumuj tych wartosci, sa juz zagregowane w month_comparison
- `change_history` = podsumowanie zmian na koncie
- `change_impact` = analiza before/after dla zmian budzetu/biddingu
- `budget_pacing` = realizacja budzetow
- `wasted_spend` = zmarnowane wydatki
- `alerts` + `health` = aktywne alerty i health score

SEKCJE RAPORTU:
1. Podsumowanie KPI — uzyj TYLKO danych z `month_comparison`, podaj delty procentowe
2. Analiza kampanii — uzyj `campaigns_detail`, skup sie na kampaniach z najwiekszymi zmianami
3. Wplyw zmian — uzyj `change_impact`, opisz co sie zmienilo i jaki mial wplyw
4. Budzety — uzyj `budget_pacing`, wskaz under/overspend
5. Rekomendacje — 5 konkretnych dzialan priorytetyzowanych wg potencjalnego wplywu

WAZNE: Kazda metryka pojawia sie DOKLADNIE raz. Nie podawaj tych samych liczb w roznych sekcjach.\
"""


class AgentService:
    """Orchestrates report generation via Claude Code headless mode."""

    def __init__(self, db: Session, client_id: int):
        self.db = db
        self.client_id = client_id
        self.analytics = AnalyticsService(db)
        self._period_start: date | None = None
        self._period_end: date | None = None

    def _date_window(self, default_days: int = 30) -> tuple[date, date]:
        """Return (start, end) date window — uses period if set, else last N days."""
        if self._period_start and self._period_end:
            return self._period_start, self._period_end
        today = date.today()
        return today - timedelta(days=default_days - 1), today

    def gather_data_for_month(self, year: int, month: int) -> dict:
        """Set period to a full calendar month, then gather monthly data."""
        import calendar as cal
        self._period_start = date(year, month, 1)
        last_day = cal.monthrange(year, month)[1]
        self._period_end = date(year, month, last_day)
        return self.gather_data("monthly")

    def gather_data(self, report_type: str) -> dict:
        """Collect data from existing services based on report type."""
        sections = REPORT_DATA_MAP.get(report_type, REPORT_DATA_MAP["freeform"])
        data = {}

        for section in sections:
            try:
                data[section] = self._gather_section(section)
            except Exception as exc:
                logger.warning("Failed to gather section %s: %s", section, exc)
                data[section] = {"error": str(exc)}

        return data

    def _gather_section(self, section: str) -> dict:
        """Dispatch to the appropriate data-gathering method."""
        handlers = {
            "kpis": self._get_kpis,
            "campaigns": self._get_campaigns_summary,
            "campaigns_detail": self._get_campaigns_detail,
            "alerts": self._get_alerts,
            "recommendations": self._get_recommendations,
            "health": self._get_health,
            "keywords": self._get_keywords,
            "search_terms": self._get_search_terms,
            "budget_pacing": self._get_budget_pacing,
            "wasted_spend": self._get_wasted_spend,
            "change_history": self._get_change_history,
            "month_comparison": self._get_month_comparison,
            "change_impact": self._get_change_impact,
        }
        handler = handlers.get(section)
        if not handler:
            return {"error": f"Unknown section: {section}"}
        return handler()

    # ------------------------------------------------------------------
    # Data gathering methods (delegate to existing services/queries)
    # ------------------------------------------------------------------

    def _agg_metrics(self, campaign_ids: list[int], start: date, end: date) -> dict:
        """Aggregate MetricDaily for given campaigns and date range."""
        rows = self.db.query(MetricDaily).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= start,
            MetricDaily.date <= end,
        ).all()
        if not rows:
            return {"clicks": 0, "impressions": 0, "cost_usd": 0,
                    "conversions": 0, "ctr": 0, "cpa": 0, "roas": 0}
        clicks = sum(r.clicks or 0 for r in rows)
        impressions = sum(r.impressions or 0 for r in rows)
        cost = sum(r.cost_micros or 0 for r in rows) / 1_000_000
        conversions = sum(r.conversions or 0 for r in rows)
        conv_value = sum(r.conversion_value_micros or 0 for r in rows) / 1_000_000
        return {
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": round(cost, 2),
            "conversions": round(conversions, 2),
            "ctr": round(clicks / impressions * 100 if impressions else 0, 2),
            "cpa": round(cost / conversions if conversions else 0, 2),
            "roas": round(conv_value / cost if cost else 0, 2),
        }

    def _get_campaign_ids(self) -> list[int]:
        """Get all campaign IDs for the current client."""
        return [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
        ).all()]

    def _get_kpis(self) -> dict:
        """KPIs with period-over-period comparison."""
        campaign_ids = self._get_campaign_ids()
        if not campaign_ids:
            return {"current": {}, "previous": {}, "note": "Brak kampanii"}

        window_start, window_end = self._date_window(7)
        window_days = (window_end - window_start).days + 1
        prev_end = window_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=window_days - 1)

        current = self._agg_metrics(campaign_ids, window_start, window_end)
        previous = self._agg_metrics(campaign_ids, prev_start, prev_end)
        period_label = f"{window_days}d"
        return {
            f"current_{period_label}": current,
            f"previous_{period_label}": previous,
            "period_days": window_days,
        }

    def _get_campaigns_summary(self) -> list:
        """Active campaigns with basic metrics."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status == "ENABLED",
        ).limit(30).all()

        if not campaigns:
            return []

        today = date.today()
        days_30_ago = today - timedelta(days=30)
        campaign_ids = [c.id for c in campaigns]

        metrics_rows = self.db.query(
            MetricDaily.campaign_id,
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
        ).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= days_30_ago,
        ).group_by(MetricDaily.campaign_id).all()

        metrics_map = {row.campaign_id: row for row in metrics_rows}

        result = []
        for c in campaigns:
            m = metrics_map.get(c.id)
            result.append({
                "name": c.name,
                "type": c.campaign_type,
                "status": c.status,
                "daily_budget_usd": round(micros_to_currency(c.budget_micros), 2),
                "role": c.campaign_role_final or c.campaign_role_auto,
                "clicks_30d": (m.clicks or 0) if m else 0,
                "impressions_30d": (m.impressions or 0) if m else 0,
                "cost_30d_usd": round((m.cost_micros or 0) / 1_000_000, 2) if m else 0,
                "conversions_30d": round((m.conversions or 0), 2) if m else 0,
            })
        return result

    def _get_campaigns_detail(self) -> list:
        """All campaigns (including paused) with metrics + optional prev-period comparison."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status.in_(["ENABLED", "PAUSED"]),
        ).limit(40).all()

        if not campaigns:
            return []

        window_start, window_end = self._date_window(30)
        campaign_ids = [c.id for c in campaigns]

        # Current period — single grouped query
        metrics_rows = self.db.query(
            MetricDaily.campaign_id,
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("conv_value"),
        ).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= window_start,
            MetricDaily.date <= window_end,
        ).group_by(MetricDaily.campaign_id).all()

        metrics_map = {row.campaign_id: row for row in metrics_rows}

        # Previous period — single grouped query (for monthly reports)
        prev_map = {}
        if self._period_start and self._period_end:
            period_days = (window_end - window_start).days + 1
            prev_end = window_start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days - 1)

            prev_rows = self.db.query(
                MetricDaily.campaign_id,
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
                func.sum(MetricDaily.conversion_value_micros).label("conv_value"),
            ).filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= prev_start,
                MetricDaily.date <= prev_end,
            ).group_by(MetricDaily.campaign_id).all()

            prev_map = {row.campaign_id: row for row in prev_rows}

        def _delta_pct(curr_val, prev_val):
            if not prev_val:
                return None
            return round((curr_val - prev_val) / abs(prev_val) * 100, 1)

        result = []
        for c in campaigns:
            m = metrics_map.get(c.id)
            cost = (m.cost_micros or 0) / 1_000_000 if m else 0
            conv = (m.conversions or 0) if m else 0
            conv_value = (m.conv_value or 0) / 1_000_000 if m else 0

            entry = {
                "name": c.name,
                "type": c.campaign_type,
                "status": c.status,
                "bidding_strategy": c.bidding_strategy,
                "daily_budget_usd": round(micros_to_currency(c.budget_micros), 2),
                "role": c.campaign_role_final or c.campaign_role_auto,
                "clicks": (m.clicks or 0) if m else 0,
                "impressions": (m.impressions or 0) if m else 0,
                "cost_usd": round(cost, 2),
                "conversions": round(conv, 2),
                "roas": round(conv_value / cost if cost else 0, 2),
                "cpa": round(cost / conv if conv else 0, 2),
                "impression_share": round((c.search_impression_share or 0) * 100, 1),
            }

            # Add prev-period comparison if available
            p = prev_map.get(c.id)
            if p is not None:
                prev_cost = (p.cost_micros or 0) / 1_000_000
                prev_conv = (p.conversions or 0)
                prev_conv_val = (p.conv_value or 0) / 1_000_000
                entry["prev_cost_usd"] = round(prev_cost, 2)
                entry["prev_conversions"] = round(prev_conv, 2)
                entry["cost_delta_pct"] = _delta_pct(cost, prev_cost)
                entry["conv_delta_pct"] = _delta_pct(conv, prev_conv)
                prev_roas = round(prev_conv_val / prev_cost if prev_cost else 0, 2)
                entry["prev_roas"] = prev_roas
                entry["roas_delta_pct"] = _delta_pct(entry["roas"], prev_roas)

            result.append(entry)
        return result

    def _get_alerts(self) -> list:
        """Unresolved alerts."""
        alerts = self.db.query(Alert).filter(
            Alert.client_id == self.client_id,
            Alert.resolved_at.is_(None),
        ).order_by(Alert.created_at.desc()).limit(20).all()

        return [
            {
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in alerts
        ]

    def _get_recommendations(self) -> list:
        """Top pending recommendations."""
        recs = self.db.query(Recommendation).filter(
            Recommendation.client_id == self.client_id,
            Recommendation.status == "pending",
        ).order_by(Recommendation.score.desc().nullslast()).limit(10).all()

        return [
            {
                "rule": r.rule_id,
                "priority": r.priority,
                "entity_name": r.entity_name,
                "reason": r.reason,
                "action": r.suggested_action,
                "score": round(r.score, 2) if r.score else None,
                "executable": r.executable,
            }
            for r in recs
        ]

    def _get_health(self) -> dict:
        """Account health score."""
        return self.analytics.get_health_score(self.client_id)

    def _get_keywords(self) -> list:
        """Top 50 keywords by cost (last 30 days)."""
        today = date.today()
        days_30_ago = today - timedelta(days=30)

        campaign_ids = [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
        ).all()]
        if not campaign_ids:
            return []

        ag_ids = [ag.id for ag in self.db.query(AdGroup).filter(
            AdGroup.campaign_id.in_(campaign_ids),
        ).all()]
        if not ag_ids:
            return []

        keywords = self.db.query(Keyword).filter(
            Keyword.ad_group_id.in_(ag_ids),
            Keyword.status != "REMOVED",
        ).all()
        kw_map = {kw.id: kw for kw in keywords}
        kw_ids = list(kw_map.keys())
        if not kw_ids:
            return []

        daily = (
            self.db.query(
                KeywordDaily.keyword_id,
                func.sum(KeywordDaily.clicks).label("clicks"),
                func.sum(KeywordDaily.impressions).label("impressions"),
                func.sum(KeywordDaily.cost_micros).label("cost_micros"),
                func.sum(KeywordDaily.conversions).label("conversions"),
            )
            .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= days_30_ago)
            .group_by(KeywordDaily.keyword_id)
            .all()
        )

        result = []
        for row in daily:
            kw = kw_map.get(row.keyword_id)
            if not kw:
                continue
            cost = (row.cost_micros or 0) / 1_000_000
            conv = row.conversions or 0
            result.append({
                "text": kw.text,
                "match_type": kw.match_type,
                "status": kw.status,
                "quality_score": kw.quality_score,
                "clicks": row.clicks or 0,
                "impressions": row.impressions or 0,
                "cost_usd": round(cost, 2),
                "conversions": round(conv, 2),
                "cpa": round(cost / conv if conv else 0, 2),
            })

        result.sort(key=lambda x: x["cost_usd"], reverse=True)
        return result[:50]

    def _get_search_terms(self) -> list:
        """Top 50 search terms by cost."""
        campaign_ids = [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
        ).all()]
        if not campaign_ids:
            return []

        from sqlalchemy import or_
        terms = (
            self.db.query(SearchTerm)
            .outerjoin(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .filter(
                or_(
                    SearchTerm.campaign_id.in_(campaign_ids),
                    AdGroup.campaign_id.in_(campaign_ids),
                ),
            )
            .all()
        )

        result = []
        for t in terms:
            cost = (t.cost_micros or 0) / 1_000_000
            result.append({
                "text": t.text,
                "clicks": t.clicks or 0,
                "impressions": t.impressions or 0,
                "cost_usd": round(cost, 2),
                "conversions": round(t.conversions or 0, 2),
                "segment": t.segment,
            })

        result.sort(key=lambda x: x["cost_usd"], reverse=True)
        return result[:50]

    def _get_budget_pacing(self) -> dict:
        """Budget pacing — calculates within a single calendar month."""
        import calendar as cal
        window_start, _window_end = self._date_window(30)
        # Determine which month to report on
        report_month = window_start.replace(day=1)
        report_year, report_mo = report_month.year, report_month.month
        days_in_month = cal.monthrange(report_year, report_mo)[1]
        month_end = date(report_year, report_mo, days_in_month)

        today = date.today()
        if today >= month_end:
            # Past month — use full month
            days_elapsed = days_in_month
        elif today >= report_month:
            # Current month — days so far
            days_elapsed = (today - report_month).days + 1
        else:
            # Future month (shouldn't happen) — full month
            days_elapsed = days_in_month
        pacing_ratio = days_elapsed / days_in_month

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status == "ENABLED",
        ).all()

        results = []
        for camp in campaigns[:30]:
            budget_monthly = micros_to_currency(camp.budget_micros) * days_in_month
            actual_micros = (
                self.db.query(func.sum(MetricDaily.cost_micros))
                .filter(
                    MetricDaily.campaign_id == camp.id,
                    MetricDaily.date >= report_month,
                    MetricDaily.date <= month_end,
                )
                .scalar()
            ) or 0
            actual = micros_to_currency(actual_micros)
            expected = budget_monthly * pacing_ratio

            if expected == 0:
                status = "no_data"
                pct = 0
            else:
                pct = actual / expected
                status = "underspend" if pct < 0.8 else ("overspend" if pct > 1.15 else "on_track")

            results.append({
                "campaign": camp.name,
                "daily_budget_usd": round(micros_to_currency(camp.budget_micros), 2),
                "actual_spend_usd": round(actual, 2),
                "expected_spend_usd": round(expected, 2),
                "pacing_pct": round(pct * 100, 1),
                "status": status,
            })

        return {
            "month": report_month.strftime("%Y-%m"),
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
            "campaigns": results,
        }

    def _get_wasted_spend(self) -> dict:
        """Wasted spend — delegates to AnalyticsService."""
        window_start, window_end = self._date_window(30)
        days = (window_end - window_start).days + 1
        return self.analytics.get_wasted_spend(self.client_id, days=days)

    # ------------------------------------------------------------------
    # Monthly report sections
    # ------------------------------------------------------------------

    def _get_change_history(self) -> dict:
        """Summarize ChangeEvents for the report period."""
        window_start, window_end = self._date_window(30)
        from datetime import datetime as dt

        events = self.db.query(ChangeEvent).filter(
            ChangeEvent.client_id == self.client_id,
            ChangeEvent.change_date_time >= dt.combine(window_start, dt.min.time()),
            ChangeEvent.change_date_time <= dt.combine(window_end, dt.max.time()),
        ).all()

        if not events:
            return {"total_changes": 0, "note": "Brak zmian w okresie"}

        by_resource_type: dict[str, int] = {}
        by_operation: dict[str, int] = {}
        by_source: dict[str, int] = {}
        user_counts: dict[str, int] = {}

        for e in events:
            rt = e.change_resource_type or "UNKNOWN"
            by_resource_type[rt] = by_resource_type.get(rt, 0) + 1
            op = e.resource_change_operation or "UNKNOWN"
            by_operation[op] = by_operation.get(op, 0) + 1
            src = e.client_type or "UNKNOWN"
            by_source[src] = by_source.get(src, 0) + 1
            if e.user_email:
                user_counts[e.user_email] = user_counts.get(e.user_email, 0) + 1

        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        notable = []
        sorted_events = sorted(events, key=lambda e: str(e.change_date_time or ""), reverse=True)
        for e in sorted_events[:20]:
            notable.append({
                "date": str(e.change_date_time)[:16] if e.change_date_time else None,
                "type": e.change_resource_type,
                "name": e.entity_name or e.campaign_name or "",
                "operation": e.resource_change_operation,
                "fields": _parse_changed_fields(e.changed_fields)[:5],
            })

        return {
            "total_changes": len(events),
            "by_resource_type": by_resource_type,
            "by_operation": by_operation,
            "by_source": by_source,
            "top_users": [{"email": email, "count": cnt} for email, cnt in top_users],
            "notable": notable,
        }

    def _get_month_comparison(self) -> dict:
        """Aggregated account-level KPIs: current period vs previous, with deltas."""
        campaign_ids = self._get_campaign_ids()
        if not campaign_ids:
            return {"note": "Brak kampanii"}

        curr_start, curr_end = self._date_window(30)
        period_days = (curr_end - curr_start).days + 1
        prev_end = curr_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)

        current = self._agg_metrics(campaign_ids, curr_start, curr_end)
        previous = self._agg_metrics(campaign_ids, prev_start, prev_end)

        def _delta_pct(curr_val, prev_val):
            if not prev_val:
                return None
            return round((curr_val - prev_val) / abs(prev_val) * 100, 1)

        deltas = {}
        for key in ["clicks", "impressions", "cost_usd", "conversions", "ctr", "cpa", "roas"]:
            deltas[f"{key}_pct"] = _delta_pct(current.get(key, 0), previous.get(key, 0))

        return {
            "period": {"label": f"{curr_start} — {curr_end}", "date_from": str(curr_start), "date_to": str(curr_end)},
            "previous_period": {"label": f"{prev_start} — {prev_end}", "date_from": str(prev_start), "date_to": str(prev_end)},
            "current": current,
            "previous": previous,
            "deltas": deltas,
        }

    def _get_change_impact(self) -> list:
        """Analyze before/after metrics for significant account changes."""
        window_start, window_end = self._date_window(30)
        from datetime import datetime as dt

        # Find campaign-level UPDATE changes with budget/bidding fields
        events = self.db.query(ChangeEvent).filter(
            ChangeEvent.client_id == self.client_id,
            ChangeEvent.change_resource_type == "CAMPAIGN",
            ChangeEvent.resource_change_operation == "UPDATE",
            ChangeEvent.change_date_time >= dt.combine(window_start, dt.min.time()),
            ChangeEvent.change_date_time <= dt.combine(window_end, dt.max.time()),
        ).order_by(ChangeEvent.change_date_time.desc()).all()

        budget_bidding_fields = {
            "campaign_budget", "budget", "bidding_strategy", "target_cpa",
            "target_roas", "maximize_conversions", "maximize_conversion_value",
            "manual_cpc", "status",
        }

        results = []
        campaign_map = {c.id: c for c in self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
        ).all()}

        for e in events:
            fields_list = _parse_changed_fields(e.changed_fields)
            if not fields_list:
                continue

            # Check if any changed field is budget/bidding related
            relevant_fields = [f for f in fields_list
                               if any(bf in f.lower() for bf in budget_bidding_fields)]
            if not relevant_fields:
                continue

            change_date = e.change_date_time.date() if e.change_date_time else None
            if not change_date:
                continue

            # Need 7 days before and after — allow pre-period data as baseline
            before_start = change_date - timedelta(days=7)
            after_end = change_date + timedelta(days=7)
            today = date.today()
            if after_end > today:
                after_end = today
            # Need at least 2 days of "after" data for meaningful comparison
            if (after_end - change_date).days < 2:
                continue

            # Find the campaign
            campaign = None
            if e.entity_id:
                for cid, c in campaign_map.items():
                    if str(c.google_campaign_id) == str(e.entity_id) or str(cid) == str(e.entity_id):
                        campaign = c
                        break
            if not campaign:
                continue

            before = self._agg_metrics([campaign.id], before_start, change_date - timedelta(days=1))
            after = self._agg_metrics([campaign.id], change_date, after_end)

            # Build impact summary
            impact_parts = []
            if before["cpa"] and after["cpa"]:
                cpa_delta = round((after["cpa"] - before["cpa"]) / before["cpa"] * 100, 1)
                impact_parts.append(f"CPA {'+' if cpa_delta > 0 else ''}{cpa_delta}%")
            if before["conversions"] and after["conversions"]:
                conv_delta = round((after["conversions"] - before["conversions"]) / before["conversions"] * 100, 1)
                impact_parts.append(f"konwersje {'+' if conv_delta > 0 else ''}{conv_delta}%")

            # Determine change type
            change_type = "other"
            fields_lower = " ".join(relevant_fields).lower()
            if "budget" in fields_lower:
                change_type = "budget_change"
            elif "bidding" in fields_lower or "target" in fields_lower:
                change_type = "bidding_change"
            elif "status" in fields_lower:
                change_type = "status_change"

            results.append({
                "change_date": str(change_date),
                "entity_name": e.entity_name or e.campaign_name or campaign.name,
                "change_type": change_type,
                "changed_fields": relevant_fields[:5],
                "before_7d": before,
                "after_7d": after,
                "impact_summary": ", ".join(impact_parts) if impact_parts else "brak danych do porownania",
            })

            if len(results) >= 10:
                break

        return results

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_prompt(self, data: dict, user_message: str) -> str:
        """Build the full prompt: system instructions + data context + user question."""
        data_json = json.dumps(data, ensure_ascii=False, default=str, indent=2)

        # Truncate if too long (keep under ~40K chars)
        if len(data_json) > 40_000:
            data_json = data_json[:40_000] + "\n... (dane skrocone)"

        return f"""{SYSTEM_PROMPT}

## DANE KLIENTA (JSON)

{data_json}

## ZAPYTANIE UZYTKOWNIKA

{user_message}
"""

    # ------------------------------------------------------------------
    # Report generation via Claude Code headless
    # ------------------------------------------------------------------

    async def generate_report(
        self, user_message: str, report_type: str = "freeform",
        pre_gathered_data: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """Invoke claude -p via stdin and stream the response.

        If pre_gathered_data is provided, skip data gathering (avoids double queries).
        """
        claude_bin = _find_claude_binary()
        if not claude_bin:
            yield json.dumps({"type": "error", "content": "Claude CLI nie jest zainstalowane lub niedostepne w PATH."})
            return

        data = pre_gathered_data if pre_gathered_data is not None else self.gather_data(report_type)
        prompt = self.build_prompt(data, user_message)

        try:
            process = await asyncio.create_subprocess_exec(
                claude_bin,
                "-p",
                "--verbose",
                "--output-format", "stream-json",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            yield json.dumps({"type": "error", "content": "Claude CLI nie jest zainstalowane lub niedostepne w PATH."})
            return

        # Send prompt via stdin (avoids Windows command line length limit)
        process.stdin.write(prompt.encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()

        try:
            while True:
                try:
                    raw_line = await asyncio.wait_for(
                        process.stdout.readline(), timeout=settings.agent_timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    yield json.dumps({"type": "error", "content": "Timeout — generowanie raportu trwalo zbyt dlugo."})
                    return

                if not raw_line:
                    break

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                # "system" init event: extract model name
                if event_type == "system":
                    model_name = event.get("model", "")
                    if model_name:
                        yield json.dumps({"type": "model", "content": model_name})
                    continue

                # "content_block_delta" event: streaming text chunks
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield json.dumps({"type": "delta", "content": text})
                    continue

                # "assistant" event: contains the full message with text content
                if event_type == "assistant" and "message" in event:
                    msg = event["message"]
                    if isinstance(msg, dict):
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    yield json.dumps({"type": "delta", "content": block["text"]})

                # "result" event: final result with usage stats
                elif event_type == "result":
                    result_text = event.get("result", "")
                    is_error = event.get("is_error", False)
                    if is_error and result_text:
                        yield json.dumps({"type": "error", "content": result_text})

                    # Extract token usage
                    usage = event.get("usage", {})
                    model_usage = event.get("modelUsage", {})
                    yield json.dumps({"type": "usage", "content": {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                        "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
                        "total_cost_usd": event.get("total_cost_usd", 0),
                        "duration_ms": event.get("duration_ms", 0),
                        "model_usage": model_usage,
                    }})

            await asyncio.wait_for(process.wait(), timeout=10)

        except asyncio.TimeoutError:
            process.kill()
            yield json.dumps({"type": "error", "content": "Timeout — proces Claude CLI nie zakonczyl sie poprawnie."})
            return

        if process.returncode != 0:
            stderr_text = ""
            if process.stderr:
                stderr_bytes = await process.stderr.read()
                stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                logger.error("Claude CLI stderr (kod %d): %s", process.returncode, stderr_text[:500])
            detail = stderr_text[:300] if stderr_text else f"kod {process.returncode}"
            yield json.dumps({"type": "error", "content": f"Claude CLI error: {detail}"})


async def check_claude_available() -> dict:
    """Check if claude CLI is installed and accessible."""
    claude_bin = _find_claude_binary()
    if not claude_bin:
        return {"available": False, "reason": "Claude CLI nie znaleziono w PATH ani w domyslnych lokalizacjach"}

    try:
        process = await asyncio.create_subprocess_exec(
            claude_bin, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        version = stdout.decode("utf-8", errors="replace").strip()
        return {"available": True, "version": version}
    except FileNotFoundError:
        return {"available": False, "reason": "Claude CLI nie znaleziono w PATH"}
    except asyncio.TimeoutError:
        return {"available": False, "reason": "Timeout sprawdzania claude CLI"}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
