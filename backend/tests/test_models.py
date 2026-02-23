"""Tests for SQLAlchemy models — creation, relationships, constraints."""

from app.models import (
    Client, Campaign, AdGroup, Keyword, SearchTerm,
    Ad, MetricDaily, Recommendation, ActionLog, Alert,
)


def test_client_creation(db):
    """Client model can be created and queried."""
    client = Client(name="Test Client", google_customer_id="123-456-7890")
    db.add(client)
    db.commit()

    result = db.query(Client).first()
    assert result.name == "Test Client"
    assert result.google_customer_id == "123-456-7890"


def test_campaign_relationship(db):
    """Campaign links to Client via foreign key."""
    client = Client(name="Test Client", google_customer_id="111")
    db.add(client)
    db.commit()

    campaign = Campaign(
        client_id=client.id,
        name="Test Campaign",
        google_campaign_id="camp-1",
        status="ENABLED",
        budget_micros=500_000_000,  # $500
    )
    db.add(campaign)
    db.commit()

    result = db.query(Campaign).first()
    assert result.name == "Test Campaign"
    assert result.budget_micros == 500_000_000
    assert result.client_id == client.id


def test_keyword_micros_columns(db):
    """Keyword stores monetary values as BigInteger micros."""
    client = Client(name="C", google_customer_id="1")
    db.add(client)
    db.commit()

    campaign = Campaign(client_id=client.id, name="Camp", google_campaign_id="c1", status="ENABLED")
    db.add(campaign)
    db.commit()

    ad_group = AdGroup(campaign_id=campaign.id, name="AG", google_ad_group_id="ag1", status="ENABLED")
    db.add(ad_group)
    db.commit()

    keyword = Keyword(
        ad_group_id=ad_group.id,
        text="test keyword",
        google_keyword_id="kw-1",
        match_type="EXACT",
        status="ENABLED",
        bid_micros=1_500_000,       # $1.50
        cost_micros=50_000_000,     # $50.00
        avg_cpc_micros=2_000_000,   # $2.00
        clicks=25,
        impressions=1000,
        conversions=3,
    )
    db.add(keyword)
    db.commit()

    result = db.query(Keyword).first()
    assert result.bid_micros == 1_500_000
    assert result.cost_micros == 50_000_000
    assert result.avg_cpc_micros == 2_000_000
    assert result.conversions == 3


def test_action_log_creation(db):
    """ActionLog model stores action history with old/new values."""
    client = Client(name="C", google_customer_id="1")
    db.add(client)
    db.commit()

    log = ActionLog(
        client_id=client.id,
        action_type="PAUSE_KEYWORD",
        entity_type="keyword",
        entity_id="kw-123",
        old_value_json='{"status": "ENABLED"}',
        new_value_json='{"status": "PAUSED"}',
        status="SUCCESS",
    )
    db.add(log)
    db.commit()

    result = db.query(ActionLog).first()
    assert result.action_type == "PAUSE_KEYWORD"
    assert result.old_value_json == '{"status": "ENABLED"}'
    assert result.status == "SUCCESS"
    assert result.reverted_at is None


def test_alert_creation(db):
    """Alert model stores anomaly detection results."""
    client = Client(name="C", google_customer_id="1")
    db.add(client)
    db.commit()

    alert = Alert(
        client_id=client.id,
        alert_type="SPEND_SPIKE",
        severity="HIGH",
        title="Spend spike: Campaign X",
        description="Campaign spend $500 is 3x above average $150",
    )
    db.add(alert)
    db.commit()

    result = db.query(Alert).first()
    assert result.alert_type == "SPEND_SPIKE"
    assert result.severity == "HIGH"
    assert result.resolved_at is None


def test_recommendation_creation(db):
    """Recommendation model stores pending optimization suggestions."""
    client = Client(name="C", google_customer_id="1")
    db.add(client)
    db.commit()

    rec = Recommendation(
        client_id=client.id,
        rule_id="rule_1_waste_spend",
        entity_type="keyword",
        entity_id="kw-456",
        priority="HIGH",
        reason="High spend ($50) with 0 conversions",
        suggested_action='{"type": "PAUSE_KEYWORD", "keyword_id": "kw-456"}',
        status="pending",
    )
    db.add(rec)
    db.commit()

    result = db.query(Recommendation).first()
    assert result.rule_id == "rule_1_waste_spend"
    assert result.priority == "HIGH"
    assert result.status == "pending"
    assert result.applied_at is None
