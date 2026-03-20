"""Tests for search-terms bulk action endpoints."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, AdGroup, SearchTerm, Keyword, NegativeKeyword


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

    client = Client(name="Bulk Test", google_customer_id="7777777777")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="bulk_c1",
        name="Search Bulk",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="bulk_ag1", name="Bulk Group", status="ENABLED")
    db.add(ag)
    db.flush()

    terms = []
    for text, clicks, cost, conv in [
        ("buty sportowe", 50, 10_000_000, 3.0),
        ("darmowe buty", 20, 5_000_000, 0),
        ("buty tanio", 15, 3_000_000, 0),
    ]:
        st = SearchTerm(
            ad_group_id=ag.id, campaign_id=campaign.id,
            text=text, clicks=clicks, impressions=clicks * 10,
            cost_micros=cost, conversions=conv, ctr=10.0,
            date_from=week_ago, date_to=today,
        )
        db.add(st)
        terms.append(st)

    db.commit()
    return client, campaign, ag, terms


class TestBulkPreview:
    def test_preview_returns_200(self, api_client, db):
        client, campaign, ag, terms = _seed(db)
        term_ids = [t.id for t in terms[:2]]
        resp = api_client.post("/api/v1/search-terms/bulk-preview", json={
            "search_term_ids": term_ids,
            "client_id": client.id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_preview_empty_ids_returns_400(self, api_client, db):
        client, _, _, _ = _seed(db)
        resp = api_client.post("/api/v1/search-terms/bulk-preview", json={
            "search_term_ids": [],
            "client_id": client.id,
        })
        assert resp.status_code == 400


class TestBulkAddNegative:
    def test_add_negative_campaign_level(self, api_client, db):
        client, campaign, ag, terms = _seed(db)
        term_ids = [terms[1].id, terms[2].id]  # waste terms
        resp = api_client.post("/api/v1/search-terms/bulk-add-negative", json={
            "search_term_ids": term_ids,
            "level": "campaign",
            "match_type": "EXACT",
            "client_id": client.id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] >= 1

    def test_add_negative_ad_group_level(self, api_client, db):
        client, campaign, ag, terms = _seed(db)
        resp = api_client.post("/api/v1/search-terms/bulk-add-negative", json={
            "search_term_ids": [terms[1].id],
            "level": "ad_group",
            "match_type": "PHRASE",
            "client_id": client.id,
        })
        assert resp.status_code == 200


class TestBulkAddKeyword:
    def test_add_keyword(self, api_client, db):
        client, campaign, ag, terms = _seed(db)
        resp = api_client.post("/api/v1/search-terms/bulk-add-keyword", json={
            "search_term_ids": [terms[0].id],
            "ad_group_id": ag.id,
            "match_type": "EXACT",
            "client_id": client.id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] >= 1
