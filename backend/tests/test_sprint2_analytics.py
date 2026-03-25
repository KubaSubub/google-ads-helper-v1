"""Sprint 2 tests — Post-Change Performance Delta (GAP 6A) and Pareto 80/20 (GAP 7).

Tests verify the analytics service methods and API endpoints.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.action_log import ActionLog
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.metric_daily import MetricDaily
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_base(db):
    """Create client + campaign + ad group."""
    client = Client(name="Sprint2 Client", google_customer_id="222-222-2222")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="s2c1",
        name="Campaign Alpha",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=10_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="s2ag1",
        name="AG Alpha",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    return client, campaign, ag


# ===========================================================================
# TASK 2.1: GAP 6A — Post-Change Performance Delta
# ===========================================================================

class TestChangeImpact:
    """Handoff tests: action 14d ago has before/after, action 3d ago → data_available=false,
    action for nonexistent campaign → no crash."""

    def test_action_14d_ago_has_before_after(self, db):
        """Action executed 14 days ago → has both pre and post metrics."""
        client, campaign, ag = _seed_base(db)

        action_date = date.today() - timedelta(days=14)
        action = ActionLog(
            client_id=client.id,
            action_type="PAUSE_KEYWORD",
            entity_type="campaign",
            entity_id=str(campaign.id),
            status="SUCCESS",
            executed_at=datetime(action_date.year, action_date.month, action_date.day),
        )
        db.add(action)

        # Add metrics before action (days -21 to -15)
        for i in range(7):
            d = action_date - timedelta(days=7-i)
            db.add(MetricDaily(
                campaign_id=campaign.id, date=d,
                clicks=50, impressions=1000, cost_micros=20_000_000,
                conversions=3.0, conversion_value_micros=100_000_000,
            ))
        # Add metrics after action (days -13 to -7)
        for i in range(7):
            d = action_date + timedelta(days=1+i)
            db.add(MetricDaily(
                campaign_id=campaign.id, date=d,
                clicks=60, impressions=1200, cost_micros=18_000_000,
                conversions=5.0, conversion_value_micros=150_000_000,
            ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_change_impact_analysis(client.id, days=60)

        assert result["summary"]["total"] >= 1
        change = result["changes"][0]
        assert change["pre_metrics"] is not None
        assert change["post_metrics"] is not None
        assert "cost_usd_pct" in change["delta"]
        assert change["impact"] in ("POSITIVE", "NEGATIVE", "NEUTRAL")

    def test_action_3d_ago_skipped_or_partial(self, db):
        """Action 3 days ago → post window incomplete, action may be skipped."""
        client, campaign, ag = _seed_base(db)

        action_date = date.today() - timedelta(days=3)
        action = ActionLog(
            client_id=client.id,
            action_type="INCREASE_BID",
            entity_type="campaign",
            entity_id=str(campaign.id),
            status="SUCCESS",
            executed_at=datetime(action_date.year, action_date.month, action_date.day),
        )
        db.add(action)

        # Only pre-action metrics
        for i in range(7):
            d = action_date - timedelta(days=7-i)
            db.add(MetricDaily(
                campaign_id=campaign.id, date=d,
                clicks=50, impressions=1000, cost_micros=20_000_000,
                conversions=3.0,
            ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_change_impact_analysis(client.id, days=60)

        # Either skipped entirely or has partial data — should not crash
        assert "changes" in result
        assert "summary" in result

    def test_nonexistent_campaign_no_crash(self, db):
        """Action for entity_id that doesn't match any campaign → no crash."""
        client, campaign, ag = _seed_base(db)

        action = ActionLog(
            client_id=client.id,
            action_type="PAUSE_KEYWORD",
            entity_type="campaign",
            entity_id="999999",  # doesn't exist
            status="SUCCESS",
            executed_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14),
        )
        db.add(action)
        db.commit()

        service = AnalyticsService(db)
        result = service.get_change_impact_analysis(client.id, days=60)

        # Should not crash, just skip or return empty
        assert "changes" in result

    def test_endpoint_returns_200(self, api_client, db):
        """GET /analytics/change-impact → 200."""
        client, _, _ = _seed_base(db)
        db.commit()

        resp = api_client.get("/api/v1/analytics/change-impact", params={"client_id": client.id})
        assert resp.status_code == 200
        data = resp.json()
        assert "changes" in data
        assert "summary" in data


# ===========================================================================
# TASK 2.2: GAP 7 — Pareto / 80-20 View
# ===========================================================================

class TestParetoAnalysis:
    """Handoff tests: 5 campaigns → HERO/TAIL flags, no conversions → graceful empty."""

    def test_5_campaigns_pareto_flags(self, db):
        """5 campaigns with varied value → top gets HERO, bottom get TAIL."""
        client = Client(name="Pareto Client", google_customer_id="333-333-3333")
        db.add(client)
        db.flush()

        values = [500, 200, 150, 100, 50]  # conv_value in USD
        for i, val in enumerate(values):
            camp = Campaign(
                client_id=client.id,
                google_campaign_id=f"pc{i}",
                name=f"Campaign {i}",
                status="ENABLED",
                campaign_type="SEARCH",
                budget_micros=10_000_000,
            )
            db.add(camp)
            db.flush()

            db.add(MetricDaily(
                campaign_id=camp.id,
                date=date.today() - timedelta(days=5),
                clicks=100,
                impressions=2000,
                cost_micros=50_000_000,
                conversions=10.0,
                conversion_value_micros=val * 1_000_000,
            ))
        db.commit()

        service = AnalyticsService(db)
        result = service.get_pareto_analysis(client.id, days=30)

        items = result["campaign_pareto"]["items"]
        assert len(items) == 5

        # First item should be HERO (highest value)
        assert items[0]["tag"] == "HERO"
        assert items[0]["conv_value_usd"] == 500.0

        # At least some TAIL items should exist
        tags = [it["tag"] for it in items]
        assert "HERO" in tags
        assert "TAIL" in tags

    def test_no_conversions_graceful_empty(self, db):
        """Client with no metric data → graceful empty response."""
        client = Client(name="Empty Client", google_customer_id="444-444-4444")
        db.add(client)
        db.flush()

        camp = Campaign(
            client_id=client.id,
            google_campaign_id="ec1",
            name="Empty Campaign",
            status="ENABLED",
            campaign_type="SEARCH",
            budget_micros=10_000_000,
        )
        db.add(camp)
        db.commit()

        service = AnalyticsService(db)
        result = service.get_pareto_analysis(client.id, days=30)

        assert result["campaign_pareto"]["total_campaigns"] == 0
        assert result["campaign_pareto"]["items"] == []

    def test_endpoint_returns_200(self, api_client, db):
        """GET /analytics/pareto-analysis → 200."""
        client, _, _ = _seed_base(db)
        db.commit()

        resp = api_client.get("/api/v1/analytics/pareto-analysis", params={"client_id": client.id})
        assert resp.status_code == 200
        data = resp.json()
        assert "campaign_pareto" in data
