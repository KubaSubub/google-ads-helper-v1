"""Tests for GET /daily-audit/ — aggregated morning PPC audit view."""

from datetime import date, timedelta, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    Campaign, Client, MetricDaily, Keyword, AdGroup, Alert,
    Ad, SearchTerm, Recommendation,
)


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed a full audit scenario."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    client = Client(name="Audit Client", google_customer_id="8888888888")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="audit_c1",
        name="Search Audit",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=100_000_000,
        search_budget_lost_is=0.15,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="audit_ag1", name="Audit Group", status="ENABLED")
    db.add(ag)
    db.flush()

    # Keywords
    kw = Keyword(ad_group_id=ag.id, google_keyword_id="audit_kw1", text="buty", match_type="EXACT", status="ENABLED")
    db.add(kw)

    # MetricDaily for today and yesterday
    db.add(MetricDaily(campaign_id=campaign.id, date=today, clicks=50, impressions=500, cost_micros=25_000_000, conversions=3.0))
    db.add(MetricDaily(campaign_id=campaign.id, date=yesterday, clicks=40, impressions=400, cost_micros=20_000_000, conversions=2.0))

    # 30 days of metrics for budget pacing
    for i in range(2, 30):
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=today - timedelta(days=i),
            clicks=45, impressions=450, cost_micros=22_000_000, conversions=2.5,
        ))

    # Disapproved ad
    db.add(Ad(
        ad_group_id=ag.id, google_ad_id="audit_ad1",
        ad_type="RESPONSIVE_SEARCH_AD", status="ENABLED",
        approval_status="DISAPPROVED",
        headlines=[{"text": "Test Ad"}],
    ))

    # Alert (recent)
    db.add(Alert(
        client_id=client.id, campaign_id=campaign.id,
        alert_type="SPEND_SPIKE", severity="HIGH",
        title="Spend spike", description="50% increase",
    ))

    # Wasted search term
    db.add(SearchTerm(
        ad_group_id=ag.id, campaign_id=campaign.id,
        text="darmowe buty",
        clicks=10, impressions=200, cost_micros=8_000_000,
        conversions=0, ctr=5.0,
        date_from=week_ago, date_to=today,
    ))

    # Pending recommendation
    db.add(Recommendation(
        client_id=client.id, campaign_id=campaign.id,
        rule_id="PAUSE_LOW_QS",
        entity_type="keyword", entity_id="kw1",
        priority="HIGH", status="pending",
        reason="Low QS keyword",
        suggested_action="Pause keyword with QS < 3",
    ))

    db.commit()
    return client


class TestDailyAudit:
    def test_returns_200_with_all_sections(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert "budget_pacing" in data
        assert "anomalies_24h" in data
        assert "disapproved_ads" in data
        assert "budget_capped_performers" in data
        assert "search_terms_needing_action" in data
        assert "pending_recommendations" in data
        assert "health_summary" in data
        assert "kpi_snapshot" in data
        assert data["client_id"] == client.id

    def test_budget_pacing_has_campaign(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        assert len(data["budget_pacing"]) >= 1
        bp = data["budget_pacing"][0]
        assert "campaign_name" in bp
        assert "daily_budget" in bp
        assert "pacing_pct" in bp

    def test_disapproved_ads_found(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        assert len(data["disapproved_ads"]) >= 1
        assert data["disapproved_ads"][0]["approval_status"] == "DISAPPROVED"

    def test_anomalies_24h_found(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        assert len(data["anomalies_24h"]) >= 1

    def test_pending_recommendations(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        assert data["pending_recommendations"]["total_pending"] >= 1

    def test_kpi_snapshot_current_vs_previous(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        snap = data["kpi_snapshot"]
        # current_period = last 3 full days (yesterday-2..yesterday)
        # previous_period = 3 days before that
        assert snap["current_clicks"] > 0
        assert snap["previous_clicks"] > 0
        assert snap["period_days"] == 3

    def test_health_summary_has_score(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        data = resp.json()
        assert "health_score" in data["health_summary"]
        assert "total_enabled_keywords" in data["health_summary"]

    def test_empty_client(self, api_client, db):
        client = Client(name="Empty Audit", google_customer_id="0001")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/daily-audit/?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["budget_pacing"] == []
        assert data["kpi_snapshot"]["current_clicks"] == 0
