"""Tests for actions router — list actions and revert."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.action_log import ActionLog
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_actions(db):
    """Seed client, campaign, keyword, and action log entries."""
    client = Client(name="Actions Client", google_customer_id="5550001110")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="ac1",
        name="Actions Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="aag1",
        name="Actions Group",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    kw = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="akw1",
        text="buty do biegania",
        match_type="EXACT",
        status="ENABLED",
        clicks=50,
        impressions=500,
        cost_micros=10_000_000,
        conversions=3.0,
        ctr=10.0,
        avg_cpc_micros=200_000,
    )
    db.add(kw)
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    action1 = ActionLog(
        client_id=client.id,
        action_type="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id=str(kw.id),
        old_value_json=json.dumps({"status": "ENABLED"}),
        new_value_json=json.dumps({"status": "PAUSED"}),
        status="SUCCESS",
        execution_mode="LOCAL",
        executed_at=now,
    )
    action2 = ActionLog(
        client_id=client.id,
        action_type="UPDATE_BID",
        entity_type="keyword",
        entity_id=str(kw.id),
        old_value_json=json.dumps({"bid_micros": 200_000}),
        new_value_json=json.dumps({"bid_micros": 300_000}),
        status="SUCCESS",
        execution_mode="LOCAL",
        executed_at=now,
    )
    action3 = ActionLog(
        client_id=client.id,
        action_type="INCREASE_BUDGET",
        entity_type="campaign",
        entity_id=str(campaign.id),
        old_value_json=json.dumps({"budget_micros": 50_000_000}),
        new_value_json=json.dumps({"budget_micros": 75_000_000}),
        status="SUCCESS",
        execution_mode="LOCAL",
        executed_at=now,
    )

    db.add_all([action1, action2, action3])
    db.commit()
    return client, campaign, kw, action1, action2, action3


# ---------------------------------------------------------------------------
# List actions
# ---------------------------------------------------------------------------


class TestListActions:
    def test_returns_actions_for_client(self, api_client, db):
        client, _, _, _, _, _ = _seed_actions(db)

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 3
        assert len(data["actions"]) == 3

    def test_actions_include_required_fields(self, api_client, db):
        client, _, _, _, _, _ = _seed_actions(db)

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}")
        action = resp.json()["actions"][0]

        required_fields = [
            "id", "action_type", "entity_type", "entity_id",
            "status", "old_value_json", "new_value_json", "executed_at",
        ]
        for field in required_fields:
            assert field in action, f"Missing field: {field}"

    def test_enriches_keyword_entity_name(self, api_client, db):
        client, _, kw, _, _, _ = _seed_actions(db)

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}")
        actions = resp.json()["actions"]

        keyword_actions = [a for a in actions if a["entity_type"] == "keyword"]
        assert len(keyword_actions) >= 1

        for action in keyword_actions:
            assert action["entity_name"] == "buty do biegania"

    def test_enriches_campaign_name(self, api_client, db):
        client, campaign, _, _, _, _ = _seed_actions(db)

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}")
        actions = resp.json()["actions"]

        campaign_action = next((a for a in actions if a["entity_type"] == "campaign"), None)
        assert campaign_action is not None
        assert campaign_action["entity_name"] == "Actions Campaign"
        assert campaign_action["campaign_name"] == "Actions Campaign"

    def test_empty_result_for_nonexistent_client(self, api_client, db):
        resp = api_client.get("/api/v1/actions/?client_id=99999")
        data = resp.json()
        assert data["total"] == 0
        assert data["actions"] == []

    def test_limit_and_offset(self, api_client, db):
        client, _, _, _, _, _ = _seed_actions(db)

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}&limit=2&offset=0")
        data = resp.json()
        assert len(data["actions"]) == 2
        assert data["total"] == 3

        resp2 = api_client.get(f"/api/v1/actions/?client_id={client.id}&limit=2&offset=2")
        data2 = resp2.json()
        assert len(data2["actions"]) == 1

    def test_returns_ordered_by_executed_at(self, api_client, db):
        """Actions should be returned ordered by executed_at descending."""
        client = Client(name="Order Client", google_customer_id="5550009990")
        db.add(client)
        db.flush()

        # Create actions with distinct timestamps
        from datetime import timedelta
        base_time = datetime(2026, 3, 1, 12, 0, 0)

        for i in range(3):
            db.add(ActionLog(
                client_id=client.id,
                action_type="PAUSE_KEYWORD",
                entity_type="keyword",
                entity_id=str(100 + i),
                status="SUCCESS",
                execution_mode="LOCAL",
                executed_at=base_time + timedelta(hours=i),
            ))
        db.commit()

        resp = api_client.get(f"/api/v1/actions/?client_id={client.id}")
        actions = resp.json()["actions"]

        # Most recent first
        timestamps = [a["executed_at"] for a in actions]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_does_not_return_other_clients_actions(self, api_client, db):
        client, _, _, _, _, _ = _seed_actions(db)

        # Create another client with no actions
        other_client = Client(name="Other Client", google_customer_id="5550002220")
        db.add(other_client)
        db.commit()

        resp = api_client.get(f"/api/v1/actions/?client_id={other_client.id}")
        data = resp.json()
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Revert action
# ---------------------------------------------------------------------------


class TestRevertAction:
    def test_revert_nonexistent_action_404(self, api_client, db):
        client, _, _, _, _, _ = _seed_actions(db)

        resp = api_client.post(
            f"/api/v1/actions/revert/99999?client_id={client.id}"
        )
        assert resp.status_code == 404

    def test_revert_wrong_client_404(self, api_client, db):
        """Action from client A cannot be reverted using client B's ID."""
        client, _, _, action1, _, _ = _seed_actions(db)

        other_client = Client(name="Wrong Client", google_customer_id="5550003330")
        db.add(other_client)
        db.commit()

        resp = api_client.post(
            f"/api/v1/actions/revert/{action1.id}?client_id={other_client.id}"
        )
        assert resp.status_code == 404
