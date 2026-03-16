"""Tests for search_terms router — list, filter, paginate."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.search_term import SearchTerm


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    today = date.today()
    week_ago = today - timedelta(days=7)

    client = Client(name="ST Client", google_customer_id="5551112220")
    db.add(client)
    db.flush()

    campaign = Campaign(client_id=client.id, google_campaign_id="stc1", name="Search Camp", status="ENABLED", campaign_type="SEARCH")
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="stag1", name="Group A", status="ENABLED")
    db.add(ag)
    db.flush()

    terms = [
        SearchTerm(ad_group_id=ag.id, text="buty sportowe", clicks=100, impressions=1000, cost_micros=20_000_000, conversions=5.0, ctr=100000, date_from=week_ago, date_to=today),
        SearchTerm(ad_group_id=ag.id, text="buty zimowe", clicks=50, impressions=500, cost_micros=10_000_000, conversions=2.0, ctr=100000, date_from=week_ago, date_to=today),
        SearchTerm(ad_group_id=ag.id, text="kalosze gumowe", clicks=2, impressions=200, cost_micros=500_000, conversions=0, ctr=10000, date_from=week_ago, date_to=today),
    ]
    db.add_all(terms)
    db.commit()
    return client, campaign, ag


class TestListSearchTerms:
    def test_returns_paginated_response(self, api_client, db):
        client, _, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_min_clicks_filter(self, api_client, db):
        client, _, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&min_clicks=50")
        data = resp.json()

        assert data["total"] == 2
        texts = [t["text"] for t in data["items"]]
        assert "kalosze gumowe" not in texts

    def test_search_filter(self, api_client, db):
        client, _, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&search=buty")
        data = resp.json()

        assert data["total"] == 2
        for item in data["items"]:
            assert "buty" in item["text"]

    def test_sort_by_clicks_asc(self, api_client, db):
        client, _, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&sort_by=clicks&sort_order=asc")
        data = resp.json()

        clicks = [t["clicks"] for t in data["items"]]
        assert clicks == sorted(clicks)

    def test_pagination(self, api_client, db):
        client, _, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&page=1&page_size=2")
        data = resp.json()

        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["total_pages"] == 2

        resp2 = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&page=2&page_size=2")
        data2 = resp2.json()
        assert len(data2["items"]) == 1

    def test_date_range_filter(self, api_client, db):
        client, _, _ = _seed(db)

        # All terms have date_from=week_ago, date_to=today
        # A future date range should return nothing
        future = (date.today() + timedelta(days=30)).isoformat()
        resp = api_client.get(f"/api/v1/search-terms/?client_id={client.id}&date_from={future}")
        data = resp.json()
        assert data["total"] == 0

    def test_empty_result_for_nonexistent_client(self, api_client, db):
        resp = api_client.get("/api/v1/search-terms/?client_id=99999")
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestSearchTermsSummary:
    def test_returns_aggregated_data(self, api_client, db):
        client, campaign, _ = _seed(db)

        resp = api_client.get(f"/api/v1/search-terms/summary?campaign_id={campaign.id}&days=30")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total_terms"] == 3
        assert data["total_clicks"] == 152  # 100+50+2
        assert len(data["top_by_cost"]) == 3
        assert data["top_by_cost"][0]["text"] == "buty sportowe"  # highest cost

    def test_empty_campaign_returns_zeroes(self, api_client, db):
        client = Client(name="Empty", google_customer_id="6662220000")
        db.add(client)
        db.flush()
        campaign = Campaign(client_id=client.id, google_campaign_id="empty", name="Empty", status="ENABLED", campaign_type="SEARCH")
        db.add(campaign)
        db.flush()
        ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="eag", name="Empty", status="ENABLED")
        db.add(ag)
        db.commit()

        resp = api_client.get(f"/api/v1/search-terms/summary?campaign_id={campaign.id}&days=30")
        data = resp.json()

        assert data["total_terms"] == 0
        assert data["total_cost_usd"] == 0
