"""Campaign comparison, benchmarks, client comparison.

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


class ComparisonMixin:
    def get_campaign_comparison(self, client_id: int, campaign_ids: list[int],
                                 days: int = 30,
                                 date_from: date | None = None,
                                 date_to: date | None = None) -> dict:
        """Side-by-side comparison of selected campaigns with all key metrics.

        For each campaign: aggregates MetricDaily in the date range and
        calculates derived metrics (CTR, CPC, CPA, ROAS, CVR).
        """
        from app.utils.date_utils import resolve_dates as _rd
        start, end = _rd(days, date_from, date_to)

        # Validate campaigns belong to client
        campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.id.in_(campaign_ids))
            .all()
        )
        if not campaigns:
            return {"campaigns": [], "period_days": (end - start).days}

        campaign_map = {c.id: c for c in campaigns}
        valid_ids = list(campaign_map.keys())

        # Aggregate MetricDaily per campaign
        rows = (
            self.db.query(
                MetricDaily.campaign_id,
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impressions"),
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
                func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
                func.avg(MetricDaily.search_impression_share).label("avg_impression_share"),
                func.avg(MetricDaily.search_budget_lost_is).label("avg_budget_lost_is"),
                func.avg(MetricDaily.search_rank_lost_is).label("avg_rank_lost_is"),
            )
            .filter(
                MetricDaily.campaign_id.in_(valid_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .group_by(MetricDaily.campaign_id)
            .all()
        )

        metrics_map = {r.campaign_id: r for r in rows}

        result = []
        for cid in valid_ids:
            c = campaign_map[cid]
            r = metrics_map.get(cid)

            if r:
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

                avg_is = r.avg_impression_share
                avg_budget_lost = r.avg_budget_lost_is
                avg_rank_lost = r.avg_rank_lost_is
            else:
                clicks = impressions = 0
                cost_usd = conv_value_usd = 0
                conversions = ctr = cpc = cpa = roas = cvr = 0
                avg_is = avg_budget_lost = avg_rank_lost = None

            result.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "campaign_type": c.campaign_type,
                "status": c.status,
                "budget_daily_usd": round((c.budget_micros or 0) / 1_000_000, 2),
                "bidding_strategy": c.bidding_strategy,
                "clicks": clicks,
                "impressions": impressions,
                "cost_usd": round(cost_usd, 2),
                "conversions": round(conversions, 2),
                "conversion_value_usd": round(conv_value_usd, 2),
                "ctr": round(ctr, 2),
                "cpc_usd": round(cpc, 2),
                "cpa_usd": round(cpa, 2),
                "roas": round(roas, 2),
                "cvr": round(cvr, 2),
                "avg_impression_share": round((avg_is or 0) * 100, 1),
                "avg_budget_lost_is": round((avg_budget_lost or 0) * 100, 1),
                "avg_rank_lost_is": round((avg_rank_lost or 0) * 100, 1),
            })

        return {
            "campaigns": result,
            "period_days": (end - start).days,
            "date_from": str(start),
            "date_to": str(end),
        }

    # ------------------------------------------------------------------
    # H2: Industry Benchmarks
    # ------------------------------------------------------------------

    def get_benchmarks(self, client_id: int, days: int = 30) -> dict:
        """Compare client metrics against industry benchmarks.

        Returns client's actual CTR/CPC/CPA/CVR/ROAS alongside industry
        averages, with per-metric verdict (above / below / on_par).
        """
        from app.models.client import Client

        client = self.db.get(Client, client_id)
        if not client:
            return {"error": "Client not found"}

        industry = client.industry or "default"
        bench = INDUSTRY_BENCHMARKS.get(industry, INDUSTRY_BENCHMARKS["default"])

        # Aggregate client metrics from MetricDaily
        today = date.today()
        start = today - timedelta(days=days)

        campaign_ids = [
            c.id for c in
            self.db.query(Campaign).filter(Campaign.client_id == client_id).all()
        ]

        if not campaign_ids:
            return {
                "industry": industry,
                "days": days,
                "client_metrics": {},
                "benchmark_metrics": bench,
                "comparison": [],
            }

        row = self.db.query(
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
        ).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= start,
        ).first()

        clicks = row.clicks or 0
        impressions = row.impressions or 0
        cost_micros = row.cost_micros or 0
        conversions = row.conversions or 0.0
        conv_value_micros = row.conv_value_micros or 0

        cost = cost_micros / 1_000_000
        conv_value = conv_value_micros / 1_000_000

        client_metrics = {
            "ctr": round((clicks / impressions * 100) if impressions else 0, 2),
            "cpc": round((cost / clicks) if clicks else 0, 2),
            "cpa": round((cost / conversions) if conversions else 0, 2),
            "cvr": round((conversions / clicks * 100) if clicks else 0, 2),
            "roas": round((conv_value / cost) if cost else 0, 2),
        }

        comparison = []
        for metric_key in ("ctr", "cpc", "cpa", "cvr", "roas"):
            client_val = client_metrics[metric_key]
            bench_val = bench[metric_key]

            if bench_val == 0:
                pct_diff = 0.0
            else:
                pct_diff = round((client_val - bench_val) / bench_val * 100, 1)

            # For CPC and CPA lower is better; for CTR, CVR, ROAS higher is better
            if metric_key in ("cpc", "cpa"):
                if pct_diff < -10:
                    verdict = "above"   # spending less = good
                elif pct_diff > 10:
                    verdict = "below"   # spending more = bad
                else:
                    verdict = "on_par"
            else:
                if pct_diff > 10:
                    verdict = "above"
                elif pct_diff < -10:
                    verdict = "below"
                else:
                    verdict = "on_par"

            comparison.append({
                "metric": metric_key,
                "client_value": client_val,
                "benchmark_value": bench_val,
                "pct_diff": pct_diff,
                "verdict": verdict,
            })

        return {
            "industry": industry,
            "days": days,
            "client_metrics": client_metrics,
            "benchmark_metrics": bench,
            "comparison": comparison,
        }

    def get_client_comparison(self, days: int = 30) -> list:
        """MCC view: compare ALL clients' KPIs side-by-side.

        Returns a list of clients with their aggregated metrics,
        sorted by ROAS descending.
        """
        from app.models.client import Client

        today = date.today()
        start = today - timedelta(days=days)

        clients = self.db.query(Client).all()
        results = []

        for client in clients:
            campaign_ids = [
                c.id for c in
                self.db.query(Campaign).filter(Campaign.client_id == client.id).all()
            ]

            if not campaign_ids:
                results.append({
                    "client_id": client.id,
                    "client_name": client.name,
                    "industry": client.industry or "default",
                    "clicks": 0,
                    "impressions": 0,
                    "cost_usd": 0,
                    "conversions": 0,
                    "conversion_value_usd": 0,
                    "ctr": 0,
                    "cpc": 0,
                    "cpa": 0,
                    "cvr": 0,
                    "roas": 0,
                })
                continue

            row = self.db.query(
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impressions"),
                func.sum(MetricDaily.cost_micros).label("cost_micros"),
                func.sum(MetricDaily.conversions).label("conversions"),
                func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
            ).filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
            ).first()

            clicks = row.clicks or 0
            impressions = row.impressions or 0
            cost_micros = row.cost_micros or 0
            conversions = row.conversions or 0.0
            conv_value_micros = row.conv_value_micros or 0

            cost = cost_micros / 1_000_000
            conv_value = conv_value_micros / 1_000_000

            results.append({
                "client_id": client.id,
                "client_name": client.name,
                "industry": client.industry or "default",
                "clicks": clicks,
                "impressions": impressions,
                "cost_usd": round(cost, 2),
                "conversions": round(conversions, 2),
                "conversion_value_usd": round(conv_value, 2),
                "ctr": round((clicks / impressions * 100) if impressions else 0, 2),
                "cpc": round((cost / clicks) if clicks else 0, 2),
                "cpa": round((cost / conversions) if conversions else 0, 2),
                "cvr": round((conversions / clicks * 100) if clicks else 0, 2),
                "roas": round((conv_value / cost) if cost else 0, 2),
            })

        # Sort by ROAS descending
        results.sort(key=lambda x: x["roas"], reverse=True)

        return results


# ---------------------------------------------------------------------------
# Industry Benchmarks (hardcoded averages)
# ---------------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # C1: DSA Targets Analysis
    # -----------------------------------------------------------------------
