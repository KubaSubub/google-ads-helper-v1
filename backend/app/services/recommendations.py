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

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Keyword, SearchTerm, Ad, AdGroup, Campaign, MetricDaily
)


def _micros_to_usd(micros) -> float:
    """Convert micros (BigInteger) to USD float."""
    return (micros or 0) / 1_000_000


def _ctr_micros_to_pct(ctr_micros) -> float:
    """Convert CTR stored as micros (50000 = 5%) to percentage float."""
    return (ctr_micros or 0) / 10_000


class RecommendationType(str, Enum):
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    INCREASE_BID = "INCREASE_BID"
    DECREASE_BID = "DECREASE_BID"
    ADD_KEYWORD = "ADD_KEYWORD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    PAUSE_AD = "PAUSE_AD"
    REALLOCATE_BUDGET = "REALLOCATE_BUDGET"


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
        "r2_cvr_multiplier": 1.2,       # Rule 2: CVR must be > avg * this
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
    }

    # Words that indicate irrelevant intent
    IRRELEVANT_WORDS = [
        "free", "cheap", "how to", "why", "download", "torrent",
        "darmowe", "za darmo", "jak", "dlaczego", "pobierz",
        "praca", "job", "salary", "wynagrodzenie",
    ]

    def __init__(self, thresholds: dict = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    def generate_all(
        self,
        db: Session,
        client_id: int,
        days: int = 30,
    ) -> list[dict]:
        """Run all 7 rules and return a combined list of recommendations."""
        recommendations: list[Recommendation] = []

        recommendations.extend(self._rule_1_pause_keywords(db, client_id, days))
        recommendations.extend(self._rule_2_increase_bid(db, client_id, days))
        recommendations.extend(self._rule_3_decrease_bid(db, client_id, days))
        recommendations.extend(self._rule_4_add_keyword(db, client_id, days))
        recommendations.extend(self._rule_5_add_negative(db, client_id, days))
        recommendations.extend(self._rule_6_pause_ad(db, client_id, days))
        recommendations.extend(self._rule_7_reallocate_budget(db, client_id, days))

        # Sort by priority: HIGH first, then MEDIUM, then LOW
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 99))

        return [r.to_dict() for r in recommendations]

    # -----------------------------------------------------------------------
    # RULE 1: Pause Keyword (high spend, zero conversions)
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

            for kw in keywords:
                if (kw.clicks or 0) == 0 or (kw.conversions or 0) < 2:
                    continue
                kw_cvr = (kw.conversions / kw.clicks * 100)
                kw_cost = _micros_to_usd(kw.cost_micros)
                kw_cpa = (kw_cost / kw.conversions) if kw.conversions > 0 else 999999

                total_cost_usd = sum(_micros_to_usd(k.cost_micros) for k in keywords)
                avg_cpa = (total_cost_usd / total_conv) if total_conv > 0 else 999999

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

        for term in terms:
            if term.text.lower() in existing_keywords:
                continue

            total_clicks = term.total_clicks or 0
            total_conv = term.total_conv or 0
            total_cost = (term.total_cost_micros or 0) / 1_000_000
            cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0

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
                    recommended_action="Add as EXACT match keyword",
                    estimated_impact="Capture more of this high-converting traffic",
                    metadata={
                        "conversions": float(total_conv),
                        "cvr": round(cvr, 2),
                        "match_type": "EXACT",
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
                        recommended_action="Add as PHRASE match keyword",
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

            # Check 1: Irrelevant words
            text_lower = term.text.lower()
            matched_words = [w for w in self.IRRELEVANT_WORDS if w in text_lower]
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
            roas = (total_conv / total_cost * 100) if total_cost > 0 else 0

            campaign_roas.append({
                "campaign": campaign,
                "roas": roas,
                "cost": total_cost,
                "conversions": total_conv,
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
                    f"'{best['campaign'].name}' has ROAS {best['roas']:.0f}% vs "
                    f"'{worst['campaign'].name}' ROAS {worst['roas']:.0f}%. "
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


# Singleton instance
recommendations_engine = RecommendationsEngine()
