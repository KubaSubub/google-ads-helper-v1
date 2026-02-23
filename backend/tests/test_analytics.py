"""Tests for AnalyticsService — KPI calculations and anomaly detection."""

from app.models import Client, Campaign, Alert
from app.services.analytics_service import AnalyticsService


def _create_client(db) -> Client:
    """Helper: create a test client."""
    client = Client(name="Test Client", google_customer_id="1")
    db.add(client)
    db.commit()
    return client


def test_kpis_empty_campaigns(db):
    """KPIs should return zeros when no campaigns exist."""
    client = _create_client(db)
    service = AnalyticsService(db)
    kpis = service.get_kpis(client.id)

    assert kpis["total_spend_usd"] == 0
    assert kpis["total_clicks"] == 0
    assert kpis["total_impressions"] == 0
    assert kpis["total_conversions"] == 0
    assert kpis["active_campaigns"] == 0


def test_kpis_with_campaigns(db):
    """KPIs should aggregate across campaigns."""
    client = _create_client(db)

    # Note: analytics_service currently uses placeholder values (TODO in service)
    # so we mainly test structure and that it doesn't crash
    for i in range(3):
        db.add(Campaign(
            client_id=client.id,
            name=f"Campaign {i}",
            google_campaign_id=f"c{i}",
            status="ENABLED",
        ))
    db.commit()

    service = AnalyticsService(db)
    kpis = service.get_kpis(client.id)

    assert kpis["active_campaigns"] == 3
    assert "total_spend_usd" in kpis
    assert "roas" in kpis
    assert "avg_ctr_pct" in kpis


def test_detect_anomalies_no_campaigns(db):
    """Anomaly detection should return empty list when no campaigns."""
    client = _create_client(db)
    service = AnalyticsService(db)
    alerts = service.detect_anomalies(client.id)
    assert alerts == []


def test_alert_deduplication(db):
    """Creating same alert twice should return None on second attempt."""
    client = _create_client(db)
    db.add(Campaign(
        client_id=client.id, name="Camp", google_campaign_id="c1", status="ENABLED"
    ))
    db.commit()

    campaign = db.query(Campaign).first()

    service = AnalyticsService(db)
    alert1 = service._create_alert(
        client_id=client.id,
        campaign_id=campaign.id,
        alert_type="SPEND_SPIKE",
        severity="HIGH",
        title="Test alert",
        description="Test",
    )
    db.commit()
    assert alert1 is not None

    # Same alert again — should be deduplicated
    alert2 = service._create_alert(
        client_id=client.id,
        campaign_id=campaign.id,
        alert_type="SPEND_SPIKE",
        severity="HIGH",
        title="Test alert",
        description="Test",
    )
    assert alert2 is None  # deduplicated


def test_resolved_alert_allows_new(db):
    """After resolving an alert, a new one of same type can be created."""
    from datetime import datetime

    client = _create_client(db)
    db.add(Campaign(
        client_id=client.id, name="Camp", google_campaign_id="c1", status="ENABLED"
    ))
    db.commit()
    campaign = db.query(Campaign).first()

    service = AnalyticsService(db)

    # Create and resolve first alert
    alert1 = service._create_alert(
        client_id=client.id,
        campaign_id=campaign.id,
        alert_type="CTR_DROP",
        severity="MEDIUM",
        title="Low CTR",
    )
    db.commit()
    alert1.resolved_at = datetime.utcnow()
    db.commit()

    # New alert of same type should be created (old one is resolved)
    alert2 = service._create_alert(
        client_id=client.id,
        campaign_id=campaign.id,
        alert_type="CTR_DROP",
        severity="MEDIUM",
        title="Low CTR again",
    )
    assert alert2 is not None
