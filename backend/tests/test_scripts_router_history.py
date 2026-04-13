"""Tests for GET /scripts/{script_id}/history endpoint."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.action_log import ActionLog
from tests.scripts_fixtures import build_basic_tree


def _seed_action_logs(db, client_id, script_id, *, ok=0, fail=0, days_ago=0):
    now = datetime.now() - timedelta(days=days_ago)
    for _ in range(ok):
        db.add(ActionLog(
            client_id=client_id,
            action_type="ADD_NEGATIVE",
            entity_type="campaign",
            entity_id="1",
            status="SUCCESS",
            execution_mode="LIVE",
            precondition_status="PASSED",
            context_json={"source": "scripts", "script_id": script_id},
            executed_at=now,
        ))
    for _ in range(fail):
        db.add(ActionLog(
            client_id=client_id,
            action_type="ADD_NEGATIVE",
            entity_type="campaign",
            entity_id="1",
            status="FAILED",
            execution_mode="LIVE",
            precondition_status="PASSED",
            context_json={"source": "scripts", "script_id": script_id},
            executed_at=now,
            error_message="mock",
        ))
    db.commit()


def test_history_empty_for_script_without_runs(db):
    tree = build_basic_tree(db)
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        r = client.get(f"/api/v1/scripts/A1/history?client_id={tree['client'].id}")
        assert r.status_code == 200
        data = r.json()
        assert data["script_id"] == "A1"
        assert data["total_runs"] == 0
        assert data["applied_total"] == 0
        assert data["last_executed_at"] is None
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_history_counts_successes_and_failures(db):
    tree = build_basic_tree(db)
    _seed_action_logs(db, tree["client"].id, "A1", ok=3, fail=1)

    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        r = client.get(f"/api/v1/scripts/A1/history?client_id={tree['client'].id}")
        assert r.status_code == 200
        data = r.json()
        assert data["applied_total"] == 3
        assert data["failed_total"] == 1
        assert data["last_executed_at"] is not None
        assert len(data["recent_days"]) >= 1
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_history_isolates_by_script_id(db):
    tree = build_basic_tree(db)
    _seed_action_logs(db, tree["client"].id, "A1", ok=2)
    _seed_action_logs(db, tree["client"].id, "D1", ok=5)

    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        r = client.get(f"/api/v1/scripts/A1/history?client_id={tree['client'].id}")
        assert r.json()["applied_total"] == 2
        r = client.get(f"/api/v1/scripts/D1/history?client_id={tree['client'].id}")
        assert r.json()["applied_total"] == 5
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_history_unknown_script_404(db):
    tree = build_basic_tree(db)
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        r = client.get(f"/api/v1/scripts/ZZ/history?client_id={tree['client'].id}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
