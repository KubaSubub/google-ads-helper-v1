"""Write action flow tests: apply/revert safety and status behavior."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.action_log import ActionLog
from app.models.ad import Ad
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


def _seed_client_tree(db, keyword_count=5):
    client = Client(name="Write Flow Client", google_customer_id="111-111-1111")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id=f"camp-{client.id}",
        name="Campaign A",
        status="ENABLED",
        budget_micros=100_000_000,
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

    ad = Ad(
        ad_group_id=ad_group.id,
        google_ad_id=f"ad-{ad_group.id}",
        ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED",
        headlines=[{"text": "Headline"}],
        descriptions=[{"text": "Description"}],
        clicks=20,
        impressions=500,
        cost_micros=15_000_000,
        conversions=0,
        ctr=40_000,
    )
    db.add(ad)

    db.commit()
    return client, campaign, ad_group, keywords, ad


def _create_recommendation(
    db,
    client_id,
    rule_id,
    entity_type,
    entity_id,
    entity_name,
    action_payload,
    campaign_id=None,
    ad_group_id=None,
    source="PLAYBOOK_RULES",
    executable=True,
):
    rec = Recommendation(
        client_id=client_id,
        rule_id=rule_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_name=entity_name,
        priority="HIGH",
        category="RECOMMENDATION",
        source=source,
        stable_key=f"{rule_id}|{client_id}|{entity_type}|{entity_id}|{entity_name}",
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        reason="test",
        suggested_action=json.dumps(action_payload),
        action_payload=action_payload,
        evidence_json={"metadata": {}, "recommended_action": rule_id},
        executable=executable,
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _pause_keyword_payload(keyword_id, campaign_id):
    return {
        "action_type": "PAUSE_KEYWORD",
        "target": {
            "entity_type": "keyword",
            "entity_id": keyword_id,
            "campaign_id": campaign_id,
            "ad_group_id": None,
            "google_resource_name": None,
        },
        "params": {},
        "preconditions": {"entity_exists": True, "expected_status": "ENABLED"},
        "revertability": {"can_revert": True, "window_hours": 24, "strategy": "ENABLE_KEYWORD"},
        "executable": True,
        "current_value": None,
        "new_value": None,
    }


def test_apply_recommendation_dry_run_does_not_mutate_state(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_KEYWORD",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        _pause_keyword_payload(keywords[0].id, campaign.id),
        campaign_id=campaign.id,
    )

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

    logs = db.query(ActionLog).all()
    assert len(logs) == 1
    assert logs[0].status == "DRY_RUN"
    assert logs[0].execution_mode == "DRY_RUN"


def test_apply_recommendation_live_success_updates_log_and_status(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_KEYWORD",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        _pause_keyword_payload(keywords[0].id, campaign.id),
        campaign_id=campaign.id,
    )

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
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=1)
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_KEYWORD",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        _pause_keyword_payload(keywords[0].id, campaign.id),
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )

    assert response.status_code == 422
    assert "Limit" in response.json()["detail"]

    db.refresh(rec)
    assert rec.status == "pending"
    logs = db.query(ActionLog).all()
    assert len(logs) == 1
    assert logs[0].status == "BLOCKED"
    assert logs[0].precondition_status == "FAILED"


def test_apply_recommendation_logs_failed_action_for_unknown_type(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=5)
    payload = {
        "action_type": "UNKNOWN_ACTION",
        "target": {"entity_type": "keyword", "entity_id": keywords[0].id, "campaign_id": campaign.id},
        "params": {},
        "preconditions": {"entity_exists": True},
        "revertability": {"can_revert": False, "window_hours": 0, "strategy": None},
        "executable": True,
        "current_value": None,
        "new_value": None,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "UNKNOWN_ACTION",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        payload,
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id, "dry_run": False},
    )

    assert response.status_code == 400

    failed_logs = db.query(ActionLog).filter(ActionLog.status == "FAILED").all()
    assert len(failed_logs) == 1
    assert failed_logs[0].action_type == "UNKNOWN_ACTION"


def test_apply_recommendation_update_bid_uses_canonical_payload(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=3)
    payload = {
        "action_type": "UPDATE_BID",
        "target": {"entity_type": "keyword", "entity_id": keywords[0].id, "campaign_id": campaign.id},
        "params": {"amount": 1.2, "amount_micros": 1_200_000, "change_pct": 20},
        "preconditions": {"entity_exists": True, "current_bid_micros": 1_000_000},
        "revertability": {"can_revert": True, "window_hours": 24, "strategy": "SET_KEYWORD_BID"},
        "executable": True,
        "current_value": 1.0,
        "new_value": 1.2,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "INCREASE_BID",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        payload,
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 200
    db.refresh(keywords[0])
    assert keywords[0].bid_micros == 1_200_000


def test_apply_recommendation_add_keyword_creates_keyword(api_client, db):
    client, campaign, ad_group, _, _ = _seed_client_tree(db, keyword_count=2)
    payload = {
        "action_type": "ADD_KEYWORD",
        "target": {"entity_type": "search_term", "entity_id": 0, "campaign_id": campaign.id, "ad_group_id": ad_group.id},
        "params": {"text": "new winner", "match_type": "PHRASE", "ad_group_id": ad_group.id},
        "preconditions": {"entity_exists": True, "keyword_absent": True},
        "revertability": {"can_revert": True, "window_hours": 24, "strategy": "PAUSE_KEYWORD"},
        "executable": True,
        "current_value": None,
        "new_value": None,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "ADD_KEYWORD",
        "search_term",
        0,
        "new winner",
        payload,
        campaign_id=campaign.id,
        ad_group_id=ad_group.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 200, response.text
    created = db.query(Keyword).filter(Keyword.ad_group_id == ad_group.id, Keyword.text == "new winner").first()
    assert created is not None
    assert created.status == "ENABLED"


def test_apply_recommendation_add_negative_creates_campaign_shadow(api_client, db):
    client, campaign, _, _, _ = _seed_client_tree(db, keyword_count=2)
    payload = {
        "action_type": "ADD_NEGATIVE",
        "target": {"entity_type": "search_term", "entity_id": 0, "campaign_id": campaign.id},
        "params": {"text": "free", "match_type": "PHRASE", "negative_level": "CAMPAIGN", "campaign_id": campaign.id},
        "preconditions": {"entity_exists": True},
        "revertability": {"can_revert": False, "window_hours": 0, "strategy": None},
        "executable": True,
        "current_value": None,
        "new_value": None,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "ADD_NEGATIVE",
        "search_term",
        0,
        "free",
        payload,
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 200, response.text
    negative = db.query(NegativeKeyword).filter(NegativeKeyword.campaign_id == campaign.id, NegativeKeyword.text == "free").first()
    assert negative is not None
    assert negative.level == "CAMPAIGN"


def test_apply_recommendation_increase_budget_updates_campaign(api_client, db):
    client, campaign, _, _, _ = _seed_client_tree(db, keyword_count=2)
    payload = {
        "action_type": "INCREASE_BUDGET",
        "target": {"entity_type": "campaign", "entity_id": campaign.id, "campaign_id": campaign.id},
        "params": {"amount": 120.0, "amount_micros": 120_000_000, "change_pct": 20},
        "preconditions": {"entity_exists": True, "current_budget_micros": 100_000_000},
        "revertability": {"can_revert": True, "window_hours": 24, "strategy": "SET_BUDGET"},
        "executable": True,
        "current_value": 100.0,
        "new_value": 120.0,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "IS_BUDGET_ALERT",
        "campaign",
        campaign.id,
        campaign.name,
        payload,
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 200
    db.refresh(campaign)
    assert campaign.budget_micros == 120_000_000


def test_revert_success_and_second_revert_blocked(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=5)
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_KEYWORD",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        _pause_keyword_payload(keywords[0].id, campaign.id),
        campaign_id=campaign.id,
    )

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
    client, _, _, keywords, _ = _seed_client_tree(db, keyword_count=5)

    expired_log = ActionLog(
        client_id=client.id,
        recommendation_id=None,
        action_type="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id=str(keywords[0].id),
        old_value_json=json.dumps({"current_val": 1.0}),
        new_value_json=json.dumps({"new_val": 0.0}),
        status="SUCCESS",
        executed_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25),
        action_payload={
            "action_type": "PAUSE_KEYWORD",
            "target": {"entity_type": "keyword", "entity_id": keywords[0].id},
            "revertability": {"can_revert": True, "window_hours": 24, "strategy": "ENABLE_KEYWORD"},
        },
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




def test_apply_recommendation_pause_ad_updates_ad_status(api_client, db):
    client, campaign, _, _, ad = _seed_client_tree(db, keyword_count=2)
    payload = {
        "action_type": "PAUSE_AD",
        "target": {"entity_type": "ad", "entity_id": ad.id, "campaign_id": campaign.id},
        "params": {},
        "preconditions": {"entity_exists": True, "expected_status": "ENABLED"},
        "revertability": {"can_revert": False, "window_hours": 0, "strategy": None},
        "executable": True,
        "current_value": None,
        "new_value": None,
    }
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_AD",
        "ad",
        ad.id,
        "Headline",
        payload,
        campaign_id=campaign.id,
    )

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 200, response.text
    db.refresh(ad)
    assert ad.status == "PAUSED"


def test_apply_recommendation_blocks_when_recommendation_expired(api_client, db):
    client, campaign, _, keywords, _ = _seed_client_tree(db, keyword_count=3)
    rec = _create_recommendation(
        db,
        client.id,
        "PAUSE_KEYWORD",
        "keyword",
        keywords[0].id,
        keywords[0].text,
        _pause_keyword_payload(keywords[0].id, campaign.id),
        campaign_id=campaign.id,
    )
    rec.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    db.commit()

    response = api_client.post(
        f"/api/v1/recommendations/{rec.id}/apply",
        params={"client_id": client.id},
    )

    assert response.status_code == 422
    assert 'expired' in response.json()['detail'].lower()

    blocked_log = db.query(ActionLog).filter(ActionLog.recommendation_id == rec.id).order_by(ActionLog.id.desc()).first()
    assert blocked_log is not None
    assert blocked_log.status == 'BLOCKED'
    assert blocked_log.precondition_status == 'FAILED'

