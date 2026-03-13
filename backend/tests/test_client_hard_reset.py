"""Tests for client hard reset endpoint."""

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    ActionLog,
    Ad,
    AdGroup,
    Alert,
    Campaign,
    ChangeEvent,
    Client,
    Keyword,
    KeywordDaily,
    MetricDaily,
    NegativeKeyword,
    Recommendation,
    SearchTerm,
    SyncLog,
)


class _ApiClientFixture:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        def _override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)
        self.client.__enter__()
        return self.client

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.__exit__(exc_type, exc_value, traceback)
        app.dependency_overrides.pop(get_db, None)


def _seed_client_runtime_data(db, suffix: str):
    client = Client(
        name=f'Client {suffix}',
        google_customer_id=f'123-456-78{suffix}',
        last_change_sync_at=datetime.now(timezone.utc),
    )
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id=f'camp-{suffix}',
        name=f'Campaign {suffix}',
        status='ENABLED',
        campaign_type='SEARCH',
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id=f'ag-{suffix}',
        name=f'Ad Group {suffix}',
        status='ENABLED',
    )
    db.add(ad_group)
    db.flush()

    keyword = Keyword(
        ad_group_id=ad_group.id,
        google_keyword_id=f'kw-{suffix}',
        text=f'keyword {suffix}',
        match_type='EXACT',
        status='ENABLED',
    )
    db.add(keyword)
    db.flush()

    db.add(Ad(
        ad_group_id=ad_group.id,
        google_ad_id=f'ad-{suffix}',
        ad_type='RESPONSIVE_SEARCH_AD',
        status='ENABLED',
    ))
    db.add(SearchTerm(
        ad_group_id=ad_group.id,
        campaign_id=campaign.id,
        text=f'search term {suffix}',
        keyword_text=keyword.text,
        match_type='EXACT',
        source='SEARCH',
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 7),
    ))
    db.add(KeywordDaily(
        keyword_id=keyword.id,
        date=date(2026, 3, 1),
        clicks=5,
        impressions=50,
    ))
    db.add(MetricDaily(
        campaign_id=campaign.id,
        date=date(2026, 3, 1),
        clicks=10,
        impressions=100,
    ))

    recommendation = Recommendation(
        client_id=client.id,
        rule_id=f'rule-{suffix}',
        entity_type='keyword',
        entity_id=str(keyword.id),
        entity_name=keyword.text,
        reason='reset me',
        suggested_action='{}',
        status='pending',
    )
    db.add(recommendation)
    db.flush()

    db.add(ActionLog(
        client_id=client.id,
        recommendation_id=recommendation.id,
        action_type='PAUSE_KEYWORD',
        entity_type='keyword',
        entity_id=str(keyword.id),
        status='SUCCESS',
    ))
    db.add(Alert(
        client_id=client.id,
        alert_type='SPEND_SPIKE',
        severity='HIGH',
        title=f'Alert {suffix}',
    ))
    db.add(ChangeEvent(
        client_id=client.id,
        resource_name=f'customers/123/changeEvents/{suffix}',
        change_date_time=datetime(2026, 3, 1, 12, 0, 0),
        client_type='GOOGLE_ADS_WEB_CLIENT',
        change_resource_type='CAMPAIGN',
        resource_change_operation='UPDATE',
    ))
    db.add(NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        text=f'negative {suffix}',
    ))
    db.add(SyncLog(
        client_id=client.id,
        status='success',
        days=30,
    ))

    db.commit()
    return client


def test_hard_reset_clears_only_selected_client_runtime_data(db):
    target_client = _seed_client_runtime_data(db, '01')
    other_client = _seed_client_runtime_data(db, '02')

    with _ApiClientFixture(db) as api_client:
        response = api_client.post(f'/api/v1/clients/{target_client.id}/hard-reset')

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert payload['deleted_campaigns'] == 1
    assert payload['deleted_recommendations'] == 1
    assert payload['deleted_action_logs'] == 1
    assert payload['deleted_alerts'] == 1
    assert payload['deleted_change_events'] == 1
    assert payload['deleted_negative_keywords'] == 1
    assert payload['deleted_sync_logs'] == 1

    db.expire_all()

    assert db.get(Client, target_client.id) is not None
    assert db.get(Client, target_client.id).last_change_sync_at is None
    assert db.query(Campaign).filter(Campaign.client_id == target_client.id).count() == 0
    assert db.query(Recommendation).filter(Recommendation.client_id == target_client.id).count() == 0
    assert db.query(ActionLog).filter(ActionLog.client_id == target_client.id).count() == 0
    assert db.query(Alert).filter(Alert.client_id == target_client.id).count() == 0
    assert db.query(ChangeEvent).filter(ChangeEvent.client_id == target_client.id).count() == 0
    assert db.query(NegativeKeyword).filter(NegativeKeyword.client_id == target_client.id).count() == 0
    assert db.query(SyncLog).filter(SyncLog.client_id == target_client.id).count() == 0

    assert db.query(Campaign).filter(Campaign.client_id == other_client.id).count() == 1
    assert db.query(Recommendation).filter(Recommendation.client_id == other_client.id).count() == 1
    assert db.query(ActionLog).filter(ActionLog.client_id == other_client.id).count() == 1
    assert db.query(Alert).filter(Alert.client_id == other_client.id).count() == 1
    assert db.query(ChangeEvent).filter(ChangeEvent.client_id == other_client.id).count() == 1
    assert db.query(NegativeKeyword).filter(NegativeKeyword.client_id == other_client.id).count() == 1
    assert db.query(SyncLog).filter(SyncLog.client_id == other_client.id).count() == 1
