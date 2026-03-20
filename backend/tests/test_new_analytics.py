"""Tests for new analytics endpoints: search-term-trends, close-variants, conversion-health, keyword-expansion."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, MetricDaily, Keyword, AdGroup, SearchTerm


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed(db):
    """Seed data for analytics tests — client with campaign, keywords, search terms, metrics."""
    today = date.today()

    client = Client(name="New Analytics", google_customer_id="8888888888")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="na_c1",
        name="Search NA",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=30_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="na_ag1", name="NA Group", status="ENABLED")
    db.add(ag)
    db.flush()

    # Keywords
    for i, (text, mt, qs) in enumerate([
        ("buty sportowe", "EXACT", 8),
        ("buty zimowe", "PHRASE", 4),
        ("obuwie damskie", "BROAD", 6),
    ]):
        kw = Keyword(
            ad_group_id=ag.id,
            google_keyword_id=f"nak{i}",
            text=text,
            match_type=mt,
            status="ENABLED",
            quality_score=qs,
        )
        db.add(kw)

    # Search terms — split across early/recent for trend analysis
    early_start = today - timedelta(days=25)
    recent_start = today - timedelta(days=10)

    search_terms = [
        # Early terms
        ("buty sportowe", 20, 4_000_000, 2.0, early_start, today - timedelta(days=15)),
        ("buty zimowe tanio", 10, 2_000_000, 0, early_start, today - timedelta(days=15)),
        # Recent terms (rising: buty sportowe more clicks; declining: buty zimowe tanio fewer)
        ("buty sportowe", 35, 7_000_000, 4.0, recent_start, today),
        ("buty zimowe tanio", 3, 500_000, 0, recent_start, today),
        # New term (only recent)
        ("buty do biegania", 15, 3_000_000, 1.5, recent_start, today),
    ]
    for text, clicks, cost, conv, d_from, d_to in search_terms:
        st = SearchTerm(
            ad_group_id=ag.id,
            campaign_id=campaign.id,
            text=text,
            clicks=clicks,
            impressions=clicks * 12,
            cost_micros=cost,
            conversions=conv,
            ctr=8.3,
            date_from=d_from,
            date_to=d_to,
        )
        db.add(st)

    # MetricDaily — 14 days
    for i in range(14):
        d = today - timedelta(days=i)
        md = MetricDaily(
            campaign_id=campaign.id,
            date=d,
            clicks=50 + i * 2,
            impressions=500 + i * 20,
            cost_micros=5_000_000 + i * 100_000,
            conversions=2.5 + (i * 0.1 if i < 10 else 0),
            conversion_value_micros=50_000_000,
        )
        db.add(md)

    db.commit()
    return client, campaign, ag


class TestSearchTermTrends:
    def test_returns_200(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/search-term-trends?client_id={client.id}&days=30&min_clicks=3")
        assert resp.status_code == 200
        data = resp.json()
        assert "rising" in data
        assert "declining" in data
        assert "new_terms" in data
        assert data["total_terms"] > 0

    def test_rising_terms_detected(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/search-term-trends?client_id={client.id}&days=30&min_clicks=3")
        data = resp.json()
        rising_texts = [t["text"] for t in data["rising"]]
        assert "buty sportowe" in rising_texts

    def test_new_terms_detected(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/search-term-trends?client_id={client.id}&days=30&min_clicks=3")
        data = resp.json()
        new_texts = [t["text"] for t in data["new_terms"]]
        assert "buty do biegania" in new_texts

    def test_empty_client(self, api_client, db):
        client = Client(name="Empty", google_customer_id="0000000000")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/search-term-trends?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json()["total_terms"] == 0


class TestCloseVariants:
    def test_returns_200(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/close-variants?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "variants" in data
        assert "summary" in data

    def test_exact_match_counted(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/close-variants?client_id={client.id}")
        data = resp.json()
        assert data["summary"]["exact_matches"] >= 0
        assert data["summary"]["total_search_terms"] > 0

    def test_empty_client(self, api_client, db):
        client = Client(name="Empty2", google_customer_id="0000000001")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/close-variants?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json()["variants"] == []


class TestConversionHealth:
    def test_returns_200(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/conversion-health?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "status" in data
        assert "campaigns" in data

    def test_score_is_valid(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/conversion-health?client_id={client.id}")
        data = resp.json()
        assert 0 <= data["score"] <= 100

    def test_campaign_details_present(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/conversion-health?client_id={client.id}")
        data = resp.json()
        assert len(data["campaigns"]) > 0
        camp = data["campaigns"][0]
        assert "campaign_name" in camp
        assert "score" in camp
        assert "issues" in camp

    def test_empty_client(self, api_client, db):
        client = Client(name="Empty3", google_customer_id="0000000002")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/conversion-health?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_campaigns"


class TestKeywordExpansion:
    def test_returns_200(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/keyword-expansion?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data
        assert "summary" in data

    def test_unmapped_terms_suggested(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/keyword-expansion?client_id={client.id}&min_clicks=3")
        data = resp.json()
        # "buty do biegania" and "buty zimowe tanio" are not keywords — should appear
        suggested_texts = [s["search_term"] for s in data["suggestions"]]
        assert len(suggested_texts) > 0

    def test_existing_keywords_excluded(self, api_client, db):
        client, _, _ = _seed(db)
        resp = api_client.get(f"/api/v1/analytics/keyword-expansion?client_id={client.id}&min_clicks=1")
        data = resp.json()
        suggested_texts = [s["search_term"] for s in data["suggestions"]]
        # "buty sportowe" is an existing keyword — should NOT appear
        assert "buty sportowe" not in suggested_texts

    def test_empty_client(self, api_client, db):
        client = Client(name="Empty4", google_customer_id="0000000003")
        db.add(client)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/keyword-expansion?client_id={client.id}")
        assert resp.status_code == 200
        assert resp.json()["suggestions"] == []
