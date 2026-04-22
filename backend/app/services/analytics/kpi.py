"""KPI aggregates + trend series (including mock fallback).

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


class KPIMixin:
    def get_kpis(self, client_id: int) -> dict:
        """Aggregate KPIs across all campaigns for a client.

        Uses MetricDaily (last 30 days) for accurate aggregation.
        """
        today = date.today()
        days_30_ago = today - timedelta(days=30)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id
        ).all()
        campaign_ids = [c.id for c in campaigns]

        if not campaign_ids:
            return {
                "total_spend_usd": 0, "total_clicks": 0, "total_impressions": 0,
                "total_conversions": 0, "total_conversion_value_usd": 0,
                "avg_ctr_pct": 0, "avg_cpc_usd": 0, "cpa_usd": 0,
                "roas": None,
                "conversion_value_tracked": False,
                "active_campaigns": 0,
            }

        # Aggregate from MetricDaily
        result = self.db.query(
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
        ).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= days_30_ago,
        ).first()

        total_clicks = result.clicks or 0
        total_impressions = result.impressions or 0
        total_spend_micros = result.cost_micros or 0
        total_conversions = result.conversions or 0.0
        total_conv_value_micros = result.conv_value_micros or 0

        total_spend_usd = total_spend_micros / 1_000_000
        total_conv_value_usd = total_conv_value_micros / 1_000_000
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
        avg_cpc = (total_spend_usd / total_clicks) if total_clicks else 0
        cpa = (total_spend_usd / total_conversions) if total_conversions else 0

        # ROAS semantics:
        # - None  → conversion value is not tracked on this account (conversions > 0 but value = 0).
        #           Downstream ROAS-based recommendations must be suppressed to avoid
        #           false "low ROAS" alerts.
        # - 0.0   → value IS tracked but genuinely zero return on spend (cost without attributed value).
        # - >0    → normal ROAS.
        conversion_value_tracked = total_conv_value_micros > 0 or total_conversions == 0
        if not total_spend_usd:
            roas = None
        elif total_conversions > 0 and total_conv_value_micros == 0:
            roas = None  # value not tracked; don't fabricate a zero
        else:
            roas = total_conv_value_usd / total_spend_usd

        return {
            "total_spend_usd": round(total_spend_usd, 2),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "total_conversions": round(total_conversions, 2),
            "total_conversion_value_usd": round(total_conv_value_usd, 2),
            "avg_ctr_pct": round(avg_ctr, 2),
            "avg_cpc_usd": round(avg_cpc, 2),
            "cpa_usd": round(cpa, 2),
            "roas": round(roas, 2) if roas is not None else None,
            "conversion_value_tracked": conversion_value_tracked,
            "active_campaigns": len([c for c in campaigns if c.status == "ENABLED"]),
        }

    def get_trends(
        self,
        client_id: int,
        metrics: list[str],
        days: int = 30,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_type: str = "ALL",
        campaign_status: str = "ALL",
        campaign_ids: list[int] | None = None,
        # backward compat alias
        status: str | None = None,
    ) -> dict:
        """Return daily aggregated metrics for TrendExplorer chart.

        Queries MetricDaily joined to Campaign, aggregates per day. Supports all
        18 unified metrics (cost, clicks, ..., search_impression_share, click_share, ...).
        Share metrics are impression-weighted when aggregating across multiple campaigns.

        When `campaign_ids` is provided, aggregation is restricted to those IDs
        (intersected with the client's campaigns). Used by the Campaigns tab to
        scope Trend Explorer to a single selected campaign.

        Falls back to mock data if MetricDaily is empty.
        """
        effective_status = campaign_status if status is None else status
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)

        client_campaign_ids = self._filter_campaign_ids(client_id, campaign_type, effective_status)
        if campaign_ids is not None:
            # Intersect with client scope so cross-client requests are rejected silently
            allowed_set = set(client_campaign_ids)
            target_campaign_ids = [cid for cid in campaign_ids if cid in allowed_set]
        else:
            target_campaign_ids = client_campaign_ids

        period_days = (date_to - date_from).days

        if not target_campaign_ids:
            return {"period_days": period_days, "data": [], "totals": {}}

        rows = (
            self.db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(target_campaign_ids),
                MetricDaily.date >= date_from,
                MetricDaily.date <= date_to,
            )
            .order_by(MetricDaily.date)
            .all()
        )

        def _fresh():
            return {
                "clicks": 0, "impressions": 0, "cost_micros": 0,
                "conversions": 0.0, "conv_value_micros": 0,
                "_sis_num": 0.0, "_stis_num": 0.0, "_satis_num": 0.0,
                "_blis_num": 0.0, "_rlis_num": 0.0, "_scs_num": 0.0,
                "_atip_num": 0.0, "_tip_num": 0.0, "_share_weight": 0,
            }

        day_map: dict[date, dict] = {}
        for r in rows:
            d = r.date
            if d not in day_map:
                day_map[d] = _fresh()
            agg = day_map[d]
            imp = r.impressions or 0
            agg["clicks"] += r.clicks or 0
            agg["impressions"] += imp
            agg["cost_micros"] += r.cost_micros or 0
            agg["conversions"] += r.conversions or 0
            agg["conv_value_micros"] += r.conversion_value_micros or 0
            if imp > 0:
                agg["_share_weight"] += imp
                if r.search_impression_share is not None:         agg["_sis_num"]  += r.search_impression_share * imp
                if r.search_top_impression_share is not None:     agg["_stis_num"] += r.search_top_impression_share * imp
                if r.search_abs_top_impression_share is not None: agg["_satis_num"] += r.search_abs_top_impression_share * imp
                if r.search_budget_lost_is is not None:           agg["_blis_num"] += r.search_budget_lost_is * imp
                if r.search_rank_lost_is is not None:             agg["_rlis_num"] += r.search_rank_lost_is * imp
                if r.search_click_share is not None:              agg["_scs_num"]  += r.search_click_share * imp
                if r.abs_top_impression_pct is not None:          agg["_atip_num"] += r.abs_top_impression_pct * imp
                if r.top_impression_pct is not None:              agg["_tip_num"]  += r.top_impression_pct * imp

        is_mock = False
        if not day_map:
            is_mock = True
            logger.warning("Returning mock trend data — no MetricDaily rows found for campaigns")
            day_map = self._mock_daily_data(target_campaign_ids, date_from, date_to)

        # Forward-fill missing days with zeros so the chart is a continuous series.
        # Matters for action markers (Recharts ReferenceLine on a categorical axis
        # disappears when the x-value doesn't exist in data) and for honest visuals:
        # a weekend gap should show as zero, not as an interpolated line.
        from datetime import timedelta as _td
        cursor = date_from
        while cursor <= date_to:
            if cursor not in day_map:
                day_map[cursor] = _fresh()
            cursor += _td(days=1)

        data = []
        for d in sorted(day_map.keys()):
            agg = day_map[d]
            clicks = agg["clicks"]
            impressions = agg["impressions"]
            cost_micros = agg["cost_micros"]
            conversions = agg["conversions"]
            conv_value = agg.get("conv_value_micros", 0) / 1_000_000
            cost = cost_micros / 1_000_000

            ctr = (clicks / impressions * 100) if impressions else 0
            cpc = (cost / clicks) if clicks else 0
            roas = (conv_value / cost) if cost else 0
            cpa = (cost / conversions) if conversions else 0
            cvr = (conversions / clicks * 100) if clicks else 0

            w = agg.get("_share_weight", 0)
            def _share(num_key: str) -> float:
                return round((agg.get(num_key, 0) / w * 100), 2) if w else 0

            metric_map = {
                "cost": round(cost, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 2),
                "conversion_value": round(conv_value, 2),
                "ctr": round(ctr, 4),
                "cpc": round(cpc, 2),
                "cpa": round(cpa, 2),
                "cvr": round(cvr, 4),
                "roas": round(roas, 2),
                "search_impression_share": _share("_sis_num"),
                "search_top_impression_share": _share("_stis_num"),
                "search_abs_top_impression_share": _share("_satis_num"),
                "search_budget_lost_is": _share("_blis_num"),
                "search_rank_lost_is": _share("_rlis_num"),
                "search_click_share": _share("_scs_num"),
                "abs_top_impression_pct": _share("_atip_num"),
                "top_impression_pct": _share("_tip_num"),
            }
            row: dict = {"date": str(d)}
            for m in metrics:
                row[m] = metric_map.get(m, 0)
            data.append(row)

        total_cost = sum(day_map[d]["cost_micros"] for d in day_map) / 1_000_000
        total_clicks = sum(day_map[d]["clicks"] for d in day_map)
        total_conversions = sum(day_map[d]["conversions"] for d in day_map)

        return {
            "period_days": period_days,
            "is_mock": is_mock,
            "data": data,
            "totals": {
                "cost": round(total_cost, 2),
                "clicks": total_clicks,
                "conversions": round(total_conversions, 2),
            },
        }

    def _mock_daily_data(self, campaign_ids: list[int], date_from: date, date_to: date) -> dict:
        """Generate mock daily data when MetricDaily is empty.

        Distributes keyword-level aggregates evenly across days with ±20% noise.
        Includes conv_value_micros so ROAS is non-zero in mock mode.
        """
        from app.models.keyword import Keyword
        from app.models.ad_group import AdGroup

        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids))
            .all()
        )

        total_clicks = sum(k.clicks or 0 for k in keywords)
        total_impressions = sum(k.impressions or 0 for k in keywords)
        total_cost_micros = sum(k.cost_micros or 0 for k in keywords)
        total_conversions = sum(k.conversions or 0 for k in keywords)
        total_conv_value_micros = sum(getattr(k, "conversion_value_micros", 0) or 0 for k in keywords)

        days = (date_to - date_from).days or 1
        day_clicks = total_clicks / days
        day_impressions = total_impressions / days
        day_cost = total_cost_micros / days
        day_conv = total_conversions / days
        day_conv_value = total_conv_value_micros / days

        day_map: dict[date, dict] = {}
        current = date_from
        rand = random.Random(42)
        while current <= date_to:
            noise = lambda: 1 + rand.uniform(-0.2, 0.2)
            day_map[current] = {
                "clicks": max(0, int(day_clicks * noise())),
                "impressions": max(0, int(day_impressions * noise())),
                "cost_micros": max(0, int(day_cost * noise())),
                "conversions": max(0, round(day_conv * noise(), 1)),
                "conv_value_micros": max(0, int(day_conv_value * noise())),
                "_share_weight": 0,  # no mock shares — keeps them at 0 in output
            }
            current += timedelta(days=1)
        return day_map

    # -----------------------------------------------------------------------
    # NEW: Health Score
    # -----------------------------------------------------------------------

    def get_campaign_trends(
        self, client_id: int, days: int = 7,
        date_from: date | None = None, date_to: date | None = None,
        campaign_type: str | None = None, campaign_status: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Return per-campaign cost trend for sparkline display."""
        effective_status = campaign_status if campaign_status is not None else status
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to, default_days=7)

        campaigns = self._filter_campaigns(client_id, campaign_type, effective_status).all()

        result = {}
        rand = random.Random(99)

        for campaign in campaigns:
            rows = (
                self.db.query(MetricDaily)
                .filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date >= date_from,
                    MetricDaily.date <= date_to,
                )
                .order_by(MetricDaily.date)
                .all()
            )

            period_days = (date_to - date_from).days or 7
            if rows:
                trend = [round(r.cost_micros / 1_000_000, 2) for r in rows]
            else:
                # Mock: gentle curve with noise around budget
                base = campaign.budget_micros / 1_000_000 / 30 if campaign.budget_micros else 10
                trend = [round(max(0, base * (1 + rand.uniform(-0.25, 0.25))), 2) for _ in range(period_days)]

            # Direction: compare first half vs second half
            half = len(trend) // 2
            if half > 0 and len(trend) >= 2:
                avg_first = sum(trend[:half]) / half
                avg_second = sum(trend[half:]) / max(len(trend) - half, 1)
                if avg_second > avg_first * 1.05:
                    direction = "up"
                elif avg_second < avg_first * 0.95:
                    direction = "down"
                else:
                    direction = "flat"
            else:
                direction = "flat"

            result[str(campaign.id)] = {
                "cost_trend": trend,
                "direction": direction,
            }

        return {"campaigns": result}

    # -----------------------------------------------------------------------
    # NEW: Impression Share Trends
    # -----------------------------------------------------------------------

    def get_impression_share_trends(
        self,
        client_id: int,
        days: int = 30,
        date_from: date | None = None, date_to: date | None = None,
        campaign_id: int | None = None,
        campaign_type: str | None = None, campaign_status: str | None = None,
    ) -> dict:
        """Daily impression share metrics for SEARCH campaigns."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_q = self._filter_campaigns(client_id, campaign_type or "SEARCH", campaign_status)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": period_days, "data": [], "summary": {}}

        rows = (
            self.db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= date_from,
                MetricDaily.date <= date_to,
            )
            .order_by(MetricDaily.date)
            .all()
        )

        # Aggregate per day (average across campaigns)
        day_map: dict[date, dict] = {}
        day_counts: dict[date, int] = {}
        for r in rows:
            d = r.date
            if d not in day_map:
                day_map[d] = {
                    "search_impression_share": 0, "search_top_impression_share": 0,
                    "search_abs_top_impression_share": 0,
                    "search_budget_lost_is": 0, "search_rank_lost_is": 0,
                    "search_click_share": 0,
                }
                day_counts[d] = 0
            if r.search_impression_share is not None:
                day_map[d]["search_impression_share"] += r.search_impression_share
                day_map[d]["search_top_impression_share"] += r.search_top_impression_share or 0
                day_map[d]["search_abs_top_impression_share"] += r.search_abs_top_impression_share or 0
                day_map[d]["search_budget_lost_is"] += r.search_budget_lost_is or 0
                day_map[d]["search_rank_lost_is"] += r.search_rank_lost_is or 0
                day_map[d]["search_click_share"] += r.search_click_share or 0
                day_counts[d] += 1

        data = []
        for d in sorted(day_map.keys()):
            n = max(day_counts[d], 1)
            data.append({
                "date": str(d),
                "impression_share": round(day_map[d]["search_impression_share"] / n, 4),
                "top_impression_share": round(day_map[d]["search_top_impression_share"] / n, 4),
                "abs_top_impression_share": round(day_map[d]["search_abs_top_impression_share"] / n, 4),
                "budget_lost_is": round(day_map[d]["search_budget_lost_is"] / n, 4),
                "rank_lost_is": round(day_map[d]["search_rank_lost_is"] / n, 4),
                "click_share": round(day_map[d]["search_click_share"] / n, 4),
            })

        # Summary: averages over entire period
        if data:
            summary = {
                k: round(sum(row[k] for row in data) / len(data), 4)
                for k in ["impression_share", "top_impression_share", "abs_top_impression_share",
                          "budget_lost_is", "rank_lost_is", "click_share"]
            }
        else:
            summary = {}

        return {"period_days": period_days, "data": data, "summary": summary}

    # -----------------------------------------------------------------------
    # NEW: Device Breakdown
    # -----------------------------------------------------------------------
