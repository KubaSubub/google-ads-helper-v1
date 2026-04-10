"""Tests for strategy_context (Marketing Mastermind Brief) on Client model.

Covers Acceptance Criteria from docs/specs/settings-mastermind-brief.md:
  AC1 — auto-migration (implicit via conftest.py Base.metadata.create_all)
  AC2 — Client.strategy_context JSON column exists and is nullable
  AC3 — Pydantic StrategyContext + LessonEntry + DecisionLogEntry schemas
  AC4 — partial PATCH merge preserves unmodified fields
  AC5 — length validators (narrative >10k, description >2k → 422)
  AC6 — LessonEntry type enum validation → 422
  AC7 — decisions_log AI-write path via PATCH
"""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Client


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_client(db, **overrides) -> Client:
    client = Client(
        name=overrides.get("name", "Strategy Test Client"),
        google_customer_id=overrides.get("google_customer_id", "5544332211"),
        currency=overrides.get("currency", "PLN"),
        strategy_context=overrides.get("strategy_context", None),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


# ── AC2 — column exists + default empty for new client ────────────────────────

def test_strategy_context_default_empty_for_new_client(api_client, db):
    client = _seed_client(db)
    resp = api_client.get(f"/api/v1/clients/{client.id}")
    assert resp.status_code == 200
    body = resp.json()
    # strategy_context present, either None or fully defaulted
    assert "strategy_context" in body
    # New client without explicit strategy_context = None
    assert body["strategy_context"] is None


# ── AC4 — round-trip strategy_narrative ───────────────────────────────────────

def test_strategy_context_round_trip_strategy_narrative(api_client, db):
    client = _seed_client(db)
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"strategy_narrative": "Brand-first, long-tail focus."}},
    )
    assert resp.status_code == 200, resp.text

    get = api_client.get(f"/api/v1/clients/{client.id}")
    sc = get.json()["strategy_context"]
    assert sc is not None
    assert sc["strategy_narrative"] == "Brand-first, long-tail focus."


# ── AC4 — lessons_learned add/remove round-trip ───────────────────────────────

def test_strategy_context_round_trip_lessons_add(api_client, db):
    client = _seed_client(db)
    lesson = {
        "type": "win",
        "title": "Geo-targeting Warszawa działa",
        "description": "Po zawężeniu do Warszawy +20% konwersji, -15% CPA.",
        "date": "2026-03-15",
    }
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"lessons_learned": [lesson]}},
    )
    assert resp.status_code == 200

    get = api_client.get(f"/api/v1/clients/{client.id}")
    sc = get.json()["strategy_context"]
    assert len(sc["lessons_learned"]) == 1
    assert sc["lessons_learned"][0]["type"] == "win"
    assert sc["lessons_learned"][0]["title"] == "Geo-targeting Warszawa działa"


# ── AC4 — partial update preserves other fields (merge semantics) ─────────────

def test_strategy_context_partial_update_preserves_other_fields(api_client, db):
    client = _seed_client(db)
    # Step 1: set strategy_narrative
    api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"strategy_narrative": "Initial strategy"}},
    )
    # Step 2: update ONLY roadmap — strategy_narrative should survive
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"roadmap": "Q2: test new landing page"}},
    )
    assert resp.status_code == 200

    get = api_client.get(f"/api/v1/clients/{client.id}")
    sc = get.json()["strategy_context"]
    assert sc["strategy_narrative"] == "Initial strategy"  # preserved
    assert sc["roadmap"] == "Q2: test new landing page"


# ── AC5 — length validation ───────────────────────────────────────────────────

def test_strategy_context_narrative_too_long_rejected(api_client, db):
    client = _seed_client(db)
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"strategy_narrative": "x" * 10001}},
    )
    assert resp.status_code == 422
    detail = str(resp.json())
    assert "10000" in detail or "narrative" in detail


def test_strategy_context_brand_voice_too_long_rejected(api_client, db):
    client = _seed_client(db)
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"brand_voice": "x" * 5001}},
    )
    assert resp.status_code == 422


def test_strategy_context_lesson_description_too_long_rejected(api_client, db):
    client = _seed_client(db)
    lesson = {
        "type": "loss",
        "title": "Test",
        "description": "x" * 2001,
        "date": "2026-04-10",
    }
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"lessons_learned": [lesson]}},
    )
    assert resp.status_code == 422


# ── AC6 — LessonEntry enum validation ─────────────────────────────────────────

def test_strategy_context_lesson_invalid_type_rejected(api_client, db):
    client = _seed_client(db)
    lesson = {
        "type": "invalid",
        "title": "Bad type",
        "description": "desc",
        "date": "2026-04-10",
    }
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"lessons_learned": [lesson]}},
    )
    assert resp.status_code == 422


# ── AC5 — too many entries rejected ───────────────────────────────────────────

def test_strategy_context_too_many_lessons_rejected(api_client, db):
    client = _seed_client(db)
    lessons = [
        {
            "type": "test",
            "title": f"Test {i}",
            "description": "desc",
            "date": "2026-04-10",
        }
        for i in range(201)
    ]
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"lessons_learned": lessons}},
    )
    assert resp.status_code == 422


# ── PATCH with null strategy_context is a no-op (does not wipe column) ───────

def test_strategy_context_patch_null_is_noop(api_client, db):
    client = _seed_client(db)
    # Step 1: set strategy_narrative
    api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"strategy_narrative": "Original narrative"}},
    )
    # Step 2: PATCH with explicit null — should NOT wipe the column
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": None},
    )
    assert resp.status_code == 200

    get = api_client.get(f"/api/v1/clients/{client.id}")
    sc = get.json()["strategy_context"]
    assert sc is not None
    assert sc["strategy_narrative"] == "Original narrative"


# ── AC7 — decisions_log AI-write path ─────────────────────────────────────────

def test_strategy_context_decisions_log_ai_write_path(api_client, db):
    client = _seed_client(db)
    entry = {
        "timestamp": "2026-04-10T10:00:00Z",
        "title": "Paused keyword X",
        "decision": "Paused 'sushi tani' due to CPA > 250 zł",
        "rationale": "Analysis: 30-day CPA 280 zł vs target 80 zł, -250% over target",
        "validation_result": "applied",
    }
    resp = api_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"strategy_context": {"decisions_log": [entry]}},
    )
    assert resp.status_code == 200, resp.text

    get = api_client.get(f"/api/v1/clients/{client.id}")
    sc = get.json()["strategy_context"]
    assert len(sc["decisions_log"]) == 1
    assert sc["decisions_log"][0]["title"] == "Paused keyword X"
    assert sc["decisions_log"][0]["validation_result"] == "applied"
