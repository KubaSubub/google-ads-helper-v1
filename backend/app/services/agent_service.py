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
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency

logger = logging.getLogger(__name__)


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
}


class AgentService:
    """Orchestrates report generation via Claude Code headless mode."""

    def __init__(self, db: Session, client_id: int):
        self.db = db
        self.client_id = client_id
        self.analytics = AnalyticsService(db)

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
        }
        handler = handlers.get(section)
        if not handler:
            return {"error": f"Unknown section: {section}"}
        return handler()

    # ------------------------------------------------------------------
    # Data gathering methods (delegate to existing services/queries)
    # ------------------------------------------------------------------

    def _get_kpis(self) -> dict:
        """KPIs with period-over-period comparison (7d current vs 7d previous)."""
        today = date.today()
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
        ).all()
        campaign_ids = [c.id for c in campaigns]
        if not campaign_ids:
            return {"current": {}, "previous": {}, "note": "Brak kampanii"}

        def _agg(start: date, end: date) -> dict:
            rows = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            ).all()
            if not rows:
                return {"clicks": 0, "impressions": 0, "cost_usd": 0,
                        "conversions": 0, "ctr": 0, "roas": 0}
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

        current = _agg(today - timedelta(days=7), today)
        previous = _agg(today - timedelta(days=14), today - timedelta(days=8))
        return {"current_7d": current, "previous_7d": previous}

    def _get_campaigns_summary(self) -> list:
        """Active campaigns with basic metrics."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status == "ENABLED",
        ).all()

        today = date.today()
        days_30_ago = today - timedelta(days=30)
        result = []
        for c in campaigns[:30]:  # truncate to 30
            metrics = self.db.query(
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impressions"),
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
            ).filter(
                MetricDaily.campaign_id == c.id,
                MetricDaily.date >= days_30_ago,
            ).first()

            result.append({
                "name": c.name,
                "type": c.campaign_type,
                "status": c.status,
                "daily_budget_usd": round(micros_to_currency(c.budget_micros), 2),
                "role": c.campaign_role_final or c.campaign_role_auto,
                "clicks_30d": metrics.clicks or 0 if metrics else 0,
                "impressions_30d": metrics.impressions or 0 if metrics else 0,
                "cost_30d_usd": round((metrics.cost_micros or 0) / 1_000_000, 2) if metrics else 0,
                "conversions_30d": round(metrics.conversions or 0, 2) if metrics else 0,
            })
        return result

    def _get_campaigns_detail(self) -> list:
        """All campaigns (including paused) with more detail."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status.in_(["ENABLED", "PAUSED"]),
        ).all()

        today = date.today()
        days_30_ago = today - timedelta(days=30)
        result = []
        for c in campaigns[:40]:
            metrics = self.db.query(
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impressions"),
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
                func.sum(MetricDaily.conversion_value_micros).label("conv_value"),
            ).filter(
                MetricDaily.campaign_id == c.id,
                MetricDaily.date >= days_30_ago,
            ).first()

            cost = (metrics.cost_micros or 0) / 1_000_000 if metrics else 0
            conv = metrics.conversions or 0 if metrics else 0
            conv_value = (metrics.conv_value or 0) / 1_000_000 if metrics else 0

            result.append({
                "name": c.name,
                "type": c.campaign_type,
                "status": c.status,
                "bidding_strategy": c.bidding_strategy,
                "daily_budget_usd": round(micros_to_currency(c.budget_micros), 2),
                "role": c.campaign_role_final or c.campaign_role_auto,
                "clicks_30d": metrics.clicks or 0 if metrics else 0,
                "impressions_30d": metrics.impressions or 0 if metrics else 0,
                "cost_30d_usd": round(cost, 2),
                "conversions_30d": round(conv, 2),
                "roas_30d": round(conv_value / cost if cost else 0, 2),
                "cpa_30d": round(cost / conv if conv else 0, 2),
                "impression_share": round((c.search_impression_share or 0) * 100, 1),
            })
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
        """Budget pacing — reuses logic from analytics router."""
        import calendar
        today = date.today()
        month_start = today.replace(day=1)
        days_elapsed = (today - month_start).days + 1
        days_in_month = calendar.monthrange(today.year, today.month)[1]
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
                .filter(MetricDaily.campaign_id == camp.id, MetricDaily.date >= month_start)
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
            "month": today.strftime("%Y-%m"),
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
            "campaigns": results,
        }

    def _get_wasted_spend(self) -> dict:
        """Wasted spend — delegates to AnalyticsService."""
        return self.analytics.get_wasted_spend(self.client_id, days=30)

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
        self, user_message: str, report_type: str = "freeform"
    ) -> AsyncGenerator[str, None]:
        """Invoke claude -p via stdin and stream the response."""
        claude_bin = _find_claude_binary()
        if not claude_bin:
            yield json.dumps({"type": "error", "content": "Claude CLI nie jest zainstalowane lub niedostepne w PATH."})
            return

        data = self.gather_data(report_type)
        prompt = self.build_prompt(data, user_message)

        try:
            process = await asyncio.create_subprocess_exec(
                claude_bin,
                "-p",
                "--output-format", "stream-json",
                "--verbose",
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
            async for raw_line in process.stdout:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                # "assistant" event: contains the full message with text content
                if event_type == "assistant" and "message" in event:
                    msg = event["message"]
                    if isinstance(msg, dict):
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    yield json.dumps({"type": "delta", "content": block["text"]})

                # "result" event: final result text (backup)
                elif event_type == "result":
                    result_text = event.get("result", "")
                    is_error = event.get("is_error", False)
                    if is_error and result_text:
                        yield json.dumps({"type": "error", "content": result_text})
                    # result text is same as assistant content — skip to avoid duplication

            await asyncio.wait_for(process.wait(), timeout=settings.agent_timeout)

        except asyncio.TimeoutError:
            process.kill()
            yield json.dumps({"type": "error", "content": "Timeout — generowanie raportu trwalo zbyt dlugo."})
            return

        if process.returncode != 0:
            stderr = ""
            if process.stderr:
                stderr_bytes = await process.stderr.read()
                stderr = stderr_bytes.decode("utf-8", errors="replace")
            yield json.dumps({"type": "error", "content": f"Claude CLI error (code {process.returncode}): {stderr[:500]}"})


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
