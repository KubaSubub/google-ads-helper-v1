"""Sprint 1 rule unit tests — R8 through R18, R19, R21.

Tests verify each rule's logic in isolation using the RecommendationsEngine
with a fresh in-memory SQLite DB per test.
"""

import pytest
from datetime import date, timedelta

from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.keyword_daily import KeywordDaily
from app.models.metric_daily import MetricDaily
from app.models.metric_segmented import MetricSegmented
from app.models.search_term import SearchTerm
from app.services.recommendations import RecommendationsEngine, RecommendationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_client_campaign_ag(db, *, campaign_type="SEARCH"):
    """Create minimal Client → Campaign → AdGroup chain, return (client, campaign, ag)."""
    client = Client(name="Test Client", google_customer_id="111-111-1111")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="gc1",
        name="Test Campaign",
        status="ENABLED",
        campaign_type=campaign_type,
        budget_micros=10_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="gag1",
        name="Test Ad Group",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    return client, campaign, ag


def _make_metric_daily(db, campaign, *, days_ago=5, **overrides):
    """Create a MetricDaily record for a campaign."""
    defaults = dict(
        campaign_id=campaign.id,
        date=date.today() - timedelta(days=days_ago),
        clicks=100,
        impressions=2000,
        cost_micros=50_000_000,
        conversions=5.0,
        conversion_value_micros=200_000_000,
        ctr=5.0,
    )
    defaults.update(overrides)
    m = MetricDaily(**defaults)
    db.add(m)
    db.flush()
    return m


def _make_keyword(db, ag, **overrides):
    """Create a keyword with sensible defaults, applying overrides."""
    defaults = dict(
        ad_group_id=ag.id,
        google_keyword_id="gkw1",
        text="test keyword",
        match_type="EXACT",
        status="ENABLED",
        clicks=10,
        impressions=500,
        cost_micros=5_000_000,
        conversions=1.0,
        ctr=2.0,
        quality_score=7,
    )
    defaults.update(overrides)
    kw = Keyword(**defaults)
    db.add(kw)
    db.flush()
    return kw


# ===========================================================================
# TASK 1.1: R8 — Quality Score Alert
# ===========================================================================

