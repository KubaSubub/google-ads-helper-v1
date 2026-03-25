"""Sprint 3 tests — Bid Strategy Health, Learning Period, ECPC Deprecation.

Tests verify target-vs-actual analysis, ECPC deprecation rule, and learning period rule.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.metric_daily import MetricDaily
from app.services.analytics_service import AnalyticsService
from app.services.recommendations import RecommendationsEngine, RecommendationType


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_base(db, **camp_overrides):
    """Create client + campaign."""
    client = Client(name="Sprint3 Client", google_customer_id="555-555-5555")
    db.add(client)
    db.flush()

    defaults = dict(
        client_id=client.id,
        google_campaign_id="s3c1",
        name="Smart Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=50_000_000,
        bidding_strategy="TARGET_CPA",
    )
    defaults.update(camp_overrides)
    campaign = Campaign(**defaults)
    db.add(campaign)
    db.flush()

    return client, campaign


# ===========================================================================
# TASK 3.1: Campaign model already has target_cpa_micros, target_roas
# ===========================================================================

class TestCampaignTargetFields:
    """Verify campaign model has target fields for Smart Bidding."""

    def test_target_cpa_micros_exists(self, db):
        client, campaign = _seed_base(db, target_cpa_micros=15_000_000)
        db.commit()
        loaded = db.get(Campaign, campaign.id)
        assert loaded.target_cpa_micros == 15_000_000

    def test_target_roas_exists(self, db):
        client, campaign = _seed_base(db, target_roas=3.5, bidding_strategy="TARGET_ROAS")
        db.commit()
        loaded = db.get(Campaign, campaign.id)
        assert loaded.target_roas == 3.5


# ===========================================================================
# TASK 3.2: GAP 10 — Bid Strategy Target vs. Actual
# ===========================================================================

class TestTargetVsActual:
    """Handoff: per campaign with Smart Bidding → compare target CPA/ROAS to actual."""

    def test_over_target_cpa(self, db):
        """Actual CPA significantly above target → OVER_TARGET."""
        client, campaign = _seed_base(db, target_cpa_micros=10_000_000)  # $10 target
        # Actual: $200 cost / 5 conv = $40 CPA → way over $10 target
        for i in range(10):
            db.add(MetricDaily(
                campaign_id=campaign.id,
                date=date.today() - timedelta(days=i+1),
                clicks=50, impressions=1000,
                cost_micros=20_000_000,
                conversions=0.5,
                conversion_value_micros=50_000_000,
            ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_target_vs_actual(client.id, days=30)

        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["status"] == "OVER_TARGET"
        assert item["target_cpa_usd"] == 10.0
        assert item["actual_cpa_usd"] > 10.0

    def test_on_target(self, db):
        """Actual CPA close to target → ON_TARGET."""
        client, campaign = _seed_base(db, target_cpa_micros=20_000_000)  # $20 target
        # Actual: $200 cost / 10 conv = $20 CPA → on target
        for i in range(10):
            db.add(MetricDaily(
                campaign_id=campaign.id,
                date=date.today() - timedelta(days=i+1),
                clicks=50, impressions=1000,
                cost_micros=20_000_000,
                conversions=1.0,
                conversion_value_micros=50_000_000,
            ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_target_vs_actual(client.id, days=30)

        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "ON_TARGET"

    def test_manual_cpc_excluded(self, db):
        """Manual CPC campaign → not in results."""
        client, campaign = _seed_base(db, bidding_strategy="MANUAL_CPC")
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=date.today() - timedelta(days=5),
            clicks=50, impressions=1000, cost_micros=20_000_000,
            conversions=5.0,
        ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_target_vs_actual(client.id, days=30)

        assert len(result["items"]) == 0

    def test_endpoint_returns_200(self, api_client, db):
        """GET /analytics/target-vs-actual → 200."""
        client, _ = _seed_base(db)
        db.commit()

        resp = api_client.get("/api/v1/analytics/target-vs-actual", params={"client_id": client.id})
        assert resp.status_code == 200


# ===========================================================================
# TASK 3.3: GAP 1C — ECPC Deprecation Alert
# ===========================================================================

class TestECPCDeprecation:
    """Handoff: campaigns with ENHANCED_CPC → ECPC_DEPRECATION HIGH."""

    def test_ecpc_campaign_generates_alert(self, db):
        """Campaign with ENHANCED_CPC → ECPC_DEPRECATION HIGH."""
        client, campaign = _seed_base(db, bidding_strategy="ENHANCED_CPC")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_22_ecpc_deprecation(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.ECPC_DEPRECATION
        assert recs[0].priority == "HIGH"
        assert recs[0].category == "ALERT"

    def test_target_cpa_not_flagged(self, db):
        """Campaign with TARGET_CPA → not flagged."""
        client, campaign = _seed_base(db, bidding_strategy="TARGET_CPA")
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_22_ecpc_deprecation(db, client.id, 30)

        assert len(recs) == 0


# ===========================================================================
# TASK 3.3: GAP 1A — Learning Period Alert
# ===========================================================================

class TestLearningPeriod:
    """Handoff: Smart Bidding campaigns stuck in learning → LEARNING_PERIOD_ALERT."""

    def test_learning_status_with_reasons(self, db):
        """Campaign with LEARNING in primary_status_reasons → LEARNING_PERIOD_ALERT."""
        import json
        client, campaign = _seed_base(
            db,
            bidding_strategy="TARGET_CPA",
            primary_status="LEARNING",
            primary_status_reasons=json.dumps(["CAMPAIGN_BIDDING_STRATEGY_LEARNING"]),
        )
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_25_learning_period(db, client.id, 30)

        assert len(recs) == 1
        assert recs[0].type == RecommendationType.LEARNING_PERIOD_ALERT

    def test_no_learning_status_no_alert(self, db):
        """Campaign without LEARNING in reasons → no alert."""
        client, campaign = _seed_base(
            db,
            bidding_strategy="TARGET_CPA",
            primary_status="ELIGIBLE",
            primary_status_reasons=None,
        )
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_25_learning_period(db, client.id, 30)

        assert len(recs) == 0

    def test_manual_cpc_not_checked(self, db):
        """MANUAL_CPC campaign → not checked for learning."""
        import json
        client, campaign = _seed_base(
            db,
            bidding_strategy="MANUAL_CPC",
            primary_status_reasons=json.dumps(["CAMPAIGN_BIDDING_STRATEGY_LEARNING"]),
        )
        db.commit()

        engine = RecommendationsEngine()
        recs = engine._rule_25_learning_period(db, client.id, 30)

        assert len(recs) == 0
