"""Quality Score audit, RSA / n-gram / match type / landing pages + conversion health.

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


class QualityMixin:
    def get_rsa_analysis(
        self, client_id: int,
        campaign_type: str | None = None, campaign_status: str | None = None,
    ) -> dict:
        """Analyze RSA ad performance per ad group."""
        from app.models.ad import Ad
        from app.models.ad_group import AdGroup

        campaign_q = self._filter_campaigns(client_id, campaign_type or "SEARCH", campaign_status)
        campaign_ids = [c.id for c in campaign_q.all()]
        if not campaign_ids:
            return {"ad_groups": []}

        ads = (
            self.db.query(Ad)
            .join(AdGroup, Ad.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids))
            .all()
        )

        # Pre-fetch all ad group names in one query
        ag_ids = set(ad.ad_group_id for ad in ads)
        ag_rows = (
            self.db.query(AdGroup.id, AdGroup.name)
            .filter(AdGroup.id.in_(ag_ids))
            .all()
        ) if ag_ids else []
        ag_cache = {row.id: row.name for row in ag_rows}

        by_group: dict[int, dict] = {}
        for ad in ads:
            gid = ad.ad_group_id
            if gid not in by_group:
                by_group[gid] = {"ad_group_name": ag_cache.get(gid, "Unknown"), "ads": []}

            headlines = ad.headlines or []
            descriptions = ad.descriptions or []
            cost = (ad.cost_micros or 0) / 1_000_000
            ctr_pct = ad.ctr or 0  # already percentage

            by_group[gid]["ads"].append({
                "id": ad.id,
                "status": ad.status,
                "approval_status": ad.approval_status,
                "ad_strength": ad.ad_strength,
                "headline_count": len(headlines),
                "description_count": len(descriptions),
                "headlines": [
                    h.get("text", h) if isinstance(h, dict) else str(h)
                    for h in headlines[:5]
                ],
                "descriptions": [
                    d.get("text", d) if isinstance(d, dict) else str(d)
                    for d in descriptions[:3]
                ],
                "pinned_count": sum(
                    1 for h in headlines
                    if isinstance(h, dict) and h.get("pinned_position")
                ),
                "clicks": ad.clicks or 0,
                "impressions": ad.impressions or 0,
                "cost_usd": round(cost, 2),
                "conversions": ad.conversions or 0,
                "ctr_pct": round(ctr_pct, 2),
                "cpc_usd": round(cost / (ad.clicks or 1), 2),
            })

        groups = []
        for gid, data in by_group.items():
            ads_list = data["ads"]
            if not ads_list:
                continue
            ctrs = [a["ctr_pct"] for a in ads_list if a["impressions"] > 0]
            best_ctr = max(ctrs) if ctrs else 0
            worst_ctr = min(ctrs) if ctrs else 0
            groups.append({
                "ad_group_id": gid,
                "ad_group_name": data["ad_group_name"],
                "ad_count": len(ads_list),
                "best_ctr": best_ctr,
                "worst_ctr": worst_ctr,
                "ctr_spread": round(best_ctr - worst_ctr, 2),
                "ads": sorted(ads_list, key=lambda a: a["ctr_pct"], reverse=True),
            })

        return {
            "ad_groups": sorted(groups, key=lambda g: g["ctr_spread"], reverse=True),
        }

    # -----------------------------------------------------------------------
    # N-gram Analysis — word-level search term aggregation
    # -----------------------------------------------------------------------

    def get_ngram_analysis(
        self, client_id: int, ngram_size: int = 1, min_occurrences: int = 2,
        campaign_type: str | None = None, campaign_status: str | None = None,
    ) -> dict:
        """Aggregate search term metrics by word/n-gram."""
        from app.models.search_term import SearchTerm
        from app.models.ad_group import AdGroup
        from collections import defaultdict
        from sqlalchemy import or_

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"ngrams": [], "ngram_size": ngram_size}

        # SEARCH terms link via ad_group_id, PMax terms link via campaign_id
        terms = (
            self.db.query(SearchTerm)
            .outerjoin(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .join(
                Campaign,
                or_(
                    SearchTerm.campaign_id == Campaign.id,
                    AdGroup.campaign_id == Campaign.id,
                ),
            )
            .filter(Campaign.id.in_(campaign_ids))
            .all()
        )

        stats: dict[str, dict] = defaultdict(
            lambda: {"clicks": 0, "impressions": 0, "cost_micros": 0,
                      "conversions": 0.0, "count": 0}
        )
        for term in terms:
            words = term.text.lower().split()
            for i in range(len(words) - ngram_size + 1):
                ngram = " ".join(words[i:i + ngram_size])
                if len(ngram) < 2:
                    continue
                stats[ngram]["clicks"] += term.clicks or 0
                stats[ngram]["impressions"] += term.impressions or 0
                stats[ngram]["cost_micros"] += term.cost_micros or 0
                stats[ngram]["conversions"] += term.conversions or 0
                stats[ngram]["count"] += 1

        results = []
        for ngram, s in stats.items():
            if s["count"] < min_occurrences:
                continue
            cost = s["cost_micros"] / 1_000_000
            results.append({
                "ngram": ngram,
                "occurrences": s["count"],
                "clicks": s["clicks"],
                "impressions": s["impressions"],
                "cost_usd": round(cost, 2),
                "conversions": round(s["conversions"], 2),
                "ctr": round(s["clicks"] / s["impressions"] * 100, 2) if s["impressions"] else 0,
                "cvr": round(s["conversions"] / s["clicks"] * 100, 2) if s["clicks"] else 0,
                "cpa": round(cost / s["conversions"], 2) if s["conversions"] else 0,
            })

        results.sort(key=lambda x: x["cost_usd"], reverse=True)
        return {"ngram_size": ngram_size, "total": len(results), "ngrams": results[:100]}

    # -----------------------------------------------------------------------
    # Match Type Analysis — keyword performance by match type
    # -----------------------------------------------------------------------

    def get_match_type_analysis(self, client_id: int, days: int = 30,
                               date_from: date | None = None, date_to: date | None = None,
                               campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Compare keyword performance grouped by match type using KeywordDaily."""
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)
        if not campaign_ids:
            return {"period_days": period_days, "match_types": []}

        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids))
            .all()
        )
        kw_match = {kw.id: kw.match_type for kw in keywords}
        kw_ids = list(kw_match.keys())
        if not kw_ids:
            return {"period_days": period_days, "match_types": []}

        daily = (
            self.db.query(KeywordDaily)
            .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from, KeywordDaily.date <= date_to)
            .all()
        )

        mt_agg: dict[str, dict] = {}
        mt_kws: dict[str, set] = {}
        for r in daily:
            mt = kw_match.get(r.keyword_id, "UNKNOWN")
            if mt not in mt_agg:
                mt_agg[mt] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                              "conversions": 0.0, "conv_value_micros": 0}
                mt_kws[mt] = set()
            mt_agg[mt]["clicks"] += r.clicks or 0
            mt_agg[mt]["impressions"] += r.impressions or 0
            mt_agg[mt]["cost_micros"] += r.cost_micros or 0
            mt_agg[mt]["conversions"] += r.conversions or 0
            mt_agg[mt]["conv_value_micros"] += r.conversion_value_micros or 0
            mt_kws[mt].add(r.keyword_id)

        total_cost = sum(a["cost_micros"] for a in mt_agg.values())
        match_types = []
        for mt, a in mt_agg.items():
            cost = a["cost_micros"] / 1_000_000
            cv = a["conv_value_micros"] / 1_000_000
            match_types.append({
                "match_type": mt,
                "keyword_count": len(mt_kws.get(mt, set())),
                "clicks": a["clicks"],
                "impressions": a["impressions"],
                "cost_usd": round(cost, 2),
                "conversions": round(a["conversions"], 2),
                "ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0,
                "cpc": round(cost / a["clicks"], 2) if a["clicks"] else 0,
                "cpa": round(cost / a["conversions"], 2) if a["conversions"] else 0,
                "roas": round(cv / cost, 2) if cost > 0 else 0,
                "cvr": round(a["conversions"] / a["clicks"] * 100, 2) if a["clicks"] else 0,
                "cost_share_pct": round(a["cost_micros"] / total_cost * 100, 1) if total_cost else 0,
            })
        match_types.sort(key=lambda x: x["cost_usd"], reverse=True)
        return {"period_days": period_days, "match_types": match_types}

    # -----------------------------------------------------------------------
    # Landing Page Analysis — performance by final URL
    # -----------------------------------------------------------------------

    def get_landing_page_analysis(self, client_id: int, days: int = 30,
                                 date_from: date | None = None, date_to: date | None = None,
                                 campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Aggregate keyword metrics grouped by landing page (final_url)."""
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"period_days": period_days, "pages": []}

        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids))
            .all()
        )
        kw_url = {kw.id: kw.final_url or "brak URL" for kw in keywords}
        kw_ids = list(kw_url.keys())
        if not kw_ids:
            return {"period_days": period_days, "pages": []}

        daily = (
            self.db.query(KeywordDaily)
            .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from, KeywordDaily.date <= date_to)
            .all()
        )

        url_agg: dict[str, dict] = {}
        url_kws: dict[str, set] = {}
        for r in daily:
            url = kw_url.get(r.keyword_id, "brak URL")
            if url not in url_agg:
                url_agg[url] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                "conversions": 0.0, "conv_value_micros": 0}
                url_kws[url] = set()
            url_agg[url]["clicks"] += r.clicks or 0
            url_agg[url]["impressions"] += r.impressions or 0
            url_agg[url]["cost_micros"] += r.cost_micros or 0
            url_agg[url]["conversions"] += r.conversions or 0
            url_agg[url]["conv_value_micros"] += r.conversion_value_micros or 0
            url_kws[url].add(r.keyword_id)

        pages = []
        for url, a in url_agg.items():
            cost = a["cost_micros"] / 1_000_000
            cv = a["conv_value_micros"] / 1_000_000
            pages.append({
                "url": url,
                "keyword_count": len(url_kws.get(url, set())),
                "clicks": a["clicks"],
                "impressions": a["impressions"],
                "cost_usd": round(cost, 2),
                "conversions": round(a["conversions"], 2),
                "ctr": round(a["clicks"] / a["impressions"] * 100, 2) if a["impressions"] else 0,
                "cvr": round(a["conversions"] / a["clicks"] * 100, 2) if a["clicks"] else 0,
                "cpa": round(cost / a["conversions"], 2) if a["conversions"] else 0,
                "roas": round(cv / cost, 2) if cost > 0 else 0,
            })
        pages.sort(key=lambda x: x["cost_usd"], reverse=True)
        return {"period_days": period_days, "pages": pages}

    # -----------------------------------------------------------------------
    # Wasted Spend Summary — total waste across all entities
    # -----------------------------------------------------------------------

    def get_conversion_tracking_health(self, client_id: int, days: int = 30,
                                       date_from: date | None = None, date_to: date | None = None,
                                       campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Audit conversion tracking setup and data quality."""
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaigns = self._filter_campaigns(client_id, campaign_type, campaign_status or "ENABLED").all()
        if not campaigns:
            return {"status": "no_campaigns", "campaigns": [], "score": 0}

        campaign_ids = [c.id for c in campaigns]
        results = []
        total_score = 0

        for c in campaigns:
            metrics = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == c.id,
                MetricDaily.date >= date_from,
                MetricDaily.date <= date_to,
            ).all()

            total_cost = sum(m.cost_micros or 0 for m in metrics) / 1_000_000
            total_conv = sum(m.conversions or 0 for m in metrics)
            total_clicks = sum(m.clicks or 0 for m in metrics)
            conv_value = sum(m.conversion_value_micros or 0 for m in metrics) / 1_000_000
            days_with_data = len(metrics)

            # Scoring
            issues = []
            camp_score = 100

            if total_cost > 50 and total_conv == 0:
                issues.append("Wydatki bez konwersji")
                camp_score -= 40

            if total_conv > 0 and conv_value == 0:
                issues.append("Konwersje bez wartości")
                camp_score -= 20

            conv_rate = total_conv / total_clicks if total_clicks else 0
            if conv_rate > 0.5:
                issues.append(f"Podejrzanie wysoki CVR ({round(conv_rate*100,1)}%)")
                camp_score -= 15

            if days_with_data < period_days * 0.5:
                issues.append(f"Braki danych ({days_with_data}/{period_days} dni)")
                camp_score -= 15

            camp_score = max(0, camp_score)
            total_score += camp_score

            results.append({
                "campaign_name": c.name,
                "campaign_type": c.campaign_type,
                "cost_usd": round(total_cost, 2),
                "conversions": round(total_conv, 2),
                "conversion_value_usd": round(conv_value, 2),
                "conv_rate_pct": round(conv_rate * 100, 2),
                "days_with_data": days_with_data,
                "score": camp_score,
                "issues": issues,
            })

        avg_score = round(total_score / len(campaigns)) if campaigns else 0

        return {
            "score": avg_score,
            "status": "healthy" if avg_score >= 80 else "warning" if avg_score >= 50 else "critical",
            "campaigns": sorted(results, key=lambda x: x["score"]),
            "total_campaigns": len(campaigns),
            "period_days": period_days,
        }

    # ------------------------------------------------------------------
    # G2: Keyword Expansion Suggestions
    # ------------------------------------------------------------------

    def get_conversion_quality_audit(self, client_id: int) -> dict:
        """Audit conversion action configuration for data quality issues."""
        from app.models.conversion_action import ConversionAction

        actions = (
            self.db.query(ConversionAction)
            .filter(ConversionAction.client_id == client_id)
            .all()
        )
        if not actions:
            return {"total_actions": 0, "issues": [], "actions": [], "quality_score": 100}

        issues = []
        action_data = []

        primary_count = sum(1 for a in actions if a.primary_for_goal)
        secondary_in_metric = [a for a in actions if not a.primary_for_goal and a.include_in_conversions_metric]

        # 2A: Primary vs secondary confusion
        if secondary_in_metric:
            issues.append({
                "type": "SECONDARY_IN_METRIC",
                "severity": "HIGH",
                "detail": f"{len(secondary_in_metric)} drugorzedne konwersje wliczane do metryki 'Konwersje'",
                "affected": [a.name for a in secondary_in_metric],
            })

        # Get tROAS campaigns
        troas_campaigns = (
            self.db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.bidding_strategy.in_(["TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE"]),
            )
            .all()
        )

        # 2B: Zero-value conversions sabotaging tROAS
        zero_value_primary = [a for a in actions if a.primary_for_goal and (a.value_settings_default_value or 0) == 0 and not a.value_settings_always_use_default]
        if zero_value_primary and troas_campaigns:
            issues.append({
                "type": "ZERO_VALUE_TROAS",
                "severity": "HIGH",
                "detail": f"{len(zero_value_primary)} konwersji primary bez wartosci przy kampaniach tROAS",
                "affected": [a.name for a in zero_value_primary],
            })

        # 2C: MANY_PER_CLICK for PURCHASE (double counting risk)
        purchase_many = [a for a in actions if a.category == "PURCHASE" and a.counting_type == "MANY_PER_CLICK"]
        if purchase_many:
            issues.append({
                "type": "DOUBLE_COUNTING_RISK",
                "severity": "MEDIUM",
                "detail": f"{len(purchase_many)} konwersji PURCHASE z 'MANY_PER_CLICK' (ryzyko podwojnego liczenia)",
                "affected": [a.name for a in purchase_many],
            })

        # 2D: Lookback window mismatch
        short_lookback = [a for a in actions if a.click_through_lookback_window_days and a.click_through_lookback_window_days < 7]
        long_lookback = [a for a in actions if a.click_through_lookback_window_days and a.click_through_lookback_window_days > 30]
        if short_lookback:
            issues.append({
                "type": "SHORT_LOOKBACK",
                "severity": "MEDIUM",
                "detail": f"{len(short_lookback)} konwersji z oknem < 7 dni",
                "affected": [a.name for a in short_lookback],
            })
        if long_lookback:
            issues.append({
                "type": "LONG_LOOKBACK",
                "severity": "LOW",
                "detail": f"{len(long_lookback)} konwersji z oknem > 30 dni",
                "affected": [a.name for a in long_lookback],
            })

        for a in actions:
            action_data.append({
                "id": a.id,
                "name": a.name,
                "category": a.category,
                "primary_for_goal": a.primary_for_goal,
                "counting_type": a.counting_type,
                "value_default": a.value_settings_default_value,
                "always_use_default": a.value_settings_always_use_default,
                "attribution_model": a.attribution_model,
                "lookback_days": a.click_through_lookback_window_days,
                "include_in_metric": a.include_in_conversions_metric,
                "conversions": a.conversions or 0,
            })

        # Quality score: 100 minus penalty per issue
        penalty = sum(30 if i["severity"] == "HIGH" else 15 if i["severity"] == "MEDIUM" else 5 for i in issues)
        quality_score = max(0, 100 - penalty)

        return {
            "total_actions": len(actions),
            "primary_count": primary_count,
            "issues": issues,
            "actions": action_data,
            "quality_score": quality_score,
        }

    # -------------------------------------------------------------------
    # GAP 4A: Age/Gender CPA Anomaly
    # -------------------------------------------------------------------
