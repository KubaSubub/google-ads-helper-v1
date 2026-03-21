"""Recommendation engine contract tests (active rules and deterministic filtering)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.client import Client
from app.services.recommendations import RecommendationType


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


def test_recommendation_type_enum_matches_active_ruleset():
    expected = {
        "PAUSE_KEYWORD",
        "INCREASE_BID",
        "DECREASE_BID",
        "ADD_KEYWORD",
        "ADD_NEGATIVE",
        "PAUSE_AD",
        "REALLOCATE_BUDGET",
        "QS_ALERT",
        "IS_BUDGET_ALERT",
        "IS_RANK_ALERT",
        "WASTED_SPEND_ALERT",
        "PMAX_CANNIBALIZATION",
        "DEVICE_ANOMALY",
        "GEO_ANOMALY",
        "BUDGET_PACING",
        "NGRAM_NEGATIVE",
        "ANALYTICS_ALERT",
        # v2.0 GAP rules (Phase A)
        "AD_GROUP_HEALTH",
        "DISAPPROVED_AD_ALERT",
        "SMART_BIDDING_CONV_ALERT",
        "ECPC_DEPRECATION",
        "SCALING_OPPORTUNITY",
        # v2.0 GAP rules (Phase B+C)
        "TARGET_DEVIATION_ALERT",
        "LEARNING_PERIOD_ALERT",
        "CONVERSION_QUALITY_ALERT",
        "DEMOGRAPHIC_ANOMALY",
        # v2.1 rules (R28-R31)
        "PMAX_CHANNEL_IMBALANCE",
        "ASSET_GROUP_AD_STRENGTH",
        "AUDIENCE_PERFORMANCE_ANOMALY",
        "MISSING_EXTENSIONS_ALERT",
    }
    actual = {member.value for member in RecommendationType}

    assert expected == actual
    assert len(actual) == 30


def test_recommendations_filters_are_deterministic(api_client, db, monkeypatch):
    client = Client(name="Rules Client", google_customer_id="333-333-3333")
    db.add(client)
    db.commit()

    generated = [
        {
            "type": "PAUSE_KEYWORD",
            "priority": "HIGH",
            "entity_type": "keyword",
            "entity_id": 1001,
            "entity_name": "kw high",
            "campaign_name": "C1",
            "reason": "high",
            "category": "RECOMMENDATION",
            "source": "PLAYBOOK_RULES",
            "executable": True,
            "action_payload": {"action_type": "PAUSE_KEYWORD", "executable": True},
            "metadata": {"k": 1},
        },
        {
            "type": "QS_ALERT",
            "priority": "MEDIUM",
            "entity_type": "keyword",
            "entity_id": 1002,
            "entity_name": "kw medium",
            "campaign_name": "C1",
            "reason": "medium",
            "category": "ALERT",
            "source": "ANALYTICS",
            "executable": False,
            "action_payload": {"action_type": None, "executable": False},
            "metadata": {"k": 2},
        },
    ]

    def _fake_generate_all(_db, _client_id, _days):
        return generated

    monkeypatch.setattr(
        "app.routers.recommendations.recommendations_engine.generate_all",
        _fake_generate_all,
    )

    all_resp = api_client.get("/api/v1/recommendations/", params={"client_id": client.id})
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 2
    assert all_resp.json()["by_source"]["PLAYBOOK_RULES"] == 1

    high_resp = api_client.get(
        "/api/v1/recommendations/",
        params={"client_id": client.id, "priority": "HIGH"},
    )
    assert high_resp.status_code == 200
    assert high_resp.json()["total"] == 1
    assert high_resp.json()["recommendations"][0]["type"] == "PAUSE_KEYWORD"

    alert_resp = api_client.get(
        "/api/v1/recommendations/",
        params={"client_id": client.id, "category": "ALERT"},
    )
    assert alert_resp.status_code == 200
    assert alert_resp.json()["total"] == 1
    assert alert_resp.json()["recommendations"][0]["type"] == "QS_ALERT"

    analytics_resp = api_client.get(
        "/api/v1/recommendations/",
        params={"client_id": client.id, "source": "ANALYTICS", "executable": False},
    )
    assert analytics_resp.status_code == 200
    assert analytics_resp.json()["total"] == 1
    assert analytics_resp.json()["recommendations"][0]["source"] == "ANALYTICS"
