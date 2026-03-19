"""Tests for AI Agent feature — API contract + service unit tests."""

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.metric_daily import MetricDaily
from app.services.agent_service import AgentService


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


def _seed_client_with_campaigns(db, num_campaigns=3):
    """Create a client with campaigns and 14 days of metrics."""
    client = Client(name="Agent Test Client", google_customer_id="999-999-9999")
    db.add(client)
    db.flush()

    today = date.today()
    campaigns = []
    for i in range(num_campaigns):
        campaign = Campaign(
            client_id=client.id,
            google_campaign_id=f"agent-camp-{i}",
            name=f"Campaign {i}",
            status="ENABLED",
            campaign_type="SEARCH",
        )
        db.add(campaign)
        db.flush()
        campaigns.append(campaign)

        # Add 14 days of metrics per campaign
        for day_offset in range(14):
            metric = MetricDaily(
                campaign_id=campaign.id,
                date=today - timedelta(days=day_offset),
                clicks=10,
                impressions=100,
                cost_micros=5_000_000,
                conversions=1.0,
                conversion_value_micros=20_000_000,
            )
            db.add(metric)

    db.commit()
    return client, campaigns


# ---------------------------------------------------------------------------
# API contract tests
# ---------------------------------------------------------------------------


class TestAgentStatusEndpoint:
    def test_returns_json_with_available_key(self, api_client):
        resp = api_client.get("/api/v1/agent/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "available" in body


class TestAgentChatEndpoint:
    def test_missing_client_id_returns_422(self, api_client):
        resp = api_client.post(
            "/api/v1/agent/chat",
            json={"message": "test", "report_type": "freeform"},
        )
        assert resp.status_code == 422

    def test_invalid_report_type_falls_back_to_freeform(self, api_client, db):
        """Invalid report_type should not cause error — falls back to freeform."""
        client = Client(name="Fallback Client", google_customer_id="111-111-1111")
        db.add(client)
        db.commit()

        with patch(
            "app.routers.agent.AgentService"
        ) as MockService:
            mock_instance = MockService.return_value

            async def mock_gen(*args, **kwargs):
                yield json.dumps({"type": "done", "content": ""})

            mock_instance.generate_report = mock_gen
            resp = api_client.post(
                f"/api/v1/agent/chat?client_id={client.id}",
                json={"message": "test", "report_type": "INVALID_TYPE"},
            )
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


class TestAgentServiceGatherData:
    def test_weekly_returns_expected_sections(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        data = service.gather_data("weekly")
        for key in ["kpis", "campaigns", "alerts", "recommendations", "health"]:
            assert key in data, f"Missing section: {key}"

    def test_freeform_returns_expected_sections(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        data = service.gather_data("freeform")
        for key in ["kpis", "campaigns", "alerts"]:
            assert key in data

    def test_unknown_report_type_uses_freeform_sections(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        data = service.gather_data("nonexistent_type")
        # Should fall back to freeform sections
        assert "kpis" in data


class TestKPIDateRanges:
    def test_both_periods_have_equal_length(self, db):
        """After FIX 3: both current and previous periods should be 7 days."""
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        kpis = service._get_kpis()
        # Both periods should have data (we seeded 14 days)
        assert "current_7d" in kpis
        assert "previous_7d" in kpis
        # Both should have clicks > 0 (we seeded 10 clicks/day)
        assert kpis["current_7d"]["clicks"] > 0
        assert kpis["previous_7d"]["clicks"] > 0
        # With 10 clicks/day for 7 days each, both should be equal
        assert kpis["current_7d"]["clicks"] == kpis["previous_7d"]["clicks"]


class TestCampaignQueries:
    def test_summary_returns_all_enabled_campaigns(self, db):
        client, campaigns = _seed_client_with_campaigns(db, num_campaigns=5)
        service = AgentService(db, client.id)
        summary = service._get_campaigns_summary()
        assert len(summary) == 5
        # Each should have metrics
        for item in summary:
            assert item["clicks_30d"] > 0

    def test_detail_returns_roas_and_cpa(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        detail = service._get_campaigns_detail()
        assert len(detail) > 0
        for item in detail:
            assert "roas" in item
            assert "cpa" in item


class TestBuildPrompt:
    def test_prompt_contains_user_message(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        data = service.gather_data("freeform")
        prompt = service.build_prompt(data, "Jak wyglada ROAS?")
        assert "Jak wyglada ROAS?" in prompt

    def test_prompt_truncates_large_data(self, db):
        client, _ = _seed_client_with_campaigns(db)
        service = AgentService(db, client.id)
        # Create artificially large data
        data = {"big": "x" * 50_000}
        prompt = service.build_prompt(data, "test")
        assert "dane skrocone" in prompt
