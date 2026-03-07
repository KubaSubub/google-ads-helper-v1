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
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Keyword, SearchTerm, Ad, AdGroup, Campaign, MetricDaily
)
from app.models.metric_segmented import MetricSegmented


def _micros_to_usd(micros) -> float:
    """Convert micros (BigInteger) to USD float."""
    return (micros or 0) / 1_000_000


def _ctr_micros_to_pct(ctr_micros) -> float:
    """Convert CTR stored as micros (50000 = 5%) to percentage float."""
    return (ctr_micros or 0) / 10_000


class RecommendationType(str, Enum):
    # MVP (R1–R7)
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    INCREASE_BID = "INCREASE_BID"
    DECREASE_BID = "DECREASE_BID"
    ADD_KEYWORD = "ADD_KEYWORD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    PAUSE_AD = "PAUSE_AD"
    REALLOCATE_BUDGET = "REALLOCATE_BUDGET"
    # v1.1 (R8–R13)
    QS_ALERT = "QS_ALERT"
    IS_BUDGET_ALERT = "IS_BUDGET_ALERT"
    IS_RANK_ALERT = "IS_RANK_ALERT"
    WASTED_SPEND_ALERT = "WASTED_SPEND_ALERT"
    PMAX_CANNIBALIZATION = "PMAX_CANNIBALIZATION"
    # v1.2 (R15–R18)
    DEVICE_ANOMALY = "DEVICE_ANOMALY"
    GEO_ANOMALY = "GEO_ANOMALY"
    BUDGET_PACING = "BUDGET_PACING"
    NGRAM_NEGATIVE = "NGRAM_NEGATIVE"


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Recommendation:
    """A single optimization recommendation."""
    type: str
    priority: str
    entity_type: str          # keyword, search_term, ad, campaign
    entity_id: int
    entity_name: str
    campaign_name: str
    reason: str
    category: str = "RECOMMENDATION"  # RECOMMENDATION (actionable) or ALERT (diagnostic)
    current_value: Optional[str] = None
    recommended_action: Optional[str] = None
    estimated_impact: Optional[str] = None
    metadata: dict = field(default_factory=dict)

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
        """Run all 17 rules and return a combined list of recommendations."""
        recommendations: list[Recommendation] = []

        # MVP rules (R1–R7)
        recommendations.extend(self._rule_1_pause_keywords(db, client_id, days))
        recommendations.extend(self._rule_2_increase_bid(db, client_id, days))
        recommendations.extend(self._rule_3_decrease_bid(db, client_id, days))
        recommendations.extend(self._rule_4_add_keyword(db, client_id, days))
        recommendations.extend(self._rule_5_add_negative(db, client_id, days))
        recommendations.extend(self._rule_6_pause_ad(db, client_id, days))
        recommendations.extend(self._rule_7_reallocate_budget(db, client_id, days))

        # v1.1 rules (R8–R13)
        recommendations.extend(self._rule_8_quality_score_alert(db, client_id, days))
        recommendations.extend(self._rule_9_is_lost_budget(db, client_id, days))
        recommendations.extend(self._rule_10_is_lost_rank(db, client_id, days))
        recommendations.extend(self._rule_11_low_ctr_high_impr(db, client_id, days))
        recommendations.extend(self._rule_12_wasted_spend_alert(db, client_id, days))
        recommendations.extend(self._rule_13_pmax_search_overlap(db, client_id, days))

        # v1.2 rules (R15–R18, excluding R14)
        recommendations.extend(self._rule_15_device_anomaly(db, client_id, days))
        recommendations.extend(self._rule_16_geo_anomaly(db, client_id, days))
        recommendations.extend(self._rule_17_budget_pacing(db, client_id, days))
        recommendations.extend(self._rule_18_ngram_negative(db, client_id, days))

        # Sort by priority: HIGH first, then MEDIUM, then LOW
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

        return [r.to_dict() for r in recommendations]

    # -----------------------------------------------------------------------
    # RULE 1: Pause Keyword (high spend, zero conversions)
    # Uses Keyword model data (refreshed during sync from Google Ads API
    # with date_from/date_to range, typically last 30 days)
    # -----------------------------------------------------------------------
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
            )
            .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .group_by(SearchTerm.text, Campaign.name, Campaign.id)
            .all()
        )

        # Get existing keywords for dedup
        existing_keywords = set(
            kw.text.lower()
            for kw in (
                db.query(Keyword.text)
                .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
                .join(Campaign, AdGroup.campaign_id == Campaign.id)
                .filter(Campaign.client_id == client_id)
                .all()
            )
        )

        # Get existing negative keywords to avoid recommending terms already negated
        existing_negatives = set()
        neg_keywords = (
            db.query(Keyword.text)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                Keyword.status == "PAUSED",
            )
            .all()
        )
        for nk in neg_keywords:
            existing_negatives.add(nk.text.lower())

        for term in terms:
            text_lower = term.text.lower()
            if text_lower in existing_keywords:
                continue
            if text_lower in existing_negatives:
                continue

            total_clicks = term.total_clicks or 0
            total_conv = term.total_conv or 0
            total_cost = (term.total_cost_micros or 0) / 1_000_000
            cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0

            # Choose match type based on word count: EXACT for 1-2 words, PHRASE for 3+
            word_count = len(term.text.strip().split())
            match_type = "EXACT" if word_count <= 2 else "PHRASE"

            if total_conv >= t["r4_min_conversions"]:
                recs.append(Recommendation(
                    type=RecommendationType.ADD_KEYWORD,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    reason=(
                        f"Search term has {total_conv:.0f} conversions "
                        f"with {cvr:.1f}% CVR. Not yet a keyword."
                    ),
                    current_value=f"Conv: {total_conv:.0f}, CVR: {cvr:.1f}%, Cost: ${total_cost:.2f}",
                    recommended_action=f"Add as {match_type} match keyword",
                    estimated_impact="Capture more of this high-converting traffic",
                    metadata={
                        "conversions": float(total_conv),
                        "cvr": round(cvr, 2),
                        "match_type": match_type,
                    },
                ))

            elif total_clicks >= t["r4_min_clicks_phrase"] and cvr == 0:
                ctr = (total_clicks / (term.total_impr or 1)) * 100
                if ctr >= t["r4_min_ctr_phrase"]:
                    recs.append(Recommendation(
                        type=RecommendationType.ADD_KEYWORD,
                        priority=Priority.LOW,
                        entity_type="search_term",
                        entity_id=0,
                        entity_name=term.text,
                        campaign_name=term.campaign_name,
                        reason=(
                            f"High engagement: {total_clicks} clicks, {ctr:.1f}% CTR. "
                            f"Worth testing as a keyword."
                        ),
                        current_value=f"Clicks: {total_clicks}, CTR: {ctr:.1f}%",
                        recommended_action=f"Add as PHRASE match keyword",
                        metadata={
                            "clicks": int(total_clicks),
                            "ctr": round(ctr, 2),
                            "match_type": "PHRASE",
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 5: Add Negative Keyword (wasted spend)
    # -----------------------------------------------------------------------
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
            )
            .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_id)
            .group_by(SearchTerm.text, Campaign.name)
            .all()
        )

        for term in terms:
            total_clicks = term.total_clicks or 0
            total_conv = term.total_conv or 0
            total_cost = (term.total_cost_micros or 0) / 1_000_000
            total_impr = term.total_impr or 1
            ctr = (total_clicks / total_impr) * 100

            # Check 1: Irrelevant words (word boundary match)
            text_lower = term.text.lower()
            matched_words = [
                p.pattern.replace(r'\b', '').replace('\\', '')
                for p in self._IRRELEVANT_PATTERNS if p.search(text_lower)
            ]
            if matched_words:
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    reason=(
                        f"Contains irrelevant word(s): {', '.join(matched_words)}. "
                        f"Cost: ${total_cost:.2f}."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, Clicks: {total_clicks}",
                    recommended_action="Add as NEGATIVE keyword (account level)",
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata={"matched_words": matched_words},
                ))
                continue

            # Check 2: Clicks but no conversions + low CTR
            if (
                total_clicks >= t["r5_min_clicks"]
                and total_conv == 0
                and ctr < t["r5_max_ctr"]
            ):
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.MEDIUM,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    reason=(
                        f"{total_clicks} clicks, 0 conversions, CTR {ctr:.2f}%. "
                        f"Wasted ${total_cost:.2f}."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, CTR: {ctr:.2f}%",
                    recommended_action="Add as NEGATIVE keyword (campaign level)",
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata={"clicks": int(total_clicks), "cost": float(total_cost)},
                ))

            # Check 3: High cost with zero conversions
            elif total_cost >= t["r5_min_cost_immediate"] and total_conv == 0:
                recs.append(Recommendation(
                    type=RecommendationType.ADD_NEGATIVE,
                    priority=Priority.HIGH,
                    entity_type="search_term",
                    entity_id=0,
                    entity_name=term.text,
                    campaign_name=term.campaign_name,
                    reason=(
                        f"Spent ${total_cost:.2f} with 0 conversions. Immediate waste."
                    ),
                    current_value=f"Cost: ${total_cost:.2f}, Conv: 0",
                    recommended_action="Add as NEGATIVE keyword immediately",
                    estimated_impact=f"Save ~${total_cost:.2f}/month",
                    metadata={"cost": float(total_cost)},
                ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 6: Pause Ad (underperforming vs best in group)
    # -----------------------------------------------------------------------
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

        today = date.today()
        cutoff = today - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        campaign_roas = []
        for campaign in campaigns:
            metrics = (
                db.query(MetricDaily)
                .filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date >= cutoff,
                )
                .all()
            )

            if not metrics:
                continue

            total_cost = sum(_micros_to_usd(m.cost_micros) for m in metrics)
            total_conv = sum(m.conversions or 0 for m in metrics)
            total_revenue = sum(_micros_to_usd(m.conversion_value_micros) for m in metrics)
            roas = (total_revenue / total_cost) if total_cost > 0 else 0

            campaign_roas.append({
                "campaign": campaign,
                "roas": roas,
                "cost": total_cost,
                "conversions": total_conv,
                "revenue": total_revenue,
            })

        if len(campaign_roas) < 2:
            return recs

        campaign_roas.sort(key=lambda x: x["roas"], reverse=True)

        best = campaign_roas[0]
        worst = campaign_roas[-1]

        best_budget = _micros_to_usd(best["campaign"].budget_micros)
        worst_budget = _micros_to_usd(worst["campaign"].budget_micros)

        if (
            worst["roas"] > 0
            and best["roas"] > worst["roas"] * t["r7_roas_ratio"]
            and worst_budget > best_budget
        ):
            move_amount = worst_budget * t["r7_budget_move_pct"] / 100
            recs.append(Recommendation(
                type=RecommendationType.REALLOCATE_BUDGET,
                priority=Priority.HIGH,
                entity_type="campaign",
                entity_id=best["campaign"].id,
                entity_name=f"{worst['campaign'].name} → {best['campaign'].name}",
                campaign_name=f"{worst['campaign'].name} → {best['campaign'].name}",
                reason=(
                    f"'{best['campaign'].name}' has ROAS {best['roas']:.2f}x vs "
                    f"'{worst['campaign'].name}' ROAS {worst['roas']:.2f}x. "
                    f"Move budget from low to high performer."
                ),
                current_value=(
                    f"Best: ${best_budget:.2f}/day, "
                    f"Worst: ${worst_budget:.2f}/day"
                ),
                recommended_action=(
                    f"Move ${move_amount:.0f}/day from '{worst['campaign'].name}' "
                    f"to '{best['campaign'].name}'"
                ),
                estimated_impact="Higher overall ROAS for the account",
                metadata={
                    "best_roas": round(best["roas"], 2),
                    "worst_roas": round(worst["roas"], 2),
                    "move_amount": round(move_amount, 2),
                },
            ))

        return recs

    # ===================================================================
    # v1.1 RULES (R8–R13) — Quick Wins, no new sync required
    # ===================================================================

    # -----------------------------------------------------------------------
    # RULE 8: Quality Score Alert — Keywords with QS < 5
    # -----------------------------------------------------------------------
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
        today = date.today()
        cutoff = today - timedelta(days=days)

        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_id,
                Campaign.status == "ENABLED",
                Campaign.search_budget_lost_is.isnot(None),
            )
            .all()
        )

        for campaign in campaigns:
            lost_is = (campaign.search_budget_lost_is or 0) * 100
            if lost_is < t["r9_min_lost_is_pct"]:
                continue

            metrics = (
                db.query(MetricDaily)
                .filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date >= cutoff,
                )
                .all()
            )
            if not metrics:
                continue

            total_cost = sum(_micros_to_usd(m.cost_micros) for m in metrics)
            total_conv = sum(m.conversions or 0 for m in metrics)
            total_revenue = sum(_micros_to_usd(m.conversion_value_micros) for m in metrics)
            roas = (total_revenue / total_cost) if total_cost > 0 else 0
            cpa = (total_cost / total_conv) if total_conv > 0 else 0
            budget_usd = _micros_to_usd(campaign.budget_micros)

            # Sub-check 1: Healthy performance → increase budget
            if total_conv > 0 and roas >= 1.0:
                priority = Priority.HIGH if lost_is > t["r9_high_lost_is_pct"] else Priority.MEDIUM
                recs.append(Recommendation(
                    type=RecommendationType.IS_BUDGET_ALERT,
                    priority=priority,
                    entity_type="campaign",
                    entity_id=campaign.id,
                    entity_name=campaign.name,
                    campaign_name=campaign.name,
                    category="RECOMMENDATION",
                    reason=(
                        f"Tracisz {lost_is:.0f}% wyświetleń z powodu budżetu "
                        f"przy ROAS {roas:.2f}x"
                    ),
                    current_value=(
                        f"Lost IS: {lost_is:.0f}%, ROAS: {roas:.2f}x, "
                        f"Budget: ${budget_usd:.2f}/day"
                    ),
                    recommended_action=(
                        f"Zwiększ budżet o {t['r9_budget_increase_pct']}%"
                    ),
                    estimated_impact=f"Potencjalnie {lost_is:.0f}% więcej wyświetleń",
                    metadata={
                        "lost_is_pct": round(lost_is, 1),
                        "roas": round(roas, 2),
                        "budget_usd": round(budget_usd, 2),
                    },
                ))

            # Sub-check 2: Lost IS > 50% + high CPA → decrease bids
            elif lost_is > 50 and total_conv > 0:
                all_metrics = (
                    db.query(MetricDaily)
                    .join(Campaign, MetricDaily.campaign_id == Campaign.id)
                    .filter(
                        Campaign.client_id == client_id,
                        MetricDaily.date >= cutoff,
                    )
                    .all()
                )
                acct_cost = sum(_micros_to_usd(m.cost_micros) for m in all_metrics)
                acct_conv = sum(m.conversions or 0 for m in all_metrics)
                avg_cpa = (acct_cost / acct_conv) if acct_conv > 0 else 0

                if avg_cpa > 0 and cpa > avg_cpa * 1.2:
                    recs.append(Recommendation(
                        type=RecommendationType.IS_BUDGET_ALERT,
                        priority=Priority.HIGH,
                        entity_type="campaign",
                        entity_id=campaign.id,
                        entity_name=campaign.name,
                        campaign_name=campaign.name,
                        category="RECOMMENDATION",
                        reason=(
                            f"Kampania wyczerpuje budżet za wcześnie — "
                            f"Lost IS: {lost_is:.0f}%, CPA: ${cpa:.2f} "
                            f"(avg konta: ${avg_cpa:.2f})"
                        ),
                        current_value=f"Lost IS: {lost_is:.0f}%, CPA: ${cpa:.2f}",
                        recommended_action=(
                            "Obniż stawki — zbyt wysoki CPA przy szybkim "
                            "wyczerpywaniu budżetu"
                        ),
                        metadata={
                            "lost_is_pct": round(lost_is, 1),
                            "cpa": round(cpa, 2),
                            "avg_cpa": round(avg_cpa, 2),
                        },
                    ))

        return recs

    # -----------------------------------------------------------------------
    # RULE 10: Impression Share Lost to Rank — Quality/Bid Problem
    # -----------------------------------------------------------------------
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

        # Get all search terms for this client
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

        # Extract n-grams (1, 2, 3 words) and aggregate metrics
        ngram_data: dict[str, dict] = defaultdict(
            lambda: {"cost": 0.0, "conv": 0.0, "clicks": 0, "terms": set()}
        )

        for term in terms:
            words = term.text.lower().strip().split()
            cost_usd = _micros_to_usd(term.cost_micros)
            conv = term.conversions or 0

            for n in range(1, 4):  # 1-gram, 2-gram, 3-gram
                for i in range(len(words) - n + 1):
                    ngram = " ".join(words[i:i + n])
                    if len(ngram) < 3:  # Skip very short n-grams
                        continue
                    ngram_data[ngram]["cost"] += cost_usd
                    ngram_data[ngram]["conv"] += conv
                    ngram_data[ngram]["clicks"] += (term.clicks or 0)
                    ngram_data[ngram]["terms"].add(term.text.lower())

        # Find wasteful n-grams
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
                    category="RECOMMENDATION",
                    reason=(
                        f"N-gram '{ngram}' pojawia się w {term_count} "
                        f"search terms, łączny koszt ${data['cost']:.2f}, "
                        f"0 konwersji"
                    ),
                    current_value=(
                        f"Cost: ${data['cost']:.2f}, Terms: {term_count}, "
                        f"Clicks: {data['clicks']}"
                    ),
                    recommended_action=(
                        "Dodaj jako broad match negative"
                    ),
                    estimated_impact=f"Save ~${data['cost']:.2f}",
                    metadata={
                        "ngram": ngram,
                        "cost": round(data["cost"], 2),
                        "term_count": term_count,
                        "clicks": data["clicks"],
                        "sample_terms": list(data["terms"])[:5],
                    },
                ))

        return recs


# Singleton instance
recommendations_engine = RecommendationsEngine()