class TestR8QualityScoreAlert:
    """Handoff spec: QS < 5 AND impressions > 100 → QS_ALERT."""

    def test_qs3_impr500_generates_medium(self, db):
        """Keyword z QS=3, impr=500 → generuje QS_ALERT MEDIUM."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, quality_score=3, impressions=500,
                      historical_search_predicted_ctr=1,
                      historical_creative_quality=2,
                      historical_landing_page_quality=3)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_8_quality_score_alert(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.QS_ALERT
        assert recs[0].priority == "MEDIUM"
        assert recs[0].category == "ALERT"

    def test_qs1_impr200_generates_high(self, db):
        """Keyword z QS=1, impr=200 → generuje QS_ALERT HIGH."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, quality_score=1, impressions=200,
                      historical_search_predicted_ctr=1,
                      historical_creative_quality=1,
                      historical_landing_page_quality=1)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_8_quality_score_alert(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.QS_ALERT
        assert recs[0].priority == "HIGH"

    def test_qs7_no_alert(self, db):
        """Keyword z QS=7 → nie generuje alertu."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, quality_score=7, impressions=500)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_8_quality_score_alert(db, client.id, 30)

        assert len(recs) == 0

    def test_qs3_low_impressions_no_alert(self, db):
        """Keyword z QS=3, impr=50 → nie generuje alertu (za mało danych)."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, quality_score=3, impressions=50)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_8_quality_score_alert(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.2: R9 — Impression Share Lost to Budget
# ===========================================================================

class TestR9ISLostBudget:
    """Handoff spec: search_budget_lost_is > 0.20, conversions > 0 → IS_BUDGET_ALERT."""

    def test_lost_is_35_with_conv_generates_alert(self, db):
        """Kampania z search_budget_lost_is=0.35, conv>0 → IS_BUDGET_ALERT."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_budget_lost_is = 0.35
        # Need MetricDaily for snapshot
        _make_metric_daily(db, campaign, conversions=5.0, cost_micros=50_000_000,
                           conversion_value_micros=200_000_000)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_9_is_lost_budget(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.IS_BUDGET_ALERT

    def test_lost_is_below_threshold_no_alert(self, db):
        """search_budget_lost_is=0.10 (below 20%) → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_budget_lost_is = 0.10
        _make_metric_daily(db, campaign, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_9_is_lost_budget(db, client.id, 30)

        assert len(recs) == 0

    def test_no_is_data_no_alert(self, db):
        """Campaign with no search_budget_lost_is → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_budget_lost_is = None
        _make_metric_daily(db, campaign, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_9_is_lost_budget(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.3: R10 — IS Lost to Rank Alert
# ===========================================================================

class TestR10ISLostRank:
    """Handoff spec: search_rank_lost_is > 0.30, search_budget_lost_is < 0.10 → IS_RANK_ALERT."""

    def test_rank_lost_40_budget_lost_5_generates_alert(self, db):
        """rank_lost=40%, budget_lost=5% → IS_RANK_ALERT MEDIUM."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_rank_lost_is = 0.40
        campaign.search_budget_lost_is = 0.05
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_10_is_lost_rank(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.IS_RANK_ALERT
        assert recs[0].priority == "MEDIUM"
        assert recs[0].category == "ALERT"

    def test_rank_lost_20_no_alert(self, db):
        """rank_lost=20% (below 30% threshold) → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_rank_lost_is = 0.20
        campaign.search_budget_lost_is = 0.05
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_10_is_lost_rank(db, client.id, 30)

        assert len(recs) == 0

    def test_rank_lost_high_but_budget_lost_high_no_alert(self, db):
        """rank_lost=40% but budget_lost=15% → no alert (budget is the issue)."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.search_rank_lost_is = 0.40
        campaign.search_budget_lost_is = 0.15
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_10_is_lost_rank(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.4: R11 — Low CTR High Impressions (match type)
# ===========================================================================

class TestR11LowCTRHighImpr:
    """Handoff spec: CTR < 0.5%, impressions > 1000, conv=0, match_type BROAD/PHRASE → LOW_CTR_KEYWORD."""

    def test_low_ctr_broad_match_generates_alert(self, db):
        """CTR=0.2%, impr=2000, conv=0, BROAD → LOW_CTR_KEYWORD MEDIUM."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, ctr=0.2, impressions=2000, conversions=0.0,
                      match_type="BROAD")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_11_low_ctr_high_impr(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.LOW_CTR_KEYWORD
        assert recs[0].priority == "MEDIUM"
        assert recs[0].category == "RECOMMENDATION"

    def test_low_ctr_phrase_match_generates_alert(self, db):
        """CTR=0.3%, impr=1500, conv=0, PHRASE → LOW_CTR_KEYWORD."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, ctr=0.3, impressions=1500, conversions=0.0,
                      match_type="PHRASE")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_11_low_ctr_high_impr(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.LOW_CTR_KEYWORD

    def test_exact_match_not_flagged(self, db):
        """EXACT match type → not flagged by R11."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, ctr=0.2, impressions=2000, conversions=0.0,
                      match_type="EXACT")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_11_low_ctr_high_impr(db, client.id, 30)

        assert len(recs) == 0

    def test_has_conversions_not_flagged(self, db):
        """conv > 0 → not flagged."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, ctr=0.2, impressions=2000, conversions=1.0,
                      match_type="BROAD")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_11_low_ctr_high_impr(db, client.id, 30)

        assert len(recs) == 0

    def test_low_impressions_not_flagged(self, db):
        """impr=500 (below 1000 threshold) → not flagged."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, ctr=0.2, impressions=500, conversions=0.0,
                      match_type="BROAD")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_11_low_ctr_high_impr(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.5: R12 — Wasted Spend Alert (per-client)
# ===========================================================================

class TestR12WastedSpend:
    """Handoff spec: Per-client alert. wasted_pct > 25%, total_spend > $50."""

    def test_30pct_wasted_generates_medium(self, db):
        """30% wasted with $100 total → WASTED_SPEND_ALERT MEDIUM."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        # Keyword with spend but 0 conversions → wasted
        _make_keyword(db, ag, google_keyword_id="kw1", text="wasted kw",
                      cost_micros=30_000_000, conversions=0.0)
        # Keyword with spend and conversions → not wasted
        _make_keyword(db, ag, google_keyword_id="kw2", text="good kw",
                      cost_micros=70_000_000, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_12_wasted_spend_alert(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.WASTED_SPEND_ALERT
        assert recs[0].priority == "MEDIUM"
        assert recs[0].category == "ALERT"
        assert recs[0].entity_type == "client"

    def test_40pct_wasted_generates_high(self, db):
        """40% wasted → HIGH priority."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, google_keyword_id="kw1", text="wasted kw",
                      cost_micros=40_000_000, conversions=0.0)
        _make_keyword(db, ag, google_keyword_id="kw2", text="good kw",
                      cost_micros=60_000_000, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_12_wasted_spend_alert(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].priority == "HIGH"

    def test_below_25pct_no_alert(self, db):
        """20% wasted → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, google_keyword_id="kw1", text="wasted kw",
                      cost_micros=20_000_000, conversions=0.0)
        _make_keyword(db, ag, google_keyword_id="kw2", text="good kw",
                      cost_micros=80_000_000, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_12_wasted_spend_alert(db, client.id, 30)

        assert len(recs) == 0

    def test_below_50_spend_no_alert(self, db):
        """Total spend < $50 → no alert even if 50% wasted."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, google_keyword_id="kw1", text="wasted kw",
                      cost_micros=20_000_000, conversions=0.0)
        _make_keyword(db, ag, google_keyword_id="kw2", text="good kw",
                      cost_micros=20_000_000, conversions=5.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_12_wasted_spend_alert(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.6: R13 — PMax vs Search Cannibalization
# ===========================================================================

class TestR13PMaxCannibalization:
    """Handoff spec: Same search term in SEARCH and PMAX → PMAX_CANNIBALIZATION."""

    def _make_search_terms(self, db, campaign, ag, text, source, cost_micros):
        """Helper to create search terms."""
        st = SearchTerm(
            campaign_id=campaign.id,
            ad_group_id=ag.id if source == "SEARCH" else None,
            text=text,
            source=source,
            clicks=10,
            impressions=100,
            cost_micros=cost_micros,
            conversions=0.0,
            date_from=date.today() - timedelta(days=30),
            date_to=date.today(),
        )
        db.add(st)
        db.flush()
        return st

    def test_overlap_generates_alert(self, db):
        """Same term in Search and PMax with PMax spend → PMAX_CANNIBALIZATION."""
        client, search_camp, ag = _seed_client_campaign_ag(db, campaign_type="SEARCH")
        pmax_camp = Campaign(
            client_id=client.id,
            google_campaign_id="gc_pmax",
            name="PMax Campaign",
            status="ENABLED",
            campaign_type="PERFORMANCE_MAX",
            budget_micros=10_000_000,
        )
        db.add(pmax_camp)
        db.flush()

        self._make_search_terms(db, search_camp, ag, "buty sportowe", "SEARCH", 30_000_000)
        self._make_search_terms(db, pmax_camp, None, "buty sportowe", "PMAX", 60_000_000)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_13_pmax_search_overlap(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.PMAX_CANNIBALIZATION
        assert recs[0].category == "ALERT"

    def test_no_overlap_no_alert(self, db):
        """Different terms in Search and PMax → no alert."""
        client, search_camp, ag = _seed_client_campaign_ag(db, campaign_type="SEARCH")
        pmax_camp = Campaign(
            client_id=client.id,
            google_campaign_id="gc_pmax",
            name="PMax Campaign",
            status="ENABLED",
            campaign_type="PERFORMANCE_MAX",
            budget_micros=10_000_000,
        )
        db.add(pmax_camp)
        db.flush()

        self._make_search_terms(db, search_camp, ag, "buty sportowe", "SEARCH", 30_000_000)
        self._make_search_terms(db, pmax_camp, None, "kurtki zimowe", "PMAX", 60_000_000)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_13_pmax_search_overlap(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.7: R15 — Device Anomaly Alert
# ===========================================================================

class TestR15DeviceAnomaly:
    """Handoff spec: Mobile CPA > 2x desktop CPA, spend > $100 → DEVICE_ANOMALY."""

    def test_mobile_cpa_2x_generates_alert(self, db):
        """Mobile CPA 3x desktop CPA with $150 spend → DEVICE_ANOMALY."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        recent = date.today() - timedelta(days=5)

        # Desktop: $100 spend, 10 conversions → CPA = $10
        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, device="COMPUTER",
                               cost_micros=100_000_000, conversions=10.0, clicks=200, impressions=1000))
        # Mobile: $150 spend, 5 conversions → CPA = $30 (3x desktop)
        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, device="MOBILE",
                               cost_micros=150_000_000, conversions=5.0, clicks=300, impressions=2000))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_15_device_anomaly(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.DEVICE_ANOMALY
        assert recs[0].category == "ALERT"

    def test_similar_cpa_no_alert(self, db):
        """Mobile CPA similar to desktop → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        recent = date.today() - timedelta(days=5)

        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, device="COMPUTER",
                               cost_micros=100_000_000, conversions=10.0, clicks=200, impressions=1000))
        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, device="MOBILE",
                               cost_micros=120_000_000, conversions=10.0, clicks=300, impressions=2000))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_15_device_anomaly(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.7: R16 — Geo Anomaly Alert
# ===========================================================================

class TestR16GeoAnomaly:
    """Handoff spec: Geo CPA > 2x campaign avg CPA → GEO_ANOMALY."""

    def test_high_cpa_city_generates_alert(self, db):
        """City with CPA 3x average → GEO_ANOMALY."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        recent = date.today() - timedelta(days=5)

        # Warszawa: $100 spend, 10 conv → CPA=$10
        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, geo_city="Warszawa",
                               cost_micros=100_000_000, conversions=10.0, clicks=200))
        # Kraków: $90 spend, 3 conv → CPA=$30 (3x avg)
        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, geo_city="Kraków",
                               cost_micros=90_000_000, conversions=3.0, clicks=100))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_16_geo_anomaly(db, client.id, 30)

        # avg CPA ~$14.6, Kraków CPA=$30 > $14.6*2 = $29.2 → alert
        assert len(recs) == 1
        assert recs[0].type == RecommendationType.GEO_ANOMALY
        assert recs[0].category == "ALERT"

    def test_no_conversions_no_alert(self, db):
        """No conversions → no CPA comparison possible → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        recent = date.today() - timedelta(days=5)

        db.add(MetricSegmented(campaign_id=campaign.id, date=recent, geo_city="Warszawa",
                               cost_micros=100_000_000, conversions=0.0, clicks=200))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_16_geo_anomaly(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.8: R17 — Budget Pacing Alert
# ===========================================================================

class TestR17BudgetPacing:
    """Handoff spec: Budget pacing — overspend or underspend alert."""

    def test_overspend_generates_high(self, db):
        """Spending 2x expected → BUDGET_PACING HIGH."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.budget_micros = 10_000_000  # $10/day

        # Add daily metric with high spend for this month
        month_start = date.today().replace(day=1)
        days_elapsed = (date.today() - month_start).days + 1

        # Total expected at this point: $10 * days_elapsed
        # Overspend: 2x expected
        overspend_total_micros = int(10_000_000 * days_elapsed * 2)
        for day_offset in range(days_elapsed):
            d = month_start + timedelta(days=day_offset)
            db.add(MetricDaily(
                campaign_id=campaign.id, date=d,
                cost_micros=overspend_total_micros // days_elapsed,
                clicks=50, impressions=500, conversions=2.0,
            ))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_17_budget_pacing(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.BUDGET_PACING
        assert recs[0].priority == "HIGH"
        assert recs[0].category == "ALERT"

    def test_normal_pacing_no_alert(self, db):
        """Spending at expected rate → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.budget_micros = 10_000_000  # $10/day

        month_start = date.today().replace(day=1)
        days_elapsed = (date.today() - month_start).days + 1

        for day_offset in range(days_elapsed):
            d = month_start + timedelta(days=day_offset)
            db.add(MetricDaily(
                campaign_id=campaign.id, date=d,
                cost_micros=10_000_000,  # exactly $10/day
                clicks=50, impressions=500, conversions=2.0,
            ))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_17_budget_pacing(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.9: R18 — N-gram Negative Detection
# ===========================================================================

class TestR18NgramNegative:
    """Handoff spec: N-gram with $100+ spend, 0 conversions, 3+ terms → NGRAM_NEGATIVE."""

    def test_expensive_ngram_generates_alert(self, db):
        """N-gram 'darmowe' in 4 terms, $200 total, 0 conv → NGRAM_NEGATIVE HIGH."""
        client, campaign, ag = _seed_client_campaign_ag(db)

        terms = [
            "darmowe buty", "darmowe kurtki", "darmowe spodnie", "darmowe czapki"
        ]
        for i, text in enumerate(terms):
            db.add(SearchTerm(
                campaign_id=campaign.id,
                ad_group_id=ag.id,
                text=text,
                source="SEARCH",
                clicks=20,
                impressions=200,
                cost_micros=50_000_000,  # $50 each → $200 total for ngram
                conversions=0.0,
                date_from=date.today() - timedelta(days=30),
                date_to=date.today(),
            ))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_18_ngram_negative(db, client.id, 30)

        ngram_recs = [r for r in recs if r.entity_name == "darmowe"]
        assert len(ngram_recs) == 1
        assert ngram_recs[0].type == RecommendationType.NGRAM_NEGATIVE
        assert ngram_recs[0].priority == "HIGH"

    def test_ngram_with_conversions_no_alert(self, db):
        """N-gram with conversions → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)

        terms = ["buty sportowe", "buty zimowe", "buty do biegania"]
        for text in terms:
            db.add(SearchTerm(
                campaign_id=campaign.id,
                ad_group_id=ag.id,
                text=text,
                source="SEARCH",
                clicks=20,
                impressions=200,
                cost_micros=50_000_000,
                conversions=2.0,  # has conversions
                date_from=date.today() - timedelta(days=30),
                date_to=date.today(),
            ))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_18_ngram_negative(db, client.id, 30)

        buty_recs = [r for r in recs if r.entity_name == "buty"]
        assert len(buty_recs) == 0

    def test_ngram_few_terms_no_alert(self, db):
        """N-gram in only 2 terms (below 3 threshold) → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)

        for text in ["darmowe buty", "darmowe kurtki"]:
            db.add(SearchTerm(
                campaign_id=campaign.id,
                ad_group_id=ag.id,
                text=text,
                source="SEARCH",
                clicks=20,
                impressions=200,
                cost_micros=60_000_000,
                conversions=0.0,
                date_from=date.today() - timedelta(days=30),
                date_to=date.today(),
            ))
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_18_ngram_negative(db, client.id, 30)

        ngram_recs = [r for r in recs if r.entity_name == "darmowe"]
        assert len(ngram_recs) == 0


# ===========================================================================
# TASK 1.11: R21 (GAP 1B) — Smart Bidding Data Starvation
# ===========================================================================

class TestR21SmartBiddingDataStarvation:
    """Handoff spec: Smart Bidding with < 50 conv/30d → SMART_BIDDING_DATA_STARVATION."""

    def test_low_conv_tcpa_generates_high(self, db):
        """TARGET_CPA with 10 conversions → SMART_BIDDING_DATA_STARVATION HIGH."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.bidding_strategy = "TARGET_CPA"
        # Add MetricDaily with low conversions
        for i in range(10):
            _make_metric_daily(db, campaign, days_ago=i+1, conversions=1.0,
                               cost_micros=10_000_000)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_21_smart_bidding_conv_threshold(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.SMART_BIDDING_DATA_STARVATION
        assert recs[0].priority == "HIGH"
        assert recs[0].category == "ALERT"

    def test_sufficient_conv_no_alert(self, db):
        """TARGET_CPA with 50 conversions → no alert."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.bidding_strategy = "TARGET_CPA"
        for i in range(30):
            _make_metric_daily(db, campaign, days_ago=i+1, conversions=2.0,
                               cost_micros=10_000_000)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_21_smart_bidding_conv_threshold(db, client.id, 30)

        assert len(recs) == 0

    def test_manual_cpc_not_flagged(self, db):
        """MANUAL_CPC strategy → not flagged."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        campaign.bidding_strategy = "MANUAL_CPC"
        _make_metric_daily(db, campaign, conversions=1.0)
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_21_smart_bidding_conv_threshold(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 1.12: R19 (GAP 8) — Ad Group Health Alerts
# ===========================================================================

class TestR19AdGroupHealth:
    """Handoff spec: Separate alerts for single ad, oversized ag, zero conv ag."""

    def test_single_ad_generates_alert(self, db):
        """Ad group with 1 active ad → SINGLE_AD_ALERT LOW."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        # Add 1 ad
        db.add(Ad(ad_group_id=ag.id, google_ad_id="gad1", ad_type="RSA", status="ENABLED"))
        # Add 2 keywords
        _make_keyword(db, ag, google_keyword_id="kw1", text="kw1")
        _make_keyword(db, ag, google_keyword_id="kw2", text="kw2")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_19_ad_group_health(db, client.id, 30)

        single_ad_recs = [r for r in recs if r.type == RecommendationType.SINGLE_AD_ALERT]
        assert len(single_ad_recs) == 1
        assert single_ad_recs[0].priority == "LOW"
        assert single_ad_recs[0].category == "ALERT"

    def test_no_ads_generates_high(self, db):
        """Ad group with 0 ads → SINGLE_AD_ALERT HIGH."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        _make_keyword(db, ag, google_keyword_id="kw1", text="kw1")
        _make_keyword(db, ag, google_keyword_id="kw2", text="kw2")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_19_ad_group_health(db, client.id, 30)

        single_ad_recs = [r for r in recs if r.type == RecommendationType.SINGLE_AD_ALERT]
        assert len(single_ad_recs) == 1
        assert single_ad_recs[0].priority == "HIGH"

    def test_oversized_ad_group_generates_alert(self, db):
        """Ad group with 35 keywords → OVERSIZED_AD_GROUP LOW."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        # Add 2 ads (good)
        db.add(Ad(ad_group_id=ag.id, google_ad_id="gad1", ad_type="RSA", status="ENABLED"))
        db.add(Ad(ad_group_id=ag.id, google_ad_id="gad2", ad_type="RSA", status="ENABLED"))
        # Add 35 keywords (too many)
        for i in range(35):
            _make_keyword(db, ag, google_keyword_id=f"kw{i}", text=f"keyword {i}")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_19_ad_group_health(db, client.id, 30)

        oversized_recs = [r for r in recs if r.type == RecommendationType.OVERSIZED_AD_GROUP]
        assert len(oversized_recs) == 1
        assert oversized_recs[0].priority == "LOW"

    def test_healthy_ad_group_no_alert(self, db):
        """Ad group with 2 ads, 10 keywords → no alerts."""
        client, campaign, ag = _seed_client_campaign_ag(db)
        db.add(Ad(ad_group_id=ag.id, google_ad_id="gad1", ad_type="RSA", status="ENABLED"))
        db.add(Ad(ad_group_id=ag.id, google_ad_id="gad2", ad_type="RSA", status="ENABLED"))
        for i in range(10):
            _make_keyword(db, ag, google_keyword_id=f"kw{i}", text=f"keyword {i}")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_19_ad_group_health(db, client.id, 30)

        assert len(recs) == 0
