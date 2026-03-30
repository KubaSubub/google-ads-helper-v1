"""Integration tests for write safety pipeline (K1/K2 audit findings).

Tests verify that all write paths go through:
1. Demo guard (ensure_demo_write_allowed)
2. Safety limits (validate_action) where applicable
3. Audit trail (ActionLog)
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client
from app.models.action_log import ActionLog
from app.models.ad_group import AdGroup
from app.models.automated_rule import AutomatedRule
from app.models.keyword import Keyword
from app.models.negative_keyword import NegativeKeyword
from app.models.search_term import SearchTerm


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_base(db):
    """Seed a client + campaign + ad_group + keyword + search_term."""
    client = Client(name="Safety Test", google_customer_id="9999999999")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="safe_c1",
        name="Search Safety",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="safe_ag1",
        name="AdGroup Safety",
        status="ENABLED",
    )
    db.add(ad_group)
    db.flush()

    # Need 6+ keywords so PAUSE safety limit (20%) is not triggered for 1 pause
    keywords = []
    for i in range(6):
        kw = Keyword(
            ad_group_id=ad_group.id,
            google_keyword_id=f"safe_kw{i}",
            text=f"test keyword {i}",
            match_type="PHRASE",
            status="ENABLED",
            bid_micros=1500000,
        )
        db.add(kw)
        keywords.append(kw)
    db.flush()
    keyword = keywords[0]

    today = date.today()
    search_term = SearchTerm(
        campaign_id=campaign.id,
        ad_group_id=ad_group.id,
        text="bad search term",
        clicks=20,
        impressions=100,
        cost_micros=500000,
        date_from=today - timedelta(days=30),
        date_to=today,
    )
    db.add(search_term)
    db.flush()

    db.commit()
    return client, campaign, ad_group, keyword, search_term


class TestRulesEngineSafety:
    """K1: Rules engine must go through safety pipeline."""

    def test_rule_execute_creates_action_log(self, api_client, db):
        """Executing a PAUSE rule must create ActionLog entries."""
        client, campaign, ad_group, keyword, _ = _seed_base(db)

        rule = AutomatedRule(
            client_id=client.id,
            name="Pause low CTR",
            enabled=True,
            entity_type="keyword",
            conditions=[{"field": "status", "op": "=", "value": "ENABLED"}],
            action_type="PAUSE",
        )
        db.add(rule)
        db.commit()

        resp = api_client.post(
            f"/api/v1/rules/{rule.id}/execute?client_id={client.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["actions_taken"] >= 1

        # Verify ActionLog was created
        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "RULE_PAUSE",
        ).all()
        assert len(logs) >= 1
        assert logs[0].status == "SUCCESS"

    def test_rule_execute_creates_action_log_for_add_negative(self, api_client, db):
        """Executing an ADD_NEGATIVE rule must create ActionLog entries."""
        client, campaign, ad_group, keyword, search_term = _seed_base(db)

        rule = AutomatedRule(
            client_id=client.id,
            name="Negate bad terms",
            enabled=True,
            entity_type="search_term",
            conditions=[{"field": "clicks", "op": ">=", "value": 10}],
            action_type="ADD_NEGATIVE",
            action_params={"match_type": "EXACT"},
        )
        db.add(rule)
        db.commit()

        resp = api_client.post(
            f"/api/v1/rules/{rule.id}/execute?client_id={client.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["actions_taken"] >= 1

        # Verify ActionLog was created
        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "RULE_ADD_NEGATIVE",
        ).all()
        assert len(logs) >= 1

    def test_rule_dry_run_no_action_log(self, api_client, db):
        """Dry run must NOT create ActionLog entries."""
        client, campaign, ad_group, keyword, _ = _seed_base(db)

        rule = AutomatedRule(
            client_id=client.id,
            name="Pause low CTR dry",
            enabled=True,
            entity_type="keyword",
            conditions=[{"field": "status", "op": "=", "value": "ENABLED"}],
            action_type="PAUSE",
        )
        db.add(rule)
        db.commit()

        resp = api_client.post(
            f"/api/v1/rules/{rule.id}/dry-run?client_id={client.id}"
        )
        assert resp.status_code == 200
        assert resp.json()["dry_run"] is True

        # No ActionLog for dry run
        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "RULE_PAUSE",
        ).all()
        assert len(logs) == 0


class TestBiddingTargetSafety:
    """H1: Bidding target must be remote-first."""

    def test_bidding_target_creates_action_log(self, api_client, db):
        """Bidding target update must create ActionLog."""
        client, campaign, _, _, _ = _seed_base(db)
        campaign.target_cpa_micros = 5000000
        db.commit()

        resp = api_client.patch(
            f"/api/v1/campaigns/{campaign.id}/bidding-target",
            params={"field": "target_cpa_micros", "value": 6000000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_sync"] is True  # API not connected in tests

        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "UPDATE_BIDDING_TARGET",
        ).all()
        assert len(logs) == 1
        assert logs[0].status == "SUCCESS"

    def test_bidding_target_invalid_field_rejected(self, api_client, db):
        """Invalid field must be rejected."""
        client, campaign, _, _, _ = _seed_base(db)
        resp = api_client.patch(
            f"/api/v1/campaigns/{campaign.id}/bidding-target",
            params={"field": "budget_micros", "value": 999},
        )
        assert resp.status_code == 400


class TestNegativeKeywordsSafety:
    """K2: Negative keyword creation must go through safety pipeline."""

    def test_create_negative_keywords_creates_action_log(self, api_client, db):
        """Creating negative keywords must create ActionLog."""
        client, campaign, _, _, _ = _seed_base(db)

        resp = api_client.post(
            "/api/v1/negative-keywords/",
            json={
                "client_id": client.id,
                "campaign_id": campaign.id,
                "texts": ["bad keyword 1", "bad keyword 2"],
                "match_type": "PHRASE",
                "negative_scope": "CAMPAIGN",
            },
        )
        assert resp.status_code == 200

        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "ADD_NEGATIVE",
        ).all()
        assert len(logs) >= 1

    def test_bulk_add_negative_creates_action_log(self, api_client, db):
        """Bulk add negative from search terms must create ActionLog."""
        client, campaign, ad_group, _, search_term = _seed_base(db)

        resp = api_client.post(
            "/api/v1/search-terms/bulk-add-negative",
            json={
                "client_id": client.id,
                "search_term_ids": [search_term.id],
                "level": "campaign",
                "match_type": "PHRASE",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] >= 1

        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "BULK_ADD_NEGATIVE",
        ).all()
        assert len(logs) >= 1


class TestPlacementExclusionSafety:
    """K2: Placement exclusion must create ActionLog."""

    def test_placement_exclusion_creates_action_log(self, api_client, db):
        """Placement exclusion must create ActionLog."""
        client, campaign, _, _, _ = _seed_base(db)
        campaign.campaign_type = "DISPLAY"
        db.commit()

        resp = api_client.post(
            "/api/v1/analytics/placement-exclusion",
            params={
                "client_id": client.id,
                "campaign_id": campaign.id,
                "placement_url": "badsite.com",
            },
        )
        # May fail due to no API connection, but ActionLog should still be created
        logs = db.query(ActionLog).filter(
            ActionLog.client_id == client.id,
            ActionLog.action_type == "ADD_PLACEMENT_EXCLUSION",
        ).all()
        assert len(logs) >= 1


class TestWriteSafetyModule:
    """Direct tests for write_safety.py helpers."""

    def test_record_write_action(self, db):
        """record_write_action creates ActionLog correctly."""
        from app.services.write_safety import record_write_action

        client = Client(name="WriteSafety Test", google_customer_id="8888888888")
        db.add(client)
        db.flush()

        log = record_write_action(
            db,
            client_id=client.id,
            action_type="TEST_ACTION",
            entity_type="test",
            entity_id=42,
            old_value={"before": True},
            new_value={"after": True},
        )
        db.commit()

        assert log.id is not None
        assert log.action_type == "TEST_ACTION"
        assert log.status == "SUCCESS"
        assert log.entity_id == "42"

    def test_count_negatives_added_today(self, db):
        """count_negatives_added_today counts today's negatives."""
        from app.services.write_safety import count_negatives_added_today, record_write_action

        client = Client(name="Count Test", google_customer_id="7777777777")
        db.add(client)
        db.flush()

        # Add some action logs for today
        for i in range(3):
            record_write_action(
                db,
                client_id=client.id,
                action_type="ADD_NEGATIVE",
                entity_type="negative_keyword",
                entity_id=i,
            )
        db.commit()

        count = count_negatives_added_today(db, client.id)
        assert count == 3
