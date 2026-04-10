"""Tests for /sync/schedule endpoints (scheduled_sync router).

Covers the 3 endpoints flagged as 0-coverage by pm-check:
- GET  /api/v1/sync/schedule?client_id=N
- POST /api/v1/sync/schedule
- DELETE /api/v1/sync/schedule?client_id=N

Contract tests lock the response shape relied on by the frontend
(RulesPage.jsx uses `enabled`, `interval_hours`, `next_run_at`).
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Client
from app.models.scheduled_sync import ScheduledSyncConfig


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded_client(db):
    client = Client(name="Schedule Client", google_customer_id="9998887776")
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


_RESPONSE_KEYS = {
    "client_id",
    "enabled",
    "interval_hours",
    "last_run_at",
    "next_run_at",
    "created_at",
}


# ─── GET /sync/schedule ────────────────────────────────────────────────


def test_get_schedule_returns_default_when_none_exists(api_client, seeded_client):
    """When no schedule exists, the endpoint returns a disabled default
    (not 404). The frontend relies on this contract to render the form."""
    resp = api_client.get(f"/api/v1/sync/schedule?client_id={seeded_client.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert _RESPONSE_KEYS.issubset(body.keys())
    assert body["client_id"] == seeded_client.id
    assert body["enabled"] is False
    assert body["interval_hours"] == 6
    assert body["last_run_at"] is None
    assert body["next_run_at"] is None


def test_get_schedule_returns_existing_config(api_client, db, seeded_client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    next_run = now + timedelta(hours=12)
    cfg = ScheduledSyncConfig(
        client_id=seeded_client.id,
        enabled=True,
        interval_hours=12,
        next_run_at=next_run,
    )
    db.add(cfg)
    db.commit()

    resp = api_client.get(f"/api/v1/sync/schedule?client_id={seeded_client.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["interval_hours"] == 12
    assert body["next_run_at"] is not None
    assert body["id"] == cfg.id


def test_get_schedule_requires_client_id(api_client):
    resp = api_client.get("/api/v1/sync/schedule")
    assert resp.status_code == 422  # missing required query param


# ─── POST /sync/schedule ───────────────────────────────────────────────


def test_post_schedule_creates_new_config(api_client, db, seeded_client):
    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": True, "interval_hours": 4},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["interval_hours"] == 4
    assert body["next_run_at"] is not None

    # Persisted
    cfg = db.query(ScheduledSyncConfig).filter_by(client_id=seeded_client.id).first()
    assert cfg is not None
    assert cfg.interval_hours == 4


def test_post_schedule_updates_existing_config(api_client, db, seeded_client):
    cfg = ScheduledSyncConfig(client_id=seeded_client.id, enabled=True, interval_hours=6)
    db.add(cfg)
    db.commit()

    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": True, "interval_hours": 24},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["interval_hours"] == 24

    # Only one row — no duplicate created
    count = db.query(ScheduledSyncConfig).filter_by(client_id=seeded_client.id).count()
    assert count == 1


def test_post_schedule_disable_clears_next_run(api_client, db, seeded_client):
    cfg = ScheduledSyncConfig(
        client_id=seeded_client.id,
        enabled=True,
        interval_hours=6,
        next_run_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=6),
    )
    db.add(cfg)
    db.commit()

    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": False, "interval_hours": 6},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["next_run_at"] is None


def test_post_schedule_rejects_interval_below_1h(api_client, seeded_client):
    """interval_hours has ge=1 constraint — guards against 0/negative."""
    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": True, "interval_hours": 0},
    )
    assert resp.status_code == 422


def test_post_schedule_rejects_interval_above_168h(api_client, seeded_client):
    """interval_hours has le=168 (7 days) — caps unrealistic schedules."""
    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": True, "interval_hours": 200},
    )
    assert resp.status_code == 422


def test_post_schedule_requires_client_id_in_body(api_client):
    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"enabled": True, "interval_hours": 6},
    )
    assert resp.status_code == 422


def test_post_schedule_recalculates_next_run_on_interval_change(
    api_client, db, seeded_client
):
    """Changing interval on an already-scheduled config must recompute next_run_at
    based on last_run (or now) + new interval."""
    last_run = datetime(2026, 4, 10, 0, 0, 0)
    cfg = ScheduledSyncConfig(
        client_id=seeded_client.id,
        enabled=True,
        interval_hours=6,
        last_run_at=last_run,
        next_run_at=last_run + timedelta(hours=6),
    )
    db.add(cfg)
    db.commit()

    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": seeded_client.id, "enabled": True, "interval_hours": 24},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Expected: last_run_at + 24h = 2026-04-11 00:00:00
    assert body["next_run_at"].startswith("2026-04-11")


# ─── DELETE /sync/schedule ─────────────────────────────────────────────


def test_delete_schedule_removes_existing_config(api_client, db, seeded_client):
    cfg = ScheduledSyncConfig(client_id=seeded_client.id, enabled=True, interval_hours=6)
    db.add(cfg)
    db.commit()

    resp = api_client.delete(f"/api/v1/sync/schedule?client_id={seeded_client.id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Gone
    assert db.query(ScheduledSyncConfig).filter_by(client_id=seeded_client.id).first() is None


def test_delete_schedule_is_idempotent_when_none_exists(api_client, seeded_client):
    """Deleting a non-existent schedule returns success (not 404) — idempotent."""
    resp = api_client.delete(f"/api/v1/sync/schedule?client_id={seeded_client.id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_schedule_requires_client_id(api_client):
    resp = api_client.delete("/api/v1/sync/schedule")
    assert resp.status_code == 422


# ─── Isolation between clients ─────────────────────────────────────────


def test_schedule_is_isolated_per_client(api_client, db):
    c1 = Client(name="Client A", google_customer_id="1111111111")
    c2 = Client(name="Client B", google_customer_id="2222222222")
    db.add_all([c1, c2])
    db.commit()

    # Enable schedule for c1 only
    resp = api_client.post(
        "/api/v1/sync/schedule",
        json={"client_id": c1.id, "enabled": True, "interval_hours": 12},
    )
    assert resp.status_code == 200

    # c1 has config, c2 returns default disabled
    r1 = api_client.get(f"/api/v1/sync/schedule?client_id={c1.id}").json()
    r2 = api_client.get(f"/api/v1/sync/schedule?client_id={c2.id}").json()

    assert r1["enabled"] is True
    assert r1["interval_hours"] == 12
    assert r2["enabled"] is False
    assert r2.get("id") is None  # default payload has no id
