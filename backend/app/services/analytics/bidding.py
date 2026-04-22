"""Smart Bidding health, target vs actual, portfolio, learning status, ad-group health.

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


class BiddingMixin:
    def get_bidding_advisor(self, client_id: int, days: int = 30,
                            date_from: date | None = None, date_to: date | None = None,
                            campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Analyze conversion volume per campaign and recommend bidding strategy."""
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaigns = self._filter_campaigns(client_id, campaign_type or "SEARCH", campaign_status or "ENABLED").all()

        MANUAL_STRATEGIES = {"MANUAL_CPC", "MAXIMIZE_CLICKS", "ENHANCED_CPC"}
        SMART_LOW = {"TARGET_CPA", "MAXIMIZE_CONVERSIONS"}
        SMART_HIGH = {"TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE"}

        results = []
        for campaign in campaigns:
            rows = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= date_from,
                MetricDaily.date <= date_to,
            ).all()

            total_conv = sum(r.conversions or 0 for r in rows)
            total_cost_usd = sum(r.cost_micros or 0 for r in rows) / 1_000_000
            current = (campaign.bidding_strategy or "UNKNOWN").upper()

            if total_conv < 30:
                recommended = "MANUAL_CPC"
                reason = f"Tylko {total_conv:.0f} konwersji w {period_days}d — za mało dla Smart Bidding (min. 30)"
                status = "OK" if current in MANUAL_STRATEGIES else "CHANGE_RECOMMENDED"
            elif total_conv <= 50:
                recommended = "TARGET_CPA"
                reason = f"{total_conv:.0f} konwersji w {period_days}d — wystarczające dla Target CPA"
                if current in SMART_LOW or current in SMART_HIGH:
                    status = "OK"
                else:
                    status = "UPGRADE_RECOMMENDED"
            else:
                recommended = "TARGET_ROAS"
                reason = f"{total_conv:.0f} konwersji w {period_days}d — wystarczające dla Target ROAS"
                if current in SMART_HIGH:
                    status = "OK"
                elif current in SMART_LOW:
                    status = "UPGRADE_RECOMMENDED"
                else:
                    status = "CHANGE_RECOMMENDED"

            results.append({
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "current_strategy": campaign.bidding_strategy,
                "recommended_strategy": recommended,
                "conversions_30d": round(total_conv, 1),
                "cost_usd": round(total_cost_usd, 2),
                "status": status,
                "reason": reason,
            })

        changes_needed = [r for r in results if r["status"] != "OK"]
        return {
            "period_days": period_days,
            "campaigns": results,
            "changes_needed": len(changes_needed),
            "summary": {
                "ok": len([r for r in results if r["status"] == "OK"]),
                "upgrade": len([r for r in results if r["status"] == "UPGRADE_RECOMMENDED"]),
                "change": len([r for r in results if r["status"] == "CHANGE_RECOMMENDED"]),
            },
        }

    # -----------------------------------------------------------------------
    # Hourly Dayparting — performance by hour of day from MetricSegmented
    # -----------------------------------------------------------------------

    def get_smart_bidding_health(self, client_id: int, days: int = 30,
                                  date_from: date | None = None, date_to: date | None = None,
                                  campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Check Smart Bidding campaigns for sufficient conversion volume."""
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"campaigns": [], "summary": {"healthy": 0, "low_volume": 0, "critical": 0}}

        smart_strategies = {"TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"}
        campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.id.in_(campaign_ids), Campaign.status == "ENABLED")
            .all()
        )
        smart_campaigns = [c for c in campaigns if (c.bidding_strategy or "").upper() in smart_strategies]

        results = []
        summary = {"healthy": 0, "low_volume": 0, "critical": 0}

        for c in smart_campaigns:
            conv_sum = (
                self.db.query(func.coalesce(func.sum(MetricDaily.conversions), 0.0))
                .filter(MetricDaily.campaign_id == c.id, MetricDaily.date >= date_from, MetricDaily.date <= date_to)
                .scalar()
            ) or 0.0

            strategy = (c.bidding_strategy or "").upper()
            min_conv = 50 if "ROAS" in strategy else 30

            if conv_sum >= min_conv:
                status = "HEALTHY"
                summary["healthy"] += 1
            elif conv_sum >= min_conv * 0.5:
                status = "LOW_VOLUME"
                summary["low_volume"] += 1
            else:
                status = "CRITICAL"
                summary["critical"] += 1

            results.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "bidding_strategy": strategy,
                "conversions_30d": round(conv_sum, 2),
                "min_recommended": min_conv,
                "status": status,
            })

        results.sort(key=lambda x: x["conversions_30d"])
        return {"campaigns": results, "summary": summary}

    # ───────────────────────────────────────────────────────
    # GAP 7A: Pareto 80/20 Analysis
    # ───────────────────────────────────────────────────────

    def get_ad_group_health(self, client_id: int, days: int = 30,
                            date_from: date | None = None, date_to: date | None = None,
                            campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Check ad group structural health: ad count, keyword count, zero-conv groups."""
        from app.models.ad_group import AdGroup
        from app.models.ad import Ad
        from app.models.keyword_daily import KeywordDaily
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"total_ad_groups": 0, "issues": [], "details": []}

        # All active ad groups
        ad_groups = (
            self.db.query(AdGroup, Campaign.name.label("campaign_name"))
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids), AdGroup.status == "ENABLED")
            .all()
        )
        if not ad_groups:
            return {"total_ad_groups": 0, "issues": [], "details": []}

        ag_ids = [ag.AdGroup.id for ag in ad_groups]
        ag_map = {ag.AdGroup.id: {"name": ag.AdGroup.name, "campaign": ag.campaign_name, "campaign_id": ag.AdGroup.campaign_id} for ag in ad_groups}

        # Count enabled ads per ad group
        from app.models.ad import Ad
        ad_counts = dict(
            self.db.query(Ad.ad_group_id, func.count(Ad.id))
            .filter(Ad.ad_group_id.in_(ag_ids), Ad.status == "ENABLED")
            .group_by(Ad.ad_group_id)
            .all()
        )

        # Count positive keywords per ad group
        kw_counts = dict(
            self.db.query(Keyword.ad_group_id, func.count(Keyword.id))
            .filter(
                Keyword.ad_group_id.in_(ag_ids),
                Keyword.status == "ENABLED",
                Keyword.criterion_kind == "POSITIVE",
            )
            .group_by(Keyword.ad_group_id)
            .all()
        )

        # Aggregate cost/conversions per ad group from KeywordDaily
        kw_to_ag = dict(
            self.db.query(Keyword.id, Keyword.ad_group_id)
            .filter(Keyword.ad_group_id.in_(ag_ids))
            .all()
        )
        ag_metrics_raw = (
            self.db.query(
                Keyword.ad_group_id,
                func.coalesce(func.sum(KeywordDaily.cost_micros), 0).label("cost"),
                func.coalesce(func.sum(KeywordDaily.conversions), 0.0).label("conv"),
            )
            .join(Keyword, KeywordDaily.keyword_id == Keyword.id)
            .filter(
                Keyword.ad_group_id.in_(ag_ids),
                KeywordDaily.date >= date_from,
                KeywordDaily.date <= date_to,
            )
            .group_by(Keyword.ad_group_id)
            .all()
        )
        ag_metrics = {r[0]: {"cost_micros": r[1], "conversions": r[2]} for r in ag_metrics_raw}

        # Build details + detect issues
        details = []
        single_ad = []
        no_ads = []
        too_few_kw = []
        too_many_kw = []
        zero_conv = []

        for ag_id in ag_ids:
            info = ag_map[ag_id]
            ads = ad_counts.get(ag_id, 0)
            kws = kw_counts.get(ag_id, 0)
            metrics = ag_metrics.get(ag_id, {"cost_micros": 0, "conversions": 0.0})
            cost_usd = round(metrics["cost_micros"] / 1_000_000, 2)
            conv = round(metrics["conversions"], 2)
            issues_list = []

            if ads == 0:
                issues_list.append("Brak reklam")
                no_ads.append(info["name"])
            elif ads == 1:
                issues_list.append("Tylko 1 reklama (brak A/B)")
                single_ad.append(info["name"])

            if kws == 0:
                issues_list.append("Brak słów kluczowych")
                too_few_kw.append(info["name"])
            elif kws < 2:
                issues_list.append(f"Za mało słów ({kws})")
                too_few_kw.append(info["name"])
            elif kws > 30:
                issues_list.append(f"Za dużo słów ({kws})")
                too_many_kw.append(info["name"])

            if cost_usd >= 50.0 and conv == 0:
                issues_list.append(f"Brak konwersji przy ${cost_usd}")
                zero_conv.append(info["name"])

            if issues_list:
                details.append({
                    "ad_group_id": ag_id,
                    "ad_group_name": info["name"],
                    "campaign_name": info["campaign"],
                    "campaign_id": info["campaign_id"],
                    "ads_count": ads,
                    "keywords_count": kws,
                    "cost_usd": cost_usd,
                    "conversions": conv,
                    "issues": issues_list,
                })

        issues_summary = []
        if no_ads:
            issues_summary.append({"type": "no_ads", "count": len(no_ads), "severity": "HIGH"})
        if single_ad:
            issues_summary.append({"type": "single_ad", "count": len(single_ad), "severity": "MEDIUM"})
        if too_few_kw:
            issues_summary.append({"type": "too_few_keywords", "count": len(too_few_kw), "severity": "LOW"})
        if too_many_kw:
            issues_summary.append({"type": "too_many_keywords", "count": len(too_many_kw), "severity": "MEDIUM"})
        if zero_conv:
            issues_summary.append({"type": "zero_conversions_high_spend", "count": len(zero_conv), "severity": "HIGH"})

        return {
            "total_ad_groups": len(ag_ids),
            "issues": issues_summary,
            "details": sorted(details, key=lambda d: len(d["issues"]), reverse=True),
            "period_days": (date_to - date_from).days,
        }

    # -------------------------------------------------------------------
    # GAP 1D: Target CPA/ROAS vs. Actual
    # -------------------------------------------------------------------

    def get_target_vs_actual(self, client_id: int, days: int = 30,
                             date_from: date | None = None, date_to: date | None = None,
                             campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Compare Smart Bidding targets (tCPA/tROAS) with actual performance."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"items": [], "period_days": 0}

        smart_campaigns = (
            self.db.query(Campaign)
            .filter(
                Campaign.id.in_(campaign_ids),
                Campaign.bidding_strategy.in_(["TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"]),
            )
            .all()
        )

        items = []
        for c in smart_campaigns:
            metrics = (
                self.db.query(
                    func.sum(MetricDaily.cost_micros).label("cost"),
                    func.sum(MetricDaily.conversions).label("conv"),
                    func.sum(MetricDaily.conversion_value_micros).label("value"),
                )
                .filter(
                    MetricDaily.campaign_id == c.id,
                    MetricDaily.date >= date_from,
                    MetricDaily.date <= date_to,
                )
                .first()
            )
            cost = int(metrics.cost or 0)
            conv = float(metrics.conv or 0)
            value = int(metrics.value or 0)

            actual_cpa = round(cost / conv / 1_000_000, 2) if conv > 0 else None
            actual_roas = round(value / cost, 2) if cost > 0 else None

            target_cpa = round(c.target_cpa_micros / 1_000_000, 2) if c.target_cpa_micros else None
            target_roas = c.target_roas

            # Determine deviation
            if c.bidding_strategy in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") and target_cpa and actual_cpa:
                deviation_pct = round((actual_cpa - target_cpa) / target_cpa * 100, 1)
                if abs(deviation_pct) < 30:
                    status = "ON_TARGET"
                elif deviation_pct > 0:
                    status = "OVER_TARGET"
                else:
                    status = "UNDER_TARGET"
            elif c.bidding_strategy in ("TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE") and target_roas and actual_roas:
                deviation_pct = round((actual_roas - target_roas) / target_roas * 100, 1)
                if abs(deviation_pct) < 30:
                    status = "ON_TARGET"
                elif deviation_pct > 0:
                    status = "OVER_TARGET"
                else:
                    status = "UNDER_TARGET"
            else:
                deviation_pct = None
                status = "NO_TARGET"

            items.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "bidding_strategy": c.bidding_strategy,
                "target_cpa_usd": target_cpa,
                "target_roas": target_roas,
                "actual_cpa_usd": actual_cpa,
                "actual_roas": actual_roas,
                "cost_usd": round(cost / 1_000_000, 2),
                "conversions": round(conv, 2),
                "value_usd": round(value / 1_000_000, 2),
                "deviation_pct": deviation_pct,
                "status": status,
            })

        return {
            "items": sorted(items, key=lambda x: abs(x["deviation_pct"] or 0), reverse=True),
            "period_days": (date_to - date_from).days,
        }

    # -------------------------------------------------------------------
    # GAP 10: Bid Strategy Performance Report (time series)
    # -------------------------------------------------------------------

    def get_bid_strategy_performance_report(self, client_id: int, days: int = 30,
                                             campaign_id: int | None = None) -> dict:
        """Daily time series of target vs actual CPA/ROAS per campaign."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, None, None)

        q = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.bidding_strategy.in_(["TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"]),
        )
        if campaign_id:
            q = q.filter(Campaign.id == campaign_id)
        campaigns = q.all()

        result = []
        for c in campaigns:
            daily = (
                self.db.query(
                    MetricDaily.date,
                    MetricDaily.cost_micros,
                    MetricDaily.conversions,
                    MetricDaily.conversion_value_micros,
                )
                .filter(
                    MetricDaily.campaign_id == c.id,
                    MetricDaily.date >= date_from,
                    MetricDaily.date <= date_to,
                )
                .order_by(MetricDaily.date)
                .all()
            )

            series = []
            values_for_rolling = []
            for row in daily:
                cost = int(row.cost_micros or 0)
                conv = float(row.conversions or 0)
                value = int(row.conversion_value_micros or 0)
                actual_cpa = round(cost / conv / 1_000_000, 2) if conv > 0 else None
                actual_roas = round(value / cost, 2) if cost > 0 else None

                metric_val = actual_cpa if c.bidding_strategy in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") else actual_roas
                values_for_rolling.append(metric_val)

                # 7-day rolling average
                recent = [v for v in values_for_rolling[-7:] if v is not None]
                rolling_7d = round(sum(recent) / len(recent), 2) if recent else None

                series.append({
                    "date": str(row.date),
                    "actual_cpa_usd": actual_cpa,
                    "actual_roas": actual_roas,
                    "rolling_7d": rolling_7d,
                    "cost_usd": round(cost / 1_000_000, 2),
                    "conversions": round(conv, 2),
                })

            target_line = None
            if c.bidding_strategy in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") and c.target_cpa_micros:
                target_line = round(c.target_cpa_micros / 1_000_000, 2)
            elif c.bidding_strategy in ("TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE") and c.target_roas:
                target_line = c.target_roas

            result.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "bidding_strategy": c.bidding_strategy,
                "metric_type": "CPA" if c.bidding_strategy in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") else "ROAS",
                "target_value": target_line,
                "series": series,
            })

        return {"campaigns": result, "period_days": (date_to - date_from).days}

    # -------------------------------------------------------------------
    # GAP 1A: Learning Period Detection
    # -------------------------------------------------------------------

    def get_learning_status(self, client_id: int) -> dict:
        """Detect campaigns in Smart Bidding learning period."""
        from app.models.change_event import ChangeEvent

        campaigns = (
            self.db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.bidding_strategy.in_(["TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"]),
            )
            .all()
        )

        items = []
        for c in campaigns:
            is_learning = False
            learning_reason = None
            days_in_learning = None

            # Check primary_status_reasons for BIDDING_STRATEGY_LEARNING
            if c.primary_status_reasons:
                import json
                try:
                    reasons = json.loads(c.primary_status_reasons) if isinstance(c.primary_status_reasons, str) else c.primary_status_reasons
                except (json.JSONDecodeError, TypeError):
                    reasons = []
                if any("LEARNING" in str(r).upper() for r in reasons):
                    is_learning = True
                    learning_reason = "primary_status_reasons contains LEARNING"

            # Estimate days in learning from last bidding strategy change
            if is_learning:
                last_change = (
                    self.db.query(ChangeEvent)
                    .filter(
                        ChangeEvent.client_id == client_id,
                        ChangeEvent.change_resource_type == "CAMPAIGN",
                        ChangeEvent.campaign_name == c.name,
                    )
                    .order_by(ChangeEvent.change_date_time.desc())
                    .first()
                )
                if last_change and last_change.change_date_time:
                    days_in_learning = (date.today() - last_change.change_date_time.date()).days

            status = "LEARNING" if is_learning else "STABLE"
            if is_learning and days_in_learning and days_in_learning > 21:
                status = "STUCK_LEARNING"
            elif is_learning and days_in_learning and days_in_learning > 14:
                status = "EXTENDED_LEARNING"

            items.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "bidding_strategy": c.bidding_strategy,
                "primary_status": c.primary_status,
                "status": status,
                "is_learning": is_learning,
                "days_in_learning": days_in_learning,
                "learning_reason": learning_reason,
            })

        learning_count = sum(1 for i in items if i["is_learning"])
        return {
            "total_smart_bidding": len(items),
            "learning_count": learning_count,
            "stuck_count": sum(1 for i in items if i["status"] == "STUCK_LEARNING"),
            "items": items,
        }

    # -------------------------------------------------------------------
    # GAP 1E: Portfolio Bid Strategy Health
    # -------------------------------------------------------------------

    def get_portfolio_strategy_health(self, client_id: int, days: int = 30,
                                       date_from: date | None = None, date_to: date | None = None) -> dict:
        """Analyze health of portfolio bid strategies (grouped campaigns)."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)

        # Find campaigns with portfolio bid strategies
        portfolio_campaigns = (
            self.db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.portfolio_bid_strategy_id.isnot(None),
            )
            .all()
        )

        if not portfolio_campaigns:
            return {"portfolios": [], "total_portfolios": 0}

        # Group by portfolio
        from collections import defaultdict
        portfolios = defaultdict(list)
        for c in portfolio_campaigns:
            portfolios[c.portfolio_bid_strategy_id].append(c)

        result = []
        for portfolio_id, campaigns in portfolios.items():
            campaign_data = []
            total_cost = 0
            total_conv = 0.0
            total_value = 0

            for c in campaigns:
                metrics = (
                    self.db.query(
                        func.sum(MetricDaily.cost_micros).label("cost"),
                        func.sum(MetricDaily.conversions).label("conv"),
                        func.sum(MetricDaily.conversion_value_micros).label("value"),
                    )
                    .filter(
                        MetricDaily.campaign_id == c.id,
                        MetricDaily.date >= date_from,
                        MetricDaily.date <= date_to,
                    )
                    .first()
                )
                cost = int(metrics.cost or 0)
                conv = float(metrics.conv or 0)
                value = int(metrics.value or 0)
                total_cost += cost
                total_conv += conv
                total_value += value

                campaign_data.append({
                    "campaign_id": c.id,
                    "campaign_name": c.name,
                    "cost_usd": round(cost / 1_000_000, 2),
                    "conversions": round(conv, 2),
                    "value_usd": round(value / 1_000_000, 2),
                    "spend_share_pct": 0,  # computed below
                })

            # Compute spend share
            for cd in campaign_data:
                cd["spend_share_pct"] = round(cd["cost_usd"] / (total_cost / 1_000_000) * 100, 1) if total_cost > 0 else 0

            # Health checks
            issues = []
            if total_conv < 50:
                issues.append({"type": "LOW_VOLUME", "detail": f"Tylko {total_conv:.0f} konwersji (min. 50)", "severity": "HIGH"})
            max_share = max((cd["spend_share_pct"] for cd in campaign_data), default=0)
            if max_share > 70 and len(campaign_data) > 1:
                dominant = next(cd for cd in campaign_data if cd["spend_share_pct"] == max_share)
                issues.append({"type": "IMBALANCE", "detail": f"{dominant['campaign_name']} to {max_share:.0f}% wydatkow", "severity": "MEDIUM"})

            result.append({
                "portfolio_id": portfolio_id,
                "bidding_strategy": campaigns[0].bidding_strategy,
                "resource_name": campaigns[0].bidding_strategy_resource_name,
                "campaign_count": len(campaigns),
                "total_cost_usd": round(total_cost / 1_000_000, 2),
                "total_conversions": round(total_conv, 2),
                "total_value_usd": round(total_value / 1_000_000, 2),
                "campaigns": campaign_data,
                "issues": issues,
            })

        return {
            "portfolios": result,
            "total_portfolios": len(result),
            "period_days": (date_to - date_from).days,
        }

    # -------------------------------------------------------------------
    # GAP 2A-2D: Conversion Data Quality Audit
    # -------------------------------------------------------------------
