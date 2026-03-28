"""Tests for GET /analytics/pmax-search-cannibalization — D3 PMax vs Search overlap."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
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
    """Seed overlapping search terms in Search and PMax campaigns."""
    client = Client(name="CannibTest", google_customer_id="9999999999")
    db.add(client)
    db.flush()

    search_camp = Campaign(client_id=client.id, google_campaign_id="s1",
                           name="Search - Brand", status="ENABLED", campaign_type="SEARCH")
    pmax_camp = Campaign(client_id=client.id, google_campaign_id="p1",
                         name="PMax - General", status="ENABLED", campaign_type="PERFORMANCE_MAX")
    db.add_all([search_camp, pmax_camp])
    db.flush()

    today = date.today()
    d5 = today - timedelta(days=5)
    d3 = today - timedelta(days=3)
    # Overlapping term — "buty skórzane" in both Search and PMax
    db.add(SearchTerm(campaign_id=search_camp.id,
                      text="buty skórzane", clicks=50, impressions=500,
                      cost_micros=25_000_000, conversions=5.0, ctr=10.0,
                      date_from=d5, date_to=today, source="SEARCH"))
    db.add(SearchTerm(campaign_id=pmax_camp.id,
                      text="buty skórzane", clicks=30, impressions=600,
                      cost_micros=40_000_000, conversions=2.0, ctr=5.0,
                      date_from=d5, date_to=today, source="PMAX"))

    # Search-only term
    db.add(SearchTerm(campaign_id=search_camp.id,
                      text="buty eleganckie", clicks=20, impressions=200,
                      cost_micros=10_000_000, conversions=3.0, ctr=10.0,
                      date_from=d3, date_to=today, source="SEARCH"))

    # PMax-only term
    db.add(SearchTerm(campaign_id=pmax_camp.id,
                      text="sandały letnie", clicks=15, impressions=300,
                      cost_micros=8_000_000, conversions=1.0, ctr=5.0,
                      date_from=d3, date_to=today, source="PMAX"))

    db.flush()
    return client


def test_cannibalization_detects_overlap(api_client, db):
    client = _seed(db)
    resp = api_client.get("/api/v1/analytics/pmax-search-cannibalization",
                          params={"client_id": client.id, "days": 30})
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary"]["total_overlap"] == 1
    assert data["summary"]["search_only"] == 1
    assert data["summary"]["pmax_only"] == 1

    # The overlapping term should be "buty skórzane"
    terms = data["overlapping_terms"]
    assert len(terms) == 1
    assert terms[0]["search_term"] == "buty skórzane"

    # Search has better CPA (25/5=5 vs 40/2=20) → winner = SEARCH
    assert terms[0]["winner"] == "SEARCH"
    assert data["summary"]["search_better_count"] == 1


def test_cannibalization_empty_returns_structure(api_client, db):
    client = Client(name="EmptyClient", google_customer_id="0000000000")
    db.add(client)
    db.flush()

    resp = api_client.get("/api/v1/analytics/pmax-search-cannibalization",
                          params={"client_id": client.id, "days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["overlapping_terms"] == []
    assert data["summary"]["total_overlap"] == 0
    assert data["recommendations"] == []


def test_cannibalization_generates_recommendations(api_client, db):
    client = _seed(db)
    resp = api_client.get("/api/v1/analytics/pmax-search-cannibalization",
                          params={"client_id": client.id, "days": 30})
    data = resp.json()

    # Should recommend adding negatives in PMax since Search wins
    rec_types = [r["type"] for r in data["recommendations"]]
    assert "add_negative_pmax" in rec_types
