"""Tests for PATCH /campaigns/{id}/bidding-target, /budget, /status endpoints."""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client


@pytest.fixture
def api_client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_with_campaign(db):
    client = Client(name="TestClient", google_customer_id="9876543210")
    db.add(client)
    db.flush()
    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="9999",
        name="Test Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
        bidding_strategy="TARGET_CPA",
        target_cpa_micros=25_000_000,
        budget_micros=100_000_000,  # 100 zł/d
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return client, campaign


# ─── Bidding target endpoint ──────────────────────────────────────────────────

def test_bidding_target_local_update_when_api_disconnected(api_client, client_with_campaign):
    """Happy path: API not connected -> local DB updates, pending_sync=True."""
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/bidding-target",
        params={"field": "target_cpa_micros", "value": 30_000_000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["old_value"] == 25_000_000
    assert data["new_value"] == 30_000_000
    assert data["pending_sync"] is True
    assert data["api_synced"] is False


def test_bidding_target_live_api_success(api_client, client_with_campaign):
    """Happy path: API connected, mutator succeeds -> api_synced=True."""
    _client, campaign = client_with_campaign
    with patch("app.services.google_ads.google_ads_service") as mock_svc:
        mock_svc.is_connected = True
        mock_svc._mutate_campaign_bidding_target = MagicMock(return_value=None)
        resp = api_client.patch(
            f"/api/v1/campaigns/{campaign.id}/bidding-target",
            params={"field": "target_cpa_micros", "value": 30_000_000},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["api_synced"] is True
    assert data["pending_sync"] is False


def test_bidding_target_api_failure_rolls_back(api_client, client_with_campaign, db):
    """API rejects -> 502, local DB NOT updated."""
    _client, campaign = client_with_campaign
    old_val = campaign.target_cpa_micros
    with patch("app.services.google_ads.google_ads_service") as mock_svc:
        mock_svc.is_connected = True
        mock_svc._mutate_campaign_bidding_target.side_effect = RuntimeError("API rejected")
        resp = api_client.patch(
            f"/api/v1/campaigns/{campaign.id}/bidding-target",
            params={"field": "target_cpa_micros", "value": 30_000_000},
        )
    assert resp.status_code == 502
    db.refresh(campaign)
    assert campaign.target_cpa_micros == old_val


def test_bidding_target_invalid_field_returns_400(api_client, client_with_campaign):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/bidding-target",
        params={"field": "target_bogus", "value": 1.0},
    )
    assert resp.status_code == 400


def test_bidding_target_campaign_not_found_returns_404(api_client):
    resp = api_client.patch(
        "/api/v1/campaigns/999999/bidding-target",
        params={"field": "target_cpa_micros", "value": 10_000_000},
    )
    assert resp.status_code == 404


# ─── Budget endpoint ──────────────────────────────────────────────────────────

def test_budget_local_update_when_api_disconnected(api_client, client_with_campaign, db):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/budget",
        params={"budget_micros": 150_000_000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["old_budget_micros"] == 100_000_000
    assert data["new_budget_micros"] == 150_000_000
    assert data["pending_sync"] is True
    db.refresh(campaign)
    assert campaign.budget_micros == 150_000_000


def test_budget_api_failure_reverts_local(api_client, client_with_campaign, db):
    """API rejects -> 502, local DB NOT updated (original budget preserved)."""
    _client, campaign = client_with_campaign
    old_budget = campaign.budget_micros
    with patch("app.services.google_ads.google_ads_service") as mock_svc:
        mock_svc.is_connected = True
        mock_svc._mutate_campaign_budget.side_effect = RuntimeError("Budget API rejected")
        resp = api_client.patch(
            f"/api/v1/campaigns/{campaign.id}/budget",
            params={"budget_micros": 999_000_000},
        )
    assert resp.status_code == 502
    db.refresh(campaign)
    assert campaign.budget_micros == old_budget


def test_budget_rejects_zero_or_negative(api_client, client_with_campaign):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/budget",
        params={"budget_micros": 0},
    )
    # gt=0 constraint in Query
    assert resp.status_code == 422


# ─── Status endpoint ──────────────────────────────────────────────────────────

def test_status_pause_local_update(api_client, client_with_campaign, db):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/status",
        params={"new_status": "PAUSED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["old_status"] == "ENABLED"
    assert data["new_status"] == "PAUSED"
    db.refresh(campaign)
    assert campaign.status == "PAUSED"


def test_status_no_change_returns_no_change_flag(api_client, client_with_campaign):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/status",
        params={"new_status": "ENABLED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("no_change") is True


def test_status_invalid_value_returns_422(api_client, client_with_campaign):
    _client, campaign = client_with_campaign
    resp = api_client.patch(
        f"/api/v1/campaigns/{campaign.id}/status",
        params={"new_status": "BOGUS"},
    )
    assert resp.status_code == 422


def test_status_campaign_not_found_returns_404(api_client):
    resp = api_client.patch(
        "/api/v1/campaigns/999999/status",
        params={"new_status": "PAUSED"},
    )
    assert resp.status_code == 404
