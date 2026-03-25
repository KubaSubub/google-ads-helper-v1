"""Verify wasted-spend endpoint reacts to date filters."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.ad_group import AdGroup
from app.models.keyword import Keyword
from app.models.keyword_daily import KeywordDaily
from app.models.search_term import SearchTerm


@pytest.fixture
def api_client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_wasted_data(db):
    """Seed keywords with daily data across 30 days and search terms across date ranges."""
    client = Client(name="WasteTest", google_customer_id="1111111111")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="Search A", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id, google_ad_group_id="ag1", name="AdGroup A",
    )
    db.add(ad_group)
    db.flush()

    today = date.today()

    # Keyword with daily data — 0 conversions, 10 clicks/day, 100_000 cost_micros/day
    # Recent 7 days => 70 clicks, 700_000 cost = 0.70 USD waste
    # Full 30 days => 300 clicks, 3_000_000 cost = 3.00 USD waste
    kw = Keyword(
        ad_group_id=ad_group.id, google_keyword_id="kw1",
        text="waste keyword", match_type="BROAD", status="ENABLED",
    )
    db.add(kw)
    db.flush()

    for i in range(30):
        db.add(KeywordDaily(
            keyword_id=kw.id,
            date=today - timedelta(days=i),
            clicks=10,
            impressions=100,
            cost_micros=100_000,
            conversions=0.0,
            conversion_value_micros=0,
        ))

    # Search term in RECENT range (last 7 days)
    db.add(SearchTerm(
        ad_group_id=ad_group.id, campaign_id=campaign.id,
        text="recent waste term", match_type="BROAD",
        clicks=5, impressions=100, cost_micros=500_000, conversions=0.0,
        date_from=today - timedelta(days=6), date_to=today,
    ))

    # Search term in OLD range (20-30 days ago) — should NOT appear in 7-day query
    db.add(SearchTerm(
        ad_group_id=ad_group.id, campaign_id=campaign.id,
        text="old waste term", match_type="BROAD",
        clicks=5, impressions=100, cost_micros=800_000, conversions=0.0,
        date_from=today - timedelta(days=30), date_to=today - timedelta(days=20),
    ))

    db.commit()
    return client


def test_wasted_spend_7_days_vs_30_days(api_client, db):
    """Wasted spend MUST differ between 7-day and 30-day windows."""
    client = _seed_wasted_data(db)

    resp_7 = api_client.get(f"/api/v1/analytics/wasted-spend?client_id={client.id}&days=7")
    assert resp_7.status_code == 200
    data_7 = resp_7.json()

    resp_30 = api_client.get(f"/api/v1/analytics/wasted-spend?client_id={client.id}&days=30")
    assert resp_30.status_code == 200
    data_30 = resp_30.json()

    waste_7 = data_7["total_waste_usd"]
    waste_30 = data_30["total_waste_usd"]

    print(f"  7-day waste: {waste_7}")
    print(f"  30-day waste: {waste_30}")
    print(f"  7-day categories: {data_7['categories']}")
    print(f"  30-day categories: {data_30['categories']}")

    # 30-day MUST be larger than 7-day (more keyword daily data + old search term)
    assert waste_30 > waste_7, (
        f"Wasted spend should be higher for 30 days ({waste_30}) than 7 days ({waste_7})"
    )


def test_wasted_spend_search_terms_date_filtered(api_client, db):
    """Old search terms should NOT appear in recent date window."""
    client = _seed_wasted_data(db)

    resp_7 = api_client.get(f"/api/v1/analytics/wasted-spend?client_id={client.id}&days=7")
    data_7 = resp_7.json()

    st_items_7 = data_7["categories"]["search_terms"]["top_items"]
    st_texts = [item["text"] for item in st_items_7]

    # "old waste term" has date_from 30 days ago, date_to 20 days ago — outside 7d window
    assert "old waste term" not in st_texts, (
        f"Old search term should NOT appear in 7-day window, but found: {st_texts}"
    )

    # "recent waste term" should appear
    assert "recent waste term" in st_texts, (
        f"Recent search term should appear in 7-day window, but got: {st_texts}"
    )


def test_wasted_spend_explicit_date_range(api_client, db):
    """Explicit date_from/date_to should filter correctly."""
    client = _seed_wasted_data(db)
    today = date.today()

    # Only last 3 days
    date_from = (today - timedelta(days=2)).isoformat()
    date_to = today.isoformat()

    resp = api_client.get(
        f"/api/v1/analytics/wasted-spend?client_id={client.id}&date_from={date_from}&date_to={date_to}"
    )
    assert resp.status_code == 200
    data = resp.json()

    # KeywordDaily: 3 days * 10 clicks = 30 clicks, 3 * 100_000 = 300_000 micros = 0.30 USD
    kw_waste = data["categories"]["keywords"]["waste_usd"]
    assert kw_waste == 0.3, f"Expected 0.3 USD keyword waste for 3 days, got {kw_waste}"
