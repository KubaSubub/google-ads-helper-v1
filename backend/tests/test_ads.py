"""Tests for /ads/{id} — ad detail with comparison vs sibling ads."""

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.ad import Ad
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client


@pytest.fixture
def api_client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded_ads(db):
    client = Client(name="AdsTest", google_customer_id="7777777777")
    db.add(client)
    db.flush()
    campaign = Campaign(
        client_id=client.id, google_campaign_id="c1",
        name="Test Camp", status="ENABLED", campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()
    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="ag1", name="AG", status="ENABLED")
    db.add(ag)
    db.flush()

    # 3 ads — top performer (100 clicks) + 2 siblings (50, 30 clicks)
    top_ad = Ad(
        ad_group_id=ag.id, google_ad_id="ad1", ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED", approval_status="APPROVED", ad_strength="EXCELLENT",
        final_url="https://example.com",
        headlines=[
            {"text": "Headline 1", "pinned_position": 1, "performance_label": "BEST"},
            {"text": "Headline 2", "pinned_position": None, "performance_label": "GOOD"},
            {"text": "Headline 3"},
        ],
        descriptions=[{"text": "Description 1"}],
        clicks=100, impressions=1000, cost_micros=50_000_000, conversions=10.0, ctr=10.0,
    )
    sib1 = Ad(
        ad_group_id=ag.id, google_ad_id="ad2", ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED", ad_strength="GOOD",
        headlines=[{"text": "Sib H1"}], descriptions=[],
        clicks=50, impressions=600, cost_micros=25_000_000, conversions=4.0, ctr=8.33,
    )
    sib2 = Ad(
        ad_group_id=ag.id, google_ad_id="ad3", ad_type="RESPONSIVE_SEARCH_AD",
        status="PAUSED", ad_strength="POOR",
        headlines=[{"text": "Sib H2"}], descriptions=[],
        clicks=30, impressions=400, cost_micros=15_000_000, conversions=2.0, ctr=7.5,
    )
    db.add_all([top_ad, sib1, sib2])
    db.commit()
    return top_ad, sib1, sib2


def test_get_ad_detail_returns_full_metadata(api_client, seeded_ads):
    top_ad, _, _ = seeded_ads
    resp = api_client.get(f"/api/v1/ads/{top_ad.id}")
    assert resp.status_code == 200
    data = resp.json()

    ad = data["ad"]
    assert ad["id"] == top_ad.id
    assert ad["ad_strength"] == "EXCELLENT"
    assert ad["approval_status"] == "APPROVED"
    assert ad["headlines_count"] == 3
    assert ad["descriptions_count"] == 1
    # Headlines normalized: text + pinned_position + performance_label
    h1 = ad["headlines"][0]
    assert h1["text"] == "Headline 1"
    assert h1["pinned_position"] == 1
    assert h1["performance_label"] == "BEST"
    # Headline without pinned_position normalizes to None
    h3 = ad["headlines"][2]
    assert h3["pinned_position"] is None
    assert h3["performance_label"] is None


def test_get_ad_detail_computes_comparison_vs_siblings(api_client, seeded_ads):
    top_ad, _, _ = seeded_ads
    resp = api_client.get(f"/api/v1/ads/{top_ad.id}")
    data = resp.json()

    comp = data["comparison"]
    assert comp["siblings_count"] == 2
    # Avg of 50 + 30 = 40 clicks
    assert comp["avg"]["clicks"] == 40
    # Top ad has 100 clicks vs avg 40 = +150%
    assert comp["diff_pct"]["clicks"] == 150.0
    # CTR: avg of 8.33 + 7.5 = 7.92 (rounded)
    # Top ad has 10 → diff +26.3%
    assert comp["diff_pct"]["ctr"] is not None
    assert comp["diff_pct"]["ctr"] > 0


def test_get_ad_detail_handles_no_siblings(api_client, db, seeded_ads):
    top_ad, sib1, sib2 = seeded_ads
    db.delete(sib1)
    db.delete(sib2)
    db.commit()
    resp = api_client.get(f"/api/v1/ads/{top_ad.id}")
    data = resp.json()
    assert data["comparison"]["siblings_count"] == 0
    # diff_pct should be None when avg is 0
    assert data["comparison"]["diff_pct"]["clicks"] is None


def test_get_ad_detail_404_when_not_found(api_client):
    resp = api_client.get("/api/v1/ads/999999")
    assert resp.status_code == 404


def test_ads_router_registered():
    """Smoke: route /ads/{id} musi byc w app.routes."""
    from app.main import app
    paths = {r.path for r in app.routes}
    assert "/api/v1/ads/{ad_id}" in paths
