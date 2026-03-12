"""Write action flow tests: apply/revert safety and status behavior."""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.action_log import ActionLog
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
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


def _seed_client_tree(db, keyword_count=5):
    client = Client(name="Write Flow Client", google_customer_id="111-111-1111")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id=f"camp-{client.id}",
        name="Campaign A",
        status="ENABLED",
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id=f"ag-{campaign.id}",
        name="AdGroup A",
        status="ENABLED",
    )
    db.add(ad_group)
    db.flush()

    keywords = []
    for idx in range(keyword_count):
        kw = Keyword(
            ad_group_id=ad_group.id,
            google_keyword_id=f"kw-{ad_group.id}-{idx}",
            text=f"keyword {idx}",
            match_type="EXACT",
            status="ENABLED",
            bid_micros=1_000_000,
            clicks=10,
            impressions=100,
            cost_micros=10_000_000,
            conversions=0,
        )
        db.add(kw)
        keywords.append(kw)

    db.commit()
    return client, campaign, ad_group, keywords


def _create_recommendation(db, client_id, keyword_id, campaign_id=None, action_type="PAUSE_KEYWORD"):
    action_payload = {
        "type": action_type,
        "entity_type": "keyword",
        "entity_id": keyword_id,
        "entity_name": "keyword",
    }
    if campaign_id is not None:
        action_payload["campaign_id"] = campaign_id

    rec = Recommendation(
        client_id=client_id,
        rule_id=action_type,
        entity_type="keyword",
        entity_id=str(keyword_id),
        entity_name="keyword",
        priority="HIGH",
        category="RECOMMENDATION",
        reason="test",
        suggested_action=json.dumps(action_payload),
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def test_apply_recommendation_dry_run_does_not_mutate_state(api_client, db):
    client, campaign, _, keywords = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(db, client.id, keywords[0].id, campaign.id)

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"

    db.refresh(rec)
    db.refresh(keywords[0])
    assert rec.status == "pending"
    assert keywords[0].status == "ENABLED"
    assert db.query(ActionLog).count() == 0


def test_apply_recommendation_live_success_updates_log_and_status(api_client, db):
    client, campaign, _, keywords = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(db, client.id, keywords[0].id, campaign.id)

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    db.refresh(rec)
    db.refresh(keywords[0])
    assert rec.status == "applied"
    assert rec.applied_at is not None
    assert keywords[0].status == "PAUSED"

    logs = db.query(ActionLog).all()
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].action_type == "PAUSE_KEYWORD"


def test_apply_recommendation_blocked_by_safety_limits(api_client, db):
    client, campaign, _, keywords = _seed_client_tree(db, keyword_count=1)
    rec = _create_recommendation(db, client.id, keywords[0].id, campaign.id)

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )

    assert response.status_code == 422
    assert "Limit" in response.json()["detail"]

    db.refresh(rec)
    assert rec.status == "pending"
    assert db.query(ActionLog).count() == 0


def test_apply_recommendation_logs_failed_action_for_unknown_type(api_client, db):
    client, _, _, keywords = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(
        db,
        client.id,
        keywords[0].id,
        campaign_id=None,
        action_type="UNKNOWN_ACTION",
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )

    assert response.status_code == 400

    failed_logs = db.query(ActionLog).filter(ActionLog.status == "FAILED").all()
    assert len(failed_logs) == 1
    assert failed_logs[0].action_type == "UNKNOWN_ACTION"


def test_revert_success_and_second_revert_blocked(api_client, db):
    client, campaign, _, keywords = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(db, client.id, keywords[0].id, campaign.id)

    apply_response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )
    assert apply_response.status_code == 200

    original_log = db.query(ActionLog).filter(ActionLog.action_type == "PAUSE_KEYWORD").first()
    assert original_log is not None

    revert_response = api_client.post(
        f"/api/v1/actions/revert/{original_log.id}",
        params={"client_id": client.id},
    )
    assert revert_response.status_code == 200
    assert revert_response.json()["status"] == "success"

    db.refresh(original_log)
    db.refresh(keywords[0])
    assert original_log.status == "REVERTED"
    assert original_log.reverted_at is not None
    assert keywords[0].status == "ENABLED"

    second_response = api_client.post(
        f"/api/v1/actions/revert/{original_log.id}",
        params={"client_id": client.id},
    )
    assert second_response.status_code == 400
    assert "Already reverted" in second_response.json()["detail"]


def test_revert_fails_after_24h_window(api_client, db):
    client, _, _, keywords = _seed_client_tree(db, keyword_count=5)

    expired_log = ActionLog(
        client_id=client.id,
        recommendation_id=None,
        action_type="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id=str(keywords[0].id),
        old_value_json=json.dumps({"current_val": 1.0}),
        new_value_json=json.dumps({"new_val": 0.0}),
        status="SUCCESS",
        executed_at=datetime.utcnow() - timedelta(hours=25),
    )
    db.add(expired_log)
    db.commit()
    db.refresh(expired_log)

    response = api_client.post(
        f"/api/v1/actions/revert/{expired_log.id}",
        params={"client_id": client.id},
    )

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
