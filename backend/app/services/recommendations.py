"""
Recommendations Engine — implements all 7 decision rules from the Playbook.

Scans the database for keywords, search terms, and ads that match
optimization rules and generates actionable recommendations with priority.

Rules implemented:
  R1: Pause Keyword (spend > threshold, conv = 0)
  R2: Increase Bid (CVR > avg, CPA < target)
  R3: Decrease Bid (CPA > target * 1.5)
  R4: Add Search Term as Keyword (conv >= 3, CVR > avg)
  R5: Add Negative Keyword (clicks > 5, conv = 0, CTR < 1%)
  R6: Pause Ad (CTR < 50% of best ad)
  R7: Reallocate Budget (ROAS comparison between campaigns)
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Keyword, SearchTerm, Ad, AdGroup, Campaign, Client, MetricDaily
)
from app.models.metric_segmented import MetricSegmented
from app.models.asset_group import AssetGroup
from app.models.asset_group_daily import AssetGroupDaily
from app.models.campaign_audience import CampaignAudienceMetric
from app.models.campaign_asset import CampaignAsset
from app.services.recommendation_contract import (
    ACTION,
    ANALYTICS,
    BLOCKED_BY_CONTEXT,
    DESTINATION_NO_HEADROOM,
    DONOR_PROTECTED_HIGH,
    DONOR_PROTECTED_MEDIUM,
    GOOGLE_ADS_API,
    INSUFFICIENT_DATA,
    INSIGHT_ONLY,
    PLAYBOOK_RULES,
    ROLE_MISMATCH,
    ROAS_ONLY_SIGNAL,
    UNKNOWN_ROLE,
    build_action_payload,
    build_stable_key,
    compute_confidence_score,
    compute_priority,
    compute_risk_score,
    default_expires_at,
    estimate_impact_micros,
    normalize_reason_codes,
)

from app.services.campaign_roles import ensure_campaign_roles


def _micros_to_usd(micros: int | None) -> float:
    return round((micros or 0) / 1_000_000, 2)


def _ctr_micros_to_pct(ctr_val: float | int | None) -> float:
    """CTR is now stored as percentage (5.0 = 5%). Return as-is."""
    return round(float(ctr_val or 0), 2)

class RecommendationType(str, Enum):
    # MVP (R1-R7)
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    INCREASE_BID = "INCREASE_BID"
    DECREASE_BID = "DECREASE_BID"
    ADD_KEYWORD = "ADD_KEYWORD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    PAUSE_AD = "PAUSE_AD"
    REALLOCATE_BUDGET = "REALLOCATE_BUDGET"
    # v1.1 (R8-R13)
    QS_ALERT = "QS_ALERT"
    IS_BUDGET_ALERT = "IS_BUDGET_ALERT"
    IS_RANK_ALERT = "IS_RANK_ALERT"
    WASTED_SPEND_ALERT = "WASTED_SPEND_ALERT"
    PMAX_CANNIBALIZATION = "PMAX_CANNIBALIZATION"
    # v1.2 (R15-R18)
    DEVICE_ANOMALY = "DEVICE_ANOMALY"
    GEO_ANOMALY = "GEO_ANOMALY"
    BUDGET_PACING = "BUDGET_PACING"
    NGRAM_NEGATIVE = "NGRAM_NEGATIVE"
    ANALYTICS_ALERT = "ANALYTICS_ALERT"
    # v2.0 GAP rules (R19+)
    AD_GROUP_HEALTH = "AD_GROUP_HEALTH"
    DISAPPROVED_AD_ALERT = "DISAPPROVED_AD_ALERT"
    SMART_BIDDING_CONV_ALERT = "SMART_BIDDING_CONV_ALERT"
    ECPC_DEPRECATION = "ECPC_DEPRECATION"
    SCALING_OPPORTUNITY = "SCALING_OPPORTUNITY"
    TARGET_DEVIATION_ALERT = "TARGET_DEVIATION_ALERT"
    LEARNING_PERIOD_ALERT = "LEARNING_PERIOD_ALERT"
    CONVERSION_QUALITY_ALERT = "CONVERSION_QUALITY_ALERT"
    DEMOGRAPHIC_ANOMALY = "DEMOGRAPHIC_ANOMALY"
    # v2.1 (R28-R31)
    PMAX_CHANNEL_IMBALANCE = "PMAX_CHANNEL_IMBALANCE"
    ASSET_GROUP_AD_STRENGTH = "ASSET_GROUP_AD_STRENGTH"
    AUDIENCE_PERFORMANCE_ANOMALY = "AUDIENCE_PERFORMANCE_ANOMALY"
    MISSING_EXTENSIONS_ALERT = "MISSING_EXTENSIONS_ALERT"


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Recommendation:
    """A single optimization recommendation."""

    type: str
    priority: str
    entity_type: str
    entity_id: int
    entity_name: str
    campaign_name: str
    reason: str
    category: str = "RECOMMENDATION"
    current_value: Optional[str] = None
    recommended_action: Optional[str] = None
    estimated_impact: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    source: str = PLAYBOOK_RULES
    campaign_id: Optional[int] = None
    ad_group_id: Optional[int] = None
    stable_key: Optional[str] = None
    action_payload: Optional[dict] = None
    evidence_json: Optional[dict] = None
    impact_micros: Optional[int] = None
    impact_score: Optional[float] = None
    confidence_score: Optional[float] = None
    risk_score: Optional[float] = None
    score: Optional[float] = None
    executable: bool = False
    expires_at: Optional[datetime] = None
    google_resource_name: Optional[str] = None
    context_outcome: Optional[str] = None
    blocked_reasons: list[str] = field(default_factory=list)
    downgrade_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class RecommendationsEngine:
    """
    Scans the local database and generates optimization recommendations
    based on the 7 decision rules from the Google Ads Playbook.
    """

    # Configurable thresholds (can be overridden per-client)
    DEFAULT_THRESHOLDS = {
        "r1_min_spend": 50.0,          # Rule 1: min spend to trigger pause
        "r1_min_clicks": 30,            # Rule 1: min clicks to trigger pause
        "r1_low_ctr_threshold": 0.5,    # Rule 1: CTR below this = irrelevant
        "r1_low_ctr_min_impr": 1000,    # Rule 1: min impressions for CTR check
        "r2_cvr_multiplier": 1.5,       # Rule 2: CVR must be > avg * 1.5× (per SAFETY_LIMITS)
        "r2_cpa_multiplier": 0.8,       # Rule 2: CPA must be < target * this
        "r2_bid_increase_pct": 20,      # Rule 2: suggested bid increase %
        "r3_cpa_multiplier": 1.5,       # Rule 3: CPA must be > target * this
        "r3_min_spend": 100.0,          # Rule 3: min spend to trigger
        "r3_bid_decrease_pct": 20,      # Rule 3: suggested bid decrease %
        "r4_min_conversions": 3,        # Rule 4: min conversions for search term
        "r4_min_clicks_phrase": 10,     # Rule 4: min clicks for phrase match
        "r4_min_ctr_phrase": 5.0,       # Rule 4: min CTR% for phrase match
        "r5_min_clicks": 5,             # Rule 5: min clicks for negative
        "r5_max_ctr": 1.0,             # Rule 5: max CTR% for negative
        "r5_min_cost_immediate": 30.0,  # Rule 5: spend threshold for immediate neg
        "r6_ctr_ratio": 0.5,           # Rule 6: pause if CTR < best * this
        "r6_min_impressions": 500,      # Rule 6: min impressions to evaluate ad
        "r6_min_cost": 50.0,           # Rule 6: spend for zero-conv check
        "r7_roas_ratio": 2.0,          # Rule 7: realloc if ROAS_A > ROAS_B * this
        "r7_budget_move_pct": 20,       # Rule 7: % of budget to move
        # v1.1 thresholds (R8–R13)
        "r8_max_qs": 5,                 # Rule 8: QS below this triggers alert
        "r8_min_impressions": 100,      # Rule 8: min impressions to evaluate
        "r9_min_lost_is_pct": 20,       # Rule 9: min lost IS % to trigger
        "r9_high_lost_is_pct": 40,      # Rule 9: HIGH priority threshold
        "r9_budget_increase_pct": 20,   # Rule 9: suggested budget increase %
        "r10_min_rank_lost_pct": 30,    # Rule 10: min rank-lost IS %
        "r10_max_budget_lost_pct": 10,  # Rule 10: max budget-lost IS (to confirm rank issue)
        "r11_max_ctr": 0.5,            # Rule 11: CTR below this = irrelevant
        "r11_min_impressions": 1000,    # Rule 11: min impressions
        "r12_wasted_pct_medium": 25,    # Rule 12: wasted spend % for MEDIUM
        "r12_wasted_pct_high": 35,      # Rule 12: wasted spend % for HIGH
        "r13_pmax_cost_ratio": 0.5,     # Rule 13: pmax_cost > search_cost * this
        "r13_high_cost_usd": 50,        # Rule 13: HIGH priority cost threshold
        # v1.2 thresholds (R15–R18)
        "r15_cpa_multiplier": 2.0,      # Rule 15: device CPA > desktop CPA * this
        "r15_min_spend": 100.0,         # Rule 15: min device spend in USD
        "r16_cpa_multiplier": 2.0,      # Rule 16: geo CPA > campaign avg CPA * this
        "r16_min_spend": 50.0,          # Rule 16: min geo spend in USD
        "r17_overspend_ratio": 1.3,     # Rule 17: actual > expected * this = overspend
        "r17_underspend_ratio": 0.5,    # Rule 17: actual < expected * this = underspend
        "r17_min_month_pct": 0.3,       # Rule 17: min % of month elapsed for underspend
        "r18_min_cost": 100.0,          # Rule 18: min n-gram total cost in USD
        "r18_min_terms": 3,             # Rule 18: min search terms containing n-gram
        # v2.0 GAP thresholds (R19+)
        "r19_min_ads": 2,               # Rule 19: min ads per ad group for A/B
        "r19_max_keywords": 30,         # Rule 19: max keywords per ad group
        "r19_min_keywords": 2,          # Rule 19: min keywords per ad group
        "r19_zero_conv_min_cost": 50.0, # Rule 19: min spend (USD) for zero-conv flag
        "r20_min_approval_status": 1,   # Rule 20: any disapproved ad triggers
        "r21_min_conv_tcpa": 30,        # Rule 21: min conv/30d for tCPA
        "r21_min_conv_troas": 50,       # Rule 21: min conv/30d for tROAS
        "r23_min_lost_is": 0.10,        # Rule 23: min lost IS for scaling opportunity
        "r23_min_pareto_pct": 0.80,     # Rule 23: top % of value for hero campaigns
        "r24_cpa_deviation_pct": 30,
        "r24_roas_deviation_pct": 30,
        "r25_max_learning_days": 14,
        "r25_stuck_learning_days": 21,
        "r27_cpa_multiplier": 2.0,
        "r27_min_spend": 50.0,
        # v2.1 thresholds (R28-R31)
        "r28_max_cost_share": 0.60,
        "r28_min_conv_share": 0.30,
        "r29_min_spend": 50.0,
        "r30_cpa_multiplier": 2.0,
        "r30_min_spend": 50.0,
        "r31_min_sitelinks": 4,
        "r31_min_callouts": 4,
    }

    # Words that indicate irrelevant intent (word boundary matched)
    IRRELEVANT_WORDS = [
        # English
        "free", "cheap", "how to", "why", "download", "torrent",
        "tutorial", "coupon", "discount code", "sample", "template",
        "job", "salary", "career", "internship", "reddit", "youtube",
        # Polish
        "darmowe", "za darmo", "jak zrobić", "dlaczego", "pobierz",
        "praca", "wynagrodzenie", "staż", "allegro", "olx",
        "recenzja", "opinie", "forum", "wikipedia", "pdf",
    ]

    # Pre-compiled word boundary patterns for irrelevant words
    _IRRELEVANT_PATTERNS = [
        re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE)
        for w in IRRELEVANT_WORDS
    ]

    def __init__(self, thresholds: dict = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    def generate_all(
        self,
        db: Session,
        client_id: int,
        days: int = 30,
    ) -> list[dict]:
        """Run all rules and return enriched recommendations."""
        client = db.get(Client, client_id)
        enabled_campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        if client and enabled_campaigns and ensure_campaign_roles(enabled_campaigns, client):
            db.flush()

        recommendations: list[Recommendation] = []

        # MVP rules (R1-R7)
        recommendations.extend(self._rule_1_pause_keywords(db, client_id, days))
        recommendations.extend(self._rule_2_increase_bid(db, client_id, days))
        recommendations.extend(self._rule_3_decrease_bid(db, client_id, days))
        recommendations.extend(self._rule_4_add_keyword(db, client_id, days))
        recommendations.extend(self._rule_5_add_negative(db, client_id, days))
        recommendations.extend(self._rule_6_pause_ad(db, client_id, days))
        recommendations.extend(self._rule_7_reallocate_budget(db, client_id, days))

        # v1.1 rules (R8-R13)
        recommendations.extend(self._rule_8_quality_score_alert(db, client_id, days))
        recommendations.extend(self._rule_9_is_lost_budget(db, client_id, days))
        recommendations.extend(self._rule_10_is_lost_rank(db, client_id, days))
        recommendations.extend(self._rule_11_low_ctr_high_impr(db, client_id, days))
        recommendations.extend(self._rule_12_wasted_spend_alert(db, client_id, days))
        recommendations.extend(self._rule_13_pmax_search_overlap(db, client_id, days))

        # v1.2 rules (R15-R18, excluding R14)
        recommendations.extend(self._rule_15_device_anomaly(db, client_id, days))
        recommendations.extend(self._rule_16_geo_anomaly(db, client_id, days))
        recommendations.extend(self._rule_17_budget_pacing(db, client_id, days))
        recommendations.extend(self._rule_18_ngram_negative(db, client_id, days))

        # v2.0 GAP rules (R19+)
        recommendations.extend(self._rule_19_ad_group_health(db, client_id, days))
        recommendations.extend(self._rule_20_disapproved_ads(db, client_id, days))
        recommendations.extend(self._rule_21_smart_bidding_conv_threshold(db, client_id, days))
        recommendations.extend(self._rule_22_ecpc_deprecation(db, client_id, days))
        recommendations.extend(self._rule_23_scaling_opportunity(db, client_id, days))
        recommendations.extend(self._rule_24_target_vs_actual(db, client_id, days))
        recommendations.extend(self._rule_25_learning_period(db, client_id, days))
        recommendations.extend(self._rule_26_conversion_quality(db, client_id, days))
        recommendations.extend(self._rule_27_demographic_anomaly(db, client_id, days))

        # v2.1 rules (R28-R31)
        recommendations.extend(self._rule_28_pmax_channel_imbalance(db, client_id, days))
        recommendations.extend(self._rule_29_asset_group_ad_strength(db, client_id, days))
        recommendations.extend(self._rule_30_audience_performance_anomaly(db, client_id, days))
        recommendations.extend(self._rule_31_missing_extensions(db, client_id, days))

        recommendations.extend(self._analytics_alerts(db, client_id, days, recommendations))

        enriched = [self._finalize_recommendation(db, client_id, days, rec) for rec in recommendations]

        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        enriched.sort(key=lambda r: (priority_order.get(r.priority, 99), -(r.impact_micros or 0)))

        return [r.to_dict() for r in enriched]

    def _rule_1_pause_keywords(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        keywords = (
            db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Keyword.status == "ENABLED",
            )
            .all()
        )

        for kw in keywords:
            campaign = (
                db.query(Campaign)
                .join(AdGroup, Campaign.id == AdGroup.campaign_id)
                .filter(AdGroup.id == kw.ad_group_id)
                .first()
            )
            camp_name = campaign.name if campaign else "Unknown"

            kw_cost = _micros_to_usd(kw.cost_micros)
            kw_ctr = _ctr_micros_to_pct(kw.ctr)

            # Check 1: High spend, no conversions
            if (
                kw_cost >= t["r1_min_spend"]
                and (kw.conversions or 0) == 0
                and (kw.clicks or 0) >= t["r1_min_clicks"]
            ):
                recs.append(Recommendation(
                    type=RecommendationType.PAUSE_KEYWORD,
                    priority=Priority.HIGH,
                    entity_type="keyword",
                    entity_id=kw.id,
                    entity_name=kw.text,
                    campaign_name=camp_name,
                    reason=(
                        f"Spent ${kw_cost:.2f} with {kw.clicks} clicks "
                        f"but 0 conversions in the last {days} days."
                    ),
                    current_value=f"Spend: ${kw_cost:.2f}, Clicks: {kw.clicks}",
                    recommended_action="Pause this keyword",
                    estimated_impact=f"Save ~${kw_cost:.2f}/month",
                    metadata={"spend": kw_cost, "clicks": kw.clicks},
                ))

            # Check 2: Very low CTR (irrelevant keyword)
            elif (
                (kw.impressions or 0) >= t["r1_low_ctr_min_impr"]
                and kw_ctr < t["r1_low_ctr_threshold"]
            ):
                recs.append(Recommendation(
                    type=RecommendationType.PAUSE_KEYWORD,
                    priority=Priority.MEDIUM,
                    entity_type="keyword",
                    entity_id=kw.id,
                    entity_name=kw.text,
                    campaign_name=camp_name,
                    reason=(
                        f"CTR is only {kw_ctr:.2f}% with {kw.impressions} impressions. "
                        f"This keyword appears irrelevant to users."
                    ),
                    current_value=f"CTR: {kw_ctr:.2f}%, Impr: {kw.impressions}",
                    recommended_action="Pause this keyword or improve ad relevance",
                    metadata={"ctr": kw_ctr, "impressions": kw.impressions},
                ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 2: Increase Bid (high performers)
    # -----------------------------------------------------------------------
    def _rule_2_increase_bid(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        for campaign in campaigns:
            keywords = (
                db.query(Keyword)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .filter(
                    AdGroup.campaign_id == campaign.id,
                    Keyword.status == "ENABLED",
                    Keyword.clicks > 0,
                )
                .all()
            )

            if not keywords:
                continue

            total_clicks = sum(k.clicks or 0 for k in keywords)
            total_conv = sum(k.conversions or 0 for k in keywords)
            avg_cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0

            total_cost_usd = sum(_micros_to_usd(k.cost_micros) for k in keywords)
            avg_cpa = (total_cost_usd / total_conv) if total_conv > 0 else 999999

            for kw in keywords:
                if (kw.clicks or 0) == 0 or (kw.conversions or 0) < 2:
                    continue
                kw_cvr = (kw.conversions / kw.clicks * 100)
                kw_cost = _micros_to_usd(kw.cost_micros)
                kw_cpa = (kw_cost / kw.conversions) if kw.conversions > 0 else 999999

                if kw_cvr > avg_cvr * t["r2_cvr_multiplier"] and kw_cpa < avg_cpa * t["r2_cpa_multiplier"]:
                    recs.append(Recommendation(
                        type=RecommendationType.INCREASE_BID,
                        priority=Priority.MEDIUM,
                        entity_type="keyword",
                        entity_id=kw.id,
                        entity_name=kw.text,
                        campaign_name=campaign.name,
                        reason=(
                            f"CVR ({kw_cvr:.1f}%) is {kw_cvr/avg_cvr:.1f}x the campaign "
                            f"average ({avg_cvr:.1f}%), and CPA (${kw_cpa:.2f}) is below target."
                        ),
                        current_value=f"CVR: {kw_cvr:.1f}%, CPA: ${kw_cpa:.2f}",
                        recommended_action=f"Increase bid by {t['r2_bid_increase_pct']}%",
                        estimated_impact="More impressions → more conversions at good CPA",
                        metadata={
                            "cvr": round(kw_cvr, 2),
                            "cpa": round(kw_cpa, 2),
                            "avg_cvr": round(avg_cvr, 2),
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 3: Decrease Bid (poor CPA)
    # -----------------------------------------------------------------------
    def _rule_3_decrease_bid(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        for campaign in campaigns:
            keywords = (
                db.query(Keyword)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .filter(
                    AdGroup.campaign_id == campaign.id,
                    Keyword.status == "ENABLED",
                    Keyword.conversions > 0,
                )
                .all()
            )

            if not keywords:
                continue

            total_cost = sum(_micros_to_usd(k.cost_micros) for k in keywords)
            total_conv = sum(k.conversions or 0 for k in keywords)
            avg_cpa = total_cost / total_conv if total_conv > 0 else 0

            for kw in keywords:
                kw_cost = _micros_to_usd(kw.cost_micros)
                if kw_cost < t["r3_min_spend"] or (kw.conversions or 0) == 0:
                    continue
                kw_cpa = kw_cost / kw.conversions

                if kw_cpa > avg_cpa * t["r3_cpa_multiplier"]:
                    recs.append(Recommendation(
                        type=RecommendationType.DECREASE_BID,
                        priority=Priority.MEDIUM,
                        entity_type="keyword",
                        entity_id=kw.id,
                        entity_name=kw.text,
                        campaign_name=campaign.name,
                        reason=(
                            f"CPA (${kw_cpa:.2f}) is {kw_cpa/avg_cpa:.1f}x the campaign "
                            f"average (${avg_cpa:.2f}). Overpaying for conversions."
                        ),
                        current_value=f"CPA: ${kw_cpa:.2f}, Avg CPA: ${avg_cpa:.2f}",
                        recommended_action=f"Decrease bid by {t['r3_bid_decrease_pct']}%",
                        estimated_impact=f"Potential savings: ~${(kw_cpa - avg_cpa) * kw.conversions:.2f}",
                        metadata={
                            "cpa": round(kw_cpa, 2),
                            "avg_cpa": round(avg_cpa, 2),
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 4: Add Search Term as Keyword (high-converting terms)
    # -----------------------------------------------------------------------
    def _rule_4_add_keyword(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        terms = (
            db.query(
                SearchTerm.text,
                func.sum(SearchTerm.conversions).label("total_conv"),
                func.sum(SearchTerm.clicks).label("total_clicks"),
                func.sum(SearchTerm.cost_micros).label("total_cost_micros"),
                func.sum(SearchTerm.impressions).label("total_impr"),
                Campaign.name.label("campaign_name"),
                Campaign.id.label("campaign_id"),
                SearchTerm.ad_group_id.label("ad_group_id"),
                SearchTerm.source.label("source"),
            )
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .group_by(
                SearchTerm.text,
                Campaign.name,
                Campaign.id,
                SearchTerm.ad_group_id,
                SearchTerm.source,
            )
            .all()
        )

        existing_keywords = set(
            (kw.text.lower(), kw.ad_group_id)
            for kw in (
                db.query(Keyword.text, Keyword.ad_group_id)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .join(Campaign, AdGroup.campaign_id == Campaign.id)
                .filter(Campaign.client_id == client_id)
                .all()
            )
        )

        for term in terms:
            text_lower = term.text.lower()
            source = term.source or "SEARCH"
            if term.ad_group_id and (text_lower, term.ad_group_id) in existing_keywords:
                continue

            total_clicks = term.total_clicks or 0
            total_conv = term.total_conv or 0
            total_cost = (term.total_cost_micros or 0) / 1_000_000
            total_impr = term.total_impr or 0
            cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0
            word_count = len(term.text.strip().split())
            match_type = "EXACT" if word_count <= 2 else "PHRASE"
            base_metadata = {
                "conversions": float(total_conv),
                "clicks": int(total_clicks),
                "impressions": int(total_impr),
                "cost": round(total_cost, 2),
                "cvr": round(cvr, 2),
                "match_type": match_type,
                "search_term_source": source,
                "campaign_id": term.campaign_id,
                "ad_group_id": term.ad_group_id,
            }

            if total_conv >= t["r4_min_conversions"]:
                if source == "SEARCH" and term.ad_group_id:
                    recs.append(Recommendation(
                        type=RecommendationType.ADD_KEYWORD,
                        priority=Priority.HIGH,
                        entity_type="search_term",
                        entity_id=0,
                        entity_name=term.text,
                        campaign_name=term.campaign_name,
                        campaign_id=term.campaign_id,
                        ad_group_id=term.ad_group_id,
                        reason=(
                            f"Search term has {total_conv:.0f} conversions "
                            f"with {cvr:.1f}% CVR. Not yet a keyword."
                        ),
                        current_value=f"Conv: {total_conv:.0f}, CVR: {cvr:.1f}%, Cost: ${total_cost:.2f}",
                        recommended_action=f"Add as {match_type} match keyword",
                        estimated_impact="Capture more of this high-converting traffic",
                        metadata=base_metadata,
                    ))
                else:
                    recs.append(Recommendation(
                        type=RecommendationType.ADD_KEYWORD,
                        priority=Priority.MEDIUM,
                        entity_type="search_term",
                        entity_id=0,
                        entity_name=term.text,
                        campaign_name=term.campaign_name,
                        campaign_id=term.campaign_id,
                        ad_group_id=term.ad_group_id,
                        category="ALERT",
                        reason=(
                            f"PMax term has {total_conv:.0f} conversions with {cvr:.1f}% CVR. "
                            "Review manually before adding as a Search keyword."
                        ),
                        current_value=f"Conv: {total_conv:.0f}, CVR: {cvr:.1f}%, Cost: ${total_cost:.2f}",
                        recommended_action="Review manually in Google Ads",
                        estimated_impact="Potential high-intent keyword candidate",
                        metadata=base_metadata,
                    ))

            elif total_clicks >= t["r4_min_clicks_phrase"] and cvr == 0:
                ctr = (total_clicks / max(total_impr, 1)) * 100
                if ctr >= t["r4_min_ctr_phrase"]:
                    metadata = dict(base_metadata)
                    metadata["ctr"] = round(ctr, 2)
                    recs.append(Recommendation(
                        type=RecommendationType.ADD_KEYWORD,
                        priority=Priority.LOW,
                        entity_type="search_term",
                        entity_id=0,
                        entity_name=term.text,
                        campaign_name=term.campaign_name,
                        campaign_id=term.campaign_id,
                        ad_group_id=term.ad_group_id,
                        category="RECOMMENDATION" if source == "SEARCH" and term.ad_group_id else "ALERT",
                        reason=(
                            f"High engagement: {total_clicks} clicks, {ctr:.1f}% CTR. "
                            f"Worth testing as a keyword."
                        ),
                        current_value=f"Clicks: {total_clicks}, CTR: {ctr:.1f}%",
                        recommended_action=(
                            "Add as PHRASE match keyword"
                            if source == "SEARCH" and term.ad_group_id
                            else "Review manually in Google Ads"
                        ),
                        metadata=metadata,
                    ))

        return recs

    def _rule_5_add_negative(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        terms = (
            db.query(
                SearchTerm.text,
                func.sum(SearchTerm.conversions).label("total_conv"),
                func.sum(SearchTerm.clicks).label("total_clicks"),
                func.sum(SearchTerm.cost_micros).label("total_cost_micros"),
                func.sum(SearchTerm.impressions).label("total_impr"),
                Campaign.name.label("campaign_name"),
                Campaign.id.label("campaign_id"),
                SearchTerm.source.label("source"),
            )
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .group_by(SearchTerm.text, Campaign.name, Campaign.id, SearchTerm.source)
            .all()
        )

        for term in terms:
            total_clicks = term.total_clicks or 0
            total_conv = term.total_conv or 0
            total_cost = (term.total_cost_micros or 0) / 1_000_000
            total_impr = term.total_impr or 1
            ctr = (total_clicks / total_impr) * 100
            source = term.source or "SEARCH"
            base_metadata = {
                "clicks": int(total_clicks),
                "impressions": int(total_impr),
                "conversions": float(total_conv),
                "cost": round(total_cost, 2),
                "ctr": round(ctr, 2),
                "campaign_id": term.campaign_id,
                "search_term_source": source,
                "negative_match_type": "PHRASE",
            }

            text_lower = term.text.lower()
            matched_words = [
                p.pattern.replace(r'\b', '').replace('\\', '')
                for p in self._IRRELEVANT_PATTERNS if p.search(text_lower)
            ]
            if matched_words:
                metadata = dict(base_metadata)
                metadata["matched_words"] = matched_words
                metadata["negative_level"] = "ACCOUNT"
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    campaign_id=term.campaign_id,
                    category="ALERT",
                    reason=(
                        f"Contains irrelevant word(s): {', '.join(matched_words)}. "
                        f"Cost: ${total_cost:.2f}."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, Clicks: {total_clicks}",
                    recommended_action="Review account-level negative manually",
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata=metadata,
                ))
                continue

            if (
                total_clicks >= t["r5_min_clicks"]
                and total_conv == 0
                and ctr < t["r5_max_ctr"]
            ):
                metadata = dict(base_metadata)
                metadata["negative_level"] = "CAMPAIGN"
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.MEDIUM,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    campaign_id=term.campaign_id,
                    category="RECOMMENDATION" if source == "SEARCH" else "ALERT",
                    reason=(
                        f"{total_clicks} clicks, 0 conversions, CTR {ctr:.2f}%. "
                        f"Wasted ${total_cost:.2f}."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, CTR: {ctr:.2f}%",
                    recommended_action=(
                        "Add as campaign negative"
                        if source == "SEARCH"
                        else "Review manually in Google Ads"
                    ),
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata=metadata,
                ))

            elif total_cost >= t["r5_min_cost_immediate"] and total_conv == 0:
                metadata = dict(base_metadata)
                metadata["negative_level"] = "CAMPAIGN"
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    campaign_id=term.campaign_id,
                    category="RECOMMENDATION" if source == "SEARCH" else "ALERT",
                    reason=(
                        f"Spent ${total_cost:.2f} with 0 conversions. Immediate waste."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, Conv: 0",
                    recommended_action=(
                        "Add as campaign negative"
                        if source == "SEARCH"
                        else "Review manually in Google Ads"
                    ),
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata=metadata,
                ))

        return recs
    def _rule_6_pause_ad(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        ad_groups = (
            db.query(AdGroup)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .all()
        )

        for ag in ad_groups:
            ads = (
                db.query(Ad)
                .filter(Ad.ad_group_id == ag.id, Ad.status == "ENABLED")
                .all()
            )

            if len(ads) < 2:
                continue

            eligible_ads = [a for a in ads if (a.impressions or 0) >= t["r6_min_impressions"]]
            if not eligible_ads:
                continue

            best_ctr = max(_ctr_micros_to_pct(a.ctr) for a in eligible_ads)
            campaign = db.query(Campaign).filter(Campaign.id == ag.campaign_id).first()
            camp_name = campaign.name if campaign else "Unknown"

            for ad in eligible_ads:
                ad_ctr = _ctr_micros_to_pct(ad.ctr)
                ad_cost = _micros_to_usd(ad.cost_micros)

                # Check 1: CTR significantly lower than best
                if best_ctr > 0 and ad_ctr < best_ctr * t["r6_ctr_ratio"]:
                    headline = ad.headline_1 or ad.headline_2 or f"Ad #{ad.id}"
                    recs.append(Recommendation(
                        type=RecommendationType.PAUSE_AD,
                        priority=Priority.MEDIUM,
                        entity_type="ad",
                        entity_id=ad.id,
                        entity_name=headline,
                        campaign_name=camp_name,
                        reason=(
                            f"CTR ({ad_ctr:.2f}%) is less than 50% of best "
                            f"ad ({best_ctr:.2f}%) in the same ad group."
                        ),
                        current_value=f"CTR: {ad_ctr:.2f}%, Best: {best_ctr:.2f}%",
                        recommended_action="Pause this ad and create a new variant",
                        metadata={
                            "ad_ctr": ad_ctr,
                            "best_ctr": best_ctr,
                            "ad_group": ag.name,
                        },
                    ))

                # Check 2: High spend, zero conversions
                if ad_cost >= t["r6_min_cost"] and (ad.conversions or 0) == 0:
                    headline = ad.headline_1 or ad.headline_2 or f"Ad #{ad.id}"
                    recs.append(Recommendation(
                        type=RecommendationType.PAUSE_AD,
                        priority=Priority.HIGH,
                        entity_type="ad",
                        entity_id=ad.id,
                        entity_name=headline,
                        campaign_name=camp_name,
                        reason=(
                            f"Spent ${ad_cost:.2f} with 0 conversions."
                        ),
                        current_value=f"Spend: ${ad_cost:.2f}, Conv: 0",
                        recommended_action="Pause this ad",
                        estimated_impact=f"Save ~${ad_cost:.2f}",
                        metadata={"spend": ad_cost},
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 7: Reallocate Budget (ROAS comparison)
    # -----------------------------------------------------------------------
    def _rule_7_reallocate_budget(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        client = db.get(Client, client_id)
        if not client:
            return recs

        cutoff = date.today() - timedelta(days=days)
        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        if campaigns and ensure_campaign_roles(campaigns, client):
            db.flush()

        snapshots = []
        for campaign in campaigns:
            snapshot = self._campaign_metrics_snapshot(db, campaign, cutoff)
            if snapshot and snapshot["roas"] > 0:
                snapshots.append(snapshot)

        if len(snapshots) < 2:
            return recs

        seen_pairs: set[tuple[int, int]] = set()

        global_best = max(snapshots, key=lambda item: item["roas"])
        global_worst = min(snapshots, key=lambda item: item["roas"])
        global_rec = self._build_reallocation_candidate(db, client, global_best, global_worst, t, cutoff)
        if global_rec:
            recs.append(global_rec)
            seen_pairs.add((global_worst["campaign"].id, global_best["campaign"].id))

        role_buckets: dict[str, list[dict]] = defaultdict(list)
        for snapshot in snapshots:
            role_buckets[snapshot["campaign"].campaign_role_final or "UNKNOWN"].append(snapshot)

        for role, bucket in role_buckets.items():
            if role == "UNKNOWN" or len(bucket) < 2:
                continue
            ranked = sorted(bucket, key=lambda item: item["roas"], reverse=True)
            best = ranked[0]
            worst = ranked[-1]
            pair_key = (worst["campaign"].id, best["campaign"].id)
            if pair_key in seen_pairs:
                continue
            candidate = self._build_reallocation_candidate(db, client, best, worst, t, cutoff)
            if candidate and candidate.context_outcome == ACTION:
                recs.append(candidate)
                seen_pairs.add(pair_key)

        return recs
    def _rule_8_quality_score_alert(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        QS_LABELS = {1: "BELOW_AVERAGE", 2: "AVERAGE", 3: "ABOVE_AVERAGE"}

        keywords = (
            db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Keyword.status == "ENABLED",
                Keyword.quality_score.isnot(None),
                Keyword.quality_score > 0,
                Keyword.quality_score < t["r8_max_qs"],
                Keyword.impressions > t["r8_min_impressions"],
            )
            .all()
        )

        for kw in keywords:
            campaign = (
                db.query(Campaign)
                .join(AdGroup, Campaign.id == AdGroup.campaign_id)
                .filter(AdGroup.id == kw.ad_group_id)
                .first()
            )
            camp_name = campaign.name if campaign else "Unknown"

            # Determine weakest subcomponent
            subcomponents = {
                "Expected CTR": kw.historical_search_predicted_ctr,
                "Ad Relevance": kw.historical_creative_quality,
                "Landing Page": kw.historical_landing_page_quality,
            }
            valid = {k: v for k, v in subcomponents.items() if v is not None}
            if valid:
                worst_name, worst_val = min(valid.items(), key=lambda x: x[1])
                worst_label = QS_LABELS.get(worst_val, "N/A")
            else:
                worst_name, worst_label = "N/A", "N/A"

            priority = Priority.HIGH if kw.quality_score <= 2 else Priority.MEDIUM

            recs.append(Recommendation(
                type=RecommendationType.QS_ALERT,
                priority=priority,
                entity_type="keyword",
                entity_id=kw.id,
                entity_name=kw.text,
                campaign_name=camp_name,
                category="ALERT",
                reason=(
                    f"Quality Score {kw.quality_score}/10 — "
                    f"najsłabszy komponent: {worst_name} ({worst_label})"
                ),
                current_value=f"QS: {kw.quality_score}, Impr: {kw.impressions}",
                recommended_action=f"Popraw {worst_name} — sprawdź w Google Ads",
                metadata={
                    "quality_score": kw.quality_score,
                    "predicted_ctr": kw.historical_search_predicted_ctr,
                    "creative_quality": kw.historical_creative_quality,
                    "landing_page_quality": kw.historical_landing_page_quality,
                },
            ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 9: Impression Share Lost to Budget — Budget Bottleneck
    # -----------------------------------------------------------------------
    def _rule_9_is_lost_budget(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        client = db.get(Client, client_id)
        if not client:
            return recs

        cutoff = date.today() - timedelta(days=days)
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.search_budget_lost_is.isnot(None),
            )
            .all()
        )
        if campaigns and ensure_campaign_roles(campaigns, client):
            db.flush()

        account_avg_cpa = self._account_avg_cpa(db, client_id, cutoff)

        for campaign in campaigns:
            lost_is = (campaign.search_budget_lost_is or 0) * 100
            if lost_is < t["r9_min_lost_is_pct"]:
                continue

            snapshot = self._campaign_metrics_snapshot(db, campaign, cutoff)
            if not snapshot:
                continue

            scale_eval = self._evaluate_can_scale(campaign, snapshot, client, account_avg_cpa)
            outcome = ACTION if scale_eval["can_scale"] else INSIGHT_ONLY
            downgrade_reasons = [] if outcome == ACTION else scale_eval["reason_codes"]
            priority = Priority.HIGH if outcome == ACTION and lost_is > t["r9_high_lost_is_pct"] else Priority.MEDIUM
            budget_usd = snapshot["budget_usd"]

            recs.append(Recommendation(
                type=RecommendationType.IS_BUDGET_ALERT,
                priority=priority,
                entity_type="campaign",
                entity_id=campaign.id,
                entity_name=campaign.name,
                campaign_name=campaign.name,
                campaign_id=campaign.id,
                category="RECOMMENDATION" if outcome == ACTION else "ALERT",
                reason=(
                    f"{campaign.name}: Lost IS {lost_is:.0f}%, role {campaign.campaign_role_final or 'UNKNOWN'}, "
                    f"ROAS {snapshot['roas']:.2f}x, avg spend ${snapshot['avg_daily_spend']:.2f}/day."
                ),
                current_value=(
                    f"Lost IS: {lost_is:.0f}%, Budget: ${budget_usd:.2f}/day, "
                    f"Avg spend: ${snapshot['avg_daily_spend']:.2f}/day"
                ),
                recommended_action=(
                    f"Increase budget by {t['r9_budget_increase_pct']}%" if outcome == ACTION
                    else "Review bids, tracking, and scale headroom before increasing budget"
                ),
                estimated_impact=(
                    f"Potentially recover {lost_is:.0f}% more impressions" if outcome == ACTION
                    else "Insight only until context confirms safe scale"
                ),
                metadata={
                    "lost_is_pct": round(lost_is, 1),
                    "roas": round(snapshot["roas"], 2),
                    "cpa": round(snapshot["cpa"], 2) if snapshot["cpa"] else 0,
                    "budget_usd": round(budget_usd, 2),
                    "avg_daily_spend": round(snapshot["avg_daily_spend"], 2),
                    "current_budget_micros": int(campaign.budget_micros or 0),
                    "budget_change_pct": t["r9_budget_increase_pct"],
                    "budget_action": "INCREASE_BUDGET" if outcome == ACTION else "REVIEW_ONLY",
                    "primary_campaign_role": campaign.campaign_role_final or "UNKNOWN",
                    "protection_level": campaign.protection_level or "HIGH",
                    "can_scale": scale_eval["can_scale"],
                    "destination_headroom": scale_eval["headroom"],
                    "search_budget_lost_is": round(lost_is, 1),
                    "days_observed": snapshot["days_observed"],
                },
                context_outcome=outcome,
                downgrade_reasons=downgrade_reasons,
            ))

        return recs
    def _rule_10_is_lost_rank(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.search_rank_lost_is.isnot(None),
            )
            .all()
        )

        for campaign in campaigns:
            rank_lost = (campaign.search_rank_lost_is or 0) * 100
            budget_lost = (campaign.search_budget_lost_is or 0) * 100

            if (
                rank_lost > t["r10_min_rank_lost_pct"]
                and budget_lost < t["r10_max_budget_lost_pct"]
            ):
                recs.append(Recommendation(
                    type=RecommendationType.IS_RANK_ALERT,
                    priority=Priority.MEDIUM,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    category="ALERT",
                    reason=(
                        f"Tracisz {rank_lost:.0f}% wyświetleń z powodu niskiego "
                        f"Ad Rank. Sprawdź Quality Score keywords i trafność reklam."
                    ),
                    current_value=(
                        f"Rank Lost IS: {rank_lost:.0f}%, "
                        f"Budget Lost IS: {budget_lost:.0f}%"
                    ),
                    recommended_action=(
                        "Popraw Quality Score keywords lub zwiększ stawki"
                    ),
                    metadata={
                        "rank_lost_pct": round(rank_lost, 1),
                        "budget_lost_pct": round(budget_lost, 1),
                    },
                ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 11: Low CTR + High Impressions — Irrelevant Keyword
    # -----------------------------------------------------------------------
    def _rule_11_low_ctr_high_impr(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        keywords = (
            db.query(Keyword)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Keyword.status == "ENABLED",
                Keyword.impressions > t["r11_min_impressions"],
                Keyword.match_type.in_(["BROAD", "PHRASE"]),
            )
            .all()
        )

        for kw in keywords:
            kw_ctr = _ctr_micros_to_pct(kw.ctr)
            if kw_ctr >= t["r11_max_ctr"]:
                continue
            if (kw.conversions or 0) > 0:
                continue

            campaign = (
                db.query(Campaign)
                .join(AdGroup, Campaign.id == AdGroup.campaign_id)
                .filter(AdGroup.id == kw.ad_group_id)
                .first()
            )
            camp_name = campaign.name if campaign else "Unknown"

            recs.append(Recommendation(
                type=RecommendationType.PAUSE_KEYWORD,
                priority=Priority.MEDIUM,
                entity_type="keyword",
                entity_id=kw.id,
                entity_name=kw.text,
                campaign_name=camp_name,
                category="RECOMMENDATION",
                reason=(
                    f"CTR {kw_ctr:.2f}% przy {kw.impressions} impressions "
                    f"i 0 konwersji ({kw.match_type} match) — "
                    f"słabe dopasowanie"
                ),
                current_value=(
                    f"CTR: {kw_ctr:.2f}%, Impr: {kw.impressions}, "
                    f"Match: {kw.match_type}"
                ),
                recommended_action=(
                    "Pause lub zmień match type na EXACT"
                ),
                metadata={
                    "ctr": kw_ctr,
                    "impressions": kw.impressions,
                    "match_type": kw.match_type,
                },
            ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 12: Wasted Spend Alert — % of budget with zero conversions
    # -----------------------------------------------------------------------
    def _rule_12_wasted_spend_alert(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        for campaign in campaigns:
            keywords = (
                db.query(Keyword)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .filter(
                    AdGroup.campaign_id == campaign.id,
                    Keyword.status == "ENABLED",
                )
                .all()
            )
            if not keywords:
                continue

            total_cost = sum(_micros_to_usd(k.cost_micros) for k in keywords)
            if total_cost <= 0:
                continue

            wasted_cost = sum(
                _micros_to_usd(k.cost_micros)
                for k in keywords
                if (k.conversions or 0) == 0
            )
            wasted_pct = (wasted_cost / total_cost) * 100

            if wasted_pct >= t["r12_wasted_pct_medium"]:
                priority = (
                    Priority.HIGH
                    if wasted_pct >= t["r12_wasted_pct_high"]
                    else Priority.MEDIUM
                )
                recs.append(Recommendation(
                    type=RecommendationType.WASTED_SPEND_ALERT,
                    priority=priority,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    category="ALERT",
                    reason=(
                        f"{wasted_pct:.0f}% budżetu (${wasted_cost:.2f}) "
                        f"idzie na keywords bez konwersji"
                    ),
                    current_value=(
                        f"Wasted: ${wasted_cost:.2f} / ${total_cost:.2f} "
                        f"({wasted_pct:.0f}%)"
                    ),
                    recommended_action=(
                        "Sprawdź keywords z conv=0 i wysokim spend — "
                        "rozważ pause lub negative"
                    ),
                    metadata={
                        "wasted_pct": round(wasted_pct, 1),
                        "wasted_usd": round(wasted_cost, 2),
                        "total_usd": round(total_cost, 2),
                    },
                ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 13: PMax vs Search Overlap — Cannibalization Alert
    # -----------------------------------------------------------------------
    def _rule_13_pmax_search_overlap(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        # Get all search terms grouped by text and source
        terms = (
            db.query(
                SearchTerm.text,
                SearchTerm.source,
                func.sum(SearchTerm.cost_micros).label("total_cost"),
                func.sum(SearchTerm.clicks).label("total_clicks"),
                func.sum(SearchTerm.conversions).label("total_conv"),
            )
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .group_by(SearchTerm.text, SearchTerm.source)
            .all()
        )

        # Build lookup: text → {source: metrics}
        term_map: dict[str, dict] = defaultdict(dict)
        for row in terms:
            term_map[row.text.lower()][row.source or "SEARCH"] = {
                "cost": _micros_to_usd(row.total_cost),
                "clicks": row.total_clicks or 0,
                "conv": row.total_conv or 0,
            }

        for text, sources in term_map.items():
            if "SEARCH" not in sources or "PMAX" not in sources:
                continue

            search = sources["SEARCH"]
            pmax = sources["PMAX"]

            if pmax["cost"] < search["cost"] * t["r13_pmax_cost_ratio"]:
                continue

            priority = (
                Priority.HIGH
                if pmax["cost"] > t["r13_high_cost_usd"]
                else Priority.MEDIUM
            )

            recs.append(Recommendation(
                type=RecommendationType.PMAX_CANNIBALIZATION,
                priority=priority,
                entity_type="search_term",
                entity_id=0,
                entity_name=text,
                campaign_name="Search + PMax",
                category="ALERT",
                reason=(
                    f"Search term '{text}' pojawia się w Search i PMax. "
                    f"PMax wydaje ${pmax['cost']:.2f} "
                    f"(Search: ${search['cost']:.2f})"
                ),
                current_value=(
                    f"PMax: ${pmax['cost']:.2f} / {pmax['clicks']} clicks, "
                    f"Search: ${search['cost']:.2f} / {search['clicks']} clicks"
                ),
                recommended_action=(
                    "Rozważ exact match w Search lub negative w PMax"
                ),
                metadata={
                    "pmax_cost": round(pmax["cost"], 2),
                    "search_cost": round(search["cost"], 2),
                    "pmax_conv": float(pmax["conv"]),
                    "search_conv": float(search["conv"]),
                },
            ))

        return recs

    # ===================================================================
    # v1.2 RULES (R15–R18) — Extended Analytics
    # ===================================================================

    # -----------------------------------------------------------------------
    # RULE 15: Device Performance Breakdown — CPA anomaly per device
    # -----------------------------------------------------------------------
    def _rule_15_device_anomaly(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        today = date.today()
        cutoff = today - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        for campaign in campaigns:
            device_stats = (
                db.query(
                    MetricSegmented.device,
                    func.sum(MetricSegmented.cost_micros).label("cost"),
                    func.sum(MetricSegmented.conversions).label("conv"),
                    func.sum(MetricSegmented.clicks).label("clicks"),
                )
                .filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date >= cutoff,
                    MetricSegmented.device.isnot(None),
                )
                .group_by(MetricSegmented.device)
                .all()
            )

            if not device_stats:
                continue

            device_cpa = {}
            for row in device_stats:
                cost = _micros_to_usd(row.cost)
                conv = row.conv or 0
                if conv > 0:
                    device_cpa[row.device] = {"cpa": cost / conv, "cost": cost}

            desktop_cpa = device_cpa.get("COMPUTER", {}).get("cpa")
            if desktop_cpa is None or desktop_cpa <= 0:
                continue

            for device, data in device_cpa.items():
                if device == "COMPUTER":
                    continue
                if (
                    data["cost"] >= t["r15_min_spend"]
                    and data["cpa"] > desktop_cpa * t["r15_cpa_multiplier"]
                ):
                    recs.append(Recommendation(
                        type=RecommendationType.DEVICE_ANOMALY,
                        priority=Priority.MEDIUM,
                        entity_type="campaign",
                        entity_id=campaign.id,
                        entity_name=campaign.name,
                        campaign_name=campaign.name,
                        category="ALERT",
                        reason=(
                            f"{device} CPA (${data['cpa']:.2f}) jest "
                            f"{data['cpa']/desktop_cpa:.1f}x wyższy niż desktop "
                            f"(${desktop_cpa:.2f})"
                        ),
                        current_value=(
                            f"{device}: CPA ${data['cpa']:.2f}, "
                            f"Desktop: CPA ${desktop_cpa:.2f}"
                        ),
                        recommended_action=(
                            f"Rozważ bid adjustment na {device} lub "
                            f"dedykowane landing pages"
                        ),
                        metadata={
                            "device": device,
                            "device_cpa": round(data["cpa"], 2),
                            "desktop_cpa": round(desktop_cpa, 2),
                            "device_spend": round(data["cost"], 2),
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 16: Geo Performance Breakdown — CPA anomaly per location
    # -----------------------------------------------------------------------
    def _rule_16_geo_anomaly(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        today = date.today()
        cutoff = today - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        for campaign in campaigns:
            geo_stats = (
                db.query(
                    MetricSegmented.geo_city,
                    func.sum(MetricSegmented.cost_micros).label("cost"),
                    func.sum(MetricSegmented.conversions).label("conv"),
                )
                .filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date >= cutoff,
                    MetricSegmented.geo_city.isnot(None),
                )
                .group_by(MetricSegmented.geo_city)
                .all()
            )

            if not geo_stats:
                continue

            # Campaign avg CPA
            total_cost = sum(_micros_to_usd(r.cost) for r in geo_stats)
            total_conv = sum(r.conv or 0 for r in geo_stats)
            avg_cpa = (total_cost / total_conv) if total_conv > 0 else 0

            if avg_cpa <= 0:
                continue

            for row in geo_stats:
                geo_cost = _micros_to_usd(row.cost)
                geo_conv = row.conv or 0
                if geo_conv <= 0 or geo_cost < t["r16_min_spend"]:
                    continue

                geo_cpa = geo_cost / geo_conv
                if geo_cpa > avg_cpa * t["r16_cpa_multiplier"]:
                    geo_name = row.geo_city or "Unknown"
                    recs.append(Recommendation(
                        type=RecommendationType.GEO_ANOMALY,
                        priority=Priority.LOW,
                        entity_type="campaign",
                        entity_id=campaign.id,
                        entity_name=campaign.name,
                        campaign_name=campaign.name,
                        category="ALERT",
                        reason=(
                            f"Lokalizacja '{geo_name}' ma CPA ${geo_cpa:.2f} "
                            f"({geo_cpa/avg_cpa:.1f}x średnia kampanii ${avg_cpa:.2f})"
                        ),
                        current_value=(
                            f"Geo CPA: ${geo_cpa:.2f}, Avg CPA: ${avg_cpa:.2f}"
                        ),
                        recommended_action=(
                            f"Rozważ geo bid adjustment dla '{geo_name}'"
                        ),
                        metadata={
                            "geo": geo_name,
                            "geo_cpa": round(geo_cpa, 2),
                            "avg_cpa": round(avg_cpa, 2),
                            "geo_spend": round(geo_cost, 2),
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 17: Budget Pacing Alert — Overspend / Underspend
    # -----------------------------------------------------------------------
    def _rule_17_budget_pacing(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds
        today = date.today()
        month_start = today.replace(day=1)
        days_in_month = (
            (month_start + timedelta(days=32)).replace(day=1) - month_start
        ).days
        days_elapsed = (today - month_start).days + 1
        month_pct = days_elapsed / days_in_month

        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.budget_micros > 0,
            )
            .all()
        )

        for campaign in campaigns:
            daily_budget = _micros_to_usd(campaign.budget_micros)
            monthly_budget = daily_budget * days_in_month
            expected_spend = monthly_budget * month_pct

            metrics = (
                db.query(func.sum(MetricDaily.cost_micros))
                .filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date >= month_start,
                )
                .scalar()
            )
            actual_spend = _micros_to_usd(metrics) if metrics else 0

            if expected_spend <= 0:
                continue

            pacing_ratio = actual_spend / expected_spend

            # Overspend
            if pacing_ratio > t["r17_overspend_ratio"]:
                pacing_pct = pacing_ratio * 100
                recs.append(Recommendation(
                    type=RecommendationType.BUDGET_PACING,
                    priority=Priority.HIGH,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    category="ALERT",
                    reason=(
                        f"Kampania wydaje za szybko — {pacing_pct:.0f}% "
                        f"budżetu przy {month_pct*100:.0f}% miesiąca"
                    ),
                    current_value=(
                        f"Actual: ${actual_spend:.2f}, "
                        f"Expected: ${expected_spend:.2f}"
                    ),
                    recommended_action=(
                        "Sprawdź czy nie ma anomalii w kosztach lub "
                        "obniż stawki"
                    ),
                    metadata={
                        "pacing_pct": round(pacing_pct, 1),
                        "actual_spend": round(actual_spend, 2),
                        "expected_spend": round(expected_spend, 2),
                        "days_elapsed": days_elapsed,
                        "days_in_month": days_in_month,
                    },
                ))

            # Underspend
            elif (
                pacing_ratio < t["r17_underspend_ratio"]
                and month_pct > t["r17_min_month_pct"]
            ):
                pacing_pct = pacing_ratio * 100
                recs.append(Recommendation(
                    type=RecommendationType.BUDGET_PACING,
                    priority=Priority.MEDIUM,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    category="ALERT",
                    reason=(
                        f"Kampania niedowydaje — {pacing_pct:.0f}% "
                        f"budżetu przy {month_pct*100:.0f}% miesiąca"
                    ),
                    current_value=(
                        f"Actual: ${actual_spend:.2f}, "
                        f"Expected: ${expected_spend:.2f}"
                    ),
                    recommended_action=(
                        "Sprawdź ograniczenia — niski search volume, "
                        "zbyt wąskie targetowanie"
                    ),
                    metadata={
                        "pacing_pct": round(pacing_pct, 1),
                        "actual_spend": round(actual_spend, 2),
                        "expected_spend": round(expected_spend, 2),
                        "days_elapsed": days_elapsed,
                        "days_in_month": days_in_month,
                    },
                ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 18: N-gram Negative Detection — Wasteful patterns in search terms
    # -----------------------------------------------------------------------
    def _rule_18_ngram_negative(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        recs = []
        t = self.thresholds

        terms = (
            db.query(
                SearchTerm.text,
                SearchTerm.cost_micros,
                SearchTerm.conversions,
                SearchTerm.clicks,
                Campaign.name.label("campaign_name"),
            )
            .join(Campaign, SearchTerm.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .all()
        )

        if not terms:
            return recs

        ngram_data: dict[str, dict] = defaultdict(
            lambda: {"cost": 0.0, "conv": 0.0, "clicks": 0, "terms": set()}
        )

        for term in terms:
            words = term.text.lower().strip().split()
            cost_usd = _micros_to_usd(term.cost_micros)
            conv = term.conversions or 0

            for n in range(1, 4):
                for i in range(len(words) - n + 1):
                    ngram = " ".join(words[i:i + n])
                    if len(ngram) < 3:
                        continue
                    ngram_data[ngram]["cost"] += cost_usd
                    ngram_data[ngram]["conv"] += conv
                    ngram_data[ngram]["clicks"] += (term.clicks or 0)
                    ngram_data[ngram]["terms"].add(term.text.lower())

        for ngram, data in ngram_data.items():
            term_count = len(data["terms"])
            if (
                data["cost"] >= t["r18_min_cost"]
                and data["conv"] == 0
                and term_count >= t["r18_min_terms"]
            ):
                recs.append(Recommendation(
                    type=RecommendationType.NGRAM_NEGATIVE,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=ngram,
                    campaign_name="Account-wide",
                    category="ALERT",
                    reason=(
                        f"N-gram '{ngram}' appears in {term_count} search terms, "
                        f"total cost ${data['cost']:.2f}, 0 conversions."
                    ),
                    current_value=(
                        f"Cost: ${data['cost']:.2f}, Terms: {term_count}, "
                        f"Clicks: {data['clicks']}"
                    ),
                    recommended_action="Review manually before adding any n-gram negative",
                    estimated_impact=f"Save ~${data['cost']:.2f}",
                    metadata={
                        "ngram": ngram,
                        "cost": round(data["cost"], 2),
                        "term_count": term_count,
                        "clicks": data["clicks"],
                        "sample_terms": list(data["terms"])[:5],
                        "negative_level": "ACCOUNT",
                    },
                ))

        return recs

    # ───────────────────────────────────────────────────────
    # v2.0 GAP rules (R19–R23)
    # ───────────────────────────────────────────────────────

    def _rule_19_ad_group_health(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 8: Flag ad groups with structural issues (single ad, keyword count, zero conv)."""
        from app.models.keyword_daily import KeywordDaily
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        ad_groups = (
            db.query(AdGroup, Campaign.name.label("campaign_name"))
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED", AdGroup.status == "ENABLED")
            .all()
        )
        if not ad_groups:
            return recs

        ag_ids = [ag.AdGroup.id for ag in ad_groups]

        ad_counts = dict(
            db.query(Ad.ad_group_id, func.count(Ad.id))
            .filter(Ad.ad_group_id.in_(ag_ids), Ad.status == "ENABLED")
            .group_by(Ad.ad_group_id).all()
        )
        kw_counts = dict(
            db.query(Keyword.ad_group_id, func.count(Keyword.id))
            .filter(Keyword.ad_group_id.in_(ag_ids), Keyword.status == "ENABLED", Keyword.criterion_kind == "POSITIVE")
            .group_by(Keyword.ad_group_id).all()
        )
        ag_cost_conv = dict(
            db.query(
                Keyword.ad_group_id,
                func.coalesce(func.sum(KeywordDaily.cost_micros), 0),
                func.coalesce(func.sum(KeywordDaily.conversions), 0.0),
            )
            .join(Keyword, KeywordDaily.keyword_id == Keyword.id)
            .filter(Keyword.ad_group_id.in_(ag_ids), KeywordDaily.date >= cutoff)
            .group_by(Keyword.ad_group_id).all()
        )

        for row in ad_groups:
            ag = row.AdGroup
            campaign_name = row.campaign_name
            ads = ad_counts.get(ag.id, 0)
            kws = kw_counts.get(ag.id, 0)
            cost_conv = ag_cost_conv.get(ag.id)
            cost_usd = _micros_to_usd(cost_conv[0]) if cost_conv else 0.0
            conv = (cost_conv[1] if cost_conv else 0.0) or 0.0

            issues = []
            if ads == 0:
                issues.append("Brak reklam")
            elif ads < t["r19_min_ads"]:
                issues.append(f"Tylko {ads} reklama (brak A/B)")
            if kws < t["r19_min_keywords"]:
                issues.append(f"Za mało słów kluczowych ({kws})")
            if kws > t["r19_max_keywords"]:
                issues.append(f"Za dużo słów kluczowych ({kws})")
            if cost_usd >= t["r19_zero_conv_min_cost"] and conv == 0:
                issues.append(f"Brak konwersji przy ${cost_usd:.0f} wydatków")

            if not issues:
                continue

            severity = Priority.HIGH if (ads == 0 or (cost_usd >= t["r19_zero_conv_min_cost"] and conv == 0)) else Priority.MEDIUM
            recs.append(Recommendation(
                type=RecommendationType.AD_GROUP_HEALTH,
                priority=severity,
                entity_type="ad_group",
                entity_id=ag.id,
                entity_name=ag.name,
                campaign_name=campaign_name,
                campaign_id=ag.campaign_id,
                ad_group_id=ag.id,
                category="ALERT",
                reason="; ".join(issues),
                current_value=f"Reklamy: {ads}, Słowa: {kws}, Koszt: ${cost_usd:.2f}, Konw.: {conv:.1f}",
                recommended_action="Dodaj brakujące reklamy lub słowa kluczowe",
                metadata={
                    "ads_count": ads,
                    "keywords_count": kws,
                    "cost_usd": round(cost_usd, 2),
                    "conversions": round(conv, 2),
                    "issues": issues,
                },
            ))

        return recs

    def _rule_20_disapproved_ads(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 9: Flag disapproved or limited ads as recommendations."""
        recs = []
        ads = (
            db.query(Ad, AdGroup.name.label("ag_name"), Campaign.name.label("c_name"), Campaign.id.label("c_id"))
            .join(AdGroup, Ad.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Ad.status == "ENABLED",
                Ad.approval_status.in_(["DISAPPROVED", "APPROVED_LIMITED"]),
            )
            .all()
        )
        for row in ads:
            ad = row.Ad
            is_disapproved = ad.approval_status == "DISAPPROVED"
            recs.append(Recommendation(
                type=RecommendationType.DISAPPROVED_AD_ALERT,
                priority=Priority.HIGH if is_disapproved else Priority.MEDIUM,
                entity_type="ad",
                entity_id=ad.id,
                entity_name=f"Ad #{ad.google_ad_id}",
                campaign_name=row.c_name,
                campaign_id=row.c_id,
                ad_group_id=ad.ad_group_id,
                category="ALERT",
                reason=f"Reklama {'odrzucona' if is_disapproved else 'ograniczona'} przez Google: {ad.approval_status}",
                current_value=f"Status: {ad.approval_status}, Typ: {ad.ad_type}",
                recommended_action="Popraw treść reklamy lub odwołaj się od decyzji Google",
                metadata={
                    "approval_status": ad.approval_status,
                    "ad_type": ad.ad_type,
                    "ad_strength": ad.ad_strength,
                },
            ))
        return recs

    def _rule_21_smart_bidding_conv_threshold(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 1B: Alert when Smart Bidding campaigns have too few conversions."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=30)

        smart_strategies = {"TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"}
        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        smart_campaigns = [c for c in campaigns if (c.bidding_strategy or "").upper() in smart_strategies]
        if not smart_campaigns:
            return recs

        for campaign in smart_campaigns:
            conv_sum = (
                db.query(func.coalesce(func.sum(MetricDaily.conversions), 0.0))
                .filter(MetricDaily.campaign_id == campaign.id, MetricDaily.date >= cutoff)
                .scalar()
            ) or 0.0

            strategy = (campaign.bidding_strategy or "").upper()
            min_conv = t["r21_min_conv_troas"] if "ROAS" in strategy else t["r21_min_conv_tcpa"]

            if conv_sum >= min_conv:
                continue

            severity = Priority.HIGH if conv_sum < min_conv * 0.5 else Priority.MEDIUM
            recs.append(Recommendation(
                type=RecommendationType.SMART_BIDDING_CONV_ALERT,
                priority=severity,
                entity_type="campaign",
                entity_id=campaign.id,
                entity_name=campaign.name,
                campaign_name=campaign.name,
                campaign_id=campaign.id,
                category="ALERT",
                reason=(
                    f"Kampania {campaign.name} ma {conv_sum:.1f} konwersji/30 dni "
                    f"przy strategii {strategy} (min. {min_conv}). "
                    f"Algorytm nie ma wystarczających danych do optymalizacji."
                ),
                current_value=f"Konwersje: {conv_sum:.1f}/30d, Min: {min_conv}, Strategia: {strategy}",
                recommended_action="Rozważ obniżenie tCPA, połączenie kampanii, lub zmianę strategii na Maximize Clicks",
                metadata={
                    "conversions_30d": round(conv_sum, 2),
                    "min_recommended": min_conv,
                    "bidding_strategy": strategy,
                    "deficit_pct": round((1 - conv_sum / min_conv) * 100, 1) if min_conv > 0 else 100,
                },
            ))
        return recs

    def _rule_22_ecpc_deprecation(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 1C: Flag campaigns still using deprecated ECPC bidding strategy."""
        recs = []
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.bidding_strategy == "ENHANCED_CPC",
            )
            .all()
        )
        for campaign in campaigns:
            recs.append(Recommendation(
                type=RecommendationType.ECPC_DEPRECATION,
                priority=Priority.HIGH,
                entity_type="campaign",
                entity_id=campaign.id,
                entity_name=campaign.name,
                campaign_name=campaign.name,
                campaign_id=campaign.id,
                category="ALERT",
                reason=(
                    f"Kampania '{campaign.name}' używa wycofanej strategii Enhanced CPC. "
                    f"Google wycofało ECPC z Search/Display w marcu 2025 — "
                    f"kampania mogła zostać automatycznie zmieniona na Manual CPC."
                ),
                current_value=f"Strategia: ENHANCED_CPC",
                recommended_action="Zmigruj na Target CPA lub Maximize Conversions",
                metadata={"bidding_strategy": "ENHANCED_CPC"},
            ))
        return recs

    def _rule_23_scaling_opportunity(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 7B: Flag hero campaigns with headroom to scale (high value + lost IS)."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        if not campaigns:
            return recs

        # Compute value per campaign
        campaign_values = []
        for c in campaigns:
            metrics = (
                db.query(
                    func.sum(MetricDaily.conversions).label("conv"),
                    func.sum(MetricDaily.conversion_value_micros).label("value"),
                    func.sum(MetricDaily.cost_micros).label("cost"),
                )
                .filter(MetricDaily.campaign_id == c.id, MetricDaily.date >= cutoff)
                .first()
            )
            value = _micros_to_usd(metrics.value or 0) if metrics else 0
            cost = _micros_to_usd(metrics.cost or 0) if metrics else 0
            conv = float(metrics.conv or 0) if metrics else 0
            campaign_values.append({"campaign": c, "value": value, "cost": cost, "conv": conv})

        total_value = sum(cv["value"] for cv in campaign_values)
        if total_value <= 0:
            return recs

        # Sort and find Pareto cutoff
        campaign_values.sort(key=lambda x: x["value"], reverse=True)
        cumulative = 0
        for cv in campaign_values:
            cumulative += cv["value"]
            cv["cumulative_pct"] = cumulative / total_value
            cv["is_hero"] = cv["cumulative_pct"] <= t["r23_min_pareto_pct"] or cv["value"] / total_value > 0.1

        heroes = [cv for cv in campaign_values if cv["is_hero"]]
        for cv in heroes:
            c = cv["campaign"]
            lost_budget = c.search_budget_lost_is or 0
            lost_rank = c.search_rank_lost_is or 0
            if lost_budget < t["r23_min_lost_is"] and lost_rank < t["r23_min_lost_is"]:
                continue

            value_pct = cv["value"] / total_value * 100
            incremental_est = round(cv["value"] * max(lost_budget, lost_rank), 2)
            recs.append(Recommendation(
                type=RecommendationType.SCALING_OPPORTUNITY,
                priority=Priority.HIGH if incremental_est > 500 else Priority.MEDIUM,
                entity_type="campaign",
                entity_id=c.id,
                entity_name=c.name,
                campaign_name=c.name,
                campaign_id=c.id,
                category="RECOMMENDATION",
                reason=(
                    f"Kampania '{c.name}' generuje {value_pct:.0f}% wartości konta, "
                    f"ale traci IS: budget {lost_budget*100:.0f}%, rank {lost_rank*100:.0f}%. "
                    f"Potencjalna dodatkowa wartość: ~${incremental_est:.0f}."
                ),
                current_value=f"Wartość: ${cv['value']:.0f} ({value_pct:.0f}%), Lost IS: {max(lost_budget, lost_rank)*100:.0f}%",
                recommended_action="Zwiększ budżet lub popraw Ad Rank dla tej kampanii",
                estimated_impact=f"~${incremental_est:.0f} dodatkowej wartości",
                metadata={
                    "value_usd": round(cv["value"], 2),
                    "value_pct": round(value_pct, 1),
                    "lost_budget_is": round(lost_budget * 100, 1),
                    "lost_rank_is": round(lost_rank * 100, 1),
                    "incremental_value_est": incremental_est,
                    "conversions": round(cv["conv"], 2),
                },
            ))
        return recs

    def _rule_24_target_vs_actual(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 1D: Flag campaigns where actual CPA/ROAS deviates significantly from target."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.bidding_strategy.in_(["TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"]),
            )
            .all()
        )

        for c in campaigns:
            metrics = (
                db.query(
                    func.sum(MetricDaily.cost_micros).label("cost"),
                    func.sum(MetricDaily.conversions).label("conv"),
                    func.sum(MetricDaily.conversion_value_micros).label("value"),
                )
                .filter(MetricDaily.campaign_id == c.id, MetricDaily.date >= cutoff)
                .first()
            )
            cost = int(metrics.cost or 0)
            conv = float(metrics.conv or 0)
            value = int(metrics.value or 0)

            if c.bidding_strategy in ("TARGET_CPA", "MAXIMIZE_CONVERSIONS") and c.target_cpa_micros and conv > 0:
                actual_cpa = cost / conv
                target_cpa = c.target_cpa_micros
                deviation = (actual_cpa - target_cpa) / target_cpa * 100
                if abs(deviation) >= t["r24_cpa_deviation_pct"]:
                    actual_usd = round(actual_cpa / 1_000_000, 2)
                    target_usd = round(target_cpa / 1_000_000, 2)
                    recs.append(Recommendation(
                        type=RecommendationType.TARGET_DEVIATION_ALERT,
                        priority=Priority.HIGH if abs(deviation) > 50 else Priority.MEDIUM,
                        entity_type="campaign",
                        entity_id=c.id,
                        entity_name=c.name,
                        campaign_name=c.name,
                        campaign_id=c.id,
                        reason=(
                            f"CPA kampanii '{c.name}' odbiega o {deviation:+.0f}% od celu. "
                            f"Aktualne: ${actual_usd}, Cel: ${target_usd}."
                        ),
                        current_value=f"CPA: ${actual_usd} vs cel ${target_usd}",
                        recommended_action="Sprawdź konwersje i dostosuj cel tCPA" if deviation > 0 else "Rozważ zwiększenie celu tCPA",
                        estimated_impact=f"Odchylenie {abs(deviation):.0f}%",
                        metadata={"actual_cpa": actual_usd, "target_cpa": target_usd, "deviation_pct": round(deviation, 1)},
                    ))

            elif c.bidding_strategy in ("TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE") and c.target_roas and cost > 0:
                actual_roas = value / cost
                target_roas = c.target_roas
                deviation = (actual_roas - target_roas) / target_roas * 100
                if abs(deviation) >= t["r24_roas_deviation_pct"]:
                    recs.append(Recommendation(
                        type=RecommendationType.TARGET_DEVIATION_ALERT,
                        priority=Priority.HIGH if abs(deviation) > 50 else Priority.MEDIUM,
                        entity_type="campaign",
                        entity_id=c.id,
                        entity_name=c.name,
                        campaign_name=c.name,
                        campaign_id=c.id,
                        reason=(
                            f"ROAS kampanii '{c.name}' odbiega o {deviation:+.0f}% od celu. "
                            f"Aktualne: {actual_roas:.2f}x, Cel: {target_roas:.2f}x."
                        ),
                        current_value=f"ROAS: {actual_roas:.2f}x vs cel {target_roas:.2f}x",
                        recommended_action="Zoptymalizuj kampanię lub dostosuj cel tROAS",
                        estimated_impact=f"Odchylenie {abs(deviation):.0f}%",
                        metadata={"actual_roas": round(actual_roas, 2), "target_roas": target_roas, "deviation_pct": round(deviation, 1)},
                    ))
        return recs

    def _rule_25_learning_period(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 1A: Alert for campaigns stuck in learning period."""
        recs = []
        t = self.thresholds
        from app.models.change_event import ChangeEvent

        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.bidding_strategy.in_(["TARGET_CPA", "TARGET_ROAS", "MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE"]),
            )
            .all()
        )

        for c in campaigns:
            if not c.primary_status_reasons:
                continue
            import json
            try:
                reasons = json.loads(c.primary_status_reasons) if isinstance(c.primary_status_reasons, str) else c.primary_status_reasons
            except (json.JSONDecodeError, TypeError):
                continue
            if not any("LEARNING" in str(r).upper() for r in reasons):
                continue

            # Estimate days in learning
            last_change = (
                db.query(ChangeEvent)
                .filter(
                    ChangeEvent.client_id == client_id,
                    ChangeEvent.change_resource_type == "CAMPAIGN",
                    ChangeEvent.campaign_name == c.name,
                )
                .order_by(ChangeEvent.change_date_time.desc())
                .first()
            )
            learning_days = (date.today() - last_change.change_date_time.date()).days if last_change and last_change.change_date_time else None

            if learning_days and learning_days > t["r25_stuck_learning_days"]:
                priority = Priority.HIGH
                status = "STUCK"
            elif learning_days and learning_days > t["r25_max_learning_days"]:
                priority = Priority.MEDIUM
                status = "EXTENDED"
            else:
                priority = Priority.LOW
                status = "LEARNING"

            recs.append(Recommendation(
                type=RecommendationType.LEARNING_PERIOD_ALERT,
                priority=priority,
                entity_type="campaign",
                entity_id=c.id,
                entity_name=c.name,
                campaign_name=c.name,
                campaign_id=c.id,
                reason=(
                    f"Kampania '{c.name}' jest w trybie uczenia ({status}). "
                    + (f"Już {learning_days} dni." if learning_days else "Czas nieokreślony.")
                ),
                current_value=f"Status: {status}, dni: {learning_days or '?'}",
                recommended_action="Nie wprowadzaj zmian podczas nauki" if status == "LEARNING" else "Rozważ reset strategii licytacji",
                metadata={"learning_days": learning_days, "status": status},
            ))
        return recs

    def _rule_26_conversion_quality(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 2A-2D: Flag conversion action configuration issues."""
        recs = []
        from app.models.conversion_action import ConversionAction

        actions = db.query(ConversionAction).filter(ConversionAction.client_id == client_id).all()
        if not actions:
            return recs

        # 2A: Secondary conversions included in metric
        secondary_in_metric = [a for a in actions if not a.primary_for_goal and a.include_in_conversions_metric]
        if secondary_in_metric:
            names = ", ".join(a.name for a in secondary_in_metric[:3])
            recs.append(Recommendation(
                type=RecommendationType.CONVERSION_QUALITY_ALERT,
                priority=Priority.HIGH,
                entity_type="client",
                entity_id=client_id,
                entity_name=f"Konwersje drugorzędne ({len(secondary_in_metric)})",
                campaign_name="(konto)",
                reason=f"{len(secondary_in_metric)} konwersji drugorzędnych wliczanych do 'Konwersje': {names}",
                current_value=f"{len(secondary_in_metric)} secondary in metric",
                recommended_action="Wyłącz drugorzędne konwersje z metryki 'Konwersje'",
                metadata={"issue_type": "SECONDARY_IN_METRIC", "count": len(secondary_in_metric)},
            ))

        # 2B: Zero-value + tROAS
        troas = db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.bidding_strategy.in_(["TARGET_ROAS", "MAXIMIZE_CONVERSION_VALUE"]),
        ).count()
        zero_val = [a for a in actions if a.primary_for_goal and (a.value_settings_default_value or 0) == 0]
        if zero_val and troas > 0:
            recs.append(Recommendation(
                type=RecommendationType.CONVERSION_QUALITY_ALERT,
                priority=Priority.HIGH,
                entity_type="client",
                entity_id=client_id,
                entity_name=f"Brak wartości konwersji ({len(zero_val)})",
                campaign_name="(konto)",
                reason=f"{len(zero_val)} primary konwersji bez wartości przy {troas} kampaniach tROAS",
                current_value=f"{len(zero_val)} zero-value primary",
                recommended_action="Ustaw wartości konwersji lub przejdź na tCPA",
                metadata={"issue_type": "ZERO_VALUE_TROAS", "count": len(zero_val)},
            ))

        return recs

    def _rule_27_demographic_anomaly(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """GAP 4A: Flag age/gender segments with CPA > 2x average."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        campaign_ids = [
            c.id for c in db.query(Campaign).filter(
                Campaign.client_id == client_id, Campaign.status == "ENABLED"
            ).all()
        ]
        if not campaign_ids:
            return recs

        # Overall average CPA
        totals = (
            db.query(
                func.sum(MetricDaily.cost_micros).label("cost"),
                func.sum(MetricDaily.conversions).label("conv"),
            )
            .filter(MetricDaily.campaign_id.in_(campaign_ids), MetricDaily.date >= cutoff)
            .first()
        )
        total_cost = int(totals.cost or 0)
        total_conv = float(totals.conv or 0)
        if total_conv <= 0:
            return recs
        avg_cpa = total_cost / total_conv / 1_000_000

        # Check age segments
        for segment_col, segment_name in [
            (MetricSegmented.age_range, "Wiek"),
            (MetricSegmented.gender, "Płeć"),
        ]:
            data = (
                db.query(
                    segment_col,
                    func.sum(MetricSegmented.cost_micros).label("cost"),
                    func.sum(MetricSegmented.conversions).label("conv"),
                )
                .filter(
                    MetricSegmented.campaign_id.in_(campaign_ids),
                    MetricSegmented.date >= cutoff,
                    segment_col.isnot(None),
                )
                .group_by(segment_col)
                .all()
            )

            for row in data:
                seg_cost = int(row.cost or 0)
                seg_conv = float(row.conv or 0)
                seg_cost_usd = round(seg_cost / 1_000_000, 2)
                if seg_conv <= 0 or seg_cost_usd < t["r27_min_spend"]:
                    continue
                seg_cpa = seg_cost / seg_conv / 1_000_000
                multiplier = seg_cpa / avg_cpa

                if multiplier >= t["r27_cpa_multiplier"]:
                    recs.append(Recommendation(
                        type=RecommendationType.DEMOGRAPHIC_ANOMALY,
                        priority=Priority.HIGH if multiplier >= 3.0 else Priority.MEDIUM,
                        entity_type="segment",
                        entity_id=client_id,
                        entity_name=f"{segment_name}: {row[0]}",
                        campaign_name="(wszystkie)",
                        reason=(
                            f"{segment_name} '{row[0]}' ma CPA ${seg_cpa:.2f} "
                            f"({multiplier:.1f}x średniej ${avg_cpa:.2f})"
                        ),
                        current_value=f"CPA: ${seg_cpa:.2f} ({multiplier:.1f}x)",
                        recommended_action=f"Rozważ wykluczenie lub zmniejszenie stawek dla {row[0]}",
                        estimated_impact=f"Potencjalna oszczędność: ${seg_cost_usd:.0f}",
                        metadata={
                            "segment": row[0],
                            "segment_type": segment_name,
                            "cpa": round(seg_cpa, 2),
                            "avg_cpa": round(avg_cpa, 2),
                            "multiplier": round(multiplier, 1),
                            "cost_usd": seg_cost_usd,
                        },
                    ))
        return recs

    def _rule_28_pmax_channel_imbalance(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """R28: Flag PMax channels where cost_share is high but conv_share is low."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        pmax_campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.campaign_type == "PERFORMANCE_MAX",
            )
            .all()
        )
        if not pmax_campaigns:
            return recs

        campaign_ids = [c.id for c in pmax_campaigns]
        campaign_map = {c.id: c for c in pmax_campaigns}

        data = (
            db.query(
                MetricSegmented.campaign_id,
                MetricSegmented.ad_network_type,
                func.sum(MetricSegmented.cost_micros).label("cost"),
                func.sum(MetricSegmented.conversions).label("conv"),
            )
            .filter(
                MetricSegmented.campaign_id.in_(campaign_ids),
                MetricSegmented.date >= cutoff,
                MetricSegmented.ad_network_type.isnot(None),
            )
            .group_by(MetricSegmented.campaign_id, MetricSegmented.ad_network_type)
            .all()
        )

        # Group by campaign
        by_campaign: dict[int, list] = defaultdict(list)
        for row in data:
            by_campaign[row.campaign_id].append(row)

        for campaign_id, rows in by_campaign.items():
            total_cost = sum(int(r.cost or 0) for r in rows)
            total_conv = sum(float(r.conv or 0) for r in rows)
            if total_cost <= 0:
                continue

            for row in rows:
                ch_cost = int(row.cost or 0)
                ch_conv = float(row.conv or 0)
                cost_share = ch_cost / total_cost
                conv_share = ch_conv / total_conv if total_conv > 0 else 0.0

                if cost_share > t["r28_max_cost_share"] and conv_share < t["r28_min_conv_share"]:
                    campaign = campaign_map[campaign_id]
                    ch_cost_usd = round(ch_cost / 1_000_000, 2)
                    recs.append(Recommendation(
                        type=RecommendationType.PMAX_CHANNEL_IMBALANCE,
                        priority=Priority.MEDIUM,
                        entity_type="campaign",
                        entity_id=campaign_id,
                        entity_name=campaign.name,
                        campaign_name=campaign.name,
                        campaign_id=campaign_id,
                        category="ALERT",
                        source=PLAYBOOK_RULES,
                        reason=(
                            f"Kanał '{row.ad_network_type}' w PMax '{campaign.name}' "
                            f"zużywa {cost_share:.0%} budżetu, ale generuje tylko {conv_share:.0%} konwersji."
                        ),
                        current_value=f"Koszt: {cost_share:.0%}, Konwersje: {conv_share:.0%}",
                        recommended_action="Sprawdź skuteczność kanału i rozważ dostosowanie sygnałów grupy zasobów.",
                        estimated_impact=f"Potencjalna oszczędność: ${ch_cost_usd:.0f}",
                        metadata={
                            "channel": row.ad_network_type,
                            "cost_share": round(cost_share, 3),
                            "conv_share": round(conv_share, 3),
                            "cost_usd": ch_cost_usd,
                            "total_cost_usd": round(total_cost / 1_000_000, 2),
                            "total_conv": round(total_conv, 2),
                        },
                    ))
        return recs

    def _rule_29_asset_group_ad_strength(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """R29: Flag asset groups with poor/average ad strength that are spending significantly."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)
        min_cost_micros = int(t["r29_min_spend"] * 1_000_000)

        campaign_ids = [
            c.id for c in db.query(Campaign).filter(
                Campaign.client_id == client_id, Campaign.status == "ENABLED"
            ).all()
        ]
        if not campaign_ids:
            return recs

        asset_groups = (
            db.query(AssetGroup)
            .filter(
                AssetGroup.campaign_id.in_(campaign_ids),
                AssetGroup.ad_strength.in_(["POOR", "AVERAGE"]),
            )
            .all()
        )
        if not asset_groups:
            return recs

        ag_ids = [ag.id for ag in asset_groups]
        ag_map = {ag.id: ag for ag in asset_groups}

        # Aggregate spend per asset group in the period
        spend_data = (
            db.query(
                AssetGroupDaily.asset_group_id,
                func.sum(AssetGroupDaily.cost_micros).label("cost"),
            )
            .filter(
                AssetGroupDaily.asset_group_id.in_(ag_ids),
                AssetGroupDaily.date >= cutoff,
            )
            .group_by(AssetGroupDaily.asset_group_id)
            .all()
        )

        for row in spend_data:
            total_cost = int(row.cost or 0)
            if total_cost < min_cost_micros:
                continue

            ag = ag_map.get(row.asset_group_id)
            if not ag:
                continue

            cost_usd = round(total_cost / 1_000_000, 2)
            campaign = db.get(Campaign, ag.campaign_id)
            campaign_name = campaign.name if campaign else "(nieznana)"
            priority = Priority.HIGH if ag.ad_strength == "POOR" else Priority.MEDIUM

            recs.append(Recommendation(
                type=RecommendationType.ASSET_GROUP_AD_STRENGTH,
                priority=priority,
                entity_type="ad_group",
                entity_id=ag.id,
                entity_name=ag.name,
                campaign_name=campaign_name,
                campaign_id=ag.campaign_id,
                category="ALERT",
                source=PLAYBOOK_RULES,
                reason=(
                    f"Grupa zasobów '{ag.name}' ma siłę reklamy '{ag.ad_strength}' "
                    f"i wydała ${cost_usd:.2f} w ostatnich {days} dniach."
                ),
                current_value=f"Ad Strength: {ag.ad_strength}, Wydatki: ${cost_usd:.2f}",
                recommended_action="Dodaj więcej zasobów (nagłówki, opisy, obrazy) aby poprawić siłę reklamy.",
                estimated_impact="Lepsza siła reklamy może zwiększyć zasięg i obniżyć CPA.",
                metadata={
                    "asset_group_id": ag.id,
                    "asset_group_name": ag.name,
                    "ad_strength": ag.ad_strength,
                    "cost_usd": cost_usd,
                    "cost_micros": total_cost,
                },
            ))
        return recs

    def _rule_30_audience_performance_anomaly(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """R30: Flag audiences with CPA significantly above average."""
        recs = []
        t = self.thresholds
        cutoff = date.today() - timedelta(days=days)

        campaign_ids = [
            c.id for c in db.query(Campaign).filter(
                Campaign.client_id == client_id, Campaign.status == "ENABLED"
            ).all()
        ]
        if not campaign_ids:
            return recs

        # Overall average CPA across all audiences
        totals = (
            db.query(
                func.sum(CampaignAudienceMetric.cost_micros).label("cost"),
                func.sum(CampaignAudienceMetric.conversions).label("conv"),
            )
            .filter(
                CampaignAudienceMetric.campaign_id.in_(campaign_ids),
                CampaignAudienceMetric.date >= cutoff,
            )
            .first()
        )
        total_cost = int(totals.cost or 0)
        total_conv = float(totals.conv or 0)
        if total_conv <= 0:
            return recs
        avg_cpa = total_cost / total_conv / 1_000_000

        # Per-audience aggregation
        audience_data = (
            db.query(
                CampaignAudienceMetric.audience_resource_name,
                func.min(CampaignAudienceMetric.audience_name).label("audience_name"),
                func.sum(CampaignAudienceMetric.cost_micros).label("cost"),
                func.sum(CampaignAudienceMetric.conversions).label("conv"),
            )
            .filter(
                CampaignAudienceMetric.campaign_id.in_(campaign_ids),
                CampaignAudienceMetric.date >= cutoff,
            )
            .group_by(CampaignAudienceMetric.audience_resource_name)
            .all()
        )

        for row in audience_data:
            aud_cost = int(row.cost or 0)
            aud_conv = float(row.conv or 0)
            aud_cost_usd = round(aud_cost / 1_000_000, 2)
            if aud_conv <= 0 or aud_cost_usd < t["r30_min_spend"]:
                continue
            aud_cpa = aud_cost / aud_conv / 1_000_000
            multiplier = aud_cpa / avg_cpa

            if multiplier >= t["r30_cpa_multiplier"]:
                aud_name = row.audience_name or row.audience_resource_name
                recs.append(Recommendation(
                    type=RecommendationType.AUDIENCE_PERFORMANCE_ANOMALY,
                    priority=Priority.MEDIUM,
                    entity_type="segment",
                    entity_id=client_id,
                    entity_name=f"Audience: {aud_name}",
                    campaign_name="(wszystkie)",
                    category="ALERT",
                    source=PLAYBOOK_RULES,
                    reason=(
                        f"Audience '{aud_name}' ma CPA ${aud_cpa:.2f} "
                        f"({multiplier:.1f}x średniej ${avg_cpa:.2f})"
                    ),
                    current_value=f"CPA: ${aud_cpa:.2f} ({multiplier:.1f}x)",
                    recommended_action=f"Rozważ wykluczenie lub zmniejszenie stawek dla '{aud_name}'",
                    estimated_impact=f"Potencjalna oszczędność: ${aud_cost_usd:.0f}",
                    metadata={
                        "audience_resource_name": row.audience_resource_name,
                        "audience_name": aud_name,
                        "cpa": round(aud_cpa, 2),
                        "avg_cpa": round(avg_cpa, 2),
                        "multiplier": round(multiplier, 1),
                        "cost_usd": aud_cost_usd,
                    },
                ))
        return recs

    def _rule_31_missing_extensions(
        self, db: Session, client_id: int, days: int
    ) -> list[Recommendation]:
        """R31: Flag Search campaigns missing minimum sitelinks or callouts."""
        recs = []
        t = self.thresholds

        search_campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.campaign_type == "SEARCH",
            )
            .all()
        )
        if not search_campaigns:
            return recs

        for campaign in search_campaigns:
            # Count assets by type for this campaign
            asset_counts = (
                db.query(
                    CampaignAsset.asset_type,
                    func.count(CampaignAsset.id).label("cnt"),
                )
                .filter(CampaignAsset.campaign_id == campaign.id)
                .group_by(CampaignAsset.asset_type)
                .all()
            )
            counts_map = {row.asset_type: row.cnt for row in asset_counts}
            sitelink_count = counts_map.get("SITELINK", 0)
            callout_count = counts_map.get("CALLOUT", 0)

            missing = []
            if sitelink_count < t["r31_min_sitelinks"]:
                missing.append(f"sitelinki ({sitelink_count}/{t['r31_min_sitelinks']})")
            if callout_count < t["r31_min_callouts"]:
                missing.append(f"objaśnienia ({callout_count}/{t['r31_min_callouts']})")

            if missing:
                recs.append(Recommendation(
                    type=RecommendationType.MISSING_EXTENSIONS_ALERT,
                    priority=Priority.HIGH,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    campaign_id=campaign.id,
                    category="RECOMMENDATION",
                    source=PLAYBOOK_RULES,
                    executable=False,
                    reason=(
                        f"Kampania '{campaign.name}' ma brakujące rozszerzenia: "
                        f"{', '.join(missing)}."
                    ),
                    current_value=f"Sitelinki: {sitelink_count}, Objaśnienia: {callout_count}",
                    recommended_action="Dodaj brakujące rozszerzenia reklam aby zwiększyć CTR i jakość reklamy.",
                    estimated_impact="Pełne rozszerzenia mogą zwiększyć CTR o 10-15%.",
                    metadata={
                        "sitelink_count": sitelink_count,
                        "callout_count": callout_count,
                        "min_sitelinks": t["r31_min_sitelinks"],
                        "min_callouts": t["r31_min_callouts"],
                        "missing_types": missing,
                    },
                ))
        return recs

    def _campaign_metrics_snapshot(self, db: Session, campaign: Campaign, cutoff: date) -> dict | None:
        metrics = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id == campaign.id,
                MetricDaily.date >= cutoff,
            )
            .all()
        )
        if not metrics:
            return None

        total_cost = sum(_micros_to_usd(m.cost_micros) for m in metrics)
        total_conv = sum(m.conversions or 0 for m in metrics)
        total_revenue = sum(_micros_to_usd(m.conversion_value_micros) for m in metrics)
        total_clicks = sum(m.clicks or 0 for m in metrics)
        total_impressions = sum(m.impressions or 0 for m in metrics)
        days_observed = max(len({m.date for m in metrics}), 1)
        budget_usd = _micros_to_usd(campaign.budget_micros)

        return {
            "campaign": campaign,
            "cost": total_cost,
            "conversions": total_conv,
            "revenue": total_revenue,
            "roas": (total_revenue / total_cost) if total_cost > 0 else 0,
            "cpa": (total_cost / total_conv) if total_conv > 0 else 0,
            "clicks": total_clicks,
            "impressions": total_impressions,
            "days_observed": days_observed,
            "avg_daily_spend": (total_cost / days_observed) if days_observed > 0 else total_cost,
            "budget_usd": budget_usd,
            "lost_is_pct": round((campaign.search_budget_lost_is or 0) * 100, 1),
        }

    def _account_avg_cpa(self, db: Session, client_id: int, cutoff: date) -> float:
        metrics = (
            db.query(MetricDaily)
            .join(Campaign, MetricDaily.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                MetricDaily.date >= cutoff,
            )
            .all()
        )
        total_cost = sum(_micros_to_usd(m.cost_micros) for m in metrics)
        total_conv = sum(m.conversions or 0 for m in metrics)
        return (total_cost / total_conv) if total_conv > 0 else 0

    def _campaign_ends_within(self, campaign: Campaign, days: int) -> bool:
        if not campaign.end_date:
            return False
        return campaign.end_date <= (date.today() + timedelta(days=days))

    def _evaluate_can_scale(
        self,
        campaign: Campaign,
        snapshot: dict | None,
        client: Client | None,
        account_avg_cpa: float,
    ) -> dict:
        reasons: list[str] = []
        if not snapshot:
            return {
                "can_scale": False,
                "headroom": False,
                "healthy_efficiency": False,
                "roas_only": False,
                "reason_codes": [INSUFFICIENT_DATA],
            }

        headroom = (
            snapshot["lost_is_pct"] >= 15
            or (snapshot["budget_usd"] > 0 and snapshot["avg_daily_spend"] >= snapshot["budget_usd"] * 0.8)
        )
        if not headroom:
            reasons.append(DESTINATION_NO_HEADROOM)

        business_rules = (client.business_rules or {}) if client and isinstance(client.business_rules, dict) else {}
        try:
            min_roas = max(float(business_rules.get("min_roas") or 0), 1.0)
        except (TypeError, ValueError):
            min_roas = 1.0

        roas_only = snapshot["revenue"] > 0 and snapshot["conversions"] < 3
        healthy_efficiency = False
        if snapshot["revenue"] > 0:
            healthy_efficiency = snapshot["roas"] >= min_roas
            if roas_only or not healthy_efficiency:
                reasons.append(ROAS_ONLY_SIGNAL)
        elif account_avg_cpa > 0 and snapshot["conversions"] >= 3:
            healthy_efficiency = snapshot["cpa"] <= account_avg_cpa * 1.1
            if not healthy_efficiency:
                reasons.append(INSUFFICIENT_DATA)
        else:
            reasons.append(INSUFFICIENT_DATA)

        if snapshot["conversions"] < 3 or snapshot["days_observed"] < 3:
            reasons.append(INSUFFICIENT_DATA)

        if self._campaign_ends_within(campaign, 7):
            reasons.append(DESTINATION_NO_HEADROOM)

        normalized = normalize_reason_codes(reasons)
        can_scale = (
            campaign.status == "ENABLED"
            and snapshot["conversions"] >= 3
            and headroom
            and healthy_efficiency
            and not roas_only
            and not self._campaign_ends_within(campaign, 7)
        )
        return {
            "can_scale": can_scale,
            "headroom": headroom,
            "healthy_efficiency": healthy_efficiency,
            "roas_only": roas_only,
            "reason_codes": normalized,
        }

    def _build_reallocation_candidate(
        self,
        db: Session,
        client: Client,
        best: dict,
        worst: dict,
        thresholds: dict,
        cutoff: date,
    ) -> Recommendation | None:
        best_campaign = best["campaign"]
        worst_campaign = worst["campaign"]
        if best_campaign.id == worst_campaign.id:
            return None

        best_budget = best["budget_usd"]
        worst_budget = worst["budget_usd"]
        if not (
            worst["roas"] > 0
            and best["roas"] > worst["roas"] * thresholds["r7_roas_ratio"]
            and worst_budget > best_budget
        ):
            return None

        move_amount = worst_budget * thresholds["r7_budget_move_pct"] / 100
        best_role = best_campaign.campaign_role_final or "UNKNOWN"
        worst_role = worst_campaign.campaign_role_final or "UNKNOWN"
        comparable = best_role == worst_role and best_role != "UNKNOWN"
        donor_protection = worst_campaign.protection_level or "HIGH"
        destination_protection = best_campaign.protection_level or "HIGH"
        scale_eval = self._evaluate_can_scale(
            best_campaign,
            best,
            client,
            self._account_avg_cpa(db, client.id, cutoff),
        )

        blocked_reasons: list[str] = []
        downgrade_reasons: list[str] = []
        context_outcome = ACTION

        if "UNKNOWN" in {best_role, worst_role}:
            context_outcome = BLOCKED_BY_CONTEXT
            blocked_reasons = [UNKNOWN_ROLE]
        elif not comparable:
            context_outcome = BLOCKED_BY_CONTEXT
            blocked_reasons = [ROLE_MISMATCH]
        elif donor_protection == "HIGH":
            context_outcome = BLOCKED_BY_CONTEXT
            blocked_reasons = [DONOR_PROTECTED_HIGH]
        elif donor_protection == "MEDIUM":
            context_outcome = INSIGHT_ONLY
            downgrade_reasons = [DONOR_PROTECTED_MEDIUM]
        elif not scale_eval["can_scale"]:
            context_outcome = INSIGHT_ONLY
            downgrade_reasons = scale_eval["reason_codes"] or [DESTINATION_NO_HEADROOM]

        roas_ratio = round(best["roas"] / worst["roas"], 2) if worst["roas"] > 0 else None
        return Recommendation(
            type=RecommendationType.REALLOCATE_BUDGET,
            priority=Priority.HIGH,
            entity_type="campaign",
            entity_id=best_campaign.id,
            entity_name=f"{worst_campaign.name} -> {best_campaign.name}",
            campaign_name=f"{worst_campaign.name} -> {best_campaign.name}",
            campaign_id=best_campaign.id,
            category="RECOMMENDATION" if context_outcome == ACTION else "ALERT",
            reason=(
                f"Candidate budget move: '{worst_campaign.name}' ({worst_role}) -> '{best_campaign.name}' ({best_role}). "
                f"ROAS {best['roas']:.2f}x vs {worst['roas']:.2f}x, move ~${move_amount:.2f}/day."
            ),
            current_value=(
                f"Best: ${best_budget:.2f}/day, Worst: ${worst_budget:.2f}/day, Ratio: {roas_ratio:.2f}x"
                if roas_ratio is not None else
                f"Best: ${best_budget:.2f}/day, Worst: ${worst_budget:.2f}/day"
            ),
            recommended_action=(
                "Review reallocation manually" if context_outcome == ACTION
                else "Insight only - check campaign role, protection and headroom first"
            ),
            estimated_impact="Higher overall ROAS if roles and scale context align",
            metadata={
                "best_roas": round(best["roas"], 2),
                "worst_roas": round(worst["roas"], 2),
                "move_amount": round(move_amount, 2),
                "from_campaign_id": worst_campaign.id,
                "to_campaign_id": best_campaign.id,
                "comparison_roas_ratio": roas_ratio,
                "primary_campaign_role": best_role,
                "counterparty_campaign_role": worst_role,
                "comparison_comparable": comparable,
                "donor_protection_level": donor_protection,
                "protection_level": destination_protection,
                "destination_can_scale": scale_eval["can_scale"],
                "destination_headroom": scale_eval["headroom"],
                "days_observed": best["days_observed"],
            },
            context_outcome=context_outcome,
            blocked_reasons=blocked_reasons,
            downgrade_reasons=downgrade_reasons,
        )

    def _build_explanation(self, rec: Recommendation, context: dict, metadata: dict) -> dict:
        def _entries(codes: list[str]) -> list[dict]:
            return [{"code": code} for code in normalize_reason_codes(codes)]

        if rec.type == RecommendationType.REALLOCATE_BUDGET:
            allowed = []
            if context.get("comparable"):
                allowed.append({"code": "SAME_ROLE_COMPARISON"})
            if context.get("can_scale"):
                allowed.append({"code": "DESTINATION_HAS_HEADROOM"})
            if context.get("donor_protection_level") == "LOW":
                allowed.append({"code": "DONOR_LOW_PROTECTION"})
            combined = normalize_reason_codes(rec.blocked_reasons + rec.downgrade_reasons)
            next_code = "MANUAL_BUDGET_REVIEW"
            if UNKNOWN_ROLE in combined:
                next_code = "SET_ROLE_OVERRIDE"
            elif DESTINATION_NO_HEADROOM in combined or ROAS_ONLY_SIGNAL in combined:
                next_code = "REVIEW_BIDS_FIRST"
            return {
                "why_allowed": allowed,
                "why_blocked": _entries(combined),
                "tradeoffs": [{"code": "BUDGET_SHIFT_REDUCES_DONOR_COVERAGE"}],
                "risk_note": {"code": "MANUAL_REVIEW_REQUIRED" if rec.context_outcome != ACTION else "MONITOR_AFTER_REALLOCATION"},
                "next_best_action": {"code": next_code},
            }

        if rec.type == RecommendationType.IS_BUDGET_ALERT:
            combined = normalize_reason_codes(rec.blocked_reasons + rec.downgrade_reasons)
            return {
                "why_allowed": ([{"code": "HEALTHY_BUDGET_HEADROOM"}] if rec.context_outcome == ACTION else []),
                "why_blocked": _entries(combined),
                "tradeoffs": [{"code": "MORE_SPEND_WITHOUT_GUARANTEED_INCREMENTALITY"}],
                "risk_note": {"code": "MONITOR_BUDGET_AFTER_CHANGE" if rec.context_outcome == ACTION else "REVIEW_CONTEXT_BEFORE_SCALING"},
                "next_best_action": {"code": "REVIEW_BIDS_FIRST" if combined else "MONITOR_BUDGET_AFTER_CHANGE"},
            }

        return {
            "why_allowed": [],
            "why_blocked": [],
            "tradeoffs": [],
            "risk_note": None,
            "next_best_action": None,
        }

    def _finalize_recommendation(
        self,
        db: Session,
        client_id: int,
        days: int,
        rec: Recommendation,
    ) -> Recommendation:
        metadata = dict(rec.metadata or {})
        rec.metadata = metadata
        rec.source = rec.source or PLAYBOOK_RULES
        metadata.setdefault("campaign_name", rec.campaign_name)
        metadata.setdefault("entity_name", rec.entity_name)

        self._infer_scope(db, rec, metadata)
        self._enrich_metadata_from_entity(db, rec, metadata)

        if not rec.context_outcome:
            rec.context_outcome = ACTION if rec.category == "RECOMMENDATION" else INSIGHT_ONLY
        rec.blocked_reasons = normalize_reason_codes(rec.blocked_reasons)
        rec.downgrade_reasons = normalize_reason_codes(rec.downgrade_reasons)

        if rec.type == RecommendationType.INCREASE_BID:
            metadata.setdefault("bid_change_pct", self.thresholds["r2_bid_increase_pct"])
        elif rec.type == RecommendationType.DECREASE_BID:
            metadata.setdefault("bid_change_pct", -self.thresholds["r3_bid_decrease_pct"])
        elif rec.type == RecommendationType.IS_BUDGET_ALERT and metadata.get("budget_action") == "INCREASE_BUDGET":
            metadata.setdefault("budget_change_pct", self.thresholds["r9_budget_increase_pct"])

        context = {
            "context_outcome": rec.context_outcome,
            "blocked_reasons": rec.blocked_reasons,
            "downgrade_reasons": rec.downgrade_reasons,
        }
        if metadata.get("primary_campaign_role"):
            context["primary_campaign_role"] = metadata.get("primary_campaign_role")
        if metadata.get("counterparty_campaign_role"):
            context["counterparty_campaign_role"] = metadata.get("counterparty_campaign_role")
        if metadata.get("comparison_comparable") is not None:
            context["comparable"] = bool(metadata.get("comparison_comparable"))
        if metadata.get("destination_can_scale") is not None:
            context["can_scale"] = bool(metadata.get("destination_can_scale"))
        elif metadata.get("can_scale") is not None:
            context["can_scale"] = bool(metadata.get("can_scale"))
        if metadata.get("destination_headroom") is not None:
            context["destination_headroom"] = bool(metadata.get("destination_headroom"))
        if metadata.get("protection_level"):
            context["protection_level"] = metadata.get("protection_level")
        if metadata.get("donor_protection_level"):
            context["donor_protection_level"] = metadata.get("donor_protection_level")

        explanation = self._build_explanation(rec, context, metadata)
        rec.evidence_json = {
            "metadata": metadata,
            "context": context,
            "explanation": explanation,
            "lookback_days": days,
            "date_from": str(date.today() - timedelta(days=days)),
            "date_to": str(date.today()),
        }

        rec_dict = rec.to_dict()
        rec.action_payload = build_action_payload({**rec_dict, "metadata": metadata, "context": context})
        rec.executable = bool((rec.action_payload or {}).get("executable"))
        rec.expires_at = rec.expires_at or default_expires_at({**rec_dict, "action_payload": rec.action_payload})
        rec.impact_micros = estimate_impact_micros({**rec_dict, "metadata": metadata})
        rec.impact_score = round(min((rec.impact_micros or 0) / 150_000_000, 1), 2)
        rec.confidence_score = compute_confidence_score({**rec_dict, "metadata": metadata}, days)
        rec.risk_score = compute_risk_score(
            {
                **rec_dict,
                "metadata": {**metadata, "context": context},
                "context": context,
                "action_payload": rec.action_payload,
                "context_outcome": rec.context_outcome,
                "blocked_reasons": rec.blocked_reasons,
                "downgrade_reasons": rec.downgrade_reasons,
            }
        )
        rec.priority, rec.score = compute_priority(
            {
                **rec_dict,
                "impact_micros": rec.impact_micros,
                "confidence_score": rec.confidence_score,
                "risk_score": rec.risk_score,
            }
        )
        rec.stable_key = build_stable_key(rec.to_dict(), client_id)
        return rec

    def _infer_scope(self, db: Session, rec: Recommendation, metadata: dict) -> None:
        rec.campaign_id = rec.campaign_id or metadata.get("campaign_id")
        rec.ad_group_id = rec.ad_group_id or metadata.get("ad_group_id")

        if rec.entity_type == "campaign" and rec.entity_id and not rec.campaign_id:
            rec.campaign_id = rec.entity_id
            return

        if rec.entity_type == "keyword" and rec.entity_id:
            kw = db.get(Keyword, rec.entity_id)
            if kw:
                rec.ad_group_id = rec.ad_group_id or kw.ad_group_id
                if kw.ad_group_id:
                    ad_group = db.get(AdGroup, kw.ad_group_id)
                    if ad_group:
                        rec.campaign_id = rec.campaign_id or ad_group.campaign_id
        elif rec.entity_type == "ad" and rec.entity_id:
            ad = db.get(Ad, rec.entity_id)
            if ad:
                rec.ad_group_id = rec.ad_group_id or ad.ad_group_id
                if ad.ad_group_id:
                    ad_group = db.get(AdGroup, ad.ad_group_id)
                    if ad_group:
                        rec.campaign_id = rec.campaign_id or ad_group.campaign_id

    def _enrich_metadata_from_entity(self, db: Session, rec: Recommendation, metadata: dict) -> None:
        if rec.entity_type == "keyword" and rec.entity_id:
            kw = db.get(Keyword, rec.entity_id)
            if not kw:
                return
            metadata.setdefault("current_bid_micros", int(kw.bid_micros or 0))
            metadata.setdefault("spend", round(_micros_to_usd(kw.cost_micros), 2))
            metadata.setdefault("clicks", int(kw.clicks or 0))
            metadata.setdefault("impressions", int(kw.impressions or 0))
            metadata.setdefault("conversions", float(kw.conversions or 0))
            metadata.setdefault("current_status", kw.status)
        elif rec.entity_type == "ad" and rec.entity_id:
            ad = db.get(Ad, rec.entity_id)
            if not ad:
                return
            metadata.setdefault("spend", round(_micros_to_usd(ad.cost_micros), 2))
            metadata.setdefault("clicks", int(ad.clicks or 0))
            metadata.setdefault("impressions", int(ad.impressions or 0))
            metadata.setdefault("conversions", float(ad.conversions or 0))
            metadata.setdefault("current_status", ad.status)
        elif rec.entity_type == "campaign" and rec.entity_id:
            campaign = db.get(Campaign, rec.entity_id)
            if not campaign:
                return
            metadata.setdefault("current_budget_micros", int(campaign.budget_micros or 0))
            metadata.setdefault("current_status", campaign.status)

        campaign = db.get(Campaign, rec.campaign_id) if rec.campaign_id else None
        if campaign:
            metadata.setdefault("primary_campaign_role", campaign.campaign_role_final or "UNKNOWN")
            metadata.setdefault("campaign_role_auto", campaign.campaign_role_auto)
            metadata.setdefault("campaign_role_final", campaign.campaign_role_final)
            metadata.setdefault("protection_level", campaign.protection_level)
            metadata.setdefault("role_source", campaign.role_source)
            metadata.setdefault("role_confidence", campaign.role_confidence)
    def _analytics_alerts(
        self,
        db: Session,
        client_id: int,
        days: int,
        recommendations: list[Recommendation],
    ) -> list[Recommendation]:
        alerts: list[Recommendation] = []
        enabled_campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )
        if not enabled_campaigns:
            return alerts

        today = date.today()
        cutoff = today - timedelta(days=days)
        prev_cutoff = cutoff - timedelta(days=days)
        campaign_ids = [c.id for c in enabled_campaigns]
        metrics = (
            db.query(MetricDaily)
            .filter(MetricDaily.campaign_id.in_(campaign_ids), MetricDaily.date >= prev_cutoff)
            .all()
        )
        current_by_campaign = {cid: {"cost": 0.0, "clicks": 0, "impr": 0, "conv": 0.0, "value": 0.0} for cid in campaign_ids}
        prev_by_campaign = {cid: {"cost": 0.0, "clicks": 0, "impr": 0, "conv": 0.0, "value": 0.0} for cid in campaign_ids}

        for metric in metrics:
            target = current_by_campaign if metric.date >= cutoff else prev_by_campaign
            row = target.setdefault(metric.campaign_id, {"cost": 0.0, "clicks": 0, "impr": 0, "conv": 0.0, "value": 0.0})
            row["cost"] += _micros_to_usd(metric.cost_micros)
            row["clicks"] += metric.clicks or 0
            row["impr"] += metric.impressions or 0
            row["conv"] += metric.conversions or 0
            row["value"] += _micros_to_usd(metric.conversion_value_micros)

        avg_cost = sum(current_by_campaign[c.id]["cost"] for c in enabled_campaigns) / max(len(enabled_campaigns), 1)
        above_avg_no_conv = [
            c.name for c in enabled_campaigns
            if current_by_campaign[c.id]["cost"] > avg_cost and current_by_campaign[c.id]["conv"] == 0
        ]
        if above_avg_no_conv:
            alerts.append(Recommendation(
                type=RecommendationType.ANALYTICS_ALERT,
                priority=Priority.HIGH,
                entity_type="campaign",
                entity_id=0,
                entity_name=above_avg_no_conv[0],
                campaign_name="; ".join(above_avg_no_conv[:3]),
                category="ALERT",
                source=ANALYTICS,
                reason=f"{len(above_avg_no_conv)} kampanii wydaje powyżej średniej bez konwersji.",
                recommended_action="Sprawdź dystrybucję wydatków i targetowanie.",
                metadata={
                    "insight_type": "ABOVE_AVG_NO_CONV",
                    "campaigns": above_avg_no_conv,
                    "cost": round(avg_cost, 2),
                },
            ))

        divergent = []
        for campaign in enabled_campaigns:
            current = current_by_campaign[campaign.id]
            previous = prev_by_campaign[campaign.id]
            prev_ctr = (previous["clicks"] / previous["impr"] * 100) if previous["impr"] else 0
            curr_ctr = (current["clicks"] / current["impr"] * 100) if current["impr"] else 0
            prev_conv = previous["conv"]
            curr_conv = current["conv"]
            ctr_delta = ((curr_ctr - prev_ctr) / prev_ctr * 100) if prev_ctr > 0 else 0
            conv_delta = ((curr_conv - prev_conv) / prev_conv * 100) if prev_conv > 0 else 0
            if ctr_delta > 10 and conv_delta < -5:
                divergent.append(campaign.name)
        if divergent:
            alerts.append(Recommendation(
                type=RecommendationType.ANALYTICS_ALERT,
                priority=Priority.MEDIUM,
                entity_type="campaign",
                entity_id=0,
                entity_name=divergent[0],
                campaign_name="; ".join(divergent[:3]),
                category="ALERT",
                source=ANALYTICS,
                reason=f"CTR rośnie, a konwersje spadają w {len(divergent)} kampaniach.",
                recommended_action="Sprawdź landing page'e i dopasowanie przekazu.",
                metadata={"insight_type": "CTR_CONV_DIVERGENCE", "campaigns": divergent},
            ))

        high_recs = [r for r in recommendations if r.category == "RECOMMENDATION" and r.priority == Priority.HIGH]
        if high_recs:
            alerts.append(Recommendation(
                type=RecommendationType.ANALYTICS_ALERT,
                priority=Priority.LOW,
                entity_type="campaign",
                entity_id=0,
                entity_name="Kolejka priorytetowa",
                campaign_name="Rekomendacje",
                category="ALERT",
                source=ANALYTICS,
                reason=f"{len(high_recs)} rekomendacji o wysokim priorytecie czeka na przegląd.",
                recommended_action="Zacznij od rekomendacji o największym wpływie.",
                metadata={"insight_type": "HIGH_RECOMMENDATION_QUEUE", "count": len(high_recs)},
            ))

        roas_values = []
        stars = []
        for campaign in enabled_campaigns:
            current = current_by_campaign[campaign.id]
            roas = (current["value"] / current["cost"]) if current["cost"] > 0 else 0
            roas_values.append(roas)
            if roas > 0:
                stars.append((campaign.name, roas))
        avg_roas = sum(roas_values) / max(len(roas_values), 1)
        standout = [name for name, roas in stars if avg_roas > 0 and roas > avg_roas * 2]
        if standout:
            alerts.append(Recommendation(
                type=RecommendationType.ANALYTICS_ALERT,
                priority=Priority.MEDIUM,
                entity_type="campaign",
                entity_id=0,
                entity_name=standout[0],
                campaign_name="; ".join(standout[:3]),
                category="ALERT",
                source=ANALYTICS,
                reason=f"{len(standout)} kampanii ma ROAS powyżej 2x średniej konta.",
                recommended_action="Rozważ skalowanie budżetu po ręcznym przeglądzie.",
                metadata={"insight_type": "ROAS_OUTLIER", "campaigns": standout},
            ))

        return alerts
# Singleton instance
recommendations_engine = RecommendationsEngine()



























