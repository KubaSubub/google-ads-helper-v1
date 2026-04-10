"""Tests for /sync/* endpoints — connection status, logs, debug, coverage, presets."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Client, Campaign, AdGroup, Keyword, MetricDaily, SyncLog


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed minimal sync test scenario."""
    client = Client(name="Sync Client", google_customer_id="1112223334")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="sync_c1",
        name="Sync Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=50_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="sync_ag1",
        name="Sync Group",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    kw = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="sync_kw1",
        text="test keyword",
        match_type="EXACT",
        status="ENABLED",
        criterion_kind="POSITIVE",
    )
    db.add(kw)
    db.flush()

    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=d,
            clicks=100 - i * 5,
            impressions=1000 - i * 50,
            cost_micros=10_000_000 - i * 500_000,
            conversions=5.0 - i * 0.3,
            ctr=10.0,
        ))

    log = SyncLog(
        client_id=client.id,
        status="success",
        days=30,
        total_synced=150,
        total_errors=0,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    return client


# ─── /sync/status ───


def test_sync_status_returns_connection_info(api_client):
    resp = api_client.get("/api/v1/sync/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "google_ads_connected" in data
    assert "configured" in data
    assert "authenticated" in data
    assert "ready" in data
    assert "message" in data


# ─── /sync/logs ───


def test_sync_logs_returns_list(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/sync/logs?client_id={client.id}")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert logs[0]["status"] == "success"
    assert logs[0]["total_synced"] == 150


def test_sync_logs_empty_client(api_client, db):
    client = Client(name="Empty", google_customer_id="9999999999")
    db.add(client)
    db.commit()
    resp = api_client.get(f"/api/v1/sync/logs?client_id={client.id}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sync_logs_limit_param(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/sync/logs?client_id={client.id}&limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


# ─── /sync/debug ───


def test_sync_debug_returns_diagnostics(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/sync/debug?client_id={client.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "campaigns" in data
    assert "keywords" in data
    assert data["campaigns"] >= 1
    assert data["keywords"] >= 1


def test_sync_debug_unknown_client(api_client, db):
    resp = api_client.get("/api/v1/sync/debug?client_id=99999")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


# ─── /sync/data-coverage ───


def test_data_coverage_returns_date_range(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/sync/data-coverage?client_id={client.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == client.id
    assert data["data_from"] is not None
    assert data["data_to"] is not None
    assert data["last_sync_status"] == "success"
    assert data["last_sync_days"] == 30


def test_data_coverage_unknown_client(api_client, db):
    resp = api_client.get("/api/v1/sync/data-coverage?client_id=99999")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_data_coverage_no_metrics(api_client, db):
    client = Client(name="NoMetrics", google_customer_id="7777777777")
    db.add(client)
    db.commit()
    resp = api_client.get(f"/api/v1/sync/data-coverage?client_id={client.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_from"] is None
    assert data["data_to"] is None
    assert data["last_sync_at"] is None


# ─── /sync/presets ───


def test_presets_returns_structure(api_client):
    resp = api_client.get("/api/v1/sync/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    assert "phases" in data
    assert "groups" in data
    assert "phase_order" in data
    assert isinstance(data["presets"], dict)
    assert isinstance(data["phases"], dict)
    assert len(data["phases"]) >= 15  # at least 15 sync phases


def test_presets_phases_have_required_fields(api_client):
    resp = api_client.get("/api/v1/sync/presets")
    data = resp.json()
    for name, phase in data["phases"].items():
        assert "label" in phase, f"Phase {name} missing label"
        assert "group" in phase, f"Phase {name} missing group"
        assert "max_days" in phase, f"Phase {name} missing max_days"


# ─── /sync/coverage ───


def test_coverage_returns_empty_dict_for_no_coverage(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/sync/coverage?client_id={client.id}")
    assert resp.status_code == 200
    data = resp.json()
    # Returns dict keyed by resource_type; empty if no SyncCoverage rows
    assert isinstance(data, dict)


# ─── /sync/trigger requires demo guard ───


def test_trigger_requires_client_id(api_client):
    resp = api_client.post("/api/v1/sync/trigger")
    assert resp.status_code == 422  # missing client_id


def test_trigger_stream_requires_client_id(api_client):
    resp = api_client.post("/api/v1/sync/trigger-stream")
    assert resp.status_code == 422  # missing client_id


# ─── /sync/trigger response contract ───
#
# The MCC Overview frontend relies on `result.success` + `result.message`
# (see syncClient in frontend/src/api.js and runSync in MCCOverviewPage.jsx).
# These tests lock the response shape so a backend refactor cannot silently
# break the frontend by renaming fields or returning a raw HTTPException.

_TRIGGER_CONTRACT_KEYS = {"success", "status", "message"}


def test_trigger_unknown_client_matches_contract(api_client):
    resp = api_client.post("/api/v1/sync/trigger?client_id=999999")
    assert resp.status_code == 200
    body = resp.json()
    assert _TRIGGER_CONTRACT_KEYS.issubset(body.keys())
    assert body["success"] is False
    assert body["status"] == "failed"
    assert isinstance(body["message"], str) and body["message"]


def test_trigger_google_ads_not_ready_matches_contract(api_client, db, monkeypatch):
    """When Google Ads is not configured, the endpoint still returns the
    structured contract (not an HTTPException) so the frontend toast works."""
    from app.services.google_ads import google_ads_service

    monkeypatch.setattr(
        google_ads_service,
        "get_connection_diagnostics",
        lambda: {
            "authenticated": False,
            "configured": False,
            "ready": False,
            "connected": False,
            "reason": "Brak credentiali Google Ads",
            "missing_credentials": ["client_id", "client_secret", "developer_token"],
            "has_login_customer_id": False,
        },
    )
    client = _seed(db)
    resp = api_client.post(f"/api/v1/sync/trigger?client_id={client.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert _TRIGGER_CONTRACT_KEYS.issubset(body.keys())
    assert body["success"] is False
    assert body["status"] == "failed"
    assert "Google Ads" in body["message"] or body["message"]
    # The "not ready" branch also exposes reason + missing_credentials for the UI
    assert "reason" in body
    assert "missing_credentials" in body
    assert isinstance(body["missing_credentials"], list)


# ─── /sync/phase requires valid phase name ───


def test_phase_unknown_name(api_client, db):
    client = _seed(db)
    resp = api_client.post(f"/api/v1/sync/phase/nonexistent_phase?client_id={client.id}&allow_demo_write=true")
    assert resp.status_code in (200, 400, 422)
    # Should either return error or reject unknown phase
