from fastapi.testclient import TestClient

from app.main import app
from app.services.credentials_service import CredentialsService
from app.services.session_service import SESSION_COOKIE_NAME, SessionService


client = TestClient(app)


def test_protected_endpoint_requires_session_cookie():
    response = client.get('/api/v1/clients/')
    assert response.status_code == 401
    assert response.json()['detail'] == 'Missing authorization token'


def test_auth_status_reports_missing_configuration(monkeypatch):
    def fake_get(_key):
        return None

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))
    response = client.get('/api/v1/auth/status')
    data = response.json()

    assert response.status_code == 200
    assert data['authenticated'] is False
    assert data['configured'] is False
    assert set(data['missing']) >= {'developer_token', 'client_id', 'client_secret', 'refresh_token'}


def test_protected_endpoint_allows_valid_cookie(monkeypatch):
    values = {
        CredentialsService.DEVELOPER_TOKEN: 'dev',
        CredentialsService.CLIENT_ID: 'cid',
        CredentialsService.CLIENT_SECRET: 'secret',
        CredentialsService.REFRESH_TOKEN: 'refresh',
    }

    def fake_get(key):
        return values.get(key)

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))

    token = SessionService.issue()
    response = client.get('/api/v1/clients/', cookies={SESSION_COOKIE_NAME: token})

    assert response.status_code == 200
    assert 'items' in response.json()

def test_auth_status_bootstrap_issues_session_cookie(monkeypatch):
    values = {
        CredentialsService.DEVELOPER_TOKEN: 'dev',
        CredentialsService.CLIENT_ID: 'cid',
        CredentialsService.CLIENT_SECRET: 'secret',
        CredentialsService.REFRESH_TOKEN: 'refresh',
    }

    def fake_get(key):
        return values.get(key)

    monkeypatch.setattr(CredentialsService, 'get', staticmethod(fake_get))

    response = client.get('/api/v1/auth/status?bootstrap=1')
    assert response.status_code == 200
    assert response.json()['authenticated'] is True
    assert SESSION_COOKIE_NAME in response.cookies
