"""Tests for keyword source diagnostics endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import AdGroup, Campaign, Client, Keyword, NegativeKeyword
from app.services.google_ads_debug import google_ads_debug_service


@pytest.fixture
def api_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_debug_client(db):
    client = Client(name="Debug Client", google_customer_id="123-456-7890")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="camp-live",
        name="Brand Search",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(campaign)
    db.flush()

    ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="ag-live",
        name="Core Group",
        status="ENABLED",
    )
    db.add(ad_group)
    db.flush()

    keyword = Keyword(
        ad_group_id=ad_group.id,
        google_keyword_id="kw-live",
        criterion_kind="POSITIVE",
        text="Bydgoszcz centrum",
        match_type="BROAD",
        status="ENABLED",
    )
    negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        ad_group_id=ad_group.id,
        google_criterion_id="neg-live",
        criterion_kind="NEGATIVE",
        text="Negative Bydgoszcz",
        match_type="PHRASE",
        negative_scope="AD_GROUP",
        status="ENABLED",
        source="GOOGLE_ADS_SYNC",
    )
    db.add(keyword)
    db.add(negative)
    db.commit()
    return client, campaign, ad_group, keyword, negative


def test_sync_debug_keywords_returns_normalized_api_and_db_matches(api_client, db, monkeypatch):
    client, _, _, keyword, negative = _seed_debug_client(db)

    def _fake_search(db, client_id, search_terms, include_removed, limit):
        assert client_id == client.id
        assert search_terms == ["bydgoszcz"]
        return {
            "client_id": client.id,
            "client_name": client.name,
            "customer_id": "1234567890",
            "search_terms": ["bydgoszcz"],
            "include_removed": False,
            "limit": 10,
            "query": "SELECT ... FROM keyword_view",
            "request_ids": {"keyword_view": "req-kv"},
            "classification": "NEGATIVE",
            "presence_state": "API_AND_DB",
            "synced_to_db": True,
            "api_count": 1,
            "local_count": 2,
            "db_rows_found": 2,
            "db_positive_rows_found": 1,
            "db_negative_rows_found": 1,
            "db_source_path": "C:/tmp/google_ads_app.db",
            "db_legacy_path": "C:/tmp/backend/google_ads_app.db",
            "db_legacy_exists": False,
            "api_rows": [
                {
                    "criterion_id": "33694032",
                    "keyword_text": "Bydgoszcz centrum",
                    "criterion_kind": "NEGATIVE",
                    "storage_kind": "API",
                    "request_id": "req-kv",
                    "source_query_type": "keyword_view",
                }
            ],
            "db_rows": [
                {
                    "criterion_id": "kw-live",
                    "criterion_kind": "POSITIVE",
                    "storage_kind": "DB_POSITIVE",
                    "db_record_id": keyword.id,
                },
                {
                    "criterion_id": "neg-live",
                    "criterion_kind": "NEGATIVE",
                    "storage_kind": "DB_NEGATIVE",
                    "db_record_id": negative.id,
                },
            ],
        }

    monkeypatch.setattr(google_ads_debug_service, "search_keyword_sources", _fake_search)

    response = api_client.get(
        "/api/v1/sync/debug/keywords",
        params=[
            ("client_id", str(client.id)),
            ("search", "bydgoszcz"),
            ("include_removed", "false"),
            ("limit", "10"),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"] == "NEGATIVE"
    assert payload["presence_state"] == "API_AND_DB"
    assert payload["request_ids"]["keyword_view"] == "req-kv"
    assert payload["db_positive_rows_found"] == 1
    assert payload["db_negative_rows_found"] == 1
    assert payload["api_rows"][0]["criterion_kind"] == "NEGATIVE"
    assert payload["db_rows"][0]["storage_kind"] == "DB_POSITIVE"
    assert payload["db_rows"][1]["storage_kind"] == "DB_NEGATIVE"


def test_keyword_source_of_truth_endpoint_returns_normalized_payload(api_client, db, monkeypatch):
    client, _, _, keyword, negative = _seed_debug_client(db)

    def _fake_build(db, client_id, criterion_id):
        assert client_id == client.id
        assert criterion_id == 33694032
        return {
            "client_id": client.id,
            "client_name": client.name,
            "customer_id": "1234567890",
            "login_customer_id": "9998887776",
            "criterion_id": "33694032",
            "google_ads_context": {
                "customer_id_used": "1234567890",
                "login_customer_id": "9998887776",
            },
            "accessible_customers": {
                "request_id": "req-accessible",
                "customer_ids": ["1234567890"],
                "contains_target_customer": True,
            },
            "mcc_customer_lookup": {
                "request_id": "req-mcc",
                "login_customer_id": "9998887776",
                "rows": [{"id": "1234567890", "manager": False}],
                "contains_target_customer": True,
            },
            "request_ids": {
                "keyword_view": "req-kv",
                "ad_group_criterion": "req-agc",
                "accessible_customers": "req-accessible",
                "mcc_customer_lookup": "req-mcc",
            },
            "classification": "NEGATIVE",
            "presence_state": "API_AND_DB",
            "synced_to_db": True,
            "db_rows_found": 2,
            "db_positive_rows_found": 1,
            "db_negative_rows_found": 1,
            "api_rows": [
                {
                    "criterion_id": "33694032",
                    "negative": True,
                    "criterion_kind": "NEGATIVE",
                    "request_id": "req-kv",
                    "source_query_type": "keyword_view",
                    "storage_kind": "API",
                }
            ],
            "db_rows": [
                {
                    "criterion_id": "kw-live",
                    "criterion_kind": "POSITIVE",
                    "storage_kind": "DB_POSITIVE",
                    "db_record_id": keyword.id,
                },
                {
                    "criterion_id": "neg-live",
                    "criterion_kind": "NEGATIVE",
                    "storage_kind": "DB_NEGATIVE",
                    "db_record_id": negative.id,
                },
            ],
            "db_source_path": "C:/tmp/google_ads_app.db",
            "db_legacy_path": "C:/tmp/backend/google_ads_app.db",
            "db_legacy_exists": False,
        }

    monkeypatch.setattr(google_ads_debug_service, "build_keyword_source_of_truth", _fake_build)

    response = api_client.get(
        "/api/v1/sync/debug/keyword-source-of-truth",
        params={"client_id": client.id, "criterion_id": 33694032},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["criterion_id"] == "33694032"
    assert payload["classification"] == "NEGATIVE"
    assert payload["presence_state"] == "API_AND_DB"
    assert payload["request_ids"]["keyword_view"] == "req-kv"
    assert payload["api_rows"][0]["negative"] is True
    assert payload["db_positive_rows_found"] == 1
    assert payload["db_negative_rows_found"] == 1
    assert payload["accessible_customers"]["contains_target_customer"] is True
    assert payload["mcc_customer_lookup"]["request_id"] == "req-mcc"
