"""Account health score + anomaly detection.

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


class HealthMixin:
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
        # Penalties are cost-weighted: magnitude scales with share of total spend
        # at risk, not campaign count. A $15 zero-conv campaign and a $5000 one
        # do not carry equal weight. Campaigns flagged here populate
        # primary_problem_ids so Efficiency pillar can skip them (root-cause dedup).
        perf_score = 100
        perf_details = {}
        primary_problem_ids: set[int] = set()

        # 1a. Zero-conversion campaigns with significant spend.
        # Spend floor ($5) prevents trivially cheap campaigns (e.g. DSA with
        # 10 clicks at $0.05 CPC) from polluting primary_problem_ids and
        # distorting the Efficiency dedup downstream.
        no_conv_ids = {
            cid for cid, agg in camp_agg.items()
            if agg["clicks"] > 10 and agg["conversions"] == 0 and agg["cost"] >= 5
        }
        no_conv_cost = sum(camp_agg[cid]["cost"] for cid in no_conv_ids)
        no_conv_share = no_conv_cost / total_cost if total_cost > 0 else 0
        if no_conv_ids:
            # Up to -40 when 50%+ of spend produces zero conversions
            perf_score -= min(no_conv_share * 80, 40)
            issues.append({
                "severity": "HIGH",
                "message": f"{len(no_conv_ids)} kampanii bez konwersji (>10 kliknięć, 0 konwersji)",
                "action": "recommendations",
            })
            primary_problem_ids.update(no_conv_ids)
        perf_details["zero_conv_campaigns"] = len(no_conv_ids)
        perf_details["zero_conv_cost_share"] = round(no_conv_share * 100, 1)

        # 1b. Low ROAS campaigns (non-brand, cost > $20)
        low_roas_ids: set[int] = set()
        for cid, agg in camp_agg.items():
            camp = agg["campaign"]
            is_brand = (camp.campaign_role_final or "").upper() in ("BRAND", "BRAND_EXACT")
            if is_brand or agg["cost"] < 20:
                continue
            roas = agg["conv_value"] / agg["cost"] if agg["cost"] > 0 else 0
            if roas < 1.0:
                low_roas_ids.add(cid)
        low_roas_cost = sum(camp_agg[cid]["cost"] for cid in low_roas_ids)
        low_roas_share = low_roas_cost / total_cost if total_cost > 0 else 0
        if low_roas_ids:
            # Up to -35 when 50%+ of spend is on sub-1 ROAS campaigns
            perf_score -= min(low_roas_share * 70, 35)
            issues.append({
                "severity": "HIGH" if low_roas_share > 0.30 else "MEDIUM",
                "message": f"{len(low_roas_ids)} kampanii z ROAS < 1 (tracisz pieniądze)",
                "action": "campaigns",
            })
            primary_problem_ids.update(low_roas_ids)
        perf_details["low_roas_campaigns"] = len(low_roas_ids)
        perf_details["low_roas_cost_share"] = round(low_roas_share * 100, 1)
        perf_details["primary_problem_campaigns"] = len(primary_problem_ids)

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

        # Root-cause dedup shared scope: campaigns NOT already flagged as primary
        # problems in Performance. Their waste is an independent symptom, not a
        # re-expression of the same root cause.
        healthy_camp_ids = [cid for cid in campaign_ids if cid not in primary_problem_ids]
        healthy_cost = sum(camp_agg[cid]["cost"] for cid in healthy_camp_ids if cid in camp_agg)

        # 3a. Wasted spend — keywords with cost but 0 conversions, scoped to
        # healthy campaigns. Denominator is healthy_cost so the ratio reflects
        # waste *within the healthy slice* (using total_cost would understate
        # severity when a large share of spend is already excluded).
        if ad_group_ids and healthy_cost > 0:
            healthy_ag_ids = [
                ag.id for ag in self.db.query(AdGroup).filter(
                    AdGroup.campaign_id.in_(healthy_camp_ids)
                ).all()
            ] if healthy_camp_ids else []
            wasted_kw = 0
            if healthy_ag_ids:
                wasted_kw = self.db.query(
                    func.sum(Keyword.cost_micros)
                ).filter(
                    Keyword.ad_group_id.in_(healthy_ag_ids),
                    Keyword.status == "ENABLED",
                    Keyword.conversions == 0,
                    Keyword.cost_micros > 0,
                ).scalar() or 0
            wasted_kw_usd = wasted_kw / 1_000_000
            wasted_pct = wasted_kw_usd / healthy_cost

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

        # 3b. Search term waste — same healthy-only scope as 3a.
        waste_terms = 0
        if healthy_camp_ids:
            waste_terms = self.db.query(
                func.sum(SearchTerm.cost_micros)
            ).filter(
                SearchTerm.campaign_id.in_(healthy_camp_ids),
                SearchTerm.conversions == 0,
                SearchTerm.cost_micros > 0,
            ).scalar() or 0
        waste_terms_usd = waste_terms / 1_000_000
        st_waste_pct = waste_terms_usd / healthy_cost if healthy_cost > 0 else 0
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
