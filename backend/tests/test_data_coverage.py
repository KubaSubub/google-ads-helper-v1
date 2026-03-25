"""Tests for GET /sync/data-coverage endpoint."""

import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, MetricDaily, SyncLog


@pytest.fixture
def api_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_client(db, name="Test Client", customer_id="111-222-3333"):
    client = Client(name=name, google_customer_id=customer_id)
    db.add(client)
    db.flush()
    return client


def _seed_campaign(db, client_id, name="Campaign 1"):
    campaign = Campaign(
        client_id=client_id,
        google_campaign_id=f"gc-{client_id}-{name}",
        name=name,
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()
    return campaign


def _seed_metrics(db, campaign_id, dates):
    for d in dates:
        db.add(MetricDaily(
            campaign_id=campaign_id,
            date=d,
            impressions=100,
            clicks=10,
            cost_micros=1000000,
            conversions=1.0,
        ))
    db.flush()


def _seed_sync_log(db, client_id, status="success", days=30, finished_at=None):
    log = SyncLog(
        client_id=client_id,
        status=status,
        days=days,
        started_at=finished_at or datetime(2026, 3, 25, 8, 0, 0),
        finished_at=finished_at or datetime(2026, 3, 25, 8, 5, 0),
    )
    db.add(log)
    db.flush()
    return log


class TestDataCoverage:
    """Tests for /sync/data-coverage endpoint."""

    def test_returns_coverage_with_data(self, api_client, db):
        """Should return correct date range when metrics exist."""
        client = _seed_client(db)
        campaign = _seed_campaign(db, client.id)
        _seed_metrics(db, campaign.id, [
            date(2026, 1, 1),
            date(2026, 1, 15),
            date(2026, 2, 10),
            date(2026, 3, 20),
        ])
        _seed_sync_log(db, client.id, finished_at=datetime(2026, 3, 25, 10, 0, 0))
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client.id})
        assert resp.status_code == 200
        data = resp.json()

        assert data["client_id"] == client.id
        assert data["data_from"] == "2026-01-01"
        assert data["data_to"] == "2026-03-20"
        assert data["last_sync_at"] is not None
        assert data["last_sync_days"] == 30
        assert data["last_sync_status"] == "success"

    def test_returns_nulls_when_no_data(self, api_client, db):
        """Should return nulls when client has no synced metrics."""
        client = _seed_client(db)
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client.id})
        assert resp.status_code == 200
        data = resp.json()

        assert data["client_id"] == client.id
        assert data["data_from"] is None
        assert data["data_to"] is None
        assert data["last_sync_at"] is None
        assert data["last_sync_days"] is None
        assert data["last_sync_status"] is None

    def test_returns_error_for_missing_client(self, api_client, db):
        """Should return error when client_id doesn't exist."""
        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": 9999})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("error") == "Client not found"

    def test_only_counts_successful_syncs(self, api_client, db):
        """Should only consider success/partial syncs, not failed ones."""
        client = _seed_client(db)
        _seed_sync_log(db, client.id, status="failed", days=30,
                       finished_at=datetime(2026, 3, 25, 12, 0, 0))
        _seed_sync_log(db, client.id, status="success", days=60,
                       finished_at=datetime(2026, 3, 24, 8, 0, 0))
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client.id})
        data = resp.json()

        # Should pick the successful sync, not the failed one
        assert data["last_sync_days"] == 60
        assert data["last_sync_status"] == "success"

    def test_partial_sync_counts(self, api_client, db):
        """Should include partial syncs as valid."""
        client = _seed_client(db)
        campaign = _seed_campaign(db, client.id)
        _seed_metrics(db, campaign.id, [date(2026, 2, 1), date(2026, 3, 1)])
        _seed_sync_log(db, client.id, status="partial", days=90,
                       finished_at=datetime(2026, 3, 25, 9, 0, 0))
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client.id})
        data = resp.json()

        assert data["data_from"] == "2026-02-01"
        assert data["data_to"] == "2026-03-01"
        assert data["last_sync_status"] == "partial"
        assert data["last_sync_days"] == 90

    def test_multiple_campaigns_merged(self, api_client, db):
        """Date range should span across all campaigns for the client."""
        client = _seed_client(db)
        c1 = _seed_campaign(db, client.id, "Campaign A")
        c2 = _seed_campaign(db, client.id, "Campaign B")
        _seed_metrics(db, c1.id, [date(2026, 1, 10), date(2026, 2, 15)])
        _seed_metrics(db, c2.id, [date(2025, 12, 1), date(2026, 3, 20)])
        _seed_sync_log(db, client.id)
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client.id})
        data = resp.json()

        assert data["data_from"] == "2025-12-01"
        assert data["data_to"] == "2026-03-20"

    def test_does_not_leak_other_client_data(self, api_client, db):
        """Coverage for one client should not include another client's data."""
        client_a = _seed_client(db, "Client A", "111-111-1111")
        client_b = _seed_client(db, "Client B", "222-222-2222")
        camp_a = _seed_campaign(db, client_a.id, "Camp A")
        camp_b = _seed_campaign(db, client_b.id, "Camp B")
        _seed_metrics(db, camp_a.id, [date(2026, 1, 1), date(2026, 3, 1)])
        _seed_metrics(db, camp_b.id, [date(2025, 6, 1), date(2026, 3, 25)])
        db.commit()

        resp = api_client.get("/api/v1/sync/data-coverage", params={"client_id": client_a.id})
        data = resp.json()

        assert data["data_from"] == "2026-01-01"
        assert data["data_to"] == "2026-03-01"
