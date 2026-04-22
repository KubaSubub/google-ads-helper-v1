"""Device / geo / demographics breakdowns + per-device trends.

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


class BreakdownMixin:
    def get_device_breakdown(
        self,
        client_id: int,
        days: int = 30,
        date_from: date | None = None, date_to: date | None = None,
        campaign_id: int | None = None,
        campaign_type: str | None = None, campaign_status: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by device."""
        effective_status = campaign_status if campaign_status is not None else status
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_q = self._filter_campaigns(client_id, campaign_type, effective_status)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": period_days, "devices": []}

        rows = (
            self.db.query(MetricSegmented)
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.device.isnot(None),
            )
            .all()
        )

        # Aggregate by device (totals + daily trends)
        device_agg: dict[str, dict] = {}
        device_daily: dict[str, dict[date, dict]] = {}
        for r in rows:
            dev = r.device
            if dev not in device_agg:
                device_agg[dev] = {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0, "conv_value_micros": 0}
                device_daily[dev] = {}
            device_agg[dev]["clicks"] += r.clicks or 0
            device_agg[dev]["impressions"] += r.impressions or 0
            device_agg[dev]["cost_micros"] += r.cost_micros or 0
            device_agg[dev]["conversions"] += r.conversions or 0
            device_agg[dev]["conv_value_micros"] += r.conversion_value_micros or 0

            d = r.date
            if d not in device_daily[dev]:
                device_daily[dev][d] = {"clicks": 0, "cost_micros": 0, "conversions": 0.0}
            device_daily[dev][d]["clicks"] += r.clicks or 0
            device_daily[dev][d]["cost_micros"] += r.cost_micros or 0
            device_daily[dev][d]["conversions"] += r.conversions or 0

        devices = []
        total_clicks = sum(d["clicks"] for d in device_agg.values())
        total_cost = sum(d["cost_micros"] for d in device_agg.values())

        for dev, agg in sorted(device_agg.items()):
            cost_usd = agg["cost_micros"] / 1_000_000
            conv_value_usd = agg["conv_value_micros"] / 1_000_000

            # Build daily trend sorted by date
            daily = device_daily.get(dev, {})
            trend = [
                {
                    "date": str(dt),
                    "clicks": daily[dt]["clicks"],
                    "cost": round(daily[dt]["cost_micros"] / 1_000_000, 2),
                    "conversions": round(daily[dt]["conversions"], 2),
                }
                for dt in sorted(daily.keys())
            ]

            devices.append({
                "device": dev,
                "clicks": agg["clicks"],
                "impressions": agg["impressions"],
                "cost_usd": round(cost_usd, 2),
                "conversions": round(agg["conversions"], 2),
                "ctr": round(agg["clicks"] / agg["impressions"] * 100, 2) if agg["impressions"] else 0,
                "cpc": round(cost_usd / agg["clicks"], 2) if agg["clicks"] else 0,
                "roas": round(conv_value_usd / cost_usd, 2) if cost_usd > 0 else 0,
                "share_clicks_pct": round(agg["clicks"] / total_clicks * 100, 1) if total_clicks else 0,
                "share_cost_pct": round(agg["cost_micros"] / total_cost * 100, 1) if total_cost else 0,
                "trend": trend,
            })

        return {"period_days": period_days, "devices": devices}

    # -----------------------------------------------------------------------
    # NEW: Trends split by device (time-series per segment)
    # -----------------------------------------------------------------------

    def get_trends_by_device(
        self,
        client_id: int,
        metric: str,
        days: int = 30,
        date_from: date | None = None, date_to: date | None = None,
        campaign_ids: list[int] | None = None,
        campaign_type: str = "ALL",
        campaign_status: str | None = None,
    ) -> dict:
        """Return daily time-series for a single metric, split by device.

        Used by TrendExplorer's device-segmentation option. For each day,
        derives the selected metric for MOBILE / DESKTOP / TABLET / OTHER
        from MetricSegmented aggregated across the matching campaigns.
        """
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        client_campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if campaign_ids is not None:
            allowed = set(client_campaign_ids)
            target = [cid for cid in campaign_ids if cid in allowed]
        else:
            target = client_campaign_ids

        if not target:
            return {"period_days": period_days, "metric": metric, "devices": {}}

        rows = (
            self.db.query(MetricSegmented)
            .filter(
                MetricSegmented.campaign_id.in_(target),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.device.isnot(None),
            )
            .all()
        )

        by_dev_day: dict[str, dict[date, dict]] = {}
        for r in rows:
            dev = r.device
            if dev not in by_dev_day:
                by_dev_day[dev] = {}
            d = r.date
            if d not in by_dev_day[dev]:
                by_dev_day[dev][d] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                      "conversions": 0.0, "conv_value_micros": 0}
            agg = by_dev_day[dev][d]
            agg["clicks"] += r.clicks or 0
            agg["impressions"] += r.impressions or 0
            agg["cost_micros"] += r.cost_micros or 0
            agg["conversions"] += r.conversions or 0
            agg["conv_value_micros"] += r.conversion_value_micros or 0

        def _value_for_day(agg: dict) -> float:
            clicks = agg["clicks"]
            impressions = agg["impressions"]
            cost = agg["cost_micros"] / 1_000_000
            conversions = agg["conversions"]
            conv_value = agg["conv_value_micros"] / 1_000_000
            if metric == "cost": return round(cost, 2)
            if metric == "clicks": return clicks
            if metric == "impressions": return impressions
            if metric == "conversions": return round(conversions, 2)
            if metric == "conversion_value": return round(conv_value, 2)
            if metric == "ctr": return round((clicks / impressions * 100) if impressions else 0, 4)
            if metric == "cpc": return round((cost / clicks) if clicks else 0, 2)
            if metric == "cpa": return round((cost / conversions) if conversions else 0, 2)
            if metric == "cvr": return round((conversions / clicks * 100) if clicks else 0, 4)
            if metric == "roas": return round((conv_value / cost) if cost else 0, 2)
            return 0

        devices: dict[str, list[dict]] = {}
        for dev, day_map in by_dev_day.items():
            series = []
            for d in sorted(day_map.keys()):
                series.append({"date": str(d), "value": _value_for_day(day_map[d])})
            devices[dev] = series

        return {
            "period_days": period_days,
            "metric": metric,
            "devices": devices,
            "is_mock": len(rows) == 0,
        }

    # -----------------------------------------------------------------------
    # NEW: Geo Breakdown
    # -----------------------------------------------------------------------

    def get_geo_breakdown(
        self,
        client_id: int,
        days: int = 7,
        date_from: date | None = None, date_to: date | None = None,
        campaign_id: int | None = None,
        limit: int = 20,
        campaign_type: str | None = None, campaign_status: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by geo_city."""
        effective_status = campaign_status if campaign_status is not None else status
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to, default_days=7)
        period_days = (date_to - date_from).days

        campaign_q = self._filter_campaigns(client_id, campaign_type, effective_status)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": period_days, "cities": []}

        rows = (
            self.db.query(MetricSegmented)
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.geo_city.isnot(None),
            )
            .all()
        )

        # Aggregate by city
        city_agg: dict[str, dict] = {}
        for r in rows:
            city = r.geo_city
            if city not in city_agg:
                city_agg[city] = {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0, "conv_value_micros": 0}
            city_agg[city]["clicks"] += r.clicks or 0
            city_agg[city]["impressions"] += r.impressions or 0
            city_agg[city]["cost_micros"] += r.cost_micros or 0
            city_agg[city]["conversions"] += r.conversions or 0
            city_agg[city]["conv_value_micros"] += r.conversion_value_micros or 0

        # Sort by cost descending, limit
        sorted_cities = sorted(city_agg.items(), key=lambda x: x[1]["cost_micros"], reverse=True)[:limit]

        total_cost = sum(a["cost_micros"] for _, a in sorted_cities)
        cities = []
        for city, agg in sorted_cities:
            cost_usd = agg["cost_micros"] / 1_000_000
            conv_value_usd = agg["conv_value_micros"] / 1_000_000
            cities.append({
                "city": city,
                "clicks": agg["clicks"],
                "impressions": agg["impressions"],
                "cost_usd": round(cost_usd, 2),
                "conversions": round(agg["conversions"], 2),
                "ctr": round(agg["clicks"] / agg["impressions"] * 100, 2) if agg["impressions"] else 0,
                "cpc": round(cost_usd / agg["clicks"], 2) if agg["clicks"] else 0,
                "roas": round(conv_value_usd / cost_usd, 2) if cost_usd > 0 else 0,
                "share_cost_pct": round(agg["cost_micros"] / total_cost * 100, 1) if total_cost else 0,
            })

        return {"period_days": period_days, "cities": cities}

    # -----------------------------------------------------------------------
    # Dayparting — day-of-week performance analysis
    # -----------------------------------------------------------------------

    def get_demographic_breakdown(self, client_id: int, days: int = 30,
                                   date_from: date | None = None, date_to: date | None = None,
                                   campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Aggregate metrics by age range and gender, flag CPA anomalies."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"age_breakdown": [], "gender_breakdown": [], "anomalies": []}

        # Age breakdown
        age_data = (
            self.db.query(
                MetricSegmented.age_range,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.impressions).label("impressions"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
                func.sum(MetricSegmented.conversion_value_micros).label("value"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.age_range.isnot(None),
            )
            .group_by(MetricSegmented.age_range)
            .all()
        )

        # Gender breakdown
        gender_data = (
            self.db.query(
                MetricSegmented.gender,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.impressions).label("impressions"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
                func.sum(MetricSegmented.conversion_value_micros).label("value"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.gender.isnot(None),
            )
            .group_by(MetricSegmented.gender)
            .all()
        )

        def _build_breakdown(data):
            items = []
            total_cost = sum(int(r.cost or 0) for r in data)
            total_conv = sum(float(r.conv or 0) for r in data)
            avg_cpa = round(total_cost / total_conv / 1_000_000, 2) if total_conv > 0 else None

            for r in data:
                cost = int(r.cost or 0)
                conv = float(r.conv or 0)
                value = int(r.value or 0)
                cpa = round(cost / conv / 1_000_000, 2) if conv > 0 else None
                roas = round(value / cost, 2) if cost > 0 else None

                items.append({
                    "segment": r[0],  # age_range or gender
                    "clicks": int(r.clicks or 0),
                    "impressions": int(r.impressions or 0),
                    "cost_usd": round(cost / 1_000_000, 2),
                    "conversions": round(conv, 2),
                    "value_usd": round(value / 1_000_000, 2),
                    "cpa_usd": cpa,
                    "roas": roas,
                    "cost_share_pct": round(cost / total_cost * 100, 1) if total_cost > 0 else 0,
                })
            return items, avg_cpa

        # Parental status breakdown
        parental_data = (
            self.db.query(
                MetricSegmented.parental_status,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.impressions).label("impressions"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
                func.sum(MetricSegmented.conversion_value_micros).label("value"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.parental_status.isnot(None),
            )
            .group_by(MetricSegmented.parental_status)
            .all()
        )

        # Income range breakdown
        income_data = (
            self.db.query(
                MetricSegmented.income_range,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.impressions).label("impressions"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
                func.sum(MetricSegmented.conversion_value_micros).label("value"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.income_range.isnot(None),
            )
            .group_by(MetricSegmented.income_range)
            .all()
        )

        age_items, age_avg_cpa = _build_breakdown(age_data)
        gender_items, gender_avg_cpa = _build_breakdown(gender_data)
        parental_items, _ = _build_breakdown(parental_data)
        income_items, _ = _build_breakdown(income_data)

        # Detect anomalies: CPA > 2x average
        anomalies = []
        for item in age_items + gender_items:
            avg = age_avg_cpa if item in age_items else gender_avg_cpa
            if avg and item["cpa_usd"] and item["cpa_usd"] > avg * 2 and item["cost_usd"] >= 50:
                anomalies.append({
                    "segment": item["segment"],
                    "cpa_usd": item["cpa_usd"],
                    "avg_cpa_usd": avg,
                    "multiplier": round(item["cpa_usd"] / avg, 1),
                    "cost_usd": item["cost_usd"],
                    "conversions": item["conversions"],
                })

        return {
            "age_breakdown": sorted(age_items, key=lambda x: x["cost_usd"], reverse=True),
            "gender_breakdown": sorted(gender_items, key=lambda x: x["cost_usd"], reverse=True),
            "parental_breakdown": sorted(parental_items, key=lambda x: x["cost_usd"], reverse=True),
            "income_breakdown": sorted(income_items, key=lambda x: x["cost_usd"], reverse=True),
            "anomalies": anomalies,
            "avg_cpa_usd": age_avg_cpa,
            "period_days": (date_to - date_from).days,
        }

    # -----------------------------------------------------------------------
    # PMax Channel Breakdown
    # -----------------------------------------------------------------------
