"""Tests for GET /analytics/dashboard-kpis — period comparison KPIs."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.metric_daily import MetricDaily


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed a client with one SEARCH campaign and metric rows for current + previous periods."""
    client = Client(name="KPI Test", google_customer_id="5555555555")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="c1",
        name="Search A",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    today = date.today()

    # Current period: days 0-6 (today through today-6) — 7 rows
    # Query range for days=7 is [today-7, today] but day 7 has no data
    for i in range(7):
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=today - timedelta(days=i),
            clicks=100,
            impressions=1000,
            cost_micros=5_000_000,
            conversions=2.0,
            conversion_value_micros=10_000_000,
        ))

    # Previous period: days 8-14 (today-8 through today-14) — 7 rows
    # Query range is [today-14, today-8]; day 7 intentionally empty to avoid overlap
    for i in range(8, 15):
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=today - timedelta(days=i),
            clicks=50,
            impressions=500,
            cost_micros=2_500_000,
            conversions=1.0,
            conversion_value_micros=5_000_000,
        ))

    db.commit()
    return client


def test_dashboard_kpis_returns_current_previous_and_change(api_client, db):
    client = _seed(db)

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7")
    assert resp.status_code == 200

    data = resp.json()
    assert "current" in data
    assert "previous" in data
    assert "change_pct" in data
    assert data["period_days"] == 7

    cur = data["current"]
    assert cur["clicks"] == 700          # 100 * 7
    assert cur["impressions"] == 7000    # 1000 * 7
    assert cur["cost_usd"] == 35.0       # 5M * 7 / 1M
    assert cur["conversions"] == 14.0    # 2 * 7
    assert cur["ctr"] == 10.0            # 700/7000 * 100

    prev = data["previous"]
    assert prev["clicks"] == 350         # 50 * 7
    assert prev["impressions"] == 3500   # 500 * 7
    assert prev["cost_usd"] == 17.5      # 2.5M * 7 / 1M


def test_dashboard_kpis_change_pct_correct(api_client, db):
    client = _seed(db)

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7")
    data = resp.json()

    # clicks: (700-350)/350 * 100 = 100.0%
    assert data["change_pct"]["clicks"] == 100.0
    # impressions: same ratio
    assert data["change_pct"]["impressions"] == 100.0
    # cost_usd: (35-17.5)/17.5 * 100 = 100.0%
    assert data["change_pct"]["cost_usd"] == 100.0


def test_dashboard_kpis_no_campaigns_returns_empty(api_client, db):
    client = Client(name="Empty", google_customer_id="6666666666")
    db.add(client)
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=30")
    assert resp.status_code == 200

    data = resp.json()
    assert data["current"] == {}
    assert data["previous"] == {}
    assert data["change_pct"] == {}


def test_dashboard_kpis_no_metrics_returns_zeroes(api_client, db):
    client = Client(name="NoMetrics", google_customer_id="7777777777")
    db.add(client)
    db.flush()
    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="c99",
        name="Empty Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7")
    assert resp.status_code == 200

    data = resp.json()
    assert data["current"]["clicks"] == 0
    assert data["current"]["cost_usd"] == 0
    assert data["current"]["roas"] == 0


def test_dashboard_kpis_campaign_type_filter(api_client, db):
    client = Client(name="TypeFilter", google_customer_id="8888888888")
    db.add(client)
    db.flush()

    search = Campaign(client_id=client.id, google_campaign_id="cs", name="Search", status="ENABLED", campaign_type="SEARCH")
    pmax = Campaign(client_id=client.id, google_campaign_id="cp", name="PMax", status="ENABLED", campaign_type="PERFORMANCE_MAX")
    db.add_all([search, pmax])
    db.flush()

    today = date.today()
    db.add(MetricDaily(campaign_id=search.id, date=today, clicks=100, impressions=1000, cost_micros=1_000_000, conversions=1.0, conversion_value_micros=0))
    db.add(MetricDaily(campaign_id=pmax.id, date=today, clicks=200, impressions=2000, cost_micros=2_000_000, conversions=2.0, conversion_value_micros=0))
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7&campaign_type=SEARCH")
    data = resp.json()

    assert data["current"]["clicks"] == 100  # only search campaign


def test_dashboard_kpis_change_pct_when_previous_zero(api_client, db):
    """When previous period has zero, change_pct should be 100 if current > 0, else 0."""
    client = Client(name="ZeroPrev", google_customer_id="9999999990")
    db.add(client)
    db.flush()

    campaign = Campaign(client_id=client.id, google_campaign_id="cz", name="New", status="ENABLED", campaign_type="SEARCH")
    db.add(campaign)
    db.flush()

    today = date.today()
    db.add(MetricDaily(campaign_id=campaign.id, date=today, clicks=50, impressions=500, cost_micros=1_000_000, conversions=1.0, conversion_value_micros=0))
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7")
    data = resp.json()

    assert data["change_pct"]["clicks"] == 100.0  # previous is 0, current > 0
    assert data["change_pct"]["roas"] == 0.0       # both 0
