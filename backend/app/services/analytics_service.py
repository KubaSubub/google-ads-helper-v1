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
        is_mock = False
        if not day_map:
            is_mock = True
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

    def get_health_score(self, client_id: int, campaign_type: str | None = None, status: str | None = None) -> dict:
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
        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_type and campaign_type != "ALL":
            campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
        if status and status != "ALL":
            campaign_q = campaign_q.filter(Campaign.status == status)
        else:
            campaign_q = campaign_q.filter(Campaign.status == "ENABLED")
        active_campaigns = campaign_q.all()

        no_conv_campaigns = []
        low_roas_campaigns = []
        campaigns_with_data = 0
        total_campaigns = len(active_campaigns)

        for campaign in active_campaigns:
            rows = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= days_30_ago,
            ).all()
            if not rows:
                continue
            campaigns_with_data += 1
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

        data_available = campaigns_with_data > 0

        # Add warning if no data available
        if total_campaigns > 0 and campaigns_with_data == 0:
            issues.insert(0, {
                "severity": "HIGH",
                "message": "Brak danych metryk — synchronizuj konto aby zebrać dane",
                "action": "sync",
            })

        return {
            "score": max(0, min(100, score)),
            "issues": issues,
            "campaigns_with_data": campaigns_with_data,
            "total_campaigns": total_campaigns,
            "data_available": data_available,
        }

    # -----------------------------------------------------------------------
    # NEW: Campaign Trends — mini sparklines for campaigns table
    # -----------------------------------------------------------------------

    def get_campaign_trends(self, client_id: int, days: int = 7, campaign_type: str | None = None, status: str | None = None) -> dict:
        """Return per-campaign cost trend for sparkline display.

        Returns last `days` daily cost values for each campaign.
        Falls back to mock data if MetricDaily is empty.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_type and campaign_type != "ALL":
            campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
        if status and status != "ALL":
            campaign_q = campaign_q.filter(Campaign.status == status)
        campaigns = campaign_q.all()

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
        campaign_type: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by device for SEARCH campaigns.

        Returns per-device totals: clicks, impressions, cost, conversions, CTR, CPC, ROAS.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        if campaign_type and campaign_type != "ALL":
            campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
        if status and status != "ALL":
            campaign_q = campaign_q.filter(Campaign.status == status)
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
        campaign_type: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Aggregate MetricSegmented by geo_city.

        Returns top cities by cost, with per-city totals.
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_id:
            campaign_q = campaign_q.filter(Campaign.id == campaign_id)
        if campaign_type and campaign_type != "ALL":
            campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
        if status and status != "ALL":
            campaign_q = campaign_q.filter(Campaign.status == status)
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

    # -----------------------------------------------------------------------
    # Dayparting — day-of-week performance analysis
    # -----------------------------------------------------------------------

    def get_dayparting(self, client_id: int, days: int = 30) -> dict:
        """Aggregate SEARCH campaign metrics by day of week from MetricDaily."""
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_ids = [
            c.id for c in self.db.query(Campaign).filter(
                Campaign.client_id == client_id,
                Campaign.campaign_type == "SEARCH",
            ).all()
        ]
        if not campaign_ids:
            return {"period_days": days, "days": []}

        rows = self.db.query(MetricDaily).filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= date_from,
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
        return {"period_days": days, "days": days_data}

    # -----------------------------------------------------------------------
    # RSA Analysis — ad copy performance per ad group
    # -----------------------------------------------------------------------

    def get_rsa_analysis(self, client_id: int) -> dict:
        """Analyze RSA ad performance per ad group for SEARCH campaigns."""
        from app.models.ad import Ad
        from app.models.ad_group import AdGroup

        ads = (
            self.db.query(Ad)
            .join(AdGroup, Ad.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Campaign.campaign_type == "SEARCH",
            )
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
    ) -> dict:
        """Aggregate search term metrics by word/n-gram."""
        from app.models.search_term import SearchTerm
        from app.models.ad_group import AdGroup
        from collections import defaultdict
        from sqlalchemy import or_

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
            .filter(Campaign.client_id == client_id)
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

    def get_match_type_analysis(self, client_id: int, days: int = 30) -> dict:
        """Compare keyword performance grouped by match type using KeywordDaily."""
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup

        today = date.today()
        date_from = today - timedelta(days=days)

        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Campaign.campaign_type == "SEARCH")
            .all()
        )
        kw_match = {kw.id: kw.match_type for kw in keywords}
        kw_ids = list(kw_match.keys())
        if not kw_ids:
            return {"period_days": days, "match_types": []}

        daily = (
            self.db.query(KeywordDaily)
            .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from)
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
        return {"period_days": days, "match_types": match_types}

    # -----------------------------------------------------------------------
    # Landing Page Analysis — performance by final URL
    # -----------------------------------------------------------------------

    def get_landing_page_analysis(self, client_id: int, days: int = 30) -> dict:
        """Aggregate keyword metrics grouped by landing page (final_url)."""
        from app.models.keyword_daily import KeywordDaily
        from app.models.ad_group import AdGroup

        today = date.today()
        date_from = today - timedelta(days=days)

        keywords = (
            self.db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        kw_url = {kw.id: kw.final_url or "brak URL" for kw in keywords}
        kw_ids = list(kw_url.keys())
        if not kw_ids:
            return {"period_days": days, "pages": []}

        daily = (
            self.db.query(KeywordDaily)
            .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from)
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
        return {"period_days": days, "pages": pages}

    # -----------------------------------------------------------------------
    # Wasted Spend Summary — total waste across all entities
    # -----------------------------------------------------------------------

    def get_wasted_spend(self, client_id: int, days: int = 30) -> dict:
        """Calculate wasted spend: keywords, search terms, ads with 0 conversions."""
        from app.models.search_term import SearchTerm
        from app.models.ad import Ad
        from app.models.ad_group import AdGroup
        from app.models.keyword_daily import KeywordDaily
        from sqlalchemy import or_

        today = date.today()
        date_from = today - timedelta(days=days)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
        ).all()
        campaign_ids = [c.id for c in campaigns]
        if not campaign_ids:
            return {"period_days": days, "total_waste_usd": 0, "total_spend_usd": 0,
                    "waste_pct": 0, "categories": {}}

        # Total spend for context
        total_spend_micros = (
            self.db.query(func.sum(MetricDaily.cost_micros))
            .filter(MetricDaily.campaign_id.in_(campaign_ids), MetricDaily.date >= date_from)
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
                .filter(KeywordDaily.keyword_id.in_(kw_ids), KeywordDaily.date >= date_from)
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

        # 2. Search terms: 0 conversions + clicks >= 3
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
        ad_waste = 0.0
        ad_waste_items = []
        ads = (
            self.db.query(Ad)
            .join(AdGroup, Ad.ad_group_id == AdGroup.id)
            .filter(AdGroup.campaign_id.in_(campaign_ids), Ad.status == "ENABLED")
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
            "period_days": days,
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

    def get_bidding_advisor(self, client_id: int, days: int = 30) -> dict:
        """Analyze conversion volume per campaign and recommend bidding strategy."""
        today = date.today()
        date_from = today - timedelta(days=days)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
            Campaign.status == "ENABLED",
        ).all()

        MANUAL_STRATEGIES = {"MANUAL_CPC", "MAXIMIZE_CLICKS", "ENHANCED_CPC"}
        SMART_LOW = {"TARGET_CPA", "MAXIMIZE_CONVERSIONS"}
        SMART_HIGH = {"TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE"}

        results = []
        for campaign in campaigns:
            rows = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= date_from,
            ).all()

            total_conv = sum(r.conversions or 0 for r in rows)
            total_cost_usd = sum(r.cost_micros or 0 for r in rows) / 1_000_000
            current = (campaign.bidding_strategy or "UNKNOWN").upper()

            if total_conv < 30:
                recommended = "MANUAL_CPC"
                reason = f"Tylko {total_conv:.0f} konwersji w {days}d — za mało dla Smart Bidding (min. 30)"
                status = "OK" if current in MANUAL_STRATEGIES else "CHANGE_RECOMMENDED"
            elif total_conv <= 50:
                recommended = "TARGET_CPA"
                reason = f"{total_conv:.0f} konwersji w {days}d — wystarczające dla Target CPA"
                if current in SMART_LOW or current in SMART_HIGH:
                    status = "OK"
                else:
                    status = "UPGRADE_RECOMMENDED"
            else:
                recommended = "TARGET_ROAS"
                reason = f"{total_conv:.0f} konwersji w {days}d — wystarczające dla Target ROAS"
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
            "period_days": days,
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

    def get_hourly_dayparting(self, client_id: int, days: int = 7) -> dict:
        """Aggregate SEARCH campaign metrics by hour of day."""
        today = date.today()
        date_from = today - timedelta(days=days)

        campaign_ids = [
            c.id for c in self.db.query(Campaign).filter(
                Campaign.client_id == client_id,
                Campaign.campaign_type == "SEARCH",
            ).all()
        ]
        if not campaign_ids:
            return {"period_days": days, "hours": []}

        rows = self.db.query(MetricSegmented).filter(
            MetricSegmented.campaign_id.in_(campaign_ids),
            MetricSegmented.date >= date_from,
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
        return {"period_days": days, "hours": hours_data}

    # ------------------------------------------------------------------
    # B2: Search Terms Trend Analysis
    # ------------------------------------------------------------------

    def get_search_term_trends(self, client_id: int, days: int = 30, min_clicks: int = 5) -> dict:
        """Analyze search term performance trends over time.

        Groups search terms by text and compares recent vs earlier performance
        to identify rising/declining terms.
        """
        from app.models.search_term import SearchTerm

        today = date.today()
        window_start = today - timedelta(days=days - 1)
        mid_point = today - timedelta(days=days // 2)

        campaign_ids = [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
        ).all()]
        if not campaign_ids:
            return {"rising": [], "declining": [], "new_terms": [], "total_terms": 0}

        terms = self.db.query(SearchTerm).filter(
            SearchTerm.campaign_id.in_(campaign_ids),
            SearchTerm.date_from >= window_start,
        ).all()

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
            "period_days": days,
        }

    # ------------------------------------------------------------------
    # B3: Close Variant Analysis
    # ------------------------------------------------------------------

    def get_close_variant_analysis(self, client_id: int, days: int = 30) -> dict:
        """Analyze close variants — search terms that triggered exact/phrase keywords
        but differ from the keyword text.
        """
        from app.models.ad_group import AdGroup
        from app.models.search_term import SearchTerm

        today = date.today()
        window_start = today - timedelta(days=days - 1)

        campaign_ids = [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
        ).all()]
        if not campaign_ids:
            return {"variants": [], "summary": {}}

        # Get search terms with their triggering keywords
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
            "period_days": days,
        }

    # ------------------------------------------------------------------
    # A3: Conversion Tracking Health
    # ------------------------------------------------------------------

    def get_conversion_tracking_health(self, client_id: int, days: int = 30) -> dict:
        """Audit conversion tracking setup and data quality."""
        today = date.today()
        window_start = today - timedelta(days=days - 1)

        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED",
        ).all()
        if not campaigns:
            return {"status": "no_campaigns", "campaigns": [], "score": 0}

        campaign_ids = [c.id for c in campaigns]
        results = []
        total_score = 0

        for c in campaigns:
            metrics = self.db.query(MetricDaily).filter(
                MetricDaily.campaign_id == c.id,
                MetricDaily.date >= window_start,
                MetricDaily.date <= today,
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

            if days_with_data < days * 0.5:
                issues.append(f"Braki danych ({days_with_data}/{days} dni)")
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
            "period_days": days,
        }

    # ------------------------------------------------------------------
    # G2: Keyword Expansion Suggestions
    # ------------------------------------------------------------------

    def get_keyword_expansion(self, client_id: int, days: int = 30, min_clicks: int = 3, min_conversions: float = 0.5) -> dict:
        """Suggest new keywords based on high-performing search terms
        that aren't already tracked as keywords.
        """
        from app.models.ad_group import AdGroup
        from app.models.search_term import SearchTerm

        today = date.today()
        window_start = today - timedelta(days=days - 1)

        campaign_ids = [c.id for c in self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.campaign_type == "SEARCH",
        ).all()]
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
            "period_days": days,
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
