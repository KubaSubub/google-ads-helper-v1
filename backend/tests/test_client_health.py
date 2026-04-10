"""Tests for GET /clients/{id}/health and business_rules validation.

Covers Acceptance Criteria from docs/specs/settings-client-info-hub.md:
  AC1  — endpoint returns 200 with 4 required keys
  AC2  — graceful degradation when Google Ads API unavailable (always returns 200)
  AC3  — conversion_tracking populated from ConversionAction table (not API)
  AC4  — sync_health.freshness is green/yellow/red based on hours since last sync
  AC7  — new business_rules fields round-trip via PATCH/GET
  AC8  — numeric validation rejects out-of-range values with 422
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Client, SyncLog
from app.models.conversion_action import ConversionAction


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db, *, hours_since_sync: float = 2.0, sync_status: str = "success",
          num_conversions: int = 2, currency: str = "PLN") -> Client:
    """Seed a client with SyncLog + ConversionAction rows for health tests."""
    client = Client(
        name="Health Test Client",
        google_customer_id="9988776655",
        currency=currency,
        business_rules={"min_roas": 2.5, "max_daily_budget": 1000},
    )
    db.add(client)
    db.flush()

    finished = datetime.now(timezone.utc) - timedelta(hours=hours_since_sync)
    started = finished - timedelta(seconds=30)
    log = SyncLog(
        client_id=client.id,
        status=sync_status,
        days=30,
        total_synced=100,
        total_errors=0,
        started_at=started,
        finished_at=finished,
    )
    db.add(log)

    for i in range(num_conversions):
        db.add(ConversionAction(
            client_id=client.id,
            google_conversion_action_id=f"ca_{client.id}_{i}",
            name=f"Conversion {i}",
            category="PURCHASE" if i == 0 else "LEAD",
            status="ENABLED",
            include_in_conversions_metric=True,
            attribution_model="DATA_DRIVEN",  # Google Ads API v23 enum value
        ))

    db.commit()
    return client


# ── AC1: endpoint structure ───────────────────────────────────────────────────

def test_health_returns_200_with_required_keys(api_client, db):
    client = _seed(db)
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("account_metadata", "sync_health", "conversion_tracking", "linked_accounts", "errors"):
        assert key in body, f"Missing key: {key}"


def test_health_unknown_client_returns_404(api_client):
    resp = api_client.get("/api/v1/clients/999999/health")
    assert resp.status_code == 404


# ── AC2: graceful degradation (Google Ads API unavailable) ───────────────────

def test_health_still_200_when_google_ads_unavailable(api_client, db, monkeypatch):
    """Even when Google Ads API is down, endpoint returns 200 using DB data."""
    from app.services import client_health_service as svc

    monkeypatch.setattr(
        svc,
        "_try_google_ads_metadata",
        lambda client: ({}, ["google_ads_api_unavailable"]),
    )
    client = _seed(db)
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "google_ads_api_unavailable" in body["errors"]
    # account_metadata still populated from DB
    assert body["account_metadata"]["customer_id"] == client.google_customer_id
    assert body["account_metadata"]["currency"] == "PLN"


# ── AC3: conversion_tracking from DB ─────────────────────────────────────────

def test_conversion_tracking_reads_from_db(api_client, db):
    client = _seed(db, num_conversions=3)
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    assert resp.status_code == 200
    ct = resp.json()["conversion_tracking"]
    assert ct["active_count"] == 3
    assert len(ct["actions"]) == 3
    assert ct["attribution_model"] is not None


def test_conversion_tracking_empty_when_no_conversions(api_client, db):
    client = _seed(db, num_conversions=0)
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    ct = resp.json()["conversion_tracking"]
    assert ct["active_count"] == 0
    assert ct["actions"] == []


# ── AC4: sync_health freshness ────────────────────────────────────────────────

@pytest.mark.parametrize("hours,expected_freshness", [
    (2.0, "green"),    # < 6h → green
    (9.0, "yellow"),   # 6-12h → yellow (daily optimizer threshold)
    (13.0, "red"),     # ≥ 12h → red (stale for daily optimization)
])
def test_sync_freshness_logic(api_client, db, hours, expected_freshness):
    client = _seed(db, hours_since_sync=hours)
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    assert resp.json()["sync_health"]["freshness"] == expected_freshness


def test_sync_health_red_when_no_sync_log(api_client, db):
    """New client with no sync history → freshness=red, last_synced_at=null."""
    client = Client(name="No Sync", google_customer_id="1111111111", currency="PLN")
    db.add(client)
    db.commit()
    resp = api_client.get(f"/api/v1/clients/{client.id}/health")
    sh = resp.json()["sync_health"]
    assert sh["freshness"] == "red"
    assert sh["last_synced_at"] is None


# ── AC7: business_rules new fields round-trip ─────────────────────────────────

def test_business_rules_new_fields_round_trip(api_client, db):
    client = _seed(db)
    payload = {
        "business_rules": {
            "min_roas": 2.5,
            "target_cpa": 50.0,
            "target_roas": 4.0,
            "ltv_per_customer": 500.0,
            "profit_margin_pct": 35,
            "brand_terms": ["SushiNaka", "sushi naka naka"],
            "priority_conversions": ["Zakup", "Lead"],
        }
    }
    patch = api_client.patch(f"/api/v1/clients/{client.id}", json=payload)
    assert patch.status_code == 200
    get = api_client.get(f"/api/v1/clients/{client.id}")
    br = get.json()["business_rules"]
    assert br["target_cpa"] == 50.0
    assert br["profit_margin_pct"] == 35
    assert br["brand_terms"] == ["SushiNaka", "sushi naka naka"]


# ── AC8: numeric range validation ─────────────────────────────────────────────

@pytest.mark.parametrize("bad_rules,expected_error_fragment", [
    ({"profit_margin_pct": 150}, "profit_margin_pct"),
    ({"profit_margin_pct": -1}, "profit_margin_pct"),
    ({"target_cpa": -10}, "target_cpa"),
    ({"brand_terms": ["x"] * 51}, "brand_terms"),
])
def test_business_rules_validation_rejects_bad_values(api_client, db, bad_rules, expected_error_fragment):
    client = _seed(db)
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"business_rules": bad_rules},
    )
    assert resp.status_code == 422
    detail = str(resp.json())
    assert expected_error_fragment in detail
