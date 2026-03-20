"""Tests for GET /semantic/clusters endpoint."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, AdGroup, SearchTerm


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

    client = Client(name="Semantic Test", google_customer_id="5555555555")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="sem_c1",
        name="Search Semantic",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="sem_ag1", name="Semantic Group", status="ENABLED")
    db.add(ag)
    db.flush()

    # Multiple related search terms that should cluster
    for text, clicks, cost, conv in [
        ("buty sportowe nike", 50, 10_000_000, 3.0),
        ("buty sportowe adidas", 40, 8_000_000, 2.0),
        ("buty do biegania", 30, 6_000_000, 1.0),
        ("kalosze gumowe", 10, 2_000_000, 0),
        ("kalosze damskie", 8, 1_500_000, 0),
        ("parasol skladany", 5, 1_000_000, 0.5),
    ]:
        db.add(SearchTerm(
            ad_group_id=ag.id, campaign_id=campaign.id,
            text=text, clicks=clicks, impressions=clicks * 10,
            cost_micros=cost, conversions=conv, ctr=10.0,
            date_from=week_ago, date_to=today,
        ))

    db.commit()
    return client


class TestSemanticClusters:
    def test_clusters_returns_200(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/semantic/clusters?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_clusters_with_params(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(
            f"/api/v1/semantic/clusters?client_id={client.id}&min_cluster_size=2&threshold=1.5"
        )
        assert resp.status_code == 200

    def test_clusters_empty_client(self, api_client, db):
        client = Client(name="Empty Semantic", google_customer_id="0002")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/semantic/clusters?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cluster_structure(self, api_client, db):
        client = _seed(db)
        resp = api_client.get(f"/api/v1/semantic/clusters?client_id={client.id}&min_cluster_size=1")
        data = resp.json()
        if len(data) > 0:
            cluster = data[0]
            assert "id" in cluster
            assert "name" in cluster
            assert "items" in cluster
            assert "metrics" in cluster
            assert "is_waste" in cluster
