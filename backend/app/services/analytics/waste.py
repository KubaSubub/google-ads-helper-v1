"""Wasted spend, account structure audit, search term trends, close variants, keyword expansion.

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


class WasteMixin:
    def get_wasted_spend(self, client_id: int, days: int = 30,
                         date_from: date | None = None, date_to: date | None = None,
                         campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Calculate wasted spend: keywords, search terms, ads with 0 conversions."""
        from app.models.search_term import SearchTerm
        from app.models.ad import Ad
        from app.models.ad_group import AdGroup
        from app.models.keyword_daily import KeywordDaily
        from sqlalchemy import or_
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"period_days": period_days, "total_waste_usd": 0, "total_spend_usd": 0,
                    "waste_pct": 0, "categories": {}}

        # Total spend for context
        total_spend_micros = (
            self.db.query(func.sum(MetricDaily.cost_micros))
            .filter(MetricDaily.campaign_id.in_(campaign_ids), MetricDaily.date >= date_from, MetricDaily.date <= date_to)
            .scalar()
        ) or 0
        total_spend = total_spend_micros / 1_000_000

        # 1. Keywords: 0 conversions + clicks >= 5 (from KeywordDaily)
        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids), Keyword.status == "ENABLED")
            .all()
        )
        kw_ids = [kw.id for kw in keywords]
        kw_map = {kw.id: kw.text for kw in keywords}

        kw_waste = 0.0
        kw_waste_items = []
        if kw_ids:
            kw_daily = (
                self.db.query(
                    KeywordDaily.keyword_id,
                    func.sum(KeywordDaily.clicks).label("clicks"),
                    func.sum(KeywordDaily.cost_micros).label("cost_micros"),
                    func.sum(KeywordDaily.conversions).label("conversions"),
                )
                .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from, KeywordDaily.date <= date_to)
                .group_by(KeywordDaily.keyword_id)
                .all()
            )
            for row in kw_daily:
                if (row.conversions or 0) == 0 and (row.clicks or 0) >= 5:
                    cost = (row.cost_micros or 0) / 1_000_000
                    kw_waste += cost
                    kw_waste_items.append({
                        "text": kw_map.get(row.keyword_id, "?"),
                        "clicks": row.clicks or 0,
                        "cost_usd": round(cost, 2),
                    })

        # 2. Search terms: 0 conversions + clicks >= 3 (filtered by date bucket)
        # Search terms have cumulative metrics for their entire date_from..date_to range.
        # We filter by date_from >= requested start so only terms whose reporting
        # period begins within the selected window are included.
        st_waste = 0.0
        st_waste_count = 0
        st_waste_items = []
        # SEARCH terms link via ad_group_id, PMax terms link via campaign_id
        terms = (
            self.db.query(SearchTerm)
            .outerjoin(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .filter(
                or_(
                    SearchTerm.campaign_id.in_(campaign_ids),
                    AdGroup.campaign_id.in_(campaign_ids),
                ),
                SearchTerm.date_from >= date_from,
                SearchTerm.date_to <= date_to,
            )
            .all()
        )
        for t in terms:
            if (t.conversions or 0) == 0 and (t.clicks or 0) >= 3:
                cost = (t.cost_micros or 0) / 1_000_000
                st_waste += cost
                st_waste_count += 1
                st_waste_items.append({
                    "text": t.text,
                    "clicks": t.clicks or 0,
                    "cost_usd": round(cost, 2),
                })

        # 3. Ads: 0 conversions + cost >= $20
        # NOTE: Ad model is a snapshot without date range fields — metrics are
        # cumulative from last sync, not filterable by period.  We approximate
        # by only including ads whose updated_at falls within the selected range.
        ad_waste = 0.0
        ad_waste_items = []
        ads = (
            self.db.query(Ad)
            .join(AdGroup, Ad.ad_group_id == AdGroup.id)
            .filter(
                AdGroup.campaign_id.in_(campaign_ids),
                Ad.status == "ENABLED",
                Ad.updated_at >= datetime.combine(date_from, datetime.min.time()),
            )
            .all()
        )
        for ad in ads:
            cost = (ad.cost_micros or 0) / 1_000_000
            if (ad.conversions or 0) == 0 and cost >= 20:
                ad_waste += cost
                headlines = ad.headlines or []
                headline = (
                    (headlines[0].get("text") if isinstance(headlines[0], dict) else str(headlines[0]))
                    if headlines else f"Ad #{ad.id}"
                )
                ad_waste_items.append({
                    "text": headline,
                    "clicks": ad.clicks or 0,
                    "cost_usd": round(cost, 2),
                })

        total_waste = kw_waste + st_waste + ad_waste

        return {
            "period_days": period_days,
            "total_waste_usd": round(total_waste, 2),
            "total_spend_usd": round(total_spend, 2),
            "waste_pct": round(total_waste / total_spend * 100, 1) if total_spend > 0 else 0,
            "categories": {
                "keywords": {
                    "waste_usd": round(kw_waste, 2),
                    "count": len(kw_waste_items),
                    "top_items": sorted(kw_waste_items, key=lambda x: x["cost_usd"], reverse=True)[:10],
                },
                "search_terms": {
                    "waste_usd": round(st_waste, 2),
                    "count": st_waste_count,
                    "top_items": sorted(st_waste_items, key=lambda x: x["cost_usd"], reverse=True)[:10],
                },
                "ads": {
                    "waste_usd": round(ad_waste, 2),
                    "count": len(ad_waste_items),
                    "top_items": sorted(ad_waste_items, key=lambda x: x["cost_usd"], reverse=True)[:10],
                },
            },
        }

    # -----------------------------------------------------------------------
    # Account Structure Audit — cannibalization, oversized groups, match mix
    # -----------------------------------------------------------------------

    def get_account_structure_audit(self, client_id: int) -> dict:
        """Detect structural issues: keyword cannibalization, oversized ad groups, match type mixing."""
        from app.models.ad_group import AdGroup
        from collections import defaultdict

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
        ).all()
        campaign_ids = [c.id for c in campaigns]
        campaign_map = {c.id: c.name for c in campaigns}
        if not campaign_ids:
            return {"total_keywords": 0, "total_ad_groups": 0, "issues": [],
                    "oversized_ad_groups": [], "mixed_match_ad_groups": [], "cannibalized_keywords": []}

        ad_groups = self.db.query(AdGroup).filter(
            AdGroup.campaign_id.in_(campaign_ids)
        ).all()
        ag_map = {ag.id: ag for ag in ad_groups}
        ag_ids = [ag.id for ag in ad_groups]

        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.ad_group_id.in_(ag_ids), Keyword.status == "ENABLED")
            .all()
        )

        # 1. Oversized ad groups (> 20 keywords)
        ag_kw_count: dict[int, int] = defaultdict(int)
        for kw in keywords:
            ag_kw_count[kw.ad_group_id] += 1

        oversized = []
        for ag_id, count in ag_kw_count.items():
            if count > 20:
                ag = ag_map.get(ag_id)
                if ag:
                    oversized.append({
                        "ad_group_id": ag_id,
                        "ad_group_name": ag.name,
                        "campaign_name": campaign_map.get(ag.campaign_id, "?"),
                        "keyword_count": count,
                    })

        # 2. Match type mixing (BROAD + EXACT in same ad group)
        ag_match_types: dict[int, set] = defaultdict(set)
        for kw in keywords:
            ag_match_types[kw.ad_group_id].add(kw.match_type)

        mixed_match = []
        for ag_id, match_types in ag_match_types.items():
            if "BROAD" in match_types and "EXACT" in match_types:
                ag = ag_map.get(ag_id)
                if ag:
                    mixed_match.append({
                        "ad_group_id": ag_id,
                        "ad_group_name": ag.name,
                        "campaign_name": campaign_map.get(ag.campaign_id, "?"),
                        "match_types": sorted(match_types),
                    })

        # 3. Keyword cannibalization: same text + match_type across different ad groups
        text_locations: dict[tuple, list] = defaultdict(list)
        for kw in keywords:
            key = (kw.text.lower().strip(), kw.match_type)
            ag = ag_map.get(kw.ad_group_id)
            if ag:
                text_locations[key].append({
                    "keyword_id": kw.id,
                    "ad_group_id": kw.ad_group_id,
                    "ad_group_name": ag.name,
                    "campaign_name": campaign_map.get(ag.campaign_id, "?"),
                    "clicks": kw.clicks or 0,
                    "cost_usd": round((kw.cost_micros or 0) / 1_000_000, 2),
                    "conversions": kw.conversions or 0,
                })

        cannibalized = []
        for (text, match_type), locations in text_locations.items():
            unique_ag_ids = set(loc["ad_group_id"] for loc in locations)
            if len(unique_ag_ids) >= 2:
                cannibalized.append({
                    "keyword_text": text,
                    "match_type": match_type,
                    "occurrences": len(locations),
                    "locations": locations,
                    "total_cost_usd": round(sum(l["cost_usd"] for l in locations), 2),
                    "total_clicks": sum(l["clicks"] for l in locations),
                })
        cannibalized.sort(key=lambda x: x["total_cost_usd"], reverse=True)

        issues = []
        if oversized:
            issues.append({"type": "oversized_ad_groups", "count": len(oversized), "severity": "MEDIUM"})
        if mixed_match:
            issues.append({"type": "mixed_match_types", "count": len(mixed_match), "severity": "MEDIUM"})
        if cannibalized:
            issues.append({"type": "cannibalization", "count": len(cannibalized), "severity": "HIGH"})

        return {
            "total_keywords": len(keywords),
            "total_ad_groups": len(ad_groups),
            "issues": issues,
            "oversized_ad_groups": oversized,
            "mixed_match_ad_groups": mixed_match,
            "cannibalized_keywords": cannibalized[:50],
        }

    # -----------------------------------------------------------------------
    # Bidding Strategy Advisor — recommend optimal strategy per campaign
    # -----------------------------------------------------------------------

    def get_search_term_trends(self, client_id: int, days: int = 30, min_clicks: int = 5,
                               date_from: date | None = None, date_to: date | None = None,
                               campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Analyze search term performance trends over time.

        Groups search terms by text and compares recent vs earlier performance
        to identify rising/declining terms.  Falls back to the full available
        date range when the requested window contains no data.
        """
        from app.models.search_term import SearchTerm
        from sqlalchemy import func as sa_func
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days
        window_start = date_from

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"rising": [], "declining": [], "new_terms": [], "total_terms": 0, "period_days": period_days}

        # Try requested window first; fall back to all available data
        terms = self.db.query(SearchTerm).filter(
            SearchTerm.campaign_id.in_(campaign_ids),
            SearchTerm.date_from >= window_start,
        ).all()

        if not terms:
            # No data in requested window — use whatever we have
            date_range = self.db.query(
                sa_func.min(SearchTerm.date_from),
                sa_func.max(SearchTerm.date_from),
            ).filter(SearchTerm.campaign_id.in_(campaign_ids)).first()
            if not date_range or not date_range[0]:
                return {"rising": [], "declining": [], "new_terms": [], "total_terms": 0, "period_days": period_days}
            window_start = date_range[0]
            actual_days = (date_range[1] - date_range[0]).days + 1
            period_days = max(actual_days, 1)
            terms = self.db.query(SearchTerm).filter(
                SearchTerm.campaign_id.in_(campaign_ids),
                SearchTerm.date_from >= window_start,
            ).all()

        mid_point = window_start + timedelta(days=period_days // 2)

        # Group by text
        term_map: dict[str, list] = {}
        for t in terms:
            term_map.setdefault(t.text, []).append(t)

        rising = []
        declining = []
        new_terms = []

        for text, entries in term_map.items():
            total_clicks = sum(e.clicks or 0 for e in entries)
            if total_clicks < min_clicks:
                continue

            early = [e for e in entries if e.date_from and e.date_from < mid_point]
            recent = [e for e in entries if e.date_from and e.date_from >= mid_point]

            if not early:
                # New term — only appears in recent half
                total_cost = sum(e.cost_micros or 0 for e in entries) / 1_000_000
                total_conv = sum(e.conversions or 0 for e in entries)
                new_terms.append({
                    "text": text,
                    "clicks": total_clicks,
                    "cost_usd": round(total_cost, 2),
                    "conversions": round(total_conv, 2),
                })
                continue

            early_clicks = sum(e.clicks or 0 for e in early)
            recent_clicks = sum(e.clicks or 0 for e in recent)

            if early_clicks == 0:
                change_pct = 100.0
            else:
                change_pct = round((recent_clicks - early_clicks) / early_clicks * 100, 1)

            total_cost = sum(e.cost_micros or 0 for e in entries) / 1_000_000
            total_conv = sum(e.conversions or 0 for e in entries)

            entry = {
                "text": text,
                "clicks_early": early_clicks,
                "clicks_recent": recent_clicks,
                "change_pct": change_pct,
                "total_cost_usd": round(total_cost, 2),
                "conversions": round(total_conv, 2),
            }

            if change_pct > 20:
                rising.append(entry)
            elif change_pct < -20:
                declining.append(entry)

        rising.sort(key=lambda x: x["change_pct"], reverse=True)
        declining.sort(key=lambda x: x["change_pct"])

        return {
            "rising": rising[:20],
            "declining": declining[:20],
            "new_terms": sorted(new_terms, key=lambda x: x["clicks"], reverse=True)[:20],
            "total_terms": len(term_map),
            "period_days": period_days,
        }

    # ------------------------------------------------------------------
    # B3: Close Variant Analysis
    # ------------------------------------------------------------------

    def get_close_variant_analysis(self, client_id: int, days: int = 30,
                                    date_from: date | None = None, date_to: date | None = None,
                                    campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Analyze close variants — search terms that triggered exact/phrase keywords
        but differ from the keyword text.  Falls back to full available date
        range when the requested window is empty.
        """
        from app.models.ad_group import AdGroup
        from app.models.search_term import SearchTerm
        from sqlalchemy import func as sa_func
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days
        window_start = date_from

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)
        if not campaign_ids:
            return {"variants": [], "summary": {}, "period_days": period_days}

        # Get search terms with their triggering keywords
        terms = self.db.query(SearchTerm).filter(
            SearchTerm.campaign_id.in_(campaign_ids),
            SearchTerm.date_from >= window_start,
        ).all()

        if not terms:
            # Fall back to all available data
            date_range = self.db.query(
                sa_func.min(SearchTerm.date_from),
            ).filter(SearchTerm.campaign_id.in_(campaign_ids)).scalar()
            if not date_range:
                return {"variants": [], "summary": {}, "period_days": period_days}
            window_start = date_range
            period_days = (date_to - window_start).days + 1
            terms = self.db.query(SearchTerm).filter(
                SearchTerm.campaign_id.in_(campaign_ids),
                SearchTerm.date_from >= window_start,
            ).all()

        # Get all keywords for matching
        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids), Keyword.status == "ENABLED")
            .all()
        )
        kw_texts = {kw.text.lower().strip(): kw for kw in keywords}

        variants = []
        exact_matches = 0
        close_variant_clicks = 0
        exact_clicks = 0

        for t in terms:
            term_lower = t.text.lower().strip()
            is_exact = term_lower in kw_texts

            if is_exact:
                exact_matches += 1
                exact_clicks += t.clicks or 0
            else:
                # Find closest keyword by shared words
                best_match = None
                best_overlap = 0
                term_words = set(term_lower.split())
                for kw_text, kw in kw_texts.items():
                    kw_words = set(kw_text.split())
                    overlap = len(term_words & kw_words)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = kw

                if best_match and best_overlap > 0:
                    close_variant_clicks += t.clicks or 0
                    variants.append({
                        "search_term": t.text,
                        "matched_keyword": best_match.text,
                        "match_type": best_match.match_type,
                        "clicks": t.clicks or 0,
                        "cost_usd": round((t.cost_micros or 0) / 1_000_000, 2),
                        "conversions": round(t.conversions or 0, 2),
                        "ctr": round(t.ctr or 0, 2),
                    })

        variants.sort(key=lambda x: x["cost_usd"], reverse=True)

        total_clicks = exact_clicks + close_variant_clicks
        return {
            "variants": variants[:30],
            "summary": {
                "total_search_terms": len(terms),
                "exact_matches": exact_matches,
                "close_variants": len(variants),
                "exact_click_share_pct": round(exact_clicks / total_clicks * 100, 1) if total_clicks else 0,
                "variant_click_share_pct": round(close_variant_clicks / total_clicks * 100, 1) if total_clicks else 0,
                "variant_cost_usd": round(sum(v["cost_usd"] for v in variants), 2),
            },
            "period_days": period_days,
        }

    # ------------------------------------------------------------------
    # A3: Conversion Tracking Health
    # ------------------------------------------------------------------

    def get_keyword_expansion(self, client_id: int, days: int = 30, min_clicks: int = 3, min_conversions: float = 0.5,
                              date_from: date | None = None, date_to: date | None = None,
                              campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Suggest new keywords based on high-performing search terms
        that aren't already tracked as keywords.
        """
        from app.models.ad_group import AdGroup
        from app.models.search_term import SearchTerm
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days
        window_start = date_from

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)
        if not campaign_ids:
            return {"suggestions": [], "summary": {}}

        # Get all current keyword texts
        existing_kw = set(
            kw.text.lower().strip()
            for kw in self.db.query(Keyword.text)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids), Keyword.status == "ENABLED")
            .all()
        )

        # Get search terms with good performance
        terms = self.db.query(SearchTerm).filter(
            SearchTerm.campaign_id.in_(campaign_ids),
            SearchTerm.date_from >= window_start,
        ).all()

        # Group by text and aggregate
        term_agg: dict[str, dict] = {}
        for t in terms:
            text = t.text.lower().strip()
            if text in existing_kw:
                continue
            if text not in term_agg:
                term_agg[text] = {
                    "clicks": 0, "impressions": 0, "cost_micros": 0,
                    "conversions": 0.0, "conv_value_micros": 0,
                    "campaign_id": t.campaign_id, "ad_group_id": t.ad_group_id,
                }
            agg = term_agg[text]
            agg["clicks"] += t.clicks or 0
            agg["impressions"] += t.impressions or 0
            agg["cost_micros"] += t.cost_micros or 0
            agg["conversions"] += t.conversions or 0

        suggestions = []
        for text, agg in term_agg.items():
            if agg["clicks"] < min_clicks:
                continue

            cost_usd = agg["cost_micros"] / 1_000_000
            cpa = cost_usd / agg["conversions"] if agg["conversions"] else None
            ctr = agg["clicks"] / agg["impressions"] * 100 if agg["impressions"] else 0

            # Scoring: high conversions + low CPA = high priority
            priority_score = 0
            if agg["conversions"] >= min_conversions:
                priority_score += 50
            if ctr > 5:
                priority_score += 20
            if agg["clicks"] >= 10:
                priority_score += 15
            if cpa and cpa < 50:
                priority_score += 15

            suggested_match = "EXACT" if agg["conversions"] >= 1 else "PHRASE"

            suggestions.append({
                "search_term": text,
                "clicks": agg["clicks"],
                "impressions": agg["impressions"],
                "ctr_pct": round(ctr, 2),
                "cost_usd": round(cost_usd, 2),
                "conversions": round(agg["conversions"], 2),
                "cpa_usd": round(cpa, 2) if cpa else None,
                "priority_score": priority_score,
                "suggested_match_type": suggested_match,
                "campaign_id": agg["campaign_id"],
                "ad_group_id": agg["ad_group_id"],
            })

        suggestions.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "suggestions": suggestions[:30],
            "summary": {
                "total_unmapped_terms": len(term_agg),
                "high_priority": sum(1 for s in suggestions if s["priority_score"] >= 50),
                "total_suggestions": len(suggestions),
                "existing_keywords": len(existing_kw),
            },
            "period_days": period_days,
        }

    # ───────────────────────────────────────────────────────
    # GAP 1B: Smart Bidding Health Monitoring
    # ───────────────────────────────────────────────────────
