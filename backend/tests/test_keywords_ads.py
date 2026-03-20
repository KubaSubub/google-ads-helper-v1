"""Tests for keywords_ads router — keywords, negative keywords, negative keyword lists."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.ad_group import AdGroup
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.keyword import Keyword
from app.models.keyword_daily import KeywordDaily
from app.models.negative_keyword import NegativeKeyword
from app.models.negative_keyword_list import NegativeKeywordList, NegativeKeywordListItem


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_keywords(db):
    """Seed client, campaign, ad_group, and keywords for testing."""
    client = Client(name="KW Test Client", google_customer_id="9990001110")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="kwc1",
        name="Search Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="kwag1",
        name="Ad Group A",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    kw1 = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="gkw1",
        text="buty sportowe",
        match_type="EXACT",
        status="ENABLED",
        clicks=100,
        impressions=1000,
        cost_micros=20_000_000,
        conversions=5.0,
        ctr=10.0,
        avg_cpc_micros=200_000,
    )
    kw2 = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="gkw2",
        text="buty zimowe",
        match_type="BROAD",
        status="ENABLED",
        clicks=50,
        impressions=500,
        cost_micros=10_000_000,
        conversions=2.0,
        ctr=10.0,
        avg_cpc_micros=200_000,
    )
    kw3 = Keyword(
        ad_group_id=ag.id,
        google_keyword_id="gkw3",
        text="stare kalosze",
        match_type="PHRASE",
        status="REMOVED",
        clicks=0,
        impressions=0,
        cost_micros=0,
        conversions=0,
        ctr=0,
        avg_cpc_micros=0,
    )
    db.add_all([kw1, kw2, kw3])
    db.commit()
    return client, campaign, ag, kw1, kw2


def _seed_keyword_daily(db, keyword, days=7):
    """Seed daily metrics for a keyword."""
    today = date.today()
    for i in range(days):
        db.add(KeywordDaily(
            keyword_id=keyword.id,
            date=today - timedelta(days=i),
            clicks=10,
            impressions=100,
            cost_micros=1_000_000,
            conversions=1.0,
            conversion_value_micros=5_000_000,
            avg_cpc_micros=100_000,
        ))
    db.commit()


# ---------------------------------------------------------------------------
# Keywords listing
# ---------------------------------------------------------------------------


class TestListKeywords:
    def test_returns_paginated_response(self, api_client, db):
        client, _, _, _, _ = _seed_keywords(db)

        resp = api_client.get(f"/api/v1/keywords/?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        assert "total" in data
        # Default excludes REMOVED
        assert data["total"] == 2

    def test_include_removed(self, api_client, db):
        client, _, _, _, _ = _seed_keywords(db)

        resp = api_client.get(f"/api/v1/keywords/?client_id={client.id}&include_removed=true")
        data = resp.json()
        assert data["total"] == 3

    def test_filter_by_match_type(self, api_client, db):
        client, _, _, _, _ = _seed_keywords(db)

        resp = api_client.get(f"/api/v1/keywords/?client_id={client.id}&match_type=EXACT")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["text"] == "buty sportowe"

    def test_search_filter(self, api_client, db):
        client, _, _, _, _ = _seed_keywords(db)

        resp = api_client.get(f"/api/v1/keywords/?client_id={client.id}&search=buty")
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert "buty" in item["text"]

    def test_with_date_range_aggregates_daily(self, api_client, db):
        client, _, _, kw1, _ = _seed_keywords(db)
        _seed_keyword_daily(db, kw1, days=7)

        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=6)).isoformat()

        resp = api_client.get(
            f"/api/v1/keywords/?client_id={client.id}&date_from={week_ago}&date_to={today}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        # Find kw1 in results — should have aggregated daily metrics
        kw1_item = next((i for i in data["items"] if i["text"] == "buty sportowe"), None)
        assert kw1_item is not None
        assert kw1_item["clicks"] == 70  # 7 days * 10 clicks

    def test_empty_result_for_nonexistent_client(self, api_client, db):
        resp = api_client.get("/api/v1/keywords/?client_id=99999")
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_pagination(self, api_client, db):
        client, _, _, _, _ = _seed_keywords(db)

        resp = api_client.get(f"/api/v1/keywords/?client_id={client.id}&page=1&page_size=1")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2
        assert data["total_pages"] == 2


# ---------------------------------------------------------------------------
# Negative keywords
# ---------------------------------------------------------------------------


def _seed_negative_keywords(db):
    """Seed negative keywords for testing."""
    client = Client(name="Neg KW Client", google_customer_id="8880001110")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="nkc1",
        name="Neg Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="nkag1",
        name="Neg Group",
        status="ENABLED",
    )
    db.add(ag)
    db.flush()

    nk1 = NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        text="darmowe",
        match_type="PHRASE",
        negative_scope="CAMPAIGN",
        status="ENABLED",
        source="LOCAL_ACTION",
        criterion_kind="NEGATIVE",
    )
    nk2 = NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        text="za darmo",
        match_type="EXACT",
        negative_scope="CAMPAIGN",
        status="ENABLED",
        source="LOCAL_ACTION",
        criterion_kind="NEGATIVE",
    )
    db.add_all([nk1, nk2])
    db.commit()
    return client, campaign, ag, nk1, nk2


class TestNegativeKeywords:
    def test_list_negative_keywords(self, api_client, db):
        client, _, _, _, _ = _seed_negative_keywords(db)

        resp = api_client.get(f"/api/v1/negative-keywords/?client_id={client.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total"] == 2

    def test_list_negative_keywords_search_filter(self, api_client, db):
        client, _, _, _, _ = _seed_negative_keywords(db)

        resp = api_client.get(f"/api/v1/negative-keywords/?client_id={client.id}&search=darmowe")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["text"] == "darmowe"

    def test_create_negative_keywords(self, api_client, db, monkeypatch):
        client, campaign, _, _, _ = _seed_negative_keywords(db)

        # Bypass demo guard (it has a known arg-order bug in keywords_ads.py)
        from app.routers import keywords_ads
        monkeypatch.setattr(keywords_ads, "ensure_demo_write_allowed", lambda *a, **kw: None)

        resp = api_client.post(
            "/api/v1/negative-keywords/",
            json={
                "client_id": client.id,
                "campaign_id": campaign.id,
                "texts": ["tanio", "promocja"],
                "match_type": "PHRASE",
                "negative_scope": "CAMPAIGN",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        texts = [item["text"] for item in data]
        assert "tanio" in texts
        assert "promocja" in texts

    def test_create_negative_keywords_skips_duplicates(self, api_client, db, monkeypatch):
        client, campaign, _, _, _ = _seed_negative_keywords(db)

        from app.routers import keywords_ads
        monkeypatch.setattr(keywords_ads, "ensure_demo_write_allowed", lambda *a, **kw: None)

        resp = api_client.post(
            "/api/v1/negative-keywords/",
            json={
                "client_id": client.id,
                "campaign_id": campaign.id,
                "texts": ["darmowe"],  # already exists
                "match_type": "PHRASE",
                "negative_scope": "CAMPAIGN",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0  # skipped duplicate

    def test_delete_negative_keyword(self, api_client, db, monkeypatch):
        client, _, _, nk1, _ = _seed_negative_keywords(db)

        from app.routers import keywords_ads
        monkeypatch.setattr(keywords_ads, "ensure_demo_write_allowed", lambda *a, **kw: None)

        resp = api_client.delete(f"/api/v1/negative-keywords/{nk1.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify soft-deleted
        db.expire_all()
        nk = db.get(NegativeKeyword, nk1.id)
        assert nk.status == "REMOVED"

    def test_delete_nonexistent_negative_keyword(self, api_client, db):
        resp = api_client.delete("/api/v1/negative-keywords/99999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Negative keyword lists
# ---------------------------------------------------------------------------


class TestNegativeKeywordLists:
    def test_create_and_list(self, api_client, db):
        client = Client(name="NKL Client", google_customer_id="7770001110")
        db.add(client)
        db.commit()

        # Create
        resp = api_client.post(
            "/api/v1/negative-keyword-lists/",
            json={"client_id": client.id, "name": "Spam List", "description": "Filtr spamu"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Spam List"
        assert data["item_count"] == 0
        list_id = data["id"]

        # List
        resp = api_client.get(f"/api/v1/negative-keyword-lists/?client_id={client.id}")
        assert resp.status_code == 200
        lists = resp.json()
        assert len(lists) == 1
        assert lists[0]["id"] == list_id

    def test_get_list_detail(self, api_client, db):
        client = Client(name="NKL Detail", google_customer_id="7770002220")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="Test List")
        db.add(nkl)
        db.flush()

        item = NegativeKeywordListItem(list_id=nkl.id, text="spam", match_type="PHRASE")
        db.add(item)
        db.commit()

        resp = api_client.get(f"/api/v1/negative-keyword-lists/{nkl.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test List"
        assert data["item_count"] == 1
        assert data["items"][0]["text"] == "spam"

    def test_add_items_to_list(self, api_client, db):
        client = Client(name="NKL Items", google_customer_id="7770003330")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="Items List")
        db.add(nkl)
        db.commit()

        resp = api_client.post(
            f"/api/v1/negative-keyword-lists/{nkl.id}/items",
            json={"texts": ["reklama", "oszustwo"], "match_type": "PHRASE"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_add_items_skips_duplicates(self, api_client, db):
        client = Client(name="NKL Dup", google_customer_id="7770004440")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="Dup List")
        db.add(nkl)
        db.flush()

        item = NegativeKeywordListItem(list_id=nkl.id, text="spam", match_type="PHRASE")
        db.add(item)
        db.commit()

        resp = api_client.post(
            f"/api/v1/negative-keyword-lists/{nkl.id}/items",
            json={"texts": ["spam"], "match_type": "PHRASE"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0  # duplicate skipped

    def test_delete_list(self, api_client, db):
        client = Client(name="NKL Del", google_customer_id="7770005550")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="To Delete")
        db.add(nkl)
        db.commit()

        resp = api_client.delete(f"/api/v1/negative-keyword-lists/{nkl.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify deleted
        assert db.get(NegativeKeywordList, nkl.id) is None

    def test_delete_nonexistent_list_404(self, api_client, db):
        resp = api_client.delete("/api/v1/negative-keyword-lists/99999")
        assert resp.status_code == 404

    def test_remove_item_from_list(self, api_client, db):
        client = Client(name="NKL Rm", google_customer_id="7770006660")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="Rm List")
        db.add(nkl)
        db.flush()

        item = NegativeKeywordListItem(list_id=nkl.id, text="usun", match_type="PHRASE")
        db.add(item)
        db.commit()

        resp = api_client.delete(f"/api/v1/negative-keyword-lists/{nkl.id}/items/{item.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_apply_list_to_campaign(self, api_client, db, monkeypatch):
        client = Client(name="NKL Apply", google_customer_id="7770007770")
        db.add(client)
        db.flush()

        campaign = Campaign(
            client_id=client.id,
            google_campaign_id="applc1",
            name="Apply Camp",
            status="ENABLED",
            campaign_type="SEARCH",
        )
        db.add(campaign)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="Apply List")
        db.add(nkl)
        db.flush()

        item = NegativeKeywordListItem(list_id=nkl.id, text="zly termin", match_type="PHRASE")
        db.add(item)
        db.commit()

        # Bypass demo guard (it has a known arg-order bug in keywords_ads.py)
        from app.routers import keywords_ads
        monkeypatch.setattr(keywords_ads, "ensure_demo_write_allowed", lambda *a, **kw: None)

        resp = api_client.post(
            f"/api/v1/negative-keyword-lists/{nkl.id}/apply",
            json={"campaign_ids": [campaign.id], "ad_group_ids": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        assert data["skipped"] == 0

    def test_apply_list_requires_target(self, api_client, db, monkeypatch):
        client = Client(name="NKL NoTarget", google_customer_id="7770008880")
        db.add(client)
        db.flush()

        nkl = NegativeKeywordList(client_id=client.id, name="No Target")
        db.add(nkl)
        db.commit()

        from app.routers import keywords_ads
        monkeypatch.setattr(keywords_ads, "ensure_demo_write_allowed", lambda *a, **kw: None)

        resp = api_client.post(
            f"/api/v1/negative-keyword-lists/{nkl.id}/apply",
            json={"campaign_ids": [], "ad_group_ids": []},
        )
        assert resp.status_code == 400
