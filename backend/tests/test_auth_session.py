"""Auth, session and sync regression tests."""

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.sync_log import SyncLog
from app.services.credentials_service import CredentialPersistenceError, CredentialsService
from app.services.google_ads import google_ads_service
from app.services.session_service import SESSION_COOKIE_NAME, SessionService


@pytest.fixture(autouse=True)
def clear_sessions():
    SessionService.clear_all()
    yield
    SessionService.clear_all()


@pytest.fixture
def api_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed_client(db, name="Sync Client", customer_id="1234567890"):
    client = Client(name=name, google_customer_id=customer_id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _auth_cookies():
    return {SESSION_COOKIE_NAME: SessionService.issue()}


def test_protected_endpoint_requires_session_cookie(api_client):
    response = api_client.get('/api/v1/clients/')
    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing authorization token'


def test_auth_status_reports_missing_configuration(api_client, monkeypatch):
    def fake_get(_key):
        return None

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))
    response = api_client.get('/api/v1/auth/status')
    data = response.json()

    assert response.status_code == 200
    assert data['authenticated'] is False
    assert data['configured'] is False
    assert set(data['missing']) >= {'developer_token', 'client_id', 'client_secret', 'refresh_token'}


def test_protected_endpoint_allows_valid_cookie(api_client, monkeypatch):
    values = {
        CredentialsService.DEVELOPER_TOKEN: 'dev',
        CredentialsService.CLIENT_ID: 'cid',
        CredentialsService.CLIENT_SECRET: 'secret',
        CredentialsService.REFRESH_TOKEN: 'refresh',
    }

    def fake_get(key):
        return values.get(key)

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))

    response = api_client.get('/api/v1/clients/', cookies=_auth_cookies())

    assert response.status_code == 200
    assert 'items' in response.json()


def test_auth_status_bootstrap_issues_session_cookie(api_client, monkeypatch):
    values = {
        CredentialsService.DEVELOPER_TOKEN: 'dev',
        CredentialsService.CLIENT_ID: 'cid',
        CredentialsService.CLIENT_SECRET: 'secret',
        CredentialsService.REFRESH_TOKEN: 'refresh',
    }

    def fake_get(key):
        return values.get(key)

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))

    response = api_client.get('/api/v1/auth/status?bootstrap=1')
    assert response.status_code == 200
    assert response.json()['authenticated'] is True
    assert SESSION_COOKIE_NAME in response.cookies


