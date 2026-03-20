"""Tests for campaigns and clients CRUD endpoints, plus ad-groups, ads, recommendations summary, bulk-preview."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, AdGroup, Ad, Keyword, SearchTerm, MetricDaily


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed client with campaign, ad group, ad, keyword, search term, metrics."""
    today = date.today()
    client = Client(name="CRUD Test Client", google_customer_id="7777777777")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id, google_campaign_id="crud_c1", name="CRUD Campaign",
        status="ENABLED", campaign_type="SEARCH", budget_micros=50_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="crud_ag1", name="CRUD Group", status="ENABLED")
    db.add(ag)
    db.flush()

    ad = Ad(
        ad_group_id=ag.id, google_ad_id="crud_ad1", ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED", headlines=[{"text": "Test"}], descriptions=[{"text": "Desc"}],
        clicks=10, impressions=100, cost_micros=1_000_000, conversions=1.0,
    )
    db.add(ad)

    kw = Keyword(
        ad_group_id=ag.id, google_keyword_id="crud_kw1", text="test keyword",
        match_type="EXACT", status="ENABLED", quality_score=7,
    )
    db.add(kw)

    st = SearchTerm(
        ad_group_id=ag.id, campaign_id=campaign.id, text="test search",
        clicks=5, impressions=50, cost_micros=500_000, conversions=0.5, ctr=10.0,
        date_from=today - timedelta(days=7), date_to=today,
    )
    db.add(st)

    for i in range(14):
        db.add(MetricDaily(
            campaign_id=campaign.id, date=today - timedelta(days=i),
            clicks=50 + i, impressions=500 + i * 10,
            cost_micros=3_000_000, conversions=1.0, conversion_value_micros=5_000_000,
        ))

    db.commit()
    return client, campaign, ag, ad, st


# ─── Clients ────────────────────────────────────────────────────────


class TestClientsList:
    def test_list_clients(self, api_client, db):
        _seed(db)
        resp = api_client.get("/api/v1/clients/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_clients_pagination(self, api_client, db):
        _seed(db)
        resp = api_client.get("/api/v1/clients/?page=1&page_size=5")
        assert resp.status_code == 200
        assert resp.json()["page"] == 1

    def test_list_clients_search(self, api_client, db):
        _seed(db)
        resp = api_client.get("/api/v1/clients/?search=CRUD")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


class TestClientDetail:
    def test_get_client(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/clients/{client.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "CRUD Test Client"

    def test_get_nonexistent_client(self, api_client, db):
        resp = api_client.get("/api/v1/clients/99999")
        assert resp.status_code == 404


class TestClientCreate:
    def test_create_client(self, api_client, db):
        resp = api_client.post("/api/v1/clients/", json={
            "name": "New Client",
            "google_customer_id": "6666666666",
        })
        assert resp.status_code in (200, 201)
        assert resp.json()["name"] == "New Client"


class TestClientUpdate:
    def test_update_client(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.patch(f"/api/v1/clients/{client.id}", json={
            "name": "Updated Name",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"


class TestClientDelete:
    def test_delete_client(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.delete(f"/api/v1/clients/{client.id}")
        assert resp.status_code == 200


# ─── Campaigns ──────────────────────────────────────────────────────


class TestCampaignsList:
    def test_list_campaigns(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_campaigns_filter_status(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/?client_id={client.id}&status=ENABLED")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_campaigns_filter_type(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/?client_id={client.id}&campaign_type=SEARCH")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_campaigns_pagination(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/?client_id={client.id}&page=1&page_size=10")
        assert resp.status_code == 200


class TestCampaignDetail:
    def test_get_campaign(self, api_client, db):
        _, campaign, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/{campaign.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "CRUD Campaign"

    def test_get_nonexistent_campaign(self, api_client, db):
        resp = api_client.get("/api/v1/campaigns/99999")
        assert resp.status_code == 404


class TestCampaignMetrics:
    def test_get_metrics(self, api_client, db):
        _, campaign, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/{campaign.id}/metrics")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) > 0

    def test_get_metrics_with_dates(self, api_client, db):
        _, campaign, _, _, _ = _seed(db)
        today = date.today()
        resp = api_client.get(
            f"/api/v1/campaigns/{campaign.id}/metrics"
            f"?date_from={today - timedelta(days=7)}&date_to={today}"
        )
        assert resp.status_code == 200


class TestCampaignKPIs:
    def test_get_kpis(self, api_client, db):
        _, campaign, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/campaigns/{campaign.id}/kpis?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert "previous" in data
        assert "change_pct" in data

    def test_kpis_nonexistent(self, api_client, db):
        resp = api_client.get("/api/v1/campaigns/99999/kpis")
        assert resp.status_code == 404


# ─── Ad Groups & Ads ────────────────────────────────────────────────


class TestAdGroups:
    def test_list_ad_groups(self, api_client, db):
        client, campaign, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/ad-groups/?client_id={client.id}&campaign_id={campaign.id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_list_ad_groups_client_only(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/ad-groups/?client_id={client.id}")
        assert resp.status_code == 200


class TestAds:
    def test_list_ads(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/ads/?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_list_ads_filter_status(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/ads/?client_id={client.id}&status=ENABLED")
        assert resp.status_code == 200


# ─── Recommendations Summary ────────────────────────────────────────


class TestRecommendationsSummary:
    def test_summary_returns_200(self, api_client, db):
        client, _, _, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/recommendations/summary?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_priority" in data
        assert "executable_total" in data


# ─── Bulk Preview ───────────────────────────────────────────────────


class TestBulkPreview:
    def test_bulk_preview(self, api_client, db):
        _, _, _, _, st = _seed(db)
        resp = api_client.post("/api/v1/search-terms/bulk-preview", json={
            "search_term_ids": [st.id],
            "client_id": st.campaign_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
