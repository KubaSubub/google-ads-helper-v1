"""Pareto, scaling opportunities, change impact, keyword overlap.

Mixin for AnalyticsService. Requires self.db (from AnalyticsBase) and shared
helpers (_filter_campaigns, _filter_campaign_ids, _aggregate_metric_daily,
_create_alert). Do not instantiate directly.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
import random

from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.alert import Alert
from app.models.metric_daily import MetricDaily
from app.models.metric_segmented import MetricSegmented
from app.models.asset_group import AssetGroup
from app.models.asset_group_daily import AssetGroupDaily
from app.models.asset_group_asset import AssetGroupAsset
from app.models.asset_group_signal import AssetGroupSignal
from app.models.campaign_audience import CampaignAudienceMetric
from app.models.campaign_asset import CampaignAsset
from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.search_term import SearchTerm
from app.models.keyword_daily import KeywordDaily
from app.utils.formatters import micros_to_currency
from loguru import logger


class InsightsMixin:
    def get_pareto_analysis(self, client_id: int, days: int = 30,
                            date_from: date | None = None, date_to: date | None = None,
                            campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Pareto 80/20 analysis — which campaigns/keywords generate 80% of value."""
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"campaign_pareto": {"total_campaigns": 0, "top_campaigns_for_80pct": 0, "items": []}, "summary": {}}

        # Campaign-level Pareto
        campaign_metrics = (
            self.db.query(
                MetricDaily.campaign_id,
                func.sum(MetricDaily.cost_micros).label("cost"),
                func.sum(MetricDaily.conversions).label("conv"),
                func.sum(MetricDaily.conversion_value_micros).label("value"),
            )
            .filter(MetricDaily.campaign_id.in_(campaign_ids), MetricDaily.date >= date_from, MetricDaily.date <= date_to)
            .group_by(MetricDaily.campaign_id)
            .all()
        )

        campaign_map = {c.id: c.name for c in self.db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).all()}
        items = []
        for row in campaign_metrics:
            items.append({
                "campaign_id": row.campaign_id,
                "name": campaign_map.get(row.campaign_id, "?"),
                "cost_usd": round((row.cost or 0) / 1_000_000, 2),
                "conversions": round(float(row.conv or 0), 2),
                "conv_value_usd": round((row.value or 0) / 1_000_000, 2),
            })

        total_value = sum(i["conv_value_usd"] for i in items)
        items.sort(key=lambda x: x["conv_value_usd"], reverse=True)

        cumulative = 0
        top_count = 0
        for item in items:
            pct = (item["conv_value_usd"] / total_value * 100) if total_value > 0 else 0
            cumulative += pct
            item["pct_of_total"] = round(pct, 2)
            item["cumulative_pct"] = round(cumulative, 2)
            if cumulative <= 80 or pct > 10:
                item["tag"] = "HERO"
                top_count += 1
            else:
                item["tag"] = "TAIL"

        summary = {}
        if items:
            summary["campaign_concentration"] = (
                f"{top_count} z {len(items)} kampanii ({round(top_count/len(items)*100)}%) generuje 80% wartości"
            )

        return {
            "campaign_pareto": {
                "total_campaigns": len(items),
                "top_campaigns_for_80pct": top_count,
                "items": items,
            },
            "summary": summary,
            "period_days": (date_to - date_from).days,
        }

    # ───────────────────────────────────────────────────────
    # GAP 7B: Scaling Opportunities
    # ───────────────────────────────────────────────────────

    def get_scaling_opportunities(self, client_id: int, days: int = 30,
                                   date_from: date | None = None, date_to: date | None = None,
                                   campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Find hero campaigns with impression share headroom to scale."""
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"opportunities": [], "summary": {}}

        campaigns = self.db.query(Campaign).filter(Campaign.id.in_(campaign_ids), Campaign.status == "ENABLED").all()

        campaign_values = []
        for c in campaigns:
            metrics = (
                self.db.query(
                    func.sum(MetricDaily.conversions).label("conv"),
                    func.sum(MetricDaily.conversion_value_micros).label("value"),
                    func.sum(MetricDaily.cost_micros).label("cost"),
                )
                .filter(MetricDaily.campaign_id == c.id, MetricDaily.date >= date_from, MetricDaily.date <= date_to)
                .first()
            )
            value = round((metrics.value or 0) / 1_000_000, 2) if metrics else 0
            cost = round((metrics.cost or 0) / 1_000_000, 2) if metrics else 0
            conv = round(float(metrics.conv or 0), 2) if metrics else 0
            campaign_values.append({"campaign": c, "value": value, "cost": cost, "conv": conv})

        total_value = sum(cv["value"] for cv in campaign_values)
        if total_value <= 0:
            return {"opportunities": [], "summary": {"total_value": 0}}

        campaign_values.sort(key=lambda x: x["value"], reverse=True)
        cumulative = 0
        opportunities = []

        for cv in campaign_values:
            cumulative += cv["value"]
            is_hero = (cumulative / total_value <= 0.80) or (cv["value"] / total_value > 0.10)
            if not is_hero:
                continue

            c = cv["campaign"]
            lost_budget = c.search_budget_lost_is or 0
            lost_rank = c.search_rank_lost_is or 0
            if lost_budget < 0.10 and lost_rank < 0.10:
                continue

            value_pct = cv["value"] / total_value * 100
            incremental = round(cv["value"] * max(lost_budget, lost_rank), 2)
            opportunities.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "value_usd": cv["value"],
                "value_pct": round(value_pct, 1),
                "cost_usd": cv["cost"],
                "conversions": cv["conv"],
                "lost_budget_is": round(lost_budget * 100, 1),
                "lost_rank_is": round(lost_rank * 100, 1),
                "incremental_value_est": incremental,
            })

        return {
            "opportunities": opportunities,
            "summary": {"total_value": round(total_value, 2), "opportunities_count": len(opportunities)},
        }

    # ───────────────────────────────────────────────────────
    # GAP 6A: Post-Change Performance Delta
    # ───────────────────────────────────────────────────────

    def get_change_impact_analysis(self, client_id: int, days: int = 60) -> dict:
        """Compute pre/post performance delta for each logged action."""
        from app.models.action_log import ActionLog
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup

        cutoff = date.today() - timedelta(days=days)

        actions = (
            self.db.query(ActionLog)
            .filter(
                ActionLog.client_id == client_id,
                ActionLog.status == "SUCCESS",
                ActionLog.executed_at >= cutoff,
            )
            .order_by(ActionLog.executed_at.desc())
            .limit(50)
            .all()
        )

        if not actions:
            return {"changes": [], "summary": {"positive": 0, "neutral": 0, "negative": 0, "total": 0}}

        changes = []
        summary = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}

        for action in actions:
            action_date = action.executed_at.date() if action.executed_at else date.today()
            pre_start = action_date - timedelta(days=7)
            pre_end = action_date - timedelta(days=1)
            post_start = action_date + timedelta(days=1)
            post_end = action_date + timedelta(days=7)

            # Skip if post window extends beyond today
            if post_end > date.today():
                post_end = date.today()
                if post_start > post_end:
                    continue

            pre_metrics = None
            post_metrics = None

            if action.entity_type == "campaign":
                try:
                    campaign_id = int(action.entity_id)
                except (ValueError, TypeError):
                    continue
                pre_metrics = self._aggregate_metric_daily(campaign_id, pre_start, pre_end)
                post_metrics = self._aggregate_metric_daily(campaign_id, post_start, post_end)
            elif action.entity_type == "keyword":
                try:
                    keyword_id = int(action.entity_id)
                except (ValueError, TypeError):
                    continue
                # Get campaign_id from keyword for campaign-level metrics
                kw = self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
                if kw and kw.ad_group_id:
                    ag = self.db.query(AdGroup).filter(AdGroup.id == kw.ad_group_id).first()
                    if ag:
                        pre_metrics = self._aggregate_metric_daily(ag.campaign_id, pre_start, pre_end)
                        post_metrics = self._aggregate_metric_daily(ag.campaign_id, post_start, post_end)

            if not pre_metrics or not post_metrics:
                continue

            delta = {}
            for metric in ["cost_usd", "conversions", "cpa_usd", "ctr", "roas"]:
                pre_val = pre_metrics.get(metric, 0)
                post_val = post_metrics.get(metric, 0)
                if pre_val and pre_val != 0:
                    delta[f"{metric}_pct"] = round((post_val - pre_val) / abs(pre_val) * 100, 1)
                else:
                    delta[f"{metric}_pct"] = 0

            # Determine impact
            cpa_improved = delta.get("cpa_usd_pct", 0) < -10
            conv_improved = delta.get("conversions_pct", 0) > 10
            cpa_worsened = delta.get("cpa_usd_pct", 0) > 10
            conv_worsened = delta.get("conversions_pct", 0) < -10

            if cpa_improved or conv_improved:
                impact = "POSITIVE"
                summary["positive"] += 1
            elif cpa_worsened or conv_worsened:
                impact = "NEGATIVE"
                summary["negative"] += 1
            else:
                impact = "NEUTRAL"
                summary["neutral"] += 1

            summary["total"] += 1

            # Get entity name from action payload or context
            entity_name = ""
            if action.action_payload and isinstance(action.action_payload, dict):
                entity_name = action.action_payload.get("entity_name", "")
            if not entity_name and action.context_json and isinstance(action.context_json, dict):
                entity_name = action.context_json.get("entity_name", "")

            changes.append({
                "action_log_id": action.id,
                "action_type": action.action_type,
                "entity_type": action.entity_type,
                "entity_id": action.entity_id,
                "entity_name": entity_name,
                "executed_at": str(action.executed_at),
                "pre_metrics": pre_metrics,
                "post_metrics": post_metrics,
                "delta": delta,
                "impact": impact,
            })

        return {"changes": changes, "summary": summary}

    # ───────────────────────────────────────────────────────
    # GAP 6B: Bid Strategy Change Impact
    # ───────────────────────────────────────────────────────

    def get_keyword_overlap(self, client_id: int) -> dict:
        """Find keywords that appear in multiple campaigns (same text).

        Returns overlapping keyword texts with per-campaign breakdown of
        clicks, cost, conversions, match type, and campaign name.
        """
        from app.models.ad_group import AdGroup

        campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        campaign_map = {c.id: c.name for c in campaigns}
        campaign_ids = list(campaign_map.keys())
        if not campaign_ids:
            return {"overlapping_keywords": [], "total_overlaps": 0, "total_wasted_cost_usd": 0}

        # Load all keywords joined through ad_groups to campaigns
        keywords = (
            self.db.query(Keyword, AdGroup.campaign_id)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids))
            .all()
        )

        # Group by normalized keyword text
        text_groups: dict[str, list[dict]] = {}
        for kw, camp_id in keywords:
            normalized = kw.text.strip().lower()
            if normalized not in text_groups:
                text_groups[normalized] = []
            text_groups[normalized].append({
                "keyword_id": kw.id,
                "campaign_id": camp_id,
                "campaign_name": campaign_map.get(camp_id, "Unknown"),
                "match_type": kw.match_type,
                "status": kw.status,
                "clicks": kw.clicks or 0,
                "impressions": kw.impressions or 0,
                "cost_usd": round((kw.cost_micros or 0) / 1_000_000, 2),
                "conversions": round(kw.conversions or 0, 2),
                "quality_score": kw.quality_score or 0,
            })

        # Filter to keywords appearing in more than one distinct campaign
        overlapping = []
        total_wasted = 0.0
        for text, entries in text_groups.items():
            unique_campaigns = set(e["campaign_id"] for e in entries)
            if len(unique_campaigns) < 2:
                continue
            total_cost = sum(e["cost_usd"] for e in entries)
            total_clicks = sum(e["clicks"] for e in entries)
            total_conversions = sum(e["conversions"] for e in entries)

            # Sort entries: highest cost first
            entries.sort(key=lambda e: e["cost_usd"], reverse=True)

            # Estimate waste: cost in all campaigns except the best-performing one
            if len(entries) > 1:
                best_cpa = None
                best_idx = 0
                for i, e in enumerate(entries):
                    if e["conversions"] > 0:
                        cpa = e["cost_usd"] / e["conversions"]
                        if best_cpa is None or cpa < best_cpa:
                            best_cpa = cpa
                            best_idx = i
                wasted = sum(e["cost_usd"] for j, e in enumerate(entries) if j != best_idx)
                total_wasted += wasted
            else:
                wasted = 0

            overlapping.append({
                "keyword_text": text,
                "campaign_count": len(unique_campaigns),
                "total_clicks": total_clicks,
                "total_cost_usd": round(total_cost, 2),
                "total_conversions": round(total_conversions, 2),
                "estimated_waste_usd": round(wasted, 2),
                "campaigns": entries,
            })

        # Sort by estimated waste descending
        overlapping.sort(key=lambda x: x["estimated_waste_usd"], reverse=True)

        return {
            "overlapping_keywords": overlapping[:50],
            "total_overlaps": len(overlapping),
            "total_wasted_cost_usd": round(total_wasted, 2),
        }

    # -----------------------------------------------------------------------
    # G4: Cross-Campaign Analysis — budget allocation
    # -----------------------------------------------------------------------
