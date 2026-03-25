"""Tests for GET /analytics/campaigns-summary — per-campaign aggregated metrics."""

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


def test_campaigns_summary_returns_per_campaign_metrics(api_client, db):
    client = Client(name="SummaryTest", google_customer_id="3333333333")
    db.add(client)
    db.flush()

    c1 = Campaign(client_id=client.id, google_campaign_id="c1", name="Camp A", status="ENABLED", campaign_type="SEARCH")
    c2 = Campaign(client_id=client.id, google_campaign_id="c2", name="Camp B", status="ENABLED", campaign_type="SEARCH")
    db.add_all([c1, c2])
    db.flush()

    today = date.today()
    for i in range(7):
        db.add(MetricDaily(campaign_id=c1.id, date=today - timedelta(days=i),
                           clicks=100, impressions=1000, cost_micros=500_000,
                           conversions=5.0, conversion_value_micros=2_000_000))
        db.add(MetricDaily(campaign_id=c2.id, date=today - timedelta(days=i),
                           clicks=50, impressions=500, cost_micros=250_000,
                           conversions=0.0, conversion_value_micros=0))
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/campaigns-summary?client_id={client.id}&days=7")
    assert resp.status_code == 200
    data = resp.json()

    camps = data["campaigns"]
    assert str(c1.id) in camps
    assert str(c2.id) in camps

    # Camp A: 7 * 100 = 700 clicks, 7 * 5 = 35 conversions, cost = 3.5, conv_value = 14
    a = camps[str(c1.id)]
    assert a["clicks"] == 700
    assert a["conversions"] == 35.0
    assert a["cost_usd"] == 3.5
    assert a["roas"] == 4.0  # 14 / 3.5

    # Camp B: 0 conversions, ROAS = 0
    b = camps[str(c2.id)]
    assert b["clicks"] == 350
    assert b["conversions"] == 0.0
    assert b["roas"] == 0


def test_campaigns_summary_date_filtered(api_client, db):
    client = Client(name="DateFilter", google_customer_id="4444444444")
    db.add(client)
    db.flush()

    c1 = Campaign(client_id=client.id, google_campaign_id="c1", name="Camp", status="ENABLED", campaign_type="SEARCH")
    db.add(c1)
    db.flush()

    today = date.today()
    # 30 days of data, 10 clicks/day
    for i in range(30):
        db.add(MetricDaily(campaign_id=c1.id, date=today - timedelta(days=i),
                           clicks=10, impressions=100, cost_micros=100_000,
                           conversions=1.0, conversion_value_micros=0))
    db.commit()

    resp_7 = api_client.get(f"/api/v1/analytics/campaigns-summary?client_id={client.id}&days=7")
    resp_30 = api_client.get(f"/api/v1/analytics/campaigns-summary?client_id={client.id}&days=30")

    clicks_7 = resp_7.json()["campaigns"][str(c1.id)]["clicks"]
    clicks_30 = resp_30.json()["campaigns"][str(c1.id)]["clicks"]

    assert clicks_7 < clicks_30
    assert clicks_7 == 80  # resolve_dates(7) = [today-7, today] = 8 days
    assert clicks_30 == 300  # resolve_dates(30) gives 30 rows of data
