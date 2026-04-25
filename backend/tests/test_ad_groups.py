"""Tests for /ad_groups endpoints — list with metrics + ads in ad group."""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.keyword_daily import KeywordDaily


@pytest.fixture
def api_client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded_campaign(db):
    client = Client(name="AdGroupsTest", google_customer_id="5555555555")
    db.add(client)
    db.flush()
    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="c1",
        name="Test Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag1 = AdGroup(campaign_id=campaign.id, google_ad_group_id="ag1", name="Brand AG", status="ENABLED")
    ag2 = AdGroup(campaign_id=campaign.id, google_ad_group_id="ag2", name="Generic AG", status="ENABLED")
    db.add_all([ag1, ag2])
    db.flush()

    kw = Keyword(ad_group_id=ag1.id, google_keyword_id="kw1", text="brand kw", match_type="EXACT", status="ENABLED")
    db.add(kw)
    db.flush()

    today = date.today()
    for i in range(7):
        db.add(KeywordDaily(
            keyword_id=kw.id, date=today - timedelta(days=i),
            clicks=20, impressions=200, cost_micros=10_000_000,
            conversions=1.0, conversion_value_micros=5_000_000,
        ))

    ad1 = Ad(
        ad_group_id=ag1.id, google_ad_id="ad1", ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED", approval_status="APPROVED", ad_strength="GOOD",
        final_url="https://example.com",
        headlines=[{"text": "Brand H1"}, {"text": "Brand H2"}, {"text": "Brand H3"}],
        descriptions=[{"text": "Desc1"}, {"text": "Desc2"}],
        clicks=100, impressions=1000, cost_micros=50_000_000, conversions=5.0, ctr=10.0,
    )
    ad2 = Ad(
        ad_group_id=ag1.id, google_ad_id="ad2", ad_type="RESPONSIVE_SEARCH_AD",
        status="PAUSED", approval_status="APPROVED_LIMITED", ad_strength="POOR",
        final_url="https://example.com",
        headlines=[{"text": "Old H1"}],
        descriptions=[],
        clicks=10, impressions=200, cost_micros=5_000_000, conversions=0.0, ctr=5.0,
    )
    db.add_all([ad1, ad2])
    db.commit()

    return client, campaign, ag1, ag2


def test_list_ad_groups_aggregates_keyword_daily(api_client, seeded_campaign):
    _client, campaign, ag1, _ag2 = seeded_campaign
    resp = api_client.get(f"/api/v1/ad_groups/?campaign_id={campaign.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    ag1_row = next(r for r in data["items"] if r["id"] == ag1.id)
    assert ag1_row["clicks"] == 140  # 7 * 20
    assert ag1_row["cost"] == 70.0  # 7 * 10 zl
    assert ag1_row["conversions"] == 7.0  # 7 * 1


def test_list_ad_groups_404_when_campaign_missing(api_client):
    resp = api_client.get("/api/v1/ad_groups/?campaign_id=999999")
    assert resp.status_code == 404


def test_list_ads_in_group_returns_metadata_and_metrics(api_client, seeded_campaign):
    _client, _campaign, ag1, _ag2 = seeded_campaign
    resp = api_client.get(f"/api/v1/ad_groups/{ag1.id}/ads")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ad_group_id"] == ag1.id
    assert data["total"] == 2
    # Sorted by clicks desc — top performer first
    top = data["items"][0]
    assert top["clicks"] == 100
    assert top["headline_1"] == "Brand H1"
    assert top["headline_2"] == "Brand H2"
    assert top["headlines_count"] == 3
    assert top["descriptions_count"] == 2
    assert top["ad_strength"] == "GOOD"
    assert top["approval_status"] == "APPROVED"
    assert top["cost"] == 50.0


def test_list_ads_in_group_404_when_missing(api_client):
    resp = api_client.get("/api/v1/ad_groups/999999/ads")
    assert resp.status_code == 404


def test_list_ads_in_group_empty_when_no_ads(api_client, seeded_campaign):
    _client, _campaign, _ag1, ag2 = seeded_campaign
    resp = api_client.get(f"/api/v1/ad_groups/{ag2.id}/ads")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
