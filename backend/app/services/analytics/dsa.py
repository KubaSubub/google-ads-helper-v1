"""Dynamic Search Ads targets, coverage, headlines, overlap.

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


class DSAMixin:
    def get_dsa_targets(self, client_id: int, campaign_type: str | None = None,
                        campaign_status: str | None = None) -> list[dict]:
        """List DSA targets with performance metrics."""
        from app.models.dsa_target import DsaTarget

        q = self.db.query(DsaTarget).filter(DsaTarget.client_id == client_id)

        # Optionally filter by campaign type/status via campaign join
        if campaign_type or campaign_status:
            campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
            if not campaign_ids:
                return []
            q = q.filter(DsaTarget.campaign_id.in_(campaign_ids))

        targets = q.all()
        result = []
        for t in targets:
            cost = (t.cost_micros or 0) / 1_000_000
            impr = t.impressions or 0
            clicks = t.clicks or 0
            conv = t.conversions or 0.0
            result.append({
                "id": t.id,
                "campaign_id": t.campaign_id,
                "campaign_name": t.campaign.name if t.campaign else None,
                "target_type": t.target_type,
                "target_value": t.target_value,
                "status": t.status,
                "clicks": clicks,
                "impressions": impr,
                "cost_usd": round(cost, 2),
                "conversions": round(conv, 2),
                "ctr": round(clicks / impr * 100, 2) if impr else 0,
                "cpa": round(cost / conv, 2) if conv > 0 else 0,
            })
        result.sort(key=lambda x: x["cost_usd"], reverse=True)
        return result

    def get_dsa_coverage(self, client_id: int) -> dict:
        """DSA coverage: which campaigns are DSA and target counts."""
        from app.models.dsa_target import DsaTarget

        # Find DSA campaigns (campaign_subtype == 'SEARCH_DYNAMIC_ADS')
        dsa_campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id,
                    Campaign.campaign_subtype == "SEARCH_DYNAMIC_ADS")
            .all()
        )
        all_search = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id,
                    Campaign.campaign_type == "SEARCH")
            .count()
        )

        campaigns_info = []
        for c in dsa_campaigns:
            target_count = (
                self.db.query(func.count(DsaTarget.id))
                .filter(DsaTarget.campaign_id == c.id)
                .scalar()
            ) or 0
            campaigns_info.append({
                "campaign_id": c.id,
                "campaign_name": c.name,
                "status": c.status,
                "target_count": target_count,
            })

        return {
            "total_search_campaigns": all_search,
            "dsa_campaign_count": len(dsa_campaigns),
            "dsa_campaigns": campaigns_info,
        }

    # -----------------------------------------------------------------------
    # C2: DSA Headlines
    # -----------------------------------------------------------------------

    def get_dsa_headlines(self, client_id: int, days: int = 30,
                          date_from: date | None = None, date_to: date | None = None,
                          campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """List DSA auto-generated headlines with metrics."""
        from app.models.dsa_headline import DsaHeadline
        from app.utils.date_utils import resolve_dates as _rd

        start, end = _rd(days, date_from, date_to)

        q = self.db.query(DsaHeadline).filter(DsaHeadline.client_id == client_id)

        if campaign_type or campaign_status:
            campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
            if not campaign_ids:
                return {"period_days": (end - start).days, "headlines": []}
            q = q.filter(DsaHeadline.campaign_id.in_(campaign_ids))

        # Date filter
        q = q.filter(DsaHeadline.date >= start, DsaHeadline.date <= end)

        rows = q.all()
        # Aggregate by (search_term_text, generated_headline, landing_page_url)
        agg: dict[tuple, dict] = {}
        for r in rows:
            key = (r.search_term_text, r.generated_headline, r.landing_page_url)
            if key not in agg:
                agg[key] = {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0,
                            "campaign_id": r.campaign_id,
                            "campaign_name": r.campaign.name if r.campaign else None}
            agg[key]["clicks"] += r.clicks or 0
            agg[key]["impressions"] += r.impressions or 0
            agg[key]["cost_micros"] += r.cost_micros or 0
            agg[key]["conversions"] += r.conversions or 0.0

        headlines = []
        for (term, headline, url), m in agg.items():
            cost = m["cost_micros"] / 1_000_000
            impr = m["impressions"]
            clicks = m["clicks"]
            conv = m["conversions"]
            headlines.append({
                "search_term": term,
                "generated_headline": headline,
                "landing_page_url": url,
                "campaign_id": m["campaign_id"],
                "campaign_name": m["campaign_name"],
                "clicks": clicks,
                "impressions": impr,
                "cost_usd": round(cost, 2),
                "conversions": round(conv, 2),
                "ctr": round(clicks / impr * 100, 2) if impr else 0,
                "cpa": round(cost / conv, 2) if conv > 0 else 0,
            })
        headlines.sort(key=lambda x: x["clicks"], reverse=True)
        return {"period_days": (end - start).days, "headlines": headlines}

    # -----------------------------------------------------------------------
    # C3: DSA-Search Overlap
    # -----------------------------------------------------------------------

    def get_dsa_search_overlap(self, client_id: int, days: int = 30,
                                date_from: date | None = None, date_to: date | None = None) -> dict:
        """Find search terms that appear in both DSA and standard Search campaigns."""
        from app.models.search_term import SearchTerm
        from app.utils.date_utils import resolve_dates as _rd

        start, end = _rd(days, date_from, date_to)

        # Identify DSA campaign IDs
        dsa_campaign_ids = [
            c.id for c in
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id,
                    Campaign.campaign_subtype == "SEARCH_DYNAMIC_ADS")
            .all()
        ]

        # Standard search campaign IDs (not DSA)
        standard_campaign_ids = [
            c.id for c in
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id,
                    Campaign.campaign_type == "SEARCH",
                    (Campaign.campaign_subtype == None) | (Campaign.campaign_subtype != "SEARCH_DYNAMIC_ADS"))
            .all()
        ]

        if not dsa_campaign_ids or not standard_campaign_ids:
            return {"period_days": (end - start).days, "overlapping_terms": [],
                    "dsa_only_count": 0, "search_only_count": 0, "overlap_count": 0}

        # Gather search term texts per bucket
        dsa_terms_q = (
            self.db.query(SearchTerm.text,
                          func.sum(SearchTerm.clicks).label("clicks"),
                          func.sum(SearchTerm.cost_micros).label("cost_micros"),
                          func.sum(SearchTerm.conversions).label("conversions"))
            .filter(SearchTerm.campaign_id.in_(dsa_campaign_ids),
                    SearchTerm.date_from >= start)
            .group_by(SearchTerm.text)
            .all()
        )

        standard_terms_q = (
            self.db.query(SearchTerm.text,
                          func.sum(SearchTerm.clicks).label("clicks"),
                          func.sum(SearchTerm.cost_micros).label("cost_micros"),
                          func.sum(SearchTerm.conversions).label("conversions"))
            .filter(SearchTerm.campaign_id.in_(standard_campaign_ids),
                    SearchTerm.date_from >= start)
            .group_by(SearchTerm.text)
            .all()
        )

        dsa_map = {r.text: {"clicks": r.clicks or 0, "cost_micros": r.cost_micros or 0,
                             "conversions": r.conversions or 0.0} for r in dsa_terms_q}
        std_map = {r.text: {"clicks": r.clicks or 0, "cost_micros": r.cost_micros or 0,
                            "conversions": r.conversions or 0.0} for r in standard_terms_q}

        overlap_texts = set(dsa_map.keys()) & set(std_map.keys())

        overlapping_terms = []
        for text in overlap_texts:
            d = dsa_map[text]
            s = std_map[text]
            d_cost = d["cost_micros"] / 1_000_000
            s_cost = s["cost_micros"] / 1_000_000
            overlapping_terms.append({
                "search_term": text,
                "dsa_clicks": d["clicks"],
                "dsa_cost_usd": round(d_cost, 2),
                "dsa_conversions": round(d["conversions"], 2),
                "search_clicks": s["clicks"],
                "search_cost_usd": round(s_cost, 2),
                "search_conversions": round(s["conversions"], 2),
                "total_cost_usd": round(d_cost + s_cost, 2),
                "recommendation": "Consider negative keyword in DSA" if s["conversions"] > d["conversions"]
                    else "DSA outperforms — consider pausing Search keyword",
            })
        overlapping_terms.sort(key=lambda x: x["total_cost_usd"], reverse=True)

        return {
            "period_days": (end - start).days,
            "dsa_only_count": len(set(dsa_map.keys()) - set(std_map.keys())),
            "search_only_count": len(set(std_map.keys()) - set(dsa_map.keys())),
            "overlap_count": len(overlap_texts),
            "overlapping_terms": overlapping_terms,
        }


INDUSTRY_BENCHMARKS = {
    "E-commerce": {"ctr": 2.69, "cpc": 1.16, "cpa": 45.27, "cvr": 2.81, "roas": 4.0},
    "Food": {"ctr": 3.11, "cpc": 0.78, "cpa": 29.42, "cvr": 3.65, "roas": 5.5},
    "Legal": {"ctr": 1.35, "cpc": 6.75, "cpa": 86.02, "cvr": 1.95, "roas": 2.0},
    "Finance": {"ctr": 2.65, "cpc": 3.44, "cpa": 56.76, "cvr": 3.23, "roas": 3.5},
    "Health": {"ctr": 3.27, "cpc": 2.62, "cpa": 78.09, "cvr": 2.89, "roas": 3.0},
    "Education": {"ctr": 3.78, "cpc": 2.40, "cpa": 72.70, "cvr": 3.39, "roas": 3.2},
    "Technology": {"ctr": 2.09, "cpc": 3.80, "cpa": 133.52, "cvr": 2.18, "roas": 3.8},
    "Real Estate": {"ctr": 3.71, "cpc": 2.37, "cpa": 116.61, "cvr": 2.47, "roas": 2.5},
    "Travel": {"ctr": 4.68, "cpc": 1.53, "cpa": 44.73, "cvr": 3.55, "roas": 5.0},
    "Automotive": {"ctr": 4.00, "cpc": 2.46, "cpa": 33.52, "cvr": 3.45, "roas": 4.5},
    "default": {"ctr": 3.17, "cpc": 2.69, "cpa": 48.96, "cvr": 3.75, "roas": 4.0},
}
