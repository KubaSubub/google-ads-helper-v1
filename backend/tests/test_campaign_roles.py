"""Campaign role classification and override contract tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.services.campaign_roles import (
    apply_manual_role_override,
    apply_role_classification,
    classify_campaign_role,
    extract_brand_signals,
)


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


@pytest.mark.parametrize(
    'client_obj,campaign_type,name,expected_role,expected_confidence',
    [
        (Client(name='Acme', google_customer_id='100-100-1000'), 'SEARCH', 'Warszawa Local Maps', 'LOCAL', 0.95),
        (Client(name='Acme', google_customer_id='100-100-1001'), 'PERFORMANCE_MAX', 'Acme PMax', 'PMAX', 0.95),
        (Client(name='Acme', google_customer_id='100-100-1002'), 'SEARCH', 'RLSA Remarketing Search', 'REMARKETING', 0.85),
        (Client(name='Nike', website='https://nike.com', google_customer_id='100-100-1003'), 'SEARCH', 'Nike Brand Search', 'BRAND', 0.85),
        (Client(name='Nike', website='https://nike.com', google_customer_id='100-100-1004'), 'SEARCH', 'Nonbrand Prospecting Search', 'PROSPECTING', 0.85),
        (Client(name='Nike', website='https://nike.com', google_customer_id='100-100-1005'), 'SEARCH', 'Generic Search Core', 'GENERIC', 0.65),
        (Client(name='Nike', website='https://nike.com', google_customer_id='100-100-1006'), 'DISPLAY', 'Awareness Video', 'UNKNOWN', 0.30),
    ],
)
def test_classify_campaign_roles_deterministically(client_obj, campaign_type, name, expected_role, expected_confidence):
    campaign = Campaign(
        client_id=1,
        google_campaign_id=f'camp-{expected_role.lower()}',
        name=name,
        campaign_type=campaign_type,
        status='ENABLED',
    )

    result = classify_campaign_role(campaign, client_obj)

    assert result.role == expected_role
    assert result.confidence == expected_confidence


def test_brand_token_extraction_normalizes_and_ignores_generic_tokens():
    generic_client = Client(
        name='Meble.pl',
        website='https://meble.pl',
        google_customer_id='200-200-2000',
    )
    tokens, _ = extract_brand_signals(generic_client)
    assert 'meble' not in tokens

    generic_campaign = Campaign(
        client_id=1,
        google_campaign_id='camp-generic',
        name='Meble Search',
        campaign_type='SEARCH',
        status='ENABLED',
    )
    assert classify_campaign_role(generic_campaign, generic_client).role == 'GENERIC'

    normalized_client = Client(
        name='Home&You',
        website='https://homeandyou.pl',
        google_customer_id='200-200-2001',
    )
    normalized_campaign = Campaign(
        client_id=1,
        google_campaign_id='camp-brand',
        name='HomeAndYou Brand Search',
        campaign_type='SEARCH',
        status='ENABLED',
    )
    result = classify_campaign_role(normalized_campaign, normalized_client)
    assert result.role == 'BRAND'
    assert result.confidence == 0.85


def test_manual_role_override_is_not_overwritten_by_auto_classification():
    client_obj = Client(name='Nike', website='https://nike.com', google_customer_id='300-300-3000')
    campaign = Campaign(
        client_id=1,
        google_campaign_id='camp-manual',
        name='Nike Brand Search',
        campaign_type='SEARCH',
        status='ENABLED',
    )

    apply_manual_role_override(campaign, 'PROSPECTING', client_obj)
    changed = apply_role_classification(campaign, client_obj)

    assert changed is False
    assert campaign.campaign_role_auto == 'BRAND'
    assert campaign.campaign_role_final == 'PROSPECTING'
    assert campaign.role_source == 'MANUAL'
    assert campaign.protection_level == 'LOW'
    assert campaign.role_confidence == 0.85


def test_campaign_role_override_endpoint_sets_and_resets_manual_role(api_client, db):
    client_obj = Client(
        name='Nike',
        website='https://nike.com',
        google_customer_id='400-400-4000',
    )
    db.add(client_obj)
    db.flush()

    campaign = Campaign(
        client_id=client_obj.id,
        google_campaign_id='camp-api',
        name='Nike Search',
        campaign_type='SEARCH',
        status='ENABLED',
        budget_micros=50_000_000,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    set_response = api_client.patch(
        f'/api/v1/campaigns/{campaign.id}',
        json={'campaign_role_final': 'PROSPECTING'},
    )
    assert set_response.status_code == 200, set_response.text
    set_body = set_response.json()
    assert set_body['campaign_role_auto'] == 'BRAND'
    assert set_body['campaign_role_final'] == 'PROSPECTING'
    assert set_body['role_source'] == 'MANUAL'
    assert set_body['protection_level'] == 'LOW'
    assert isinstance(set_body['role_confidence'], float)

    reset_response = api_client.patch(
        f'/api/v1/campaigns/{campaign.id}',
        json={'campaign_role_final': None},
    )
    assert reset_response.status_code == 200, reset_response.text
    reset_body = reset_response.json()
    assert reset_body['campaign_role_auto'] == 'BRAND'
    assert reset_body['campaign_role_final'] == 'BRAND'
    assert reset_body['role_source'] == 'AUTO'
    assert reset_body['protection_level'] == 'HIGH'

