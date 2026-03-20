"""Tests for POST /recommendations/bulk-apply endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, Recommendation


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    client = Client(name="BulkApply Test", google_customer_id="6666666666")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="ba_c1",
        name="Search BA",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    # Add recommendations matching different categories
    recs = []
    for rule_id, priority in [
        ("PAUSE_LOW_QS", "HIGH"),
        ("PAUSE_ZERO_CONV", "HIGH"),
        ("ADD_NEGATIVE_WASTED", "MEDIUM"),
    ]:
        rec = Recommendation(
            client_id=client.id,
            campaign_id=campaign.id,
            rule_id=rule_id,
            entity_type="keyword",
            entity_id=f"kw_{rule_id}",
            priority=priority,
            status="pending",
            reason="Test recommendation",
            suggested_action=f"Apply {rule_id}",
        )
        db.add(rec)
        recs.append(rec)

    db.commit()
    return client, recs


class TestBulkApply:
    def test_dry_run_clean_waste(self, api_client, db):
        client, recs = _seed(db)
        resp = api_client.post("/api/v1/recommendations/bulk-apply", json={
            "client_id": client.id,
            "category": "clean_waste",
            "dry_run": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "dry_run" in data
        assert data["dry_run"] is True

    def test_dry_run_pause_burning(self, api_client, db):
        client, recs = _seed(db)
        resp = api_client.post("/api/v1/recommendations/bulk-apply", json={
            "client_id": client.id,
            "category": "pause_burning",
            "dry_run": True,
        })
        assert resp.status_code == 200

    def test_dry_run_add_negatives(self, api_client, db):
        client, recs = _seed(db)
        resp = api_client.post("/api/v1/recommendations/bulk-apply", json={
            "client_id": client.id,
            "category": "add_negatives",
            "dry_run": True,
        })
        assert resp.status_code == 200

    def test_invalid_category(self, api_client, db):
        client, recs = _seed(db)
        resp = api_client.post("/api/v1/recommendations/bulk-apply", json={
            "client_id": client.id,
            "category": "nonexistent",
            "dry_run": True,
        })
        assert resp.status_code == 400

    def test_all_categories_accepted(self, api_client, db):
        client, _ = _seed(db)
        for cat in ["clean_waste", "pause_burning", "boost_winners", "emergency_brake", "add_negatives"]:
            resp = api_client.post("/api/v1/recommendations/bulk-apply", json={
                "client_id": client.id,
                "category": cat,
                "dry_run": True,
            })
            assert resp.status_code == 200, f"Category {cat} failed"
