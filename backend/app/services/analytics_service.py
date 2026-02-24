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
from app.utils.formatters import micros_to_currency


class AnalyticsService:
    """Handles KPI calculations and anomaly detection."""

    def __init__(self, db: Session):
        self.db = db

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

            campaign_metrics[campaign.id] = {
                "spend_7d": sum(r.cost_micros or 0 for r in rows_7d),
                "clicks_7d": sum(r.clicks or 0 for r in rows_7d),
                "impressions_7d": sum(r.impressions or 0 for r in rows_7d),
                "conversions_7d": sum(r.conversions or 0 for r in rows_7d),
                "conversions_30d": sum(r.conversions or 0 for r in rows_30d),
                "days_30d": len(rows_30d),
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
        campaign_type: str = "ALL",
        status: str = "ALL",
    ) -> dict:
        """Return daily aggregated metrics for TrendExplorer chart.

        Queries MetricDaily joined to Campaign, aggregates per day.
        Falls back to mock data if MetricDaily is empty.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        # Build campaign filter
        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_type != "ALL":
            campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
        if status != "ALL":
            campaign_q = campaign_q.filter(Campaign.status == status)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": days, "data": [], "totals": {}}

        # Query daily rows
        rows = (
            self.db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= date_from,
                MetricDaily.date <= today,
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
        if not day_map:
            day_map = self._mock_daily_data(campaign_ids, date_from, today)

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
            "period_days": days,
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

    def get_health_score(self, client_id: int) -> dict:
        """Calculate account health score (0-100) based on lightweight DB queries.

        Does NOT call recommendations_engine — uses only MetricDaily + Alert + Campaign.
        """
        score = 100
        issues = []
        today = date.today()
        days_30_ago = today - timedelta(days=30)
        days_7_ago = today - timedelta(days=7)
        days_14_ago = today - timedelta(days=14)

        # 1. Unresolved alerts
        alerts = self.db.query(Alert).filter(
            Alert.client_id == client_id,
            Alert.resolved_at.is_(None),
        ).all()
        high_alerts = [a for a in alerts if a.severity == "HIGH"]
        med_alerts = [a for a in alerts if a.severity == "MEDIUM"]
        score -= len(high_alerts) * 10
        score -= len(med_alerts) * 5
        if high_alerts:
            issues.append({
                "severity": "HIGH",
                "message": f"{len(high_alerts)} alert{'y' if len(high_alerts) > 1 else ''} wysokiej wagi wymagają uwagi",
                "action": "alerts",
            })
        if med_alerts:
            issues.append({
                "severity": "MEDIUM",
                "message": f"{len(med_alerts)} alert{'y' if len(med_alerts) > 1 else ''} średniej wagi",
                "action": "alerts",
            })

        # 2. Active campaigns with 0 conversions in last 30 days
        active_campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED",
        ).all()

        no_conv_campaigns = []
        low_roas_campaigns = []

        for campaign in active_campaigns:
            rows = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= days_30_ago,
            ).all()
            if not rows:
                continue
            total_conv = sum(r.conversions or 0 for r in rows)
            total_conv_value = sum(r.conversion_value_micros or 0 for r in rows) / 1_000_000
            total_cost = sum(r.cost_micros or 0 for r in rows) / 1_000_000
            total_clicks = sum(r.clicks or 0 for r in rows)

            if total_clicks > 10 and total_conv == 0:
                no_conv_campaigns.append(campaign.name)
                score -= 3

            roas = total_conv_value / total_cost if total_cost > 0 else 0
            if total_cost > 10 and roas < 1:
                low_roas_campaigns.append(campaign.name)
                score -= 5

        if no_conv_campaigns:
            issues.append({
                "severity": "HIGH",
                "message": f"{len(no_conv_campaigns)} kampania/e aktywne bez konwersji (ostatnie 30 dni)",
                "action": "recommendations",
            })
        if low_roas_campaigns:
            issues.append({
                "severity": "MEDIUM",
                "message": f"{len(low_roas_campaigns)} kampania/e z ROAS < 1 (tracisz pieniądze)",
                "action": "campaigns",
            })

        # 3. CTR trend: last 7d vs previous 7d
        campaign_ids = [c.id for c in active_campaigns]
        if campaign_ids:
            def _sum_ctr(d_from, d_to):
                rows = self.db.query(MetricDaily).filter(
                    MetricDaily.campaign_id.in_(campaign_ids),
                    MetricDaily.date >= d_from,
                    MetricDaily.date <= d_to,
                ).all()
                clicks = sum(r.clicks or 0 for r in rows)
                impressions = sum(r.impressions or 0 for r in rows)
                return clicks / impressions if impressions else 0

            ctr_last = _sum_ctr(days_7_ago, today)
            ctr_prev = _sum_ctr(days_14_ago, days_7_ago)
            if ctr_prev > 0 and ctr_last < ctr_prev * 0.85:
                score -= 5
                drop_pct = round((ctr_prev - ctr_last) / ctr_prev * 100, 1)
                issues.append({
                    "severity": "MEDIUM",
                    "message": f"CTR spada {drop_pct}% tydzień do tygodnia",
                    "action": "keywords",
                })

        # Positive insights
        if active_campaigns and not no_conv_campaigns and not low_roas_campaigns and not high_alerts:
            issues.append({
                "severity": "INFO",
                "message": "Konto w dobrej kondycji — brak krytycznych problemów",
                "action": "dashboard",
            })

        return {
            "score": max(0, min(100, score)),
            "issues": issues,
        }

    # -----------------------------------------------------------------------
    # NEW: Campaign Trends — mini sparklines for campaigns table
    # -----------------------------------------------------------------------

    def get_campaign_trends(self, client_id: int, days: int = 7) -> dict:
        """Return per-campaign cost trend for sparkline display.

        Returns last `days` daily cost values for each campaign.
        Falls back to mock data if MetricDaily is empty.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
        ).all()

        result = {}
        rand = random.Random(99)

        for campaign in campaigns:
            rows = (
                self.db.query(MetricDaily)
                .filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date >= date_from,
                    MetricDaily.date <= today,
                )
                .order_by(MetricDaily.date)
                .all()
            )

            if rows:
                trend = [round(r.cost_micros / 1_000_000, 2) for r in rows]
            else:
                # Mock: gentle curve with noise around budget
                base = campaign.budget_micros / 1_000_000 / 30 if campaign.budget_micros else 10
                trend = [round(max(0, base * (1 + rand.uniform(-0.25, 0.25))), 2) for _ in range(days)]

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
        campaign_id: int | None = None,
    ) -> dict:
        """Daily impression share metrics for SEARCH campaigns.

        Returns time-series of IS, budget-lost IS, rank-lost IS per day.
        If campaign_id is provided, returns for that campaign only.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
        )
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": days, "data": [], "summary": {}}

        rows = (
            self.db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= date_from,
                MetricDaily.date <= today,
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

        return {"period_days": days, "data": data, "summary": summary}

    # -----------------------------------------------------------------------
    # NEW: Device Breakdown
    # -----------------------------------------------------------------------

    def get_device_breakdown(
        self,
        client_id: int,
        days: int = 30,
        campaign_id: int | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by device for SEARCH campaigns.

        Returns per-device totals: clicks, impressions, cost, conversions, CTR, CPC, ROAS.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": days, "devices": []}

        rows = (
            self.db.query(MetricSegmented)
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= today,
                MetricSegmented.device.isnot(None),
            )
            .all()
        )

        # Aggregate by device
        device_agg: dict[str, dict] = {}
        for r in rows:
            dev = r.device
            if dev not in device_agg:
                device_agg[dev] = {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0, "conv_value_micros": 0}
            device_agg[dev]["clicks"] += r.clicks or 0
            device_agg[dev]["impressions"] += r.impressions or 0
            device_agg[dev]["cost_micros"] += r.cost_micros or 0
            device_agg[dev]["conversions"] += r.conversions or 0
            device_agg[dev]["conv_value_micros"] += r.conversion_value_micros or 0

        devices = []
        total_clicks = sum(d["clicks"] for d in device_agg.values())
        total_cost = sum(d["cost_micros"] for d in device_agg.values())

        for dev, agg in sorted(device_agg.items()):
            cost_usd = agg["cost_micros"] / 1_000_000
            conv_value_usd = agg["conv_value_micros"] / 1_000_000
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
            })

        return {"period_days": days, "devices": devices}

    # -----------------------------------------------------------------------
    # NEW: Geo Breakdown
    # -----------------------------------------------------------------------

    def get_geo_breakdown(
        self,
        client_id: int,
        days: int = 7,
        campaign_id: int | None = None,
        limit: int = 20,
    ) -> dict:
        """Aggregate MetricSegmented by geo_city.

        Returns top cities by cost, with per-city totals.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        campaign_ids = [c.id for c in campaign_q.all()]

        if not campaign_ids:
            return {"period_days": days, "cities": []}

        rows = (
            self.db.query(MetricSegmented)
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= date_from,
                MetricSegmented.date <= today,
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

        return {"period_days": days, "cities": cities}

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
