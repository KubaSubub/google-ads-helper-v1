"""Dayparting (DoW + hourly), bid strategy change impact, budget allocation.

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


class PacingMixin:
    def get_dayparting(
        self, client_id: int, days: int = 30,
        date_from: date | None = None, date_to: date | None = None,
        campaign_type: str | None = None, campaign_status: str | None = None,
    ) -> dict:
        """Aggregate campaign metrics by day of week from MetricDaily.

        Returns per-day aggregates + averages (avg_*) for every metric so the
        UI can show 'avg/observation' under each cell. Currency is the account
        currency (Client.currency). For windows <= 21 days each day_of_week
        bucket also includes the concrete `dates` it covers.
        """
        from app.utils.date_utils import resolve_dates as _rd
        from app.models.client import Client as ClientModel
        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        client = self.db.query(ClientModel).filter(ClientModel.id == client_id).first()
        currency = client.currency if client else "PLN"

        ct_used = (campaign_type or "ALL").upper()
        campaign_ids = self._filter_campaign_ids(client_id, ct_used, campaign_status)
        if not campaign_ids:
            return {
                "period_days": period_days,
                "currency": currency,
                "campaign_type_used": ct_used,
                "days": [],
            }

        rows = self.db.query(MetricDaily).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= date_from,
            MetricDaily.date <= date_to,
        ).all()

        dow_agg: dict[int, dict] = {}
        dow_dates: dict[int, set] = {}
        for r in rows:
            dow = r.date.weekday()
            if dow not in dow_agg:
                dow_agg[dow] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                "conversions": 0.0, "conv_value_micros": 0, "count": 0}
                dow_dates[dow] = set()
            dow_agg[dow]["clicks"] += r.clicks or 0
            dow_agg[dow]["impressions"] += r.impressions or 0
            dow_agg[dow]["cost_micros"] += r.cost_micros or 0
            dow_agg[dow]["conversions"] += r.conversions or 0
            dow_agg[dow]["conv_value_micros"] += r.conversion_value_micros or 0
            dow_agg[dow]["count"] += 1
            dow_dates[dow].add(r.date)

        DOW_NAMES = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
        include_dates = period_days <= 21
        days_data = []
        for dow in range(7):
            a = dow_agg.get(dow, {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                  "conversions": 0.0, "conv_value_micros": 0, "count": 0})
            cost = a["cost_micros"] / 1_000_000
            cv = a["conv_value_micros"] / 1_000_000
            n = max(a["count"], 1)
            row = {
                "day_of_week": dow,
                "day_name": DOW_NAMES[dow],
                "observations": a["count"],
                "clicks": a["clicks"],
                "impressions": a["impressions"],
                "cost_amount": round(cost, 2),
                "conversions": round(a["conversions"], 2),
                "conversion_value_amount": round(cv, 2),
                "avg_clicks": round(a["clicks"] / n),
                "avg_impressions": round(a["impressions"] / n),
                "avg_cost_amount": round(cost / n, 2),
                "avg_conversions": round(a["conversions"] / n, 2),
                "avg_conversion_value_amount": round(cv / n, 2),
                "ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0,
                "cpc": round(cost / a["clicks"], 2) if a["clicks"] else 0,
                "cpa": round(cost / a["conversions"], 2) if a["conversions"] else 0,
                "roas": round(cv / cost, 2) if cost > 0 else 0,
                "cvr": round(a["conversions"] / a["clicks"] * 100, 2) if a["clicks"] else 0,
                "aov": round(cv / a["conversions"], 2) if a["conversions"] else 0,
                # Per-observation averages (matches frontend `avg_${metric}` lookup)
                "avg_ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0,
                "avg_cpc": round(cost / a["clicks"], 2) if a["clicks"] else 0,
                "avg_cpa": round(cost / a["conversions"], 2) if a["conversions"] else 0,
                "avg_roas": round(cv / cost, 2) if cost > 0 else 0,
                "avg_cvr": round(a["conversions"] / a["clicks"] * 100, 2) if a["clicks"] else 0,
                "avg_aov": round(cv / a["conversions"], 2) if a["conversions"] else 0,
            }
            if include_dates:
                row["dates"] = sorted(d.strftime("%d.%m") for d in dow_dates.get(dow, set()))
            # Backwards-compat alias (legacy "cost_usd" key still used by some clients)
            row["cost_usd"] = row["cost_amount"]
            row["avg_cost_usd"] = row["avg_cost_amount"]
            days_data.append(row)
        return {
            "period_days": period_days,
            "currency": currency,
            "campaign_type_used": ct_used,
            "days": days_data,
        }

    # -----------------------------------------------------------------------
    # RSA Analysis — ad copy performance per ad group
    # -----------------------------------------------------------------------

    def get_hourly_dayparting(self, client_id: int, days: int = 7,
                              date_from: date | None = None, date_to: date | None = None,
                              campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Aggregate campaign metrics by hour of day.

        Default `campaign_type = "ALL"` — covers PMax/Shopping/Display as well.
        Returns `currency` (account currency) + `campaign_type_used` so the UI
        can label values correctly and warn the operator when filter is active.
        """
        from app.utils.date_utils import resolve_dates as _rd
        from app.models.client import Client as ClientModel

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        client = self.db.query(ClientModel).filter(ClientModel.id == client_id).first()
        currency = client.currency if client else "PLN"
        ct_used = (campaign_type or "ALL").upper()

        campaign_ids = self._filter_campaign_ids(client_id, ct_used, campaign_status)
        if not campaign_ids:
            return {
                "period_days": period_days,
                "currency": currency,
                "campaign_type_used": ct_used,
                "hours": [],
            }

        rows = self.db.query(MetricSegmented).filter(
            MetricSegmented.campaign_id.in_(campaign_ids),
            MetricSegmented.date >= date_from,
            MetricSegmented.date <= date_to,
            MetricSegmented.hour_of_day.isnot(None),
            MetricSegmented.device.is_(None),
            MetricSegmented.geo_city.is_(None),
        ).all()

        hour_agg: dict[int, dict] = {}
        for r in rows:
            h = r.hour_of_day
            if h not in hour_agg:
                hour_agg[h] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                               "conversions": 0.0, "conv_value_micros": 0, "count": 0}
            hour_agg[h]["clicks"] += r.clicks or 0
            hour_agg[h]["impressions"] += r.impressions or 0
            hour_agg[h]["cost_micros"] += r.cost_micros or 0
            hour_agg[h]["conversions"] += r.conversions or 0
            hour_agg[h]["conv_value_micros"] += r.conversion_value_micros or 0
            hour_agg[h]["count"] += 1

        hours_data = []
        for h in range(24):
            a = hour_agg.get(h, {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                  "conversions": 0.0, "conv_value_micros": 0, "count": 0})
            cost = a["cost_micros"] / 1_000_000
            cv = a["conv_value_micros"] / 1_000_000
            n = max(a["count"], 1)
            hours_data.append({
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "clicks": a["clicks"],
                "impressions": a["impressions"],
                "cost_usd": round(cost, 2),
                "conversions": round(a["conversions"], 2),
                "avg_clicks": round(a["clicks"] / n),
                "avg_cost_usd": round(cost / n, 2),
                "avg_conversions": round(a["conversions"] / n, 2),
                "ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0,
                "cpc": round(cost / a["clicks"], 2) if a["clicks"] else 0,
                "cpa": round(cost / a["conversions"], 2) if a["conversions"] else 0,
                "roas": round(cv / cost, 2) if cost > 0 else 0,
                "cvr": round(a["conversions"] / a["clicks"] * 100, 2) if a["clicks"] else 0,
                "observations": a["count"],
            })
        return {
            "period_days": period_days,
            "currency": currency,
            "campaign_type_used": ct_used,
            "hours": hours_data,
        }

    # ------------------------------------------------------------------
    # B2: Search Terms Trend Analysis
    # ------------------------------------------------------------------

    def get_bid_strategy_change_impact(self, client_id: int, days: int = 90) -> dict:
        """Analyze performance impact of bid strategy changes from change events."""
        from app.models.change_event import ChangeEvent
        import json

        cutoff = date.today() - timedelta(days=days)

        events = (
            self.db.query(ChangeEvent)
            .filter(
                ChangeEvent.client_id == client_id,
                ChangeEvent.change_resource_type == "CAMPAIGN",
                ChangeEvent.change_date_time >= cutoff,
            )
            .order_by(ChangeEvent.change_date_time.desc())
            .all()
        )

        # Filter to strategy changes
        strategy_changes = []
        for ev in events:
            changed = ev.changed_fields
            if not changed:
                continue
            if isinstance(changed, str):
                try:
                    changed = json.loads(changed)
                except (json.JSONDecodeError, TypeError):
                    continue
            if not isinstance(changed, list):
                continue
            has_strategy = any("bidding_strategy" in str(f).lower() for f in changed)
            if not has_strategy:
                continue

            # Parse old/new strategy
            old_strategy = None
            new_strategy = None
            if ev.old_resource_json:
                old_data = ev.old_resource_json if isinstance(ev.old_resource_json, dict) else {}
                if isinstance(ev.old_resource_json, str):
                    try:
                        old_data = json.loads(ev.old_resource_json)
                    except (json.JSONDecodeError, TypeError):
                        old_data = {}
                old_strategy = old_data.get("bidding_strategy_type") or old_data.get("bidding_strategy")
            if ev.new_resource_json:
                new_data = ev.new_resource_json if isinstance(ev.new_resource_json, dict) else {}
                if isinstance(ev.new_resource_json, str):
                    try:
                        new_data = json.loads(ev.new_resource_json)
                    except (json.JSONDecodeError, TypeError):
                        new_data = {}
                new_strategy = new_data.get("bidding_strategy_type") or new_data.get("bidding_strategy")

            change_date = ev.change_date_time.date() if ev.change_date_time else None
            if not change_date:
                continue

            # Get campaign_id from entity_id
            campaign = (
                self.db.query(Campaign)
                .filter(Campaign.client_id == client_id)
                .filter(Campaign.name == ev.campaign_name)
                .first()
            ) if ev.campaign_name else None

            if not campaign:
                continue

            pre_metrics = self._aggregate_metric_daily(campaign.id, change_date - timedelta(days=14), change_date - timedelta(days=1))
            post_metrics = self._aggregate_metric_daily(campaign.id, change_date + timedelta(days=1), min(change_date + timedelta(days=14), date.today()))

            if not pre_metrics or not post_metrics:
                continue

            # Compute delta
            delta = {}
            for metric in ["cost_usd", "conversions", "cpa_usd", "ctr", "roas"]:
                pre_val = pre_metrics.get(metric, 0)
                post_val = post_metrics.get(metric, 0)
                if pre_val and pre_val != 0:
                    delta[f"{metric}_pct"] = round((post_val - pre_val) / abs(pre_val) * 100, 1)
                else:
                    delta[f"{metric}_pct"] = 0

            impact = "NEUTRAL"
            if delta.get("conversions_pct", 0) > 10 or delta.get("cpa_usd_pct", 0) < -10:
                impact = "POSITIVE"
            elif delta.get("conversions_pct", 0) < -10 or delta.get("cpa_usd_pct", 0) > 10:
                impact = "NEGATIVE"

            strategy_changes.append({
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "change_date": str(change_date),
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "pre_metrics": pre_metrics,
                "post_metrics": post_metrics,
                "delta": delta,
                "impact": impact,
                "user_email": ev.user_email,
            })

        return {
            "strategy_changes": strategy_changes,
            "summary": {
                "total": len(strategy_changes),
                "positive": sum(1 for s in strategy_changes if s["impact"] == "POSITIVE"),
                "neutral": sum(1 for s in strategy_changes if s["impact"] == "NEUTRAL"),
                "negative": sum(1 for s in strategy_changes if s["impact"] == "NEGATIVE"),
            },
        }

    # ───────────────────────────────────────────────────────
    # GAP 8: Ad Group Health Checks
    # ───────────────────────────────────────────────────────

    def get_budget_allocation(self, client_id: int, days: int = 30,
                              date_from: date | None = None, date_to: date | None = None) -> dict:
        """Compare CPA/ROAS across campaigns and suggest budget reallocation.

        Identifies donor campaigns (high CPA, low ROAS) and recipient campaigns
        (low CPA, high ROAS) and builds reallocation suggestions.
        """
        from app.utils.date_utils import resolve_dates as _rd
        start, end = _rd(days, date_from, date_to)

        campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        if not campaigns:
            return {"campaigns": [], "suggestions": [], "period_days": (end - start).days}

        campaign_map = {c.id: c for c in campaigns}
        campaign_ids = list(campaign_map.keys())

        # Aggregate MetricDaily per campaign in the date range
        rows = (
            self.db.query(
                MetricDaily.campaign_id,
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impressions"),
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
                func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
            )
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .group_by(MetricDaily.campaign_id)
            .all()
        )

        campaign_metrics = []
        for r in rows:
            c = campaign_map.get(r.campaign_id)
            if not c:
                continue

            clicks = r.clicks or 0
            impressions = r.impressions or 0
            cost_micros = r.cost_micros or 0
            conversions = r.conversions or 0
            conv_value_micros = r.conv_value_micros or 0

            cost_usd = cost_micros / 1_000_000
            conv_value_usd = conv_value_micros / 1_000_000
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (cost_usd / clicks) if clicks > 0 else 0
            cpa = (cost_usd / conversions) if conversions > 0 else 0
            roas = (conv_value_usd / cost_usd) if cost_usd > 0 else 0
            cvr = (conversions / clicks * 100) if clicks > 0 else 0

            budget_daily_usd = round((c.budget_micros or 0) / 1_000_000, 2)
            budget_lost = c.search_budget_lost_is

            campaign_metrics.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "campaign_type": c.campaign_type,
                "budget_daily_usd": budget_daily_usd,
                "cost_usd": round(cost_usd, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 2),
                "conversion_value_usd": round(conv_value_usd, 2),
                "ctr": round(ctr, 2),
                "cpc_usd": round(cpc, 2),
                "cpa_usd": round(cpa, 2),
                "roas": round(roas, 2),
                "cvr": round(cvr, 2),
                "impression_share_lost_budget": round((budget_lost or 0) * 100, 1),
            })

        # Build suggestions: donor/recipient pairs
        suggestions = []
        if len(campaign_metrics) >= 2:
            # Separate into campaigns with conversions (rankable) and without
            with_conv = [cm for cm in campaign_metrics if cm["conversions"] > 0]

            if len(with_conv) >= 2:
                # Sort by CPA: lowest CPA = best recipient, highest CPA = potential donor
                sorted_by_cpa = sorted(with_conv, key=lambda x: x["cpa_usd"])

                # Top recipients: low CPA, especially with budget-lost IS
                recipients = sorted_by_cpa[:max(1, len(sorted_by_cpa) // 3)]
                donors = sorted_by_cpa[-max(1, len(sorted_by_cpa) // 3):]

                # Only suggest if there's a meaningful CPA gap
                for donor in donors:
                    for recipient in recipients:
                        if donor["campaign_id"] == recipient["campaign_id"]:
                            continue
                        if donor["cpa_usd"] <= recipient["cpa_usd"] * 1.3:
                            continue  # CPA gap too small

                        # Calculate suggested reallocation (10-20% of donor budget)
                        move_pct = 0.15
                        if recipient["impression_share_lost_budget"] > 20:
                            move_pct = 0.20
                        move_amount = round(donor["budget_daily_usd"] * move_pct, 2)

                        # Estimate impact
                        saved_cpa = donor["cpa_usd"] - recipient["cpa_usd"]

                        suggestions.append({
                            "type": "reallocation",
                            "priority": "high" if saved_cpa > 10 else "medium",
                            "donor_campaign_id": donor["campaign_id"],
                            "donor_campaign_name": donor["campaign_name"],
                            "donor_cpa_usd": donor["cpa_usd"],
                            "recipient_campaign_id": recipient["campaign_id"],
                            "recipient_campaign_name": recipient["campaign_name"],
                            "recipient_cpa_usd": recipient["cpa_usd"],
                            "recipient_budget_lost_is": recipient["impression_share_lost_budget"],
                            "suggested_move_usd": move_amount,
                            "estimated_cpa_savings_usd": round(saved_cpa, 2),
                            "reason": (
                                f"CPA {donor['campaign_name']}: ${donor['cpa_usd']:.2f} vs "
                                f"{recipient['campaign_name']}: ${recipient['cpa_usd']:.2f}. "
                                f"Move ~${move_amount:.2f}/day to improve overall CPA."
                            ),
                        })

            # Also flag zero-conversion campaigns with significant spend
            for cm in campaign_metrics:
                if cm["conversions"] == 0 and cm["cost_usd"] > 10:
                    suggestions.append({
                        "type": "review_spend",
                        "priority": "high" if cm["cost_usd"] > 50 else "medium",
                        "campaign_id": cm["campaign_id"],
                        "campaign_name": cm["campaign_name"],
                        "cost_usd": cm["cost_usd"],
                        "reason": (
                            f"{cm['campaign_name']} spent ${cm['cost_usd']:.2f} with 0 conversions "
                            f"in {(end - start).days} days. Review or pause."
                        ),
                    })

        # Sort campaign_metrics by cost descending for display
        campaign_metrics.sort(key=lambda x: x["cost_usd"], reverse=True)

        return {
            "campaigns": campaign_metrics,
            "suggestions": suggestions,
            "period_days": (end - start).days,
            "total_cost_usd": round(sum(cm["cost_usd"] for cm in campaign_metrics), 2),
            "avg_cpa_usd": round(
                sum(cm["cost_usd"] for cm in campaign_metrics) /
                max(sum(cm["conversions"] for cm in campaign_metrics), 0.01), 2
            ),
        }

    # -----------------------------------------------------------------------
    # G4: Cross-Campaign Analysis — campaign comparison
    # -----------------------------------------------------------------------
