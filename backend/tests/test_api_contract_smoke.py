"""API contract smoke tests for core endpoint groups."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.recommendation import Recommendation


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
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


def _seed_contract_data(db):
    client = Client(name="Smoke Client", google_customer_id="222-222-2222")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id=f"camp-{client.id}",
        name="Contract Campaign",
        status="ENABLED",
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id=f"ag-{campaign.id}",
        name="Contract Group",
        status="ENABLED",
    )
    db.add(ad_group)
    db.flush()

    kw = Keyword(
        ad_group_id=ad_group.id,
        google_keyword_id=f"kw-{ad_group.id}",
        criterion_kind="POSITIVE",
        text="contract keyword",
        match_type="EXACT",
        status="ENABLED",
        clicks=10,
        impressions=100,
        cost_micros=5_000_000,
    )
    db.add(kw)
    db.add(
        NegativeKeyword(
            client_id=client.id,
            campaign_id=campaign.id,
            ad_group_id=ad_group.id,
            google_criterion_id=f"neg-{ad_group.id}",
            criterion_kind="NEGATIVE",
            text="contract negative",
            match_type="PHRASE",
            negative_scope="AD_GROUP",
            status="ENABLED",
            source="GOOGLE_ADS_SYNC",
        )
    )
    db.flush()

    rec = Recommendation(
        client_id=client.id,
        rule_id="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id=str(kw.id),
        entity_name=kw.text,
        priority="HIGH",
        category="RECOMMENDATION",
        reason="contract smoke",
        suggested_action=json.dumps(
            {
                "type": "PAUSE_KEYWORD",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "entity_name": kw.text,
            }
        ),
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return client, rec


def _routes_set():
    available = set()
    for route in app.routes:
        if not route.path.startswith("/api/v1"):
            continue
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            available.add((method, route.path))
    return available


def test_contract_routes_exist_for_critical_groups():
    expected = {
        ("GET", "/api/v1/auth/status"),
        ("GET", "/api/v1/clients/"),
        ("POST", "/api/v1/sync/trigger"),
        ("GET", "/api/v1/sync/status"),
        ("GET", "/api/v1/negative-keywords/"),
        ("GET", "/api/v1/recommendations/"),
        ("POST", "/api/v1/recommendations/{recommendation_id}/apply"),
        ("GET", "/api/v1/actions/"),
        ("POST", "/api/v1/actions/revert/{action_log_id}"),
        ("GET", "/api/v1/analytics/kpis"),
    }

    available = _routes_set()
    missing = sorted(expected - available)
    assert not missing, f"Missing contract routes: {missing}"


def test_contract_smoke_across_auth_clients_sync_recommendations_actions_analytics(api_client, db):
    client_obj, recommendation = _seed_contract_data(db)

    checks = [
        ("get", "/api/v1/auth/status", None, 200),
        ("get", "/api/v1/clients/", {"page": 1, "page_size": 20}, 200),
        ("get", "/api/v1/sync/status", None, 200),
        ("get", "/api/v1/negative-keywords/", {"client_id": client_obj.id}, 200),
        ("post", "/api/v1/sync/trigger", {"client_id": client_obj.id, "days": 7}, 200),
        ("get", "/api/v1/recommendations/", {"client_id": client_obj.id}, 200),
        (
            "post",
            f"/api/v1/recommendations/{recommendation.id}/apply",
            {"client_id": client_obj.id, "dry_run": True},
            200,
        ),
        ("get", "/api/v1/actions/", {"client_id": client_obj.id}, 200),
        ("post", "/api/v1/actions/revert/999999", {"client_id": client_obj.id}, 404),
        ("get", "/api/v1/analytics/kpis", {"client_id": client_obj.id}, 200),
    ]

    for method, path, params, expected_status in checks:
        response = getattr(api_client, method)(path, params=params)
        assert response.status_code == expected_status, (
            f"Unexpected status for {method.upper()} {path}: "
            f"expected {expected_status}, got {response.status_code}, body={response.text}"
        )


