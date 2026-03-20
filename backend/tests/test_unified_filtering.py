"""Integration tests for unified filtering — date_from/date_to + campaign_type/campaign_status on endpoints."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, MetricDaily, AdGroup, Keyword, SearchTerm, MetricSegmented


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed client with SEARCH + DISPLAY campaigns and date-ranged metrics."""
    today = date.today()
    client = Client(name="Filter Integration", google_customer_id="5555555555")
    db.add(client)
    db.flush()

    # Two campaigns: SEARCH (ENABLED) and DISPLAY (PAUSED)
    search_camp = Campaign(
        client_id=client.id, google_campaign_id="uf_s1", name="Search Camp",
        status="ENABLED", campaign_type="SEARCH", budget_micros=30_000_000,
    )
    display_camp = Campaign(
        client_id=client.id, google_campaign_id="uf_d1", name="Display Camp",
        status="PAUSED", campaign_type="DISPLAY", budget_micros=20_000_000,
    )
    db.add_all([search_camp, display_camp])
    db.flush()

    ag = AdGroup(campaign_id=search_camp.id, google_ad_group_id="uf_ag1", name="UF Group", status="ENABLED")
    db.add(ag)
    db.flush()

    kw = Keyword(ad_group_id=ag.id, google_keyword_id="uf_kw1", text="test keyword",
                 match_type="EXACT", status="ENABLED", quality_score=7)
    db.add(kw)

    st = SearchTerm(
        ad_group_id=ag.id, campaign_id=search_camp.id, text="test search term",
        clicks=20, impressions=200, cost_micros=2_000_000, conversions=1.0, ctr=10.0,
        date_from=today - timedelta(days=14), date_to=today,
    )
    db.add(st)

    # Metrics for both campaigns — 30 days
    for camp in [search_camp, display_camp]:
        for i in range(30):
            d = today - timedelta(days=i)
            db.add(MetricDaily(
                campaign_id=camp.id, date=d,
                clicks=50 + i, impressions=500 + i * 10,
                cost_micros=3_000_000 + i * 50_000,
                conversions=1.5, conversion_value_micros=10_000_000,
            ))

    # Segmented metrics for device
    for device in ["MOBILE", "DESKTOP"]:
        db.add(MetricSegmented(
            campaign_id=search_camp.id, date=today,
            device=device, clicks=25, impressions=250,
            cost_micros=1_500_000, conversions=0.5,
        ))

    db.commit()
    return client, search_camp, display_camp


class TestDashboardKPIsFiltering:
    def test_date_from_date_to_override_days(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/dashboard-kpis?client_id={client.id}"
            f"&date_from={today - timedelta(days=7)}&date_to={today}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert data["current"]["clicks"] > 0

    def test_campaign_type_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp_search = api_client.get(
            f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&campaign_type=SEARCH&days=7"
        )
        resp_all = api_client.get(
            f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&campaign_type=ALL&days=7"
        )
        assert resp_search.status_code == 200
        assert resp_all.status_code == 200
        # SEARCH-only should have less or equal clicks than ALL
        assert resp_search.json()["current"]["clicks"] <= resp_all.json()["current"]["clicks"]

    def test_campaign_status_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&campaign_status=PAUSED&days=7"
        )
        assert resp.status_code == 200
        # Only PAUSED campaign (Display) should be included
        assert resp.json()["current"]["clicks"] > 0

    def test_status_alias_backward_compat(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&status=ENABLED&days=7"
        )
        assert resp.status_code == 200


class TestTrendsFiltering:
    def test_date_range_params(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/trends?client_id={client.id}"
            f"&metrics=cost&date_from={today - timedelta(days=7)}&date_to={today}"
        )
        assert resp.status_code == 200

    def test_campaign_type_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/trends?client_id={client.id}&metrics=clicks"
            f"&campaign_type=SEARCH&campaign_status=ENABLED&days=14"
        )
        assert resp.status_code == 200


class TestCampaignKPIsFiltering:
    def test_date_range_overrides_days(self, api_client, db):
        client, campaign, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/campaigns/{campaign.id}/kpis"
            f"?date_from={today - timedelta(days=7)}&date_to={today}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert "previous" in data


class TestHealthScoreFiltering:
    def test_with_campaign_type(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/health-score?client_id={client.id}&campaign_type=SEARCH"
        )
        assert resp.status_code == 200
        assert "score" in resp.json()


class TestDeviceBreakdownFiltering:
    def test_with_all_filter_params(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/device-breakdown?client_id={client.id}"
            f"&date_from={today - timedelta(days=7)}&date_to={today}"
            f"&campaign_type=SEARCH&campaign_status=ENABLED"
        )
        assert resp.status_code == 200


class TestSearchOptFiltering:
    def test_dayparting_with_filters(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/dayparting?client_id={client.id}"
            f"&date_from={today - timedelta(days=14)}&date_to={today}"
            f"&campaign_type=SEARCH"
        )
        assert resp.status_code == 200

    def test_wasted_spend_with_filters(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/wasted-spend?client_id={client.id}"
            f"&campaign_type=SEARCH&campaign_status=ENABLED&days=14"
        )
        assert resp.status_code == 200

    def test_match_type_with_date_range(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/match-type-analysis?client_id={client.id}"
            f"&date_from={today - timedelta(days=14)}&date_to={today}"
        )
        assert resp.status_code == 200

    def test_rsa_with_campaign_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/rsa-analysis?client_id={client.id}&campaign_type=SEARCH"
        )
        assert resp.status_code == 200

    def test_ngram_with_campaign_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/ngram-analysis?client_id={client.id}"
            f"&campaign_type=SEARCH&campaign_status=ENABLED"
        )
        assert resp.status_code == 200

    def test_landing_pages_with_filters(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/landing-pages?client_id={client.id}"
            f"&campaign_type=SEARCH&days=14"
        )
        assert resp.status_code == 200

    def test_bidding_advisor_with_filters(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/bidding-advisor?client_id={client.id}"
            f"&campaign_type=SEARCH&campaign_status=ENABLED&days=14"
        )
        assert resp.status_code == 200

    def test_hourly_dayparting_with_filters(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/hourly-dayparting?client_id={client.id}"
            f"&campaign_type=SEARCH&days=7"
        )
        assert resp.status_code == 200


class TestRecommendationsFiltering:
    def test_date_range_params(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/recommendations/?client_id={client.id}"
            f"&date_from={today - timedelta(days=14)}&date_to={today}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_summary_with_date_range(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/recommendations/summary?client_id={client.id}"
            f"&date_from={today - timedelta(days=7)}&date_to={today}"
        )
        assert resp.status_code == 200
        assert "total" in resp.json()


class TestImpressionShareFiltering:
    def test_with_campaign_filter(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/impression-share?client_id={client.id}"
            f"&campaign_type=SEARCH&campaign_status=ENABLED&days=14"
        )
        assert resp.status_code == 200


class TestGeoBreakdownFiltering:
    def test_with_all_params(self, api_client, db):
        client, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/analytics/geo-breakdown?client_id={client.id}"
            f"&date_from={today - timedelta(days=7)}&date_to={today}"
            f"&campaign_type=SEARCH&limit=10"
        )
        assert resp.status_code == 200


class TestBudgetPacingFiltering:
    def test_with_campaign_type(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/budget-pacing?client_id={client.id}&campaign_type=SEARCH"
        )
        assert resp.status_code == 200

    def test_with_campaign_status(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(
            f"/api/v1/analytics/budget-pacing?client_id={client.id}&campaign_status=ENABLED"
        )
        assert resp.status_code == 200