def test_auth_setup_returns_error_when_secure_store_write_fails(api_client, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise CredentialPersistenceError("Nie udalo sie zapisac credentials w Windows Credential Manager.")

    monkeypatch.setattr("app.routers.auth.CredentialsService.save_and_verify", _raise)

    response = api_client.post(
        "/api/v1/auth/setup",
        json={
            "developer_token": "dev-token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "login_customer_id": "",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Nie udalo sie zapisac credentials w Windows Credential Manager."


def test_setup_values_returns_only_local_setup_credentials(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.CredentialsService.get_google_ads_credentials",
        lambda: {
            "developer_token": "dev-token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "refresh_token": "refresh-token",
            "login_customer_id": "9988776655",
        },
    )

    response = api_client.get("/api/v1/auth/setup-values")

    assert response.status_code == 200
    assert response.json() == {
        "developer_token": "dev-token",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "login_customer_id": "9988776655",
    }
    assert "refresh_token" not in response.json()


def test_auth_status_reports_not_ready_when_only_refresh_token_exists(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.services.google_ads.CredentialsService.get_google_ads_credentials",
        lambda: {
            "developer_token": None,
            "client_id": None,
            "client_secret": None,
            "refresh_token": "refresh-token",
            "login_customer_id": None,
        },
    )
    monkeypatch.setattr(
        "app.routers.auth.CredentialsService.get",
        lambda key: "refresh-token" if key == CredentialsService.REFRESH_TOKEN else None,
    )

    response = api_client.get("/api/v1/auth/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is False
    assert payload["oauth_authenticated"] is True
    assert payload["configured"] is False
    assert payload["ready"] is False
    assert set(payload["missing_credentials"]) == {
        CredentialsService.DEVELOPER_TOKEN,
        CredentialsService.CLIENT_ID,
        CredentialsService.CLIENT_SECRET,
    }
    assert "developer_token" in payload["reason"]


def test_discover_accounts_reads_mcc_from_secure_store(monkeypatch):
    class FakeCustomerClient:
        def __init__(self, customer_id, name, manager=False):
            self.id = customer_id
            self.descriptive_name = name
            self.manager = manager

    class FakeRow:
        def __init__(self, customer_id, name, manager=False):
            self.customer_client = FakeCustomerClient(customer_id, name, manager)

    class FakeSearchService:
        def __init__(self):
            self.called_customer_id = None

        def search(self, customer_id, query):
            self.called_customer_id = customer_id
            assert "customer_client" in query
            return [FakeRow(4567891234, "Managed Account")]

    class FakeClient:
        def __init__(self, service):
            self._service = service

        def get_service(self, name):
            assert name == "GoogleAdsService"
            return self._service

    fake_search_service = FakeSearchService()
    monkeypatch.setattr(
        "app.services.google_ads.CredentialsService.get",
        lambda key: "9988776655" if key == CredentialsService.LOGIN_CUSTOMER_ID else None,
    )
    monkeypatch.setattr(google_ads_service, "client", FakeClient(fake_search_service), raising=False)

    accounts = google_ads_service.discover_accounts()

    assert fake_search_service.called_customer_id == "9988776655"
    assert accounts == [{"customer_id": "4567891234", "name": "Managed Account"}]


def test_sync_campaigns_falls_back_to_minimal_query_when_extended_query_is_rejected(db, monkeypatch):
    client = _seed_client(db, customer_id="1234567890")

    class FakeEnum:
        def __init__(self, name):
            self.name = name

    class FakeCampaignBudget:
        def __init__(self, amount_micros):
            self.amount_micros = amount_micros

    class FakeCampaignRow:
        def __init__(self):
            self.campaign = type(
                "CampaignRowData",
                (),
                {
                    "id": 777,
                    "name": "Brand Search",
                    "status": FakeEnum("ENABLED"),
                    "advertising_channel_type": FakeEnum("SEARCH"),
                },
            )()
            self.campaign_budget = FakeCampaignBudget(1230000)

    class FakeSearchService:
        def __init__(self):
            self.calls = []

        def search(self, customer_id, query):
            self.calls.append((customer_id, query))
            if len(self.calls) == 1:
                raise RuntimeError("Request contains an invalid argument.")
            return [FakeCampaignRow()]

    class FakeClient:
        def __init__(self, service):
            self._service = service

        def get_service(self, name):
            assert name == "GoogleAdsService"
            return self._service

    fake_search_service = FakeSearchService()
    monkeypatch.setattr(google_ads_service, "client", FakeClient(fake_search_service), raising=False)

    synced = google_ads_service.sync_campaigns(db, "123-456-7890")

    assert synced == 1
    assert fake_search_service.calls[0][0] == "1234567890"
    assert fake_search_service.calls[1][0] == "1234567890"
    assert "campaign.bidding_strategy_type" in fake_search_service.calls[0][1]
    assert "campaign.bidding_strategy_type" not in fake_search_service.calls[1][1]

    campaign = db.query(Campaign).filter(Campaign.client_id == client.id).one()
    assert campaign.google_campaign_id == "777"
    assert campaign.name == "Brand Search"
    assert campaign.budget_micros == 1230000


def test_clients_discover_returns_explicit_error_when_mcc_missing(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.clients.google_ads_service.get_connection_diagnostics",
        lambda: {
            "authenticated": True,
            "configured": True,
            "ready": True,
            "connected": True,
            "reason": "Google Ads API jest gotowe do uzycia.",
            "missing_credentials": [],
            "has_login_customer_id": False,
        },
    )
    monkeypatch.setattr(
        "app.routers.clients.CredentialsService.get",
        lambda key: None,
    )

    response = api_client.post("/api/v1/clients/discover", cookies=_auth_cookies())

    assert response.status_code == 503
    assert "login_customer_id" in response.json()["detail"]


@pytest.mark.parametrize(
    ("campaign_result", "expected_status", "expected_success", "expected_message_fragment"),
    [
        (RuntimeError("campaigns boom"), "failed", False, "przerwana"),
        (5, "partial", False, "czesciowo"),
    ],
)
def test_sync_trigger_reports_failed_and_partial_states(
    api_client,
    db,
    monkeypatch,
    campaign_result,
    expected_status,
    expected_success,
    expected_message_fragment,
):
    client = _seed_client(db)

    monkeypatch.setattr(
        "app.routers.sync.google_ads_service.get_connection_diagnostics",
        lambda: {
            "authenticated": True,
            "configured": True,
            "ready": True,
            "connected": True,
            "reason": "Google Ads API jest gotowe do uzycia.",
            "missing_credentials": [],
            "has_login_customer_id": True,
        },
    )

    def _campaigns(*_args, **_kwargs):
        if isinstance(campaign_result, Exception):
            raise campaign_result
        return campaign_result

    def _phase_ok(result):
        def _inner(*_args, **_kwargs):
            return result
        return _inner

    def _phase_error(*_args, **_kwargs):
        raise RuntimeError("phase failure")

    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_campaigns", _campaigns)
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_campaign_impression_share", _phase_error)
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_ad_groups", _phase_ok(2))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_keywords", _phase_ok(1))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_keyword_daily", _phase_ok(1))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_daily_metrics", _phase_ok(3))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_device_metrics", _phase_ok(0))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_geo_metrics", _phase_ok(0))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_search_terms", _phase_ok(0))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_pmax_search_terms", _phase_ok(0))
    monkeypatch.setattr("app.routers.sync.google_ads_service.sync_change_events", _phase_ok(0))

    response = api_client.post(
        "/api/v1/sync/trigger",
        params={"client_id": client.id, "days": 30, "allow_demo_write": True},
        cookies=_auth_cookies(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == expected_status
    assert payload["success"] is expected_success
    assert expected_message_fragment in payload["message"]
    if isinstance(campaign_result, Exception):
        assert "campaigns boom" in payload["message"]

    sync_log = db.query(SyncLog).order_by(SyncLog.id.desc()).first()
    assert sync_log is not None
    assert sync_log.status == expected_status
