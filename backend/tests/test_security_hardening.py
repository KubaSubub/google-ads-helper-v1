"""Security hardening tests: auth, OAuth state, action mapping/safety."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.action_types import ActionType, map_action_type
from app.services.google_ads import GoogleAdsService
from app.services.session_service import SessionService
from app.models import Client, Campaign, AdGroup, Keyword


def test_protected_endpoint_requires_token():
    client = TestClient(app)
    response = client.get('/api/v1/clients/?page=1&page_size=20')
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(SessionService, 'is_valid', lambda token: False)

    response = client.get(
        '/api/v1/clients/?page=1&page_size=20',
        headers={'Authorization': 'Bearer invalid-token'},
    )
    assert response.status_code == 403


def test_oauth_state_validation_rejects_missing_or_wrong():
    SessionService.clear_oauth_state()
    SessionService.issue_oauth_state()

    assert SessionService.verify_oauth_state(None) is False

    SessionService.issue_oauth_state()
    assert SessionService.verify_oauth_state('wrong-state') is False


def test_action_type_mapping_is_explicit():
    assert map_action_type('INCREASE_BID') == ActionType.UPDATE_BID
    assert map_action_type('DECREASE_BID') == ActionType.UPDATE_BID
    assert map_action_type('SET_KEYWORD_BID') == ActionType.SET_KEYWORD_BID


def test_google_ads_apply_action_blocks_unsafe_bid(db):
    client = Client(name='C', google_customer_id='111')
    db.add(client)
    db.commit()

    campaign = Campaign(client_id=client.id, name='Camp', google_campaign_id='c1', status='ENABLED', budget_micros=100000000)
    db.add(campaign)
    db.commit()

    ad_group = AdGroup(campaign_id=campaign.id, name='AG', google_ad_group_id='ag1', status='ENABLED')
    db.add(ad_group)
    db.commit()

    keyword = Keyword(
        ad_group_id=ad_group.id,
        text='kw',
        google_keyword_id='kw-1',
        match_type='EXACT',
        status='ENABLED',
        bid_micros=1_000_000,
        clicks=10,
        impressions=100,
        cost_micros=0,
        conversions=0,
    )
    db.add(keyword)
    db.commit()

    service = GoogleAdsService()
    result = service.apply_action(
        db,
        action_type='UPDATE_BID',
        entity_id=keyword.id,
        params={'amount': 200.0},
        client_id=client.id,
    )

    assert result['status'] == 'error'
    assert 'Safety violation' in result['message']
