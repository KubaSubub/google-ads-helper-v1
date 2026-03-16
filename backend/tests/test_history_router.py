"""Tests for history router — unified timeline, change events, filters."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.action_log import ActionLog
from app.models.change_event import ChangeEvent
from app.models.client import Client


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    client = Client(name="History Client", google_customer_id="7778889990")
    db.add(client)
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Recent action (< 24h) — should be revertable
    action_recent = ActionLog(
        client_id=client.id,
        action_type="INCREASE_BUDGET",
        entity_type="campaign",
        entity_id="1",
        status="SUCCESS",
        executed_at=now - timedelta(hours=2),
    )
    # Old action (> 24h) — should NOT be revertable
    action_old = ActionLog(
        client_id=client.id,
        action_type="SET_BID",
        entity_type="keyword",
        entity_id="10",
        status="SUCCESS",
        executed_at=now - timedelta(hours=30),
    )
    # ADD_NEGATIVE action (recent, SUCCESS) — should NOT be revertable
    action_negative = ActionLog(
        client_id=client.id,
        action_type="ADD_NEGATIVE",
        entity_type="keyword",
        entity_id="20",
        status="SUCCESS",
        executed_at=now - timedelta(hours=1),
    )
    # Already reverted action — should NOT be revertable
    action_reverted = ActionLog(
        client_id=client.id,
        action_type="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id="30",
        status="SUCCESS",
        executed_at=now - timedelta(hours=3),
        reverted_at=now - timedelta(hours=1),
    )
    db.add_all([action_recent, action_old, action_negative, action_reverted])
    db.flush()

    # External change event — NOT linked to action_log
    event_external = ChangeEvent(
        client_id=client.id,
        resource_name="customers/123/campaigns/456~2026-03-16",
        change_date_time=now - timedelta(hours=5),
        user_email="user@example.com",
        client_type="GOOGLE_ADS_WEB_CLIENT",
        change_resource_type="CAMPAIGN",
        resource_change_operation="UPDATE",
    )
    # Linked change event — linked to action_log (should be excluded from unified)
    event_linked = ChangeEvent(
        client_id=client.id,
        resource_name="customers/123/campaigns/789~2026-03-16",
        change_date_time=now - timedelta(hours=2),
        user_email=None,
        client_type="GOOGLE_ADS_API",
        change_resource_type="CAMPAIGN",
        resource_change_operation="UPDATE",
        action_log_id=action_recent.id,
    )
    db.add_all([event_external, event_linked])
    db.commit()
    return client


class TestUnifiedTimeline:
    def test_returns_merged_entries_sorted_by_timestamp_desc(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/unified?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 5  # 4 actions + 1 external event (linked excluded)

        timestamps = [e["timestamp"] for e in data["entries"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_can_revert_only_for_recent_success_non_negative_non_reverted(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/unified?client_id={client.id}")
        entries = resp.json()["entries"]

        revertable = [e for e in entries if e["can_revert"]]
        assert len(revertable) == 1
        assert revertable[0]["operation"] == "INCREASE_BUDGET"

    def test_excludes_linked_change_events(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/unified?client_id={client.id}")
        entries = resp.json()["entries"]

        external_events = [e for e in entries if e["source"] == "external"]
        assert len(external_events) == 1
        assert external_events[0]["user_email"] == "user@example.com"

    def test_helper_entries_have_correct_source(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/unified?client_id={client.id}")
        entries = resp.json()["entries"]

        helper_entries = [e for e in entries if e["source"] == "helper"]
        assert len(helper_entries) == 4
        for e in helper_entries:
            assert e["client_type"] == "GOOGLE_ADS_HELPER"


class TestListChangeEvents:
    def test_returns_all_events_for_client(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2  # both events (linked + external)

    def test_filter_by_operation(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/?client_id={client.id}&operation=UPDATE")
        data = resp.json()
        assert data["total"] == 2


class TestGetFilters:
    def test_returns_distinct_values(self, api_client, db):
        client = _seed(db)

        resp = api_client.get(f"/api/v1/history/filters?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert "CAMPAIGN" in data["resource_types"]
        assert "user@example.com" in data["user_emails"]
        assert "GOOGLE_ADS_WEB_CLIENT" in data["client_types"]
