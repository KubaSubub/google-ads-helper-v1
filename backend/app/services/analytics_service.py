"""Analytics Service - KPI calculations + Anomaly Detection (Feature 7).

Provides:
- Aggregate KPIs across all campaigns
- Anomaly detection (spend spikes, conversion drops, CTR drops)
- Campaign performance comparison

Called during sync Phase 5.
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


class AnalyticsService:
    """Handles KPI calculations and anomaly detection."""

    def __init__(self, db: Session):
        self.db = db

    def _filter_campaigns(self, client_id: int, campaign_type: str | None = None, campaign_status: str | None = None):
        """Build filtered Campaign query. Reusable across all analytics methods."""
        q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_type and campaign_type != "ALL":
            q = q.filter(Campaign.campaign_type == campaign_type)
        if campaign_status and campaign_status != "ALL":
            q = q.filter(Campaign.status == campaign_status)
        return q

    def _filter_campaign_ids(self, client_id: int, campaign_type: str | None = None, campaign_status: str | None = None) -> list[int]:
        """Return list of campaign IDs matching filters."""
        return [c.id for c in self._filter_campaigns(client_id, campaign_type, campaign_status).all()]

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
                "avg_ctr_pct": 0, "avg_cpc_usd": 0, "cpa_usd": 0, "roas": 0,
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
        roas = (total_conv_value_usd / total_spend_usd) if total_spend_usd else 0

        return {
            "total_spend_usd": round(total_spend_usd, 2),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "total_conversions": round(total_conversions, 2),
            "total_conversion_value_usd": round(total_conv_value_usd, 2),
            "avg_ctr_pct": round(avg_ctr, 2),
            "avg_cpc_usd": round(avg_cpc, 2),
            "cpa_usd": round(cpa, 2),
            "roas": round(roas, 2),
            "active_campaigns": len([c for c in campaigns if c.status == "ENABLED"]),
        }

    def detect_anomalies(self, client_id: int) -> list:
        """Run anomaly detection rules using MetricDaily data.

        Rules:
        1. SPEND_SPIKE: campaign spend > 3x proportional share (last 7 days)
        2. CONVERSION_DROP: daily avg >= 3 but recent 7d total < expected
        3. CTR_DROP: campaign CTR < 0.5% with impressions > 1000 (last 7 days)
        """
        alerts_created = []
        today = date.today()
        days_7_ago = today - timedelta(days=7)
        days_30_ago = today - timedelta(days=30)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED",
        ).all()

        if not campaigns:
            return alerts_created

        # Aggregate last 7 days per campaign from MetricDaily
        campaign_metrics = {}
        for campaign in campaigns:
            rows_7d = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= days_7_ago,
            ).all()
            rows_30d = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= days_30_ago,
            ).all()

            # Last 3 days for CPA sustained check
            rows_3d = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= today - timedelta(days=3),
            ).order_by(MetricDaily.date).all()

            campaign_metrics[campaign.id] = {
                "spend_7d": sum(r.cost_micros or 0 for r in rows_7d),
                "spend_30d": sum(r.cost_micros or 0 for r in rows_30d),
                "clicks_7d": sum(r.clicks or 0 for r in rows_7d),
                "impressions_7d": sum(r.impressions or 0 for r in rows_7d),
                "conversions_7d": sum(r.conversions or 0 for r in rows_7d),
                "conversions_30d": sum(r.conversions or 0 for r in rows_30d),
                "days_30d": len(rows_30d),
                "daily_3d": [
                    {"cost": r.cost_micros or 0, "conversions": r.conversions or 0}
                    for r in rows_3d
                ],
            }

        total_spend_7d = sum(m["spend_7d"] for m in campaign_metrics.values())
        avg_spend_7d = total_spend_7d / len(campaigns) if campaigns else 0

        for campaign in campaigns:
            m = campaign_metrics.get(campaign.id, {})

            # Rule 1: SPEND_SPIKE — campaign spend > 3x average
            if avg_spend_7d > 0 and m["spend_7d"] > avg_spend_7d * 3:
                alert = self._create_alert(
                    client_id=client_id,
                    campaign_id=campaign.id,
                    alert_type="SPEND_SPIKE",
                    severity="HIGH",
                    title=f"Spend spike: {campaign.name}",
                    description=(
                        f"Wydatki kampanii ${m['spend_7d']/1_000_000:.2f} "
                        f"przekraczaja 3x srednia ${avg_spend_7d/1_000_000:.2f} (ostatnie 7 dni)"
                    ),
                )
                if alert:
                    alerts_created.append(alert)

            # Rule 2: CONVERSION_DROP — expected >= 3/day but recent much lower
            daily_avg_30d = m["conversions_30d"] / max(m["days_30d"], 1)
            if daily_avg_30d >= 3:
                expected_7d = daily_avg_30d * 7
                if m["conversions_7d"] < expected_7d * 0.5:  # < 50% of expected
                    alert = self._create_alert(
                        client_id=client_id,
                        campaign_id=campaign.id,
                        alert_type="CONVERSION_DROP",
                        severity="HIGH",
                        title=f"Spadek konwersji: {campaign.name}",
                        description=(
                            f"Oczekiwano ~{daily_avg_30d:.1f}/dzien, "
                            f"ostatnie 7 dni: {m['conversions_7d']:.1f} total"
                        ),
                    )
                    if alert:
                        alerts_created.append(alert)

            # Rule 3: CTR_DROP — CTR < 0.5% with meaningful traffic
            if m["impressions_7d"] > 1000:
                ctr = m["clicks_7d"] / m["impressions_7d"]
                if ctr < 0.005:  # < 0.5%
                    alert = self._create_alert(
                        client_id=client_id,
                        campaign_id=campaign.id,
                        alert_type="CTR_DROP",
                        severity="MEDIUM",
                        title=f"Niski CTR: {campaign.name}",
                        description=f"CTR {ctr*100:.2f}% ponizej progu 0.5%",
                    )
                    if alert:
                        alerts_created.append(alert)

            # Rule 4: CPA_SUSTAINED — CPA > 150% of 30d average for 3+ consecutive days
            conv_30d = m["conversions_30d"]
            daily_3d = m.get("daily_3d", [])
            if conv_30d > 0 and len(daily_3d) >= 3:
                avg_cpa_30d = m["spend_30d"] / conv_30d
                cpa_threshold = avg_cpa_30d * 1.5
                all_high = True
                for d in daily_3d:
                    if d["conversions"] > 0:
                        day_cpa = d["cost"] / d["conversions"]
                        if day_cpa <= cpa_threshold:
                            all_high = False
                            break
                    else:
                        # 0 conversions with cost > 0 counts as infinite CPA
                        if d["cost"] == 0:
                            all_high = False
                            break
                if all_high:
                    alert = self._create_alert(
                        client_id=client_id,
                        campaign_id=campaign.id,
                        alert_type="CPA_SUSTAINED",
                        severity="HIGH",
                        title=f"Wysoki CPA przez 3+ dni: {campaign.name}",
                        description=(
                            f"CPA przekracza 150% sredniej z 30 dni "
                            f"(srednia: {avg_cpa_30d/1_000_000:.2f} zl) przez ostatnie 3 dni"
                        ),
                    )
                    if alert:
                        alerts_created.append(alert)

            # Rule 5: DISAPPROVED_ADS — any disapproved ads in ENABLED campaigns
        from app.models.ad import Ad as AdModel
        from app.models.ad_group import AdGroup as AGModel

        disapproved_count = (
            self.db.query(AdModel)
            .join(AGModel, AdModel.ad_group_id == AGModel.id)
            .join(Campaign, AGModel.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                AdModel.approval_status == "DISAPPROVED",
            )
            .count()
        )
        if disapproved_count > 0:
            alert = self._create_alert(
                client_id=client_id,
                campaign_id=None,
                alert_type="DISAPPROVED_ADS",
                severity="HIGH",
                title=f"Odrzucone reklamy: {disapproved_count} szt.",
                description=f"{disapproved_count} reklam odrzuconych — kampanie traca ruch",
            )
            if alert:
                alerts_created.append(alert)

        self.db.commit()
        return alerts_created

    # -----------------------------------------------------------------------
    # NEW: Trends — time-series data per day for TrendExplorer
    # -----------------------------------------------------------------------

    def get_trends(
        self,
        client_id: int,
        metrics: list[str],
        days: int = 30,
        date_from: date | None = None,
        date_to: date | None = None,
        campaign_type: str = "ALL",
        campaign_status: str = "ALL",
        # backward compat alias
        status: str | None = None,
    ) -> dict:
        """Return daily aggregated metrics for TrendExplorer chart.

        Queries MetricDaily joined to Campaign, aggregates per day.
        Falls back to mock data if MetricDaily is empty.
        """
        effective_status = campaign_status if status is None else status
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type, effective_status)
        period_days = (date_to - date_from).days

        if not campaign_ids:
            return {"period_days": period_days, "data": [], "totals": {}}

        # Query daily rows
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

        # Aggregate per day
        day_map: dict[date, dict] = {}
        for r in rows:
            d = r.date
            if d not in day_map:
                day_map[d] = {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0, "conv_value_micros": 0}
            day_map[d]["clicks"] += r.clicks or 0
            day_map[d]["impressions"] += r.impressions or 0
            day_map[d]["cost_micros"] += r.cost_micros or 0
            day_map[d]["conversions"] += r.conversions or 0
            day_map[d]["conv_value_micros"] += r.conversion_value_micros or 0

        # If no real data → generate mock from campaign aggregates
        is_mock = False
        if not day_map:
            is_mock = True
            logger.warning("Returning mock trend data — no MetricDaily rows found for campaigns")
            day_map = self._mock_daily_data(campaign_ids, date_from, date_to)

        # Build output rows with derived metrics
        data = []
        for d in sorted(day_map.keys()):
            agg = day_map[d]
            clicks = agg["clicks"]
            impressions = agg["impressions"]
            cost_micros = agg["cost_micros"]
            conversions = agg["conversions"]
            conv_value_usd = agg.get("conv_value_micros", 0) / 1_000_000
            cost_usd = cost_micros / 1_000_000

            ctr = clicks / impressions if impressions else 0
            cpc = cost_usd / clicks if clicks else 0
            roas = conv_value_usd / cost_usd if cost_usd else 0  # Real ROAS = revenue / cost
            cpa = cost_usd / conversions if conversions else 0
            cvr = conversions / clicks if clicks else 0

            row: dict = {"date": str(d)}
            metric_map = {
                "cost": round(cost_usd, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 2),
                "ctr": round(ctr * 100, 4),
                "cpc": round(cpc, 2),
                "roas": round(roas, 2),
                "cpa": round(cpa, 2),
                "cvr": round(cvr * 100, 4),
            }
            for m in metrics:
                if m in metric_map:
                    row[m] = metric_map[m]
                else:
                    row[m] = 0
            data.append(row)

        # Totals
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
        """
        from app.models.keyword import Keyword
        from app.models.ad_group import AdGroup

        # Aggregate from keywords as baseline
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

        days = (date_to - date_from).days or 1
        day_clicks = total_clicks / days
        day_impressions = total_impressions / days
        day_cost = total_cost_micros / days
        day_conv = total_conversions / days

        day_map: dict[date, dict] = {}
        current = date_from
        rand = random.Random(42)  # deterministic
        while current <= date_to:
            noise = lambda: 1 + rand.uniform(-0.2, 0.2)
            day_map[current] = {
                "clicks": max(0, int(day_clicks * noise())),
                "impressions": max(0, int(day_impressions * noise())),
                "cost_micros": max(0, int(day_cost * noise())),
                "conversions": max(0, round(day_conv * noise(), 1)),
            }
            current += timedelta(days=1)
        return day_map

    # -----------------------------------------------------------------------
    # NEW: Health Score
    # -----------------------------------------------------------------------

    def get_health_score(
        self, client_id: int, campaign_type: str | None = None,
        campaign_status: str | None = None, status: str | None = None,
        days: int | None = None, date_from: date | None = None, date_to: date | None = None,
    ) -> dict:
        """Calculate account health score (0-100) based on 6 weighted pillars.

        Pillars (weight):
          1. Performance (25%) — conversions, ROAS, zero-conv campaigns
          2. Quality     (20%) — Quality Score, ad strength
          3. Efficiency  (20%) — wasted spend, search term pollution
          4. Coverage    (15%) — impression share, lost IS
          5. Stability   (10%) — alerts, CTR trend
          6. Structure   (10%) — budget pacing, ad group health
        """
        effective_status = campaign_status if campaign_status is not None else status
        from app.utils.date_utils import resolve_dates as _rd
        period_start, period_end = _rd(days, date_from, date_to)
        period_len = (period_end - period_start).days or 1

        issues: list[dict] = []

        # --- Fetch campaigns ---
        campaign_q = self._filter_campaigns(client_id, campaign_type, effective_status)
        if not effective_status or effective_status == "ALL":
            campaign_q = campaign_q.filter(Campaign.status == "ENABLED")
        active_campaigns = campaign_q.all()
        total_campaigns = len(active_campaigns)
        campaign_ids = [c.id for c in active_campaigns]

        if not campaign_ids:
            return self._health_empty_response(total_campaigns, issues)

        # --- Batch-load MetricDaily for all campaigns in period ---
        all_metrics = self.db.query(MetricDaily).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= period_start,
            MetricDaily.date <= period_end,
        ).all()

        if not all_metrics:
            issues.insert(0, {
                "severity": "HIGH",
                "message": "Brak danych metryk — synchronizuj konto aby zebrać dane",
                "action": "sync",
            })
            return self._health_empty_response(total_campaigns, issues)

        from collections import defaultdict
        metrics_by_camp = defaultdict(list)
        for m in all_metrics:
            metrics_by_camp[m.campaign_id].append(m)
        campaigns_with_data = len(metrics_by_camp)

        # Pre-aggregate per campaign
        camp_agg = {}
        for camp in active_campaigns:
            rows = metrics_by_camp.get(camp.id, [])
            if not rows:
                continue
            camp_agg[camp.id] = {
                "campaign": camp,
                "clicks": sum(r.clicks or 0 for r in rows),
                "impressions": sum(r.impressions or 0 for r in rows),
                "conversions": sum(r.conversions or 0 for r in rows),
                "conv_value": sum(r.conversion_value_micros or 0 for r in rows) / 1_000_000,
                "cost": sum(r.cost_micros or 0 for r in rows) / 1_000_000,
                "search_is": [r.search_impression_share for r in rows if r.search_impression_share is not None],
                "budget_lost_is": [r.search_budget_lost_is for r in rows if r.search_budget_lost_is is not None],
                "rank_lost_is": [r.search_rank_lost_is for r in rows if r.search_rank_lost_is is not None],
            }

        total_cost = sum(a["cost"] for a in camp_agg.values())
        total_conv = sum(a["conversions"] for a in camp_agg.values())
        total_conv_value = sum(a["conv_value"] for a in camp_agg.values())

        # =====================================================================
        # PILLAR 1: PERFORMANCE (25%) — conversions, ROAS, zero-conv campaigns
        # =====================================================================
        perf_score = 100
        perf_details = {}

        # 1a. Zero-conversion campaigns with significant spend
        no_conv_camps = []
        for cid, agg in camp_agg.items():
            if agg["clicks"] > 10 and agg["conversions"] == 0:
                no_conv_camps.append(agg["campaign"].name)
        if no_conv_camps:
            pct_no_conv = len(no_conv_camps) / campaigns_with_data
            perf_score -= min(pct_no_conv * 60, 40)  # up to -40 if all camps have 0 conv
            issues.append({
                "severity": "HIGH",
                "message": f"{len(no_conv_camps)} kampanii bez konwersji (>10 kliknięć, 0 konwersji)",
                "action": "recommendations",
            })
        perf_details["zero_conv_campaigns"] = len(no_conv_camps)

        # 1b. Low ROAS campaigns (non-brand, cost > $20)
        low_roas_camps = []
        for cid, agg in camp_agg.items():
            camp = agg["campaign"]
            is_brand = (camp.campaign_role_final or "").upper() in ("BRAND", "BRAND_EXACT")
            if is_brand or agg["cost"] < 20:
                continue
            roas = agg["conv_value"] / agg["cost"] if agg["cost"] > 0 else 0
            if roas < 1.0:
                low_roas_camps.append(camp.name)
        if low_roas_camps:
            pct_low_roas = len(low_roas_camps) / max(1, campaigns_with_data)
            perf_score -= min(pct_low_roas * 50, 35)  # up to -35
            issues.append({
                "severity": "HIGH" if len(low_roas_camps) > 2 else "MEDIUM",
                "message": f"{len(low_roas_camps)} kampanii z ROAS < 1 (tracisz pieniądze)",
                "action": "campaigns",
            })
        perf_details["low_roas_campaigns"] = len(low_roas_camps)

        # 1c. Overall ROAS health
        overall_roas = total_conv_value / total_cost if total_cost > 0 else 0
        if overall_roas >= 3:
            pass  # excellent
        elif overall_roas >= 2:
            perf_score -= 5
        elif overall_roas >= 1:
            perf_score -= 15
        else:
            perf_score -= 25
        perf_details["overall_roas"] = round(overall_roas, 2)
        perf_score = max(0, perf_score)

        # =====================================================================
        # PILLAR 2: QUALITY (20%) — Quality Score, ad strength
        # =====================================================================
        qual_score = 100
        qual_details = {}

        # 2a. Quality Score from Keywords
        ad_group_ids = [ag.id for ag in self.db.query(AdGroup).filter(
            AdGroup.campaign_id.in_(campaign_ids)
        ).all()]

        qs_keywords = []
        if ad_group_ids:
            qs_keywords = self.db.query(Keyword.quality_score).filter(
                Keyword.ad_group_id.in_(ad_group_ids),
                Keyword.status == "ENABLED",
                Keyword.quality_score > 0,
            ).all()

        if qs_keywords:
            qs_values = [k[0] for k in qs_keywords]
            avg_qs = sum(qs_values) / len(qs_values)
            low_qs_count = sum(1 for v in qs_values if v < 5)
            low_qs_pct = low_qs_count / len(qs_values)

            # Average QS scoring: 7+ = full, 5-7 = partial, <5 = heavy penalty
            if avg_qs >= 7:
                pass  # perfect
            elif avg_qs >= 6:
                qual_score -= 10
            elif avg_qs >= 5:
                qual_score -= 25
            else:
                qual_score -= 40

            # Low QS keyword percentage
            if low_qs_pct > 0.3:
                qual_score -= 20
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{low_qs_count}/{len(qs_values)} słów kluczowych z Quality Score < 5 ({low_qs_pct*100:.0f}%)",
                    "action": "keywords",
                })
            elif low_qs_pct > 0.15:
                qual_score -= 10
                issues.append({
                    "severity": "LOW",
                    "message": f"{low_qs_count} słów z niskim Quality Score (< 5)",
                    "action": "keywords",
                })

            qual_details["avg_quality_score"] = round(avg_qs, 1)
            qual_details["low_qs_count"] = low_qs_count
            qual_details["total_keywords"] = len(qs_values)
        else:
            qual_details["avg_quality_score"] = None
            qual_details["total_keywords"] = 0

        # 2b. Ad Strength
        ads = []
        if ad_group_ids:
            ads = self.db.query(Ad.ad_strength).filter(
                Ad.ad_group_id.in_(ad_group_ids),
                Ad.status == "ENABLED",
                Ad.ad_strength.isnot(None),
            ).all()

        if ads:
            strength_map = {"EXCELLENT": 4, "GOOD": 3, "AVERAGE": 2, "POOR": 1}
            total_ads = len(ads)
            poor_ads = sum(1 for a in ads if (a[0] or "").upper() == "POOR")
            avg_ads = sum(1 for a in ads if (a[0] or "").upper() == "AVERAGE")
            weak_pct = (poor_ads + avg_ads) / total_ads if total_ads else 0

            if weak_pct > 0.5:
                qual_score -= 20
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{poor_ads + avg_ads}/{total_ads} reklam z siłą POOR/AVERAGE — popraw nagłówki i opisy",
                    "action": "recommendations",
                })
            elif weak_pct > 0.25:
                qual_score -= 10
            qual_details["poor_ads"] = poor_ads
            qual_details["average_ads"] = avg_ads
            qual_details["total_ads"] = total_ads
        else:
            qual_details["total_ads"] = 0

        qual_score = max(0, qual_score)

        # =====================================================================
        # PILLAR 3: EFFICIENCY (20%) — wasted spend, search term pollution
        # =====================================================================
        eff_score = 100
        eff_details = {}

        # 3a. Wasted spend — keywords with cost but 0 conversions
        if ad_group_ids and total_cost > 0:
            wasted_kw = self.db.query(
                func.sum(Keyword.cost_micros)
            ).filter(
                Keyword.ad_group_id.in_(ad_group_ids),
                Keyword.status == "ENABLED",
                Keyword.conversions == 0,
                Keyword.cost_micros > 0,
            ).scalar() or 0
            wasted_kw_usd = wasted_kw / 1_000_000
            wasted_pct = wasted_kw_usd / total_cost if total_cost > 0 else 0

            if wasted_pct > 0.4:
                eff_score -= 35
                issues.append({
                    "severity": "HIGH",
                    "message": f"{wasted_pct*100:.0f}% budżetu na słowa bez konwersji (${wasted_kw_usd:,.0f})",
                    "action": "keywords",
                })
            elif wasted_pct > 0.25:
                eff_score -= 20
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{wasted_pct*100:.0f}% budżetu na słowa bez konwersji",
                    "action": "keywords",
                })
            elif wasted_pct > 0.15:
                eff_score -= 10
            eff_details["wasted_spend_pct"] = round(wasted_pct * 100, 1)
        else:
            eff_details["wasted_spend_pct"] = 0

        # 3b. Search term waste — search terms with cost but 0 conversions
        waste_terms = self.db.query(
            func.sum(SearchTerm.cost_micros)
        ).filter(
            SearchTerm.campaign_id.in_(campaign_ids),
            SearchTerm.conversions == 0,
            SearchTerm.cost_micros > 0,
        ).scalar() or 0
        waste_terms_usd = waste_terms / 1_000_000
        st_waste_pct = waste_terms_usd / total_cost if total_cost > 0 else 0
        if st_waste_pct > 0.3:
            eff_score -= 25
            issues.append({
                "severity": "MEDIUM",
                "message": f"{st_waste_pct*100:.0f}% wydatków na wyszukiwania bez konwersji — dodaj wykluczenia",
                "action": "search-terms",
            })
        elif st_waste_pct > 0.2:
            eff_score -= 15
        eff_details["search_term_waste_pct"] = round(st_waste_pct * 100, 1)

        # 3c. Budget pacing (uses period dates, not hardcoded today)
        import calendar as _cal
        ref_date = period_end
        month_start = ref_date.replace(day=1)
        days_elapsed = (ref_date - month_start).days + 1
        days_in_month = _cal.monthrange(ref_date.year, ref_date.month)[1]
        month_progress = days_elapsed / days_in_month

        pacing_issues = 0
        if month_progress > 0.10:
            for cid, agg in camp_agg.items():
                camp = agg["campaign"]
                if not camp.budget_micros or camp.budget_micros <= 0:
                    continue
                budget_monthly = (camp.budget_micros / 1_000_000) * days_in_month
                # Get spend for this month only
                month_spend_micros = sum(
                    r.cost_micros or 0 for r in metrics_by_camp.get(camp.id, [])
                    if r.date >= month_start
                )
                actual_spend = month_spend_micros / 1_000_000
                expected_spend = budget_monthly * month_progress
                if expected_spend <= 0:
                    continue
                pct = actual_spend / expected_spend

                if pct < 0.40 and month_progress > 0.30:
                    pacing_issues += 1
                    issues.append({
                        "severity": "MEDIUM",
                        "message": f"'{camp.name}' niedowydaje budżetu ({pct*100:.0f}% oczekiwanego)",
                        "action": "campaigns",
                    })
                elif pct > 1.30:
                    pacing_issues += 1
                    issues.append({
                        "severity": "HIGH",
                        "message": f"'{camp.name}' przepala budżet ({pct*100:.0f}% oczekiwanego)",
                        "action": "campaigns",
                    })

        if pacing_issues:
            eff_score -= min(pacing_issues * 10, 20)
        eff_details["pacing_issues"] = pacing_issues
        eff_score = max(0, eff_score)

        # =====================================================================
        # PILLAR 4: COVERAGE (15%) — impression share
        # =====================================================================
        cov_score = 100
        cov_details = {}

        # Only for SEARCH campaigns (IS is not meaningful for PMax/Display)
        search_camps = [cid for cid, agg in camp_agg.items()
                        if (agg["campaign"].campaign_type or "").upper() == "SEARCH"]

        all_is_vals = []
        all_budget_lost = []
        all_rank_lost = []
        for cid in search_camps:
            agg = camp_agg[cid]
            all_is_vals.extend(agg["search_is"])
            all_budget_lost.extend(agg["budget_lost_is"])
            all_rank_lost.extend(agg["rank_lost_is"])

        if all_is_vals:
            avg_is = sum(all_is_vals) / len(all_is_vals)
            # IS scoring: >80% = great, 60-80% ok, 40-60% concern, <40% bad
            if avg_is >= 0.80:
                pass
            elif avg_is >= 0.60:
                cov_score -= 15
            elif avg_is >= 0.40:
                cov_score -= 30
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"Impression Share średnio {avg_is*100:.0f}% — tracisz widoczność",
                    "action": "campaigns",
                })
            else:
                cov_score -= 45
                issues.append({
                    "severity": "HIGH",
                    "message": f"Impression Share tylko {avg_is*100:.0f}% — kampanie są słabo widoczne",
                    "action": "campaigns",
                })
            cov_details["avg_impression_share"] = round(avg_is * 100, 1)
        else:
            cov_details["avg_impression_share"] = None

        if all_budget_lost:
            avg_budget_lost = sum(all_budget_lost) / len(all_budget_lost)
            if avg_budget_lost > 0.20:
                cov_score -= 25
                issues.append({
                    "severity": "HIGH",
                    "message": f"Tracisz {avg_budget_lost*100:.0f}% wyświetleń przez zbyt niski budżet",
                    "action": "campaigns",
                })
            elif avg_budget_lost > 0.10:
                cov_score -= 15
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{avg_budget_lost*100:.0f}% wyświetleń utraconych przez budżet",
                    "action": "campaigns",
                })
            cov_details["avg_budget_lost_is"] = round(avg_budget_lost * 100, 1)
        else:
            cov_details["avg_budget_lost_is"] = None

        if all_rank_lost:
            avg_rank_lost = sum(all_rank_lost) / len(all_rank_lost)
            if avg_rank_lost > 0.25:
                cov_score -= 20
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{avg_rank_lost*100:.0f}% wyświetleń utraconych przez niski ranking (QS/stawki)",
                    "action": "keywords",
                })
            elif avg_rank_lost > 0.15:
                cov_score -= 10
            cov_details["avg_rank_lost_is"] = round(avg_rank_lost * 100, 1)
        else:
            cov_details["avg_rank_lost_is"] = None

        cov_score = max(0, cov_score)

        # =====================================================================
        # PILLAR 5: STABILITY (10%) — alerts, CTR trend
        # =====================================================================
        stab_score = 100
        stab_details = {}

        # 5a. Unresolved alerts
        alerts = self.db.query(Alert).filter(
            Alert.client_id == client_id,
            Alert.resolved_at.is_(None),
        ).all()
        high_alerts = [a for a in alerts if a.severity == "HIGH"]
        med_alerts = [a for a in alerts if a.severity == "MEDIUM"]

        if high_alerts:
            stab_score -= min(len(high_alerts) * 15, 40)
            issues.append({
                "severity": "HIGH",
                "message": f"{len(high_alerts)} nierozwiązanych alertów HIGH",
                "action": "alerts",
            })
        if med_alerts:
            stab_score -= min(len(med_alerts) * 8, 20)
            if not high_alerts:  # don't spam issues
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{len(med_alerts)} alertów MEDIUM do przejrzenia",
                    "action": "alerts",
                })
        stab_details["high_alerts"] = len(high_alerts)
        stab_details["medium_alerts"] = len(med_alerts)

        # 5b. CTR trend (second half vs first half, exclude PMax/Display/Video)
        half_period = period_len // 2
        ctr_eligible_ids = [c.id for c in active_campaigns
                           if (c.campaign_type or "").upper() not in ("PERFORMANCE_MAX", "DISPLAY", "VIDEO")]
        midpoint = period_start + timedelta(days=half_period)

        if ctr_eligible_ids and half_period >= 3:
            def _sum_ctr(d_from, d_to):
                subset = [r for r in all_metrics
                          if r.campaign_id in ctr_eligible_ids and d_from <= r.date <= d_to]
                clicks = sum(r.clicks or 0 for r in subset)
                imps = sum(r.impressions or 0 for r in subset)
                return clicks / imps if imps else 0

            ctr_last = _sum_ctr(midpoint, period_end)
            ctr_prev = _sum_ctr(period_start, midpoint)
            if ctr_prev > 0 and ctr_last < ctr_prev * 0.85:
                drop_pct = round((ctr_prev - ctr_last) / ctr_prev * 100, 1)
                stab_score -= min(drop_pct, 30)  # proportional to drop, max -30
                issues.append({
                    "severity": "HIGH" if drop_pct > 25 else "MEDIUM",
                    "message": f"CTR spadł o {drop_pct}% w drugiej połowie okresu",
                    "action": "keywords",
                })
                stab_details["ctr_drop_pct"] = drop_pct
            else:
                stab_details["ctr_drop_pct"] = 0
        else:
            stab_details["ctr_drop_pct"] = 0

        stab_score = max(0, stab_score)

        # =====================================================================
        # PILLAR 6: STRUCTURE (10%) — ad group health, extensions
        # =====================================================================
        struct_score = 100
        struct_details = {}

        if ad_group_ids:
            # 6a. Ad groups with < 2 enabled ads
            ad_counts = self.db.query(
                Ad.ad_group_id, func.count(Ad.id)
            ).filter(
                Ad.ad_group_id.in_(ad_group_ids),
                Ad.status == "ENABLED",
            ).group_by(Ad.ad_group_id).all()
            ad_count_map = dict(ad_counts)
            thin_groups = sum(1 for agid in ad_group_ids if ad_count_map.get(agid, 0) < 2)
            if thin_groups > 0:
                thin_pct = thin_groups / len(ad_group_ids)
                struct_score -= min(thin_pct * 50, 30)
                if thin_pct > 0.2:
                    issues.append({
                        "severity": "MEDIUM",
                        "message": f"{thin_groups} grup reklam z < 2 reklamami — ograniczone testowanie",
                        "action": "recommendations",
                    })
            struct_details["thin_ad_groups"] = thin_groups

            # 6b. Missing sitelink extensions (campaign level)
            sitelink_camps = set()
            camp_assets = self.db.query(CampaignAsset.campaign_id).filter(
                CampaignAsset.campaign_id.in_(campaign_ids),
                CampaignAsset.asset_type == "SITELINK",
            ).distinct().all()
            sitelink_camps = {ca[0] for ca in camp_assets}
            missing_sitelinks = [agg["campaign"].name for cid, agg in camp_agg.items()
                                 if cid not in sitelink_camps
                                 and (agg["campaign"].campaign_type or "").upper() == "SEARCH"]
            if missing_sitelinks:
                struct_score -= min(len(missing_sitelinks) * 10, 25)
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"{len(missing_sitelinks)} kampanii Search bez sitelinków",
                    "action": "recommendations",
                })
            struct_details["missing_sitelinks"] = len(missing_sitelinks)
        else:
            struct_details["thin_ad_groups"] = 0
            struct_details["missing_sitelinks"] = 0

        struct_score = max(0, struct_score)

        # =====================================================================
        # FINAL: Weighted average
        # =====================================================================
        pillars = {
            "performance": {"score": round(perf_score), "weight": 25, "details": perf_details},
            "quality":     {"score": round(qual_score), "weight": 20, "details": qual_details},
            "efficiency":  {"score": round(eff_score),  "weight": 20, "details": eff_details},
            "coverage":    {"score": round(cov_score),  "weight": 15, "details": cov_details},
            "stability":   {"score": round(stab_score), "weight": 10, "details": stab_details},
            "structure":   {"score": round(struct_score), "weight": 10, "details": struct_details},
        }

        final_score = sum(p["score"] * p["weight"] for p in pillars.values()) / 100
        final_score = max(0, min(100, round(final_score)))

        # Sort issues: HIGH first, then MEDIUM, then LOW/INFO
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
        issues.sort(key=lambda i: severity_order.get(i.get("severity", "INFO"), 99))

        # Positive message if no issues
        if not issues:
            issues.append({
                "severity": "INFO",
                "message": "Konto w dobrej kondycji — brak krytycznych problemów",
                "action": "dashboard",
            })

        return {
            "score": final_score,
            "issues": issues,
            "breakdown": pillars,
            "campaigns_with_data": campaigns_with_data,
            "total_campaigns": total_campaigns,
            "data_available": campaigns_with_data > 0,
        }

    def _health_empty_response(self, total_campaigns: int, issues: list) -> dict:
        """Return health score response when no data is available."""
        empty_pillar = {"score": 0, "weight": 0, "details": {}}
        return {
            "score": 0,
            "issues": issues or [{"severity": "HIGH", "message": "Brak aktywnych kampanii", "action": "sync"}],
            "breakdown": {
                "performance": {**empty_pillar, "weight": 25},
                "quality": {**empty_pillar, "weight": 20},
                "efficiency": {**empty_pillar, "weight": 20},
                "coverage": {**empty_pillar, "weight": 15},
                "stability": {**empty_pillar, "weight": 10},
                "structure": {**empty_pillar, "weight": 10},
            },
            "campaigns_with_data": 0,
            "total_campaigns": total_campaigns,
            "data_available": False,
        }

    # -----------------------------------------------------------------------
    # NEW: Campaign Trends — mini sparklines for campaigns table
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

    def get_dayparting(
        self, client_id: int, days: int = 30,
        date_from: date | None = None, date_to: date | None = None,
        campaign_type: str | None = None, campaign_status: str | None = None,
    ) -> dict:
        """Aggregate campaign metrics by day of week from MetricDaily."""
        from app.utils.date_utils import resolve_dates as _rd
        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)
        if not campaign_ids:
            return {"period_days": period_days, "days": []}

        rows = self.db.query(MetricDaily).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= date_from,
            MetricDaily.date <= date_to,
        ).all()

        dow_agg: dict[int, dict] = {}
        for r in rows:
            dow = r.date.weekday()
            if dow not in dow_agg:
                dow_agg[dow] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                "conversions": 0.0, "conv_value_micros": 0, "count": 0}
            dow_agg[dow]["clicks"] += r.clicks or 0
            dow_agg[dow]["impressions"] += r.impressions or 0
            dow_agg[dow]["cost_micros"] += r.cost_micros or 0
            dow_agg[dow]["conversions"] += r.conversions or 0
            dow_agg[dow]["conv_value_micros"] += r.conversion_value_micros or 0
            dow_agg[dow]["count"] += 1

        DOW_NAMES = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
        days_data = []
        for dow in range(7):
            a = dow_agg.get(dow, {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                  "conversions": 0.0, "conv_value_micros": 0, "count": 0})
            cost = a["cost_micros"] / 1_000_000
            cv = a["conv_value_micros"] / 1_000_000
            n = max(a["count"], 1)
            days_data.append({
                "day_of_week": dow,
                "day_name": DOW_NAMES[dow],
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
            })
        return {"period_days": period_days, "days": days_data}

    # -----------------------------------------------------------------------
    # RSA Analysis — ad copy performance per ad group
    # -----------------------------------------------------------------------

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

    def get_hourly_dayparting(self, client_id: int, days: int = 7,
                              date_from: date | None = None, date_to: date | None = None,
                              campaign_type: str | None = None, campaign_status: str | None = None) -> dict:
        """Aggregate SEARCH campaign metrics by hour of day."""
        from app.utils.date_utils import resolve_dates as _rd

        date_from, date_to = _rd(days, date_from, date_to)
        period_days = (date_to - date_from).days

        campaign_ids = self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)
        if not campaign_ids:
            return {"period_days": period_days, "hours": []}

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
            })
        return {"period_days": period_days, "hours": hours_data}

    # ------------------------------------------------------------------
    # B2: Search Terms Trend Analysis
    # ------------------------------------------------------------------

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

    def _aggregate_metric_daily(self, campaign_id: int, start: date, end: date) -> dict | None:
        """Helper: aggregate MetricDaily for a campaign over a date range."""
        result = (
            self.db.query(
                func.sum(MetricDaily.cost_micros).label("cost"),
                func.sum(MetricDaily.conversions).label("conv"),
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impr"),
                func.sum(MetricDaily.conversion_value_micros).label("value"),
            )
            .filter(
                MetricDaily.campaign_id == campaign_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .first()
        )
        if not result or not result.clicks:
            return None

        cost = (result.cost or 0) / 1_000_000
        conv = float(result.conv or 0)
        clicks = result.clicks or 0
        impr = result.impr or 0
        value = (result.value or 0) / 1_000_000

        return {
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "cpa_usd": round(cost / conv, 2) if conv > 0 else 0,
            "ctr": round(clicks / impr * 100, 2) if impr > 0 else 0,
            "roas": round(value / cost, 2) if cost > 0 else 0,
            "clicks": clicks,
            "impressions": impr,
        }

    # ───────────────────────────────────────────────────────
    # GAP 6B: Bid Strategy Change Impact
    # ───────────────────────────────────────────────────────

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

    def _create_alert(self, **kwargs) -> Alert | None:
        """Create alert if not already exists (deduplicate).

        Args:
            **kwargs: Alert fields (client_id, campaign_id, alert_type, etc.)

        Returns:
            Alert object if created, None if already exists
        """
        # Check if similar unresolved alert exists
        existing = self.db.query(Alert).filter(
            Alert.client_id == kwargs["client_id"],
            Alert.campaign_id == kwargs.get("campaign_id"),
            Alert.alert_type == kwargs["alert_type"],
            Alert.resolved_at.is_(None)  # only unresolved
        ).first()

        if existing:
            return None  # already reported

        alert = Alert(**kwargs)
        self.db.add(alert)
        return alert

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
