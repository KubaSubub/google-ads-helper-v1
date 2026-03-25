"""Tests for GET /analytics/wow-comparison — period-over-period comparison."""

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
    client = Client(name="WoW Test", google_customer_id="7777777777")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="Search A", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    today = date.today()
    # 14 days of data: days 0-13
    # Current week: days 0-6 (100 clicks/day)
    # Previous week: days 7-13 (50 clicks/day)
    for i in range(14):
        clicks = 100 if i < 7 else 50
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=today - timedelta(days=i),
            clicks=clicks,
            impressions=clicks * 10,
            cost_micros=clicks * 10_000,
            conversions=clicks / 10,
            conversion_value_micros=clicks * 50_000,
        ))
    db.commit()
    return client


def test_wow_returns_current_and_previous(api_client, db):
    client = _seed(db)

    resp = api_client.get(f"/api/v1/analytics/wow-comparison?client_id={client.id}&days=7&metric=clicks")
    assert resp.status_code == 200

    data = resp.json()
    assert data["metric"] == "clicks"
    assert data["period_days"] == 7
    assert len(data["current"]) > 0
    assert len(data["previous"]) > 0

    # Current period should have higher clicks (100/day) than previous (50/day)
    current_total = sum(d["value"] for d in data["current"])
    previous_total = sum(d["value"] for d in data["previous"])
    assert current_total > previous_total


def test_wow_different_metrics(api_client, db):
    client = _seed(db)

    for metric in ["cost", "clicks", "conversions", "roas", "ctr"]:
        resp = api_client.get(
            f"/api/v1/analytics/wow-comparison?client_id={client.id}&days=7&metric={metric}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric"] == metric
        assert len(data["current"]) > 0


def test_wow_no_campaigns_returns_empty(api_client, db):
    client = Client(name="Empty", google_customer_id="8888888888")
    db.add(client)
    db.commit()

    resp = api_client.get(f"/api/v1/analytics/wow-comparison?client_id={client.id}&days=7&metric=cost")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"] == []
    assert data["previous"] == []
