"""PMax channels, asset groups, search themes, extensions, cannibalization.

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


class PMaxMixin:
    def get_pmax_channel_breakdown(
        self,
        client_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by ad_network_type for PMax campaigns."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(None, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"channels": [], "total_cost_micros": 0, "total_conversions": 0.0}

        rows = (
            self.db.query(
                MetricSegmented.ad_network_type,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.impressions).label("impressions"),
                func.sum(MetricSegmented.conversions).label("conv"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversion_value_micros).label("value"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.ad_network_type.isnot(None),
            )
            .group_by(MetricSegmented.ad_network_type)
            .all()
        )

        total_cost = sum(int(r.cost or 0) for r in rows)
        total_conv = sum(float(r.conv or 0) for r in rows)

        channels = []
        for r in rows:
            cost = int(r.cost or 0)
            conv = float(r.conv or 0)
            channels.append({
                "network_type": r.ad_network_type,
                "clicks": int(r.clicks or 0),
                "impressions": int(r.impressions or 0),
                "conversions": round(conv, 2),
                "cost_micros": cost,
                "cost_share_pct": round(cost / total_cost * 100, 1) if total_cost > 0 else 0,
                "conv_share_pct": round(conv / total_conv * 100, 1) if total_conv > 0 else 0,
            })

        return {
            "channels": sorted(channels, key=lambda x: x["cost_micros"], reverse=True),
            "total_cost_micros": total_cost,
            "total_conversions": round(total_conv, 2),
        }

    def get_pmax_channel_trends(
        self,
        client_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> dict:
        """Daily breakdown of PMax cost/conversions per channel (ad_network_type)."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(None, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"trends": [], "channels": []}

        rows = (
            self.db.query(
                MetricSegmented.date,
                MetricSegmented.ad_network_type,
                func.sum(MetricSegmented.clicks).label("clicks"),
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= date_to,
                MetricSegmented.ad_network_type.isnot(None),
            )
            .group_by(MetricSegmented.date, MetricSegmented.ad_network_type)
            .order_by(MetricSegmented.date)
            .all()
        )

        # Pivot into {date: {channel: metrics}} structure
        from collections import OrderedDict
        by_date: OrderedDict = OrderedDict()
        all_channels = set()
        for r in rows:
            d = str(r.date)
            ch = r.ad_network_type
            all_channels.add(ch)
            if d not in by_date:
                by_date[d] = {}
            by_date[d][ch] = {
                "clicks": int(r.clicks or 0),
                "cost": round(int(r.cost or 0) / 1_000_000, 2),
                "conversions": round(float(r.conv or 0), 2),
            }

        channels = sorted(all_channels)
        trends = []
        for d, ch_map in by_date.items():
            entry = {"date": d}
            for ch in channels:
                m = ch_map.get(ch, {"clicks": 0, "cost": 0, "conversions": 0})
                entry[f"{ch}_cost"] = m["cost"]
                entry[f"{ch}_conv"] = m["conversions"]
            trends.append(entry)

        return {"trends": trends, "channels": channels}

    # -----------------------------------------------------------------------
    # Asset Group Performance
    # -----------------------------------------------------------------------

    def get_asset_group_performance(
        self,
        client_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Query AssetGroup + aggregate AssetGroupDaily metrics, include asset counts and ad_strength."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(None, date_from, date_to)

        # Get PMax campaign IDs for this client
        pmax_campaign_ids = [
            c.id for c in self.db.query(Campaign).filter(
                Campaign.client_id == client_id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        ]
        if not pmax_campaign_ids:
            return {"asset_groups": []}

        asset_groups = (
            self.db.query(AssetGroup)
            .filter(AssetGroup.campaign_id.in_(pmax_campaign_ids))
            .all()
        )
        if not asset_groups:
            return {"asset_groups": []}

        result = []
        for ag in asset_groups:
            # Aggregate daily metrics
            agg = self.db.query(
                func.sum(AssetGroupDaily.clicks).label("clicks"),
                func.sum(AssetGroupDaily.impressions).label("impressions"),
                func.sum(AssetGroupDaily.cost_micros).label("cost"),
                func.sum(AssetGroupDaily.conversions).label("conv"),
                func.sum(AssetGroupDaily.conversion_value_micros).label("value"),
            ).filter(
                AssetGroupDaily.asset_group_id == ag.id,
                AssetGroupDaily.date >= date_from,
                AssetGroupDaily.date <= date_to,
            ).first()

            total_clicks = int(agg.clicks or 0)
            total_cost = int(agg.cost or 0)
            total_conv = float(agg.conv or 0)
            total_value = int(agg.value or 0)

            cpa_micros = int(total_cost / total_conv) if total_conv > 0 else 0
            roas = round(total_value / total_cost, 2) if total_cost > 0 else 0.0

            # Get assets with performance labels
            assets_list = self.db.query(AssetGroupAsset).filter(
                AssetGroupAsset.asset_group_id == ag.id,
            ).all()

            assets_data = [
                {
                    "type": a.asset_type,
                    "text": a.text_content,
                    "performance_label": a.performance_label,
                }
                for a in assets_list
            ]

            result.append({
                "id": ag.id,
                "name": ag.name,
                "ad_strength": ag.ad_strength,
                "status": ag.status,
                "total_clicks": total_clicks,
                "total_cost_micros": total_cost,
                "total_conversions": round(total_conv, 2),
                "cpa_micros": cpa_micros,
                "roas": roas,
                "asset_count": len(assets_list),
                "assets": assets_data,
            })

        return {"asset_groups": result}

    # -----------------------------------------------------------------------
    # PMax Search Themes
    # -----------------------------------------------------------------------

    def get_pmax_search_themes(self, client_id: int) -> dict:
        """Query AssetGroupSignal grouped by asset_group, cross-reference with performance."""
        pmax_campaign_ids = [
            c.id for c in self.db.query(Campaign).filter(
                Campaign.client_id == client_id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        ]
        if not pmax_campaign_ids:
            return {"asset_groups": []}

        asset_groups = (
            self.db.query(AssetGroup)
            .filter(AssetGroup.campaign_id.in_(pmax_campaign_ids))
            .all()
        )
        if not asset_groups:
            return {"asset_groups": []}

        result = []
        for ag in asset_groups:
            signals = self.db.query(AssetGroupSignal).filter(
                AssetGroupSignal.asset_group_id == ag.id,
            ).all()

            search_themes = [
                s.search_theme_text
                for s in signals
                if s.signal_type == "SEARCH_THEME" and s.search_theme_text
            ]
            audience_signals = [
                {"name": s.audience_name or s.audience_resource_name, "type": s.signal_type}
                for s in signals
                if s.signal_type != "SEARCH_THEME" and (s.audience_name or s.audience_resource_name)
            ]

            # Cross-reference performance (last 30 days)
            perf = self.db.query(
                func.sum(AssetGroupDaily.cost_micros).label("cost"),
                func.sum(AssetGroupDaily.conversions).label("conv"),
            ).filter(
                AssetGroupDaily.asset_group_id == ag.id,
                AssetGroupDaily.date >= date.today() - timedelta(days=30),
            ).first()

            result.append({
                "name": ag.name,
                "search_themes": search_themes,
                "audience_signals": audience_signals,
                "performance": {
                    "cost_micros": int(perf.cost or 0) if perf else 0,
                    "conversions": round(float(perf.conv or 0), 2) if perf else 0.0,
                },
            })

        return {"asset_groups": result}

    # -----------------------------------------------------------------------
    # Audience Performance
    # -----------------------------------------------------------------------

    def get_audience_performance(
        self,
        client_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> dict:
        """Aggregate CampaignAudienceMetric per audience, compute CPA anomaly flags."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(None, date_from, date_to)
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"audiences": [], "avg_cpa_micros": 0}

        rows = (
            self.db.query(
                CampaignAudienceMetric.audience_name,
                CampaignAudienceMetric.audience_type,
                func.sum(CampaignAudienceMetric.clicks).label("clicks"),
                func.sum(CampaignAudienceMetric.impressions).label("impressions"),
                func.sum(CampaignAudienceMetric.cost_micros).label("cost"),
                func.sum(CampaignAudienceMetric.conversions).label("conv"),
                func.sum(CampaignAudienceMetric.conversion_value_micros).label("value"),
            )
            .filter(
                CampaignAudienceMetric.campaign_id.in_(campaign_ids),
                CampaignAudienceMetric.date >= date_from,
                CampaignAudienceMetric.date <= date_to,
            )
            .group_by(CampaignAudienceMetric.audience_name, CampaignAudienceMetric.audience_type)
            .all()
        )

        total_cost = sum(int(r.cost or 0) for r in rows)
        total_conv = sum(float(r.conv or 0) for r in rows)
        avg_cpa_micros = int(total_cost / total_conv) if total_conv > 0 else 0

        audiences = []
        for r in rows:
            cost = int(r.cost or 0)
            conv = float(r.conv or 0)
            value = int(r.value or 0)
            cpa_micros = int(cost / conv) if conv > 0 else 0
            roas = round(value / cost, 2) if cost > 0 else 0.0
            is_anomaly = (cpa_micros > avg_cpa_micros * 2 and cost > 50_000_000) if avg_cpa_micros > 0 else False

            audiences.append({
                "audience_name": r.audience_name,
                "audience_type": r.audience_type,
                "clicks": int(r.clicks or 0),
                "impressions": int(r.impressions or 0),
                "cost_micros": cost,
                "conversions": round(conv, 2),
                "cpa_micros": cpa_micros,
                "roas": roas,
                "is_anomaly": is_anomaly,
            })

        return {
            "audiences": sorted(audiences, key=lambda x: x["cost_micros"], reverse=True),
            "avg_cpa_micros": avg_cpa_micros,
        }

    # -----------------------------------------------------------------------
    # Missing Extensions Audit
    # -----------------------------------------------------------------------

    def get_missing_extensions_audit(
        self,
        client_id: int,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> dict:
        """Check CampaignAsset grouped by campaign for min extension counts."""
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"campaigns": [], "overall_score": 0}

        campaigns = self.db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).all()
        campaign_name_map = {c.id: c.name for c in campaigns}

        MIN_SITELINKS = 4
        MIN_CALLOUTS = 4
        MIN_SNIPPETS = 1

        results = []
        total_score = 0.0

        for cid in campaign_ids:
            assets = self.db.query(CampaignAsset).filter(
                CampaignAsset.campaign_id == cid,
            ).all()

            sitelink_count = sum(1 for a in assets if a.asset_type == "SITELINK")
            callout_count = sum(1 for a in assets if a.asset_type == "CALLOUT")
            snippet_count = sum(1 for a in assets if a.asset_type == "STRUCTURED_SNIPPET")
            has_call = any(a.asset_type == "CALL" for a in assets)

            missing = []
            if sitelink_count < MIN_SITELINKS:
                missing.append(f"Need {MIN_SITELINKS - sitelink_count} more sitelinks")
            if callout_count < MIN_CALLOUTS:
                missing.append(f"Need {MIN_CALLOUTS - callout_count} more callouts")
            if snippet_count < MIN_SNIPPETS:
                missing.append(f"Need {MIN_SNIPPETS - snippet_count} more structured snippets")

            # Extension score: each category max 33.3%, call bonus
            score = 0.0
            score += min(sitelink_count / MIN_SITELINKS, 1.0) * 30
            score += min(callout_count / MIN_CALLOUTS, 1.0) * 30
            score += min(snippet_count / MIN_SNIPPETS, 1.0) * 30
            score += 10 if has_call else 0
            score = round(min(score, 100), 1)
            total_score += score

            results.append({
                "campaign_name": campaign_name_map.get(cid, f"Campaign #{cid}"),
                "sitelink_count": sitelink_count,
                "callout_count": callout_count,
                "snippet_count": snippet_count,
                "has_call": has_call,
                "extension_score": score,
                "missing": missing,
            })

        overall_score = round(total_score / len(campaign_ids), 1) if campaign_ids else 0

        return {
            "campaigns": sorted(results, key=lambda x: x["extension_score"]),
            "overall_score": overall_score,
        }

    # -----------------------------------------------------------------------
    # Extension Performance
    # -----------------------------------------------------------------------

    def get_extension_performance(
        self,
        client_id: int,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> dict:
        """Query CampaignAsset with metrics, group by asset_type."""
        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, campaign_status)
        if not campaign_ids:
            return {"by_type": [], "extensions": []}

        assets = (
            self.db.query(CampaignAsset)
            .filter(CampaignAsset.campaign_id.in_(campaign_ids))
            .all()
        )

        campaign_name_map = {
            c.id: c.name
            for c in self.db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).all()
        }

        # Group by asset_type for summary
        type_agg: dict[str, dict] = {}
        extensions = []

        for a in assets:
            at = a.asset_type
            if at not in type_agg:
                type_agg[at] = {
                    "total_clicks": 0, "total_impressions": 0, "count": 0,
                    "performance_labels": {"BEST": 0, "GOOD": 0, "LOW": 0},
                }
            type_agg[at]["total_clicks"] += a.clicks or 0
            type_agg[at]["total_impressions"] += a.impressions or 0
            type_agg[at]["count"] += 1
            label = (a.performance_label or "").upper()
            if label in type_agg[at]["performance_labels"]:
                type_agg[at]["performance_labels"][label] += 1

            extensions.append({
                "campaign_name": campaign_name_map.get(a.campaign_id, f"Campaign #{a.campaign_id}"),
                "asset_type": at,
                "asset_name": a.asset_name,
                "clicks": a.clicks or 0,
                "impressions": a.impressions or 0,
                "ctr": round(a.ctr or 0, 2),
                "performance_label": a.performance_label,
            })

        by_type = []
        for at, agg in sorted(type_agg.items()):
            avg_ctr = round(agg["total_clicks"] / agg["total_impressions"] * 100, 2) if agg["total_impressions"] > 0 else 0
            by_type.append({
                "asset_type": at,
                "total_clicks": agg["total_clicks"],
                "total_impressions": agg["total_impressions"],
                "avg_ctr": avg_ctr,
                "count": agg["count"],
                "performance_labels": agg["performance_labels"],
            })

        return {
            "by_type": by_type,
            "extensions": sorted(extensions, key=lambda x: x["clicks"], reverse=True),
        }

    # ------------------------------------------------------------------
    # PMax vs Search Cannibalization (D3)
    # ------------------------------------------------------------------

    def get_pmax_search_cannibalization(
        self,
        client_id: int,
        days: int = 30,
        date_from: date | None = None,
        date_to: date | None = None,
        min_clicks: int = 2,
    ) -> dict:
        """Detect search terms appearing in both PMax and Search campaigns.

        Compares CPA/ROAS per source and recommends negatives for PMax.
        """
        from app.models.search_term import SearchTerm
        from app.models.campaign import Campaign
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)

        # Get all search terms for this client with source info
        terms = (
            self.db.query(SearchTerm)
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                SearchTerm.date_from >= date_from,
            )
            .all()
        )

        if not terms:
            return {
                "overlapping_terms": [],
                "summary": {
                    "total_overlap": 0,
                    "overlap_cost_usd": 0,
                    "pmax_only": 0,
                    "search_only": 0,
                    "pmax_better_count": 0,
                    "search_better_count": 0,
                },
                "recommendations": [],
            }

        # Build campaign name lookup from joined Campaign
        campaign_name_map: dict[int, str] = {}
        for t in terms:
            if t.campaign_id and t.campaign_id not in campaign_name_map:
                campaign_name_map[t.campaign_id] = t.campaign.name if t.campaign else f"Campaign #{t.campaign_id}"

        # Build per-source aggregation: term_text -> {SEARCH: {...}, PMAX: {...}}
        term_agg: dict[str, dict] = {}

        for t in terms:
            text = t.text.lower().strip()
            source = t.source or "SEARCH"
            if text not in term_agg:
                term_agg[text] = {}
            if source not in term_agg[text]:
                term_agg[text][source] = {
                    "clicks": 0, "impressions": 0, "cost_micros": 0,
                    "conversions": 0.0, "campaign_ids": set(),
                }
            agg = term_agg[text][source]
            agg["clicks"] += t.clicks or 0
            agg["impressions"] += t.impressions or 0
            agg["cost_micros"] += t.cost_micros or 0
            agg["conversions"] += t.conversions or 0
            agg["campaign_ids"].add(t.campaign_id)

        # Find overlapping terms (present in both SEARCH and PMAX)
        overlapping = []
        pmax_only = 0
        search_only = 0
        pmax_better = 0
        search_better = 0
        total_overlap_cost = 0

        for text, sources in term_agg.items():
            has_search = "SEARCH" in sources
            has_pmax = "PMAX" in sources

            if has_search and has_pmax:
                s = sources["SEARCH"]
                p = sources["PMAX"]

                # Skip low-volume terms
                total_clicks = s["clicks"] + p["clicks"]
                if total_clicks < min_clicks:
                    continue

                s_cost = s["cost_micros"] / 1_000_000
                p_cost = p["cost_micros"] / 1_000_000
                s_cpa = s_cost / s["conversions"] if s["conversions"] > 0 else None
                p_cpa = p_cost / p["conversions"] if p["conversions"] > 0 else None
                s_conv_rate = s["conversions"] / s["clicks"] * 100 if s["clicks"] > 0 else 0
                p_conv_rate = p["conversions"] / p["clicks"] * 100 if p["clicks"] > 0 else 0

                # Determine winner
                winner = "tie"
                if s_cpa is not None and p_cpa is not None:
                    if s_cpa < p_cpa * 0.8:
                        winner = "SEARCH"
                        search_better += 1
                    elif p_cpa < s_cpa * 0.8:
                        winner = "PMAX"
                        pmax_better += 1
                elif s["conversions"] > 0 and p["conversions"] == 0:
                    winner = "SEARCH"
                    search_better += 1
                elif p["conversions"] > 0 and s["conversions"] == 0:
                    winner = "PMAX"
                    pmax_better += 1

                overlap_cost = s_cost + p_cost
                total_overlap_cost += overlap_cost

                overlapping.append({
                    "search_term": text,
                    "search": {
                        "clicks": s["clicks"],
                        "cost_usd": round(s_cost, 2),
                        "conversions": round(s["conversions"], 2),
                        "cpa": round(s_cpa, 2) if s_cpa is not None else None,
                        "conv_rate": round(s_conv_rate, 2),
                        "campaigns": [campaign_name_map.get(cid, str(cid)) for cid in s["campaign_ids"]],
                    },
                    "pmax": {
                        "clicks": p["clicks"],
                        "cost_usd": round(p_cost, 2),
                        "conversions": round(p["conversions"], 2),
                        "cpa": round(p_cpa, 2) if p_cpa is not None else None,
                        "conv_rate": round(p_conv_rate, 2),
                        "campaigns": [campaign_name_map.get(cid, str(cid)) for cid in p["campaign_ids"]],
                    },
                    "winner": winner,
                    "total_cost_usd": round(overlap_cost, 2),
                })
            elif has_pmax and not has_search:
                pmax_only += 1
            elif has_search and not has_pmax:
                search_only += 1

        # Sort by total cost descending
        overlapping.sort(key=lambda x: x["total_cost_usd"], reverse=True)

        # Generate recommendations
        recommendations = []
        search_wins = [o for o in overlapping if o["winner"] == "SEARCH"]
        pmax_wins = [o for o in overlapping if o["winner"] == "PMAX"]

        if search_wins:
            top_terms = ", ".join(f'"{o["search_term"]}"' for o in search_wins[:3])
            recommendations.append({
                "type": "add_negative_pmax",
                "priority": "high" if len(search_wins) >= 3 else "medium",
                "message": f"Dodaj {len(search_wins)} terminów jako negative w PMax — Search osiąga lepsze CPA. "
                           f"Np. {top_terms}",
                "count": len(search_wins),
            })

        if pmax_wins:
            recommendations.append({
                "type": "review_search_keywords",
                "priority": "medium",
                "message": f"{len(pmax_wins)} terminów ma lepsze wyniki w PMax niż Search — "
                           f"rozważ obniżenie stawek lub pauzę tych keywords w Search.",
                "count": len(pmax_wins),
            })

        if total_overlap_cost > 50:
            recommendations.append({
                "type": "overlap_cost_alert",
                "priority": "high" if total_overlap_cost > 200 else "medium",
                "message": f"Kanibalizacja PMax ↔ Search kosztuje {total_overlap_cost:.0f} zł. "
                           f"Rozważ rozdzielenie budżetów lub dodanie negatywów.",
                "count": len(overlapping),
            })

        return {
            "overlapping_terms": overlapping[:30],
            "summary": {
                "total_overlap": len(overlapping),
                "overlap_cost_usd": round(total_overlap_cost, 2),
                "pmax_only": pmax_only,
                "search_only": search_only,
                "pmax_better_count": pmax_better,
                "search_better_count": search_better,
            },
            "recommendations": recommendations,
        }

    # -----------------------------------------------------------------------
    # G4: Cross-Campaign Analysis — keyword overlap
    # -----------------------------------------------------------------------
