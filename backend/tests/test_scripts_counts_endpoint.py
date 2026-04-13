"""Tests for GET /scripts/counts — bulk counts endpoint with TTL cache."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers.scripts import _COUNTS_CACHE
from tests.scripts_fixtures import add_search_term, build_basic_tree


def _client(db):
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _cleanup():
    from app.database import get_db
    app.dependency_overrides.pop(get_db, None)
    _COUNTS_CACHE.clear()


def test_counts_returns_all_registered_scripts(db):
    tree = build_basic_tree(db)
    add_search_term(db, tree=tree, text="sushi wroclaw taksi", clicks=20, cost_pln=50, conversions=0)
    try:
        client = _client(db)
        r = client.get(f"/api/v1/scripts/counts?client_id={tree['client'].id}")
        assert r.status_code == 200
        body = r.json()
        assert body["cached"] is False
        counts = body["counts"]
        # Every registered script should appear.
        for sid in ("A1", "A2", "A3", "A6", "B1", "C2", "D1", "D3", "F1"):
            assert sid in counts
            assert "total" in counts[sid]
            assert "savings" in counts[sid]
    finally:
        _cleanup()


def test_counts_second_call_is_cached(db):
    tree = build_basic_tree(db)
    try:
        client = _client(db)
        r1 = client.get(f"/api/v1/scripts/counts?client_id={tree['client'].id}")
        assert r1.status_code == 200
        assert r1.json()["cached"] is False

        r2 = client.get(f"/api/v1/scripts/counts?client_id={tree['client'].id}")
        assert r2.status_code == 200
        assert r2.json()["cached"] is True
        # Same payload
        assert r1.json()["counts"] == r2.json()["counts"]
    finally:
        _cleanup()


def test_counts_cache_isolated_by_date_range(db):
    tree = build_basic_tree(db)
    try:
        client = _client(db)
        r1 = client.get(
            f"/api/v1/scripts/counts?client_id={tree['client'].id}"
            f"&date_from=2026-03-01&date_to=2026-03-31"
        )
        assert r1.json()["cached"] is False
        r2 = client.get(
            f"/api/v1/scripts/counts?client_id={tree['client'].id}"
            f"&date_from=2026-04-01&date_to=2026-04-30"
        )
        # Different cache key → fresh miss, not cached.
        assert r2.json()["cached"] is False
    finally:
        _cleanup()
