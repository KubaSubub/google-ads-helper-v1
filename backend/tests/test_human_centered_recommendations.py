"""Human-centered recommendation guardrail tests."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.metric_daily import MetricDaily
from app.services.recommendation_contract import (
    ACTION,
    BLOCKED_BY_CONTEXT,
    INSUFFICIENT_DATA,
    INSIGHT_ONLY,
    ROLE_MISMATCH,
    ROAS_ONLY_SIGNAL,
)
from app.services.recommendations import recommendations_engine


@pytest.fixture
def db():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed_client(db, name='Nike', website='https://nike.com', business_rules=None):
    client = Client(
        name=name,
        website=website,
        google_customer_id=f'{name[:3].upper()}-123-4567',
        business_rules=business_rules or {'min_roas': 2.0},
    )
    db.add(client)
    db.flush()
    return client


def _seed_campaign(db, client_id, google_campaign_id, name, campaign_type='SEARCH', budget_usd=100, lost_is=0.0):
    campaign = Campaign(
        client_id=client_id,
        google_campaign_id=google_campaign_id,
        name=name,
        campaign_type=campaign_type,
        status='ENABLED',
        budget_micros=int(budget_usd * 1_000_000),
        search_budget_lost_is=lost_is,
    )
    db.add(campaign)
    db.flush()
    return campaign


def _add_metrics(db, campaign, days, daily_cost, daily_value, daily_conversions, clicks=80, impressions=1000):
    today = date.today()
    daily_cost_micros = int(daily_cost * 1_000_000)
    daily_value_micros = int(daily_value * 1_000_000)
    avg_cpc = int(daily_cost_micros / max(clicks, 1))
    ctr = (clicks / impressions * 100) if impressions else 0
    cvr = (daily_conversions / clicks * 100) if clicks else 0
    roas = (daily_value / daily_cost) if daily_cost else 0

    for offset in range(days):
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=today - timedelta(days=offset),
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            conversions=daily_conversions,
            conversion_rate=cvr,
            cost_micros=daily_cost_micros,
            conversion_value_micros=daily_value_micros,
            roas=roas,
            avg_cpc_micros=avg_cpc,
        ))


def test_reallocate_budget_blocks_role_mismatch_between_brand_and_pmax(db):
    client = _seed_client(db)
    brand = _seed_campaign(db, client.id, 'brand', 'Nike Brand Search', budget_usd=60, lost_is=0.25)
    pmax = _seed_campaign(db, client.id, 'pmax', 'Main PMax', campaign_type='PERFORMANCE_MAX', budget_usd=220, lost_is=0.05)

    _add_metrics(db, brand, days=7, daily_cost=10, daily_value=120, daily_conversions=2)
    _add_metrics(db, pmax, days=7, daily_cost=35, daily_value=50, daily_conversions=2)
    db.commit()

    recommendations = recommendations_engine.generate_all(db, client.id, 30)
    candidate = next(rec for rec in recommendations if rec['type'] == 'REALLOCATE_BUDGET')

    assert candidate['context_outcome'] == BLOCKED_BY_CONTEXT
    assert candidate['blocked_reasons'] == [ROLE_MISMATCH]
    assert candidate['action_payload']['action_type'] == 'REALLOCATE_BUDGET'
    assert candidate['action_payload']['executable'] is False
    assert candidate['evidence_json']['context']['primary_campaign_role'] == 'BRAND'
    assert candidate['evidence_json']['context']['counterparty_campaign_role'] == 'PMAX'


def test_reallocate_budget_allows_generic_to_generic_with_headroom(db):
    client = _seed_client(db, name='Generic Store', website='https://genericshop.com')
    best = _seed_campaign(db, client.id, 'generic-best', 'Generic Search Winners', budget_usd=50, lost_is=0.30)
    worst = _seed_campaign(db, client.id, 'generic-worst', 'Generic Search Costly', budget_usd=200, lost_is=0.05)

    _add_metrics(db, best, days=7, daily_cost=10, daily_value=60, daily_conversions=2)
    _add_metrics(db, worst, days=7, daily_cost=35, daily_value=40, daily_conversions=2)
    db.commit()

    recommendations = recommendations_engine.generate_all(db, client.id, 30)
    candidate = next(rec for rec in recommendations if rec['type'] == 'REALLOCATE_BUDGET')

    assert candidate['context_outcome'] == ACTION
    assert candidate['blocked_reasons'] == []
    assert candidate['downgrade_reasons'] == []
    assert candidate['action_payload']['action_type'] == 'REALLOCATE_BUDGET'
    assert candidate['action_payload']['executable'] is False
    assert candidate['evidence_json']['context']['primary_campaign_role'] == 'GENERIC'
    assert candidate['evidence_json']['context']['counterparty_campaign_role'] == 'GENERIC'
    assert candidate['evidence_json']['context']['comparable'] is True
    assert candidate['evidence_json']['context']['can_scale'] is True


def test_budget_alert_becomes_action_when_campaign_has_scale_headroom(db):
    client = _seed_client(db, name='Scale Store', website='https://scalestore.com')
    campaign = _seed_campaign(db, client.id, 'scale', 'Generic Search Scale', budget_usd=80, lost_is=0.35)

    _add_metrics(db, campaign, days=7, daily_cost=16, daily_value=64, daily_conversions=1)
    db.commit()

    recommendations = recommendations_engine.generate_all(db, client.id, 30)
    budget_rec = next(rec for rec in recommendations if rec['type'] == 'IS_BUDGET_ALERT')

    assert budget_rec['context_outcome'] == ACTION
    assert budget_rec['action_payload']['action_type'] == 'INCREASE_BUDGET'
    assert budget_rec['action_payload']['executable'] is True
    assert budget_rec['evidence_json']['context']['can_scale'] is True


def test_budget_alert_downgrades_when_signal_is_roas_only_or_insufficient(db):
    client = _seed_client(db, name='Weak Signal', website='https://weaksignal.com')
    campaign = _seed_campaign(db, client.id, 'weak', 'Generic Search Weak', budget_usd=90, lost_is=0.40)

    _add_metrics(db, campaign, days=7, daily_cost=18, daily_value=22, daily_conversions=0.2)
    db.commit()

    recommendations = recommendations_engine.generate_all(db, client.id, 30)
    budget_rec = next(rec for rec in recommendations if rec['type'] == 'IS_BUDGET_ALERT')

    assert budget_rec['context_outcome'] == INSIGHT_ONLY
    assert budget_rec['action_payload']['executable'] is False
    assert any(code in budget_rec['downgrade_reasons'] for code in [ROAS_ONLY_SIGNAL, INSUFFICIENT_DATA])
    assert budget_rec['evidence_json']['context']['can_scale'] is False


def test_recommendations_api_exposes_context_and_explanation_fields(api_client, db):
    client = _seed_client(db, name='API Store', website='https://apistore.com')
    best = _seed_campaign(db, client.id, 'api-best', 'Generic Search Best', budget_usd=45, lost_is=0.25)
    worst = _seed_campaign(db, client.id, 'api-worst', 'Generic Search Worst', budget_usd=180, lost_is=0.05)

    _add_metrics(db, best, days=7, daily_cost=9, daily_value=60, daily_conversions=2)
    _add_metrics(db, worst, days=7, daily_cost=35, daily_value=35, daily_conversions=2)
    db.commit()

    response = api_client.get('/api/v1/recommendations/', params={'client_id': client.id})
    assert response.status_code == 200, response.text

    body = response.json()
    candidate = next(rec for rec in body['recommendations'] if rec['type'] == 'REALLOCATE_BUDGET')

    assert candidate['context_outcome'] == ACTION
    assert isinstance(candidate['blocked_reasons'], list)
    assert isinstance(candidate['downgrade_reasons'], list)
    assert candidate['evidence_json']['context']['primary_campaign_role'] == 'GENERIC'
    assert isinstance(candidate['why_allowed'], list)
    assert isinstance(candidate['why_blocked'], list)
    assert isinstance(candidate['tradeoffs'], list)
    assert candidate['risk_note']['code']
    assert candidate['next_best_action']['code']

