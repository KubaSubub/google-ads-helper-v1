"""Regression tests for positive/negative keyword sync hardening."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import AdGroup, Campaign, Client, Keyword, NegativeKeyword
from app.services.google_ads import GoogleAdsService


class FakeEnum:
    def __init__(self, name):
        self.name = name


class FakeClient:
    def __init__(self, search_service):
        self._search_service = search_service

    def get_service(self, name):
        assert name == "GoogleAdsService"
        return self._search_service


class QueueSearchService:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def search(self, customer_id, query):
        self.calls.append((customer_id, query))
        if not self.responses:
            return []
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def api_client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def seed_client_tree_with_keyword_cache(db):
    client = Client(name="Cleanup Client", google_customer_id="123-456-7890")
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

    db.commit()
    return client, campaign, ad_group


def build_campaign_row(campaign_id="camp-fresh", name="Fresh Campaign", status="ENABLED"):
    return SimpleNamespace(
        campaign=SimpleNamespace(
            id=campaign_id,
            name=name,
            status=FakeEnum(status),
            advertising_channel_type=FakeEnum("SEARCH"),
        ),
        campaign_budget=SimpleNamespace(amount_micros=2_500_000),
    )


def build_ad_group_row(campaign_id="camp-live", ad_group_id="ag-fresh", name="Fresh Group", status="ENABLED"):
    return SimpleNamespace(
        campaign=SimpleNamespace(id=campaign_id),
        ad_group=SimpleNamespace(
            id=ad_group_id,
            name=name,
            status=FakeEnum(status),
            cpc_bid_micros=1_200_000,
        ),
    )


def build_positive_keyword_row(
    ad_group_id="ag-live",
    keyword_id="kw-fresh",
    text="fresh keyword",
    status="ENABLED",
):
    metrics = SimpleNamespace(
        clicks=12,
        impressions=120,
        ctr=0.1,
        conversions=3,
        conversions_value=120.0,
        cost_micros=42_000_000,
        average_cpc=3_500_000,
        search_impression_share=0.42,
        search_top_impression_share=None,
        search_absolute_top_impression_share=None,
        search_rank_lost_impression_share=None,
        search_rank_lost_top_impression_share=None,
        search_rank_lost_absolute_top_impression_share=None,
        search_exact_match_impression_share=None,
        historical_quality_score=None,
        historical_creative_quality_score=None,
        historical_landing_page_quality_score=None,
        historical_search_predicted_ctr=None,
        all_conversions=None,
        all_conversions_value=None,
        cross_device_conversions=None,
        value_per_conversion=None,
        conversions_value_per_cost=None,
        absolute_top_impression_percentage=None,
        top_impression_percentage=None,
    )
    criterion = SimpleNamespace(
        criterion_id=keyword_id,
        keyword=SimpleNamespace(text=text, match_type=FakeEnum("EXACT")),
        status=FakeEnum(status),
        negative=False,
        final_urls=[],
        effective_cpc_bid_micros=1_100_000,
        quality_info=SimpleNamespace(quality_score=7),
    )
    return SimpleNamespace(
        campaign=SimpleNamespace(id="camp-live"),
        ad_group=SimpleNamespace(id=ad_group_id),
        ad_group_criterion=criterion,
        metrics=metrics,
    )


def build_negative_ad_group_row(
    campaign_id="camp-live",
    ad_group_id="ag-live",
    criterion_id="neg-ag-1",
    text="negative keyword",
    match_type="PHRASE",
    status="ENABLED",
):
    criterion = SimpleNamespace(
        criterion_id=criterion_id,
        resource_name=f"customers/1234567890/adGroupCriteria/{ad_group_id}~{criterion_id}",
        keyword=SimpleNamespace(text=text, match_type=FakeEnum(match_type)),
        status=FakeEnum(status),
        negative=True,
    )
    return SimpleNamespace(
        campaign=SimpleNamespace(id=campaign_id),
        ad_group=SimpleNamespace(id=ad_group_id),
        ad_group_criterion=criterion,
    )


def build_negative_campaign_row(
    campaign_id="camp-live",
    criterion_id="neg-camp-1",
    text="campaign negative",
    match_type="BROAD",
    status="ENABLED",
):
    criterion = SimpleNamespace(
        criterion_id=criterion_id,
        resource_name=f"customers/1234567890/campaignCriteria/{campaign_id}~{criterion_id}",
        keyword=SimpleNamespace(text=text, match_type=FakeEnum(match_type)),
        status=FakeEnum(status),
        negative=True,
    )
    return SimpleNamespace(
        campaign=SimpleNamespace(id=campaign_id),
        campaign_criterion=criterion,
    )


def test_sync_campaigns_marks_missing_local_campaigns_removed(db):
    client, _, _ = seed_client_tree_with_keyword_cache(db)
    stale_campaign = Campaign(
        client_id=client.id,
        google_campaign_id="camp-stale",
        name="Stale Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
    )
    db.add(stale_campaign)
    db.commit()

    service = GoogleAdsService()
    service.client = FakeClient(QueueSearchService(responses=[[build_campaign_row()]]))

    synced = service.sync_campaigns(db, "123-456-7890")

    db.refresh(stale_campaign)
    fresh_campaign = db.query(Campaign).filter(Campaign.google_campaign_id == "camp-fresh").one()

    assert synced == 1
    assert stale_campaign.status == "REMOVED"
    assert fresh_campaign.status == "ENABLED"


def test_sync_ad_groups_marks_missing_local_ad_groups_removed(db):
    _, campaign, _ = seed_client_tree_with_keyword_cache(db)
    stale_ad_group = AdGroup(
        campaign_id=campaign.id,
        google_ad_group_id="ag-stale",
        name="Stale Group",
        status="ENABLED",
    )
    db.add(stale_ad_group)
    db.commit()

    service = GoogleAdsService()
    service.client = FakeClient(QueueSearchService(responses=[[build_ad_group_row()]]))

    synced = service.sync_ad_groups(db, "123-456-7890")

    db.refresh(stale_ad_group)
    fresh_ad_group = db.query(AdGroup).filter(AdGroup.google_ad_group_id == "ag-fresh").one()

    assert synced == 1
    assert stale_ad_group.status == "REMOVED"
    assert fresh_ad_group.status == "ENABLED"


def test_positive_keyword_sync_marks_missing_local_keywords_removed(db):
    _, _, ad_group = seed_client_tree_with_keyword_cache(db)
    stale_keyword = Keyword(
        ad_group_id=ad_group.id,
        google_keyword_id="kw-stale",
        text="stale keyword",
        match_type="EXACT",
        status="ENABLED",
    )
    db.add(stale_keyword)
    db.commit()

    service = GoogleAdsService()
    service.client = FakeClient(QueueSearchService(responses=[[build_positive_keyword_row()]]))

    synced = service.sync_keywords(db, "123-456-7890")

    db.refresh(stale_keyword)
    fresh_keyword = db.query(Keyword).filter(Keyword.google_keyword_id == "kw-fresh").one()

    assert synced == 1
    assert stale_keyword.status == "REMOVED"
    assert fresh_keyword.status == "ENABLED"
    assert fresh_keyword.text == "fresh keyword"
    assert fresh_keyword.criterion_kind == "POSITIVE"


def test_positive_keyword_sync_skips_negative_rows_warns_and_marks_false_positive_removed(db, monkeypatch):
    _, _, ad_group = seed_client_tree_with_keyword_cache(db)
    stale_false_positive = Keyword(
        ad_group_id=ad_group.id,
        google_keyword_id="kw-negative",
        criterion_kind="POSITIVE",
        text="negative keyword",
        match_type="BROAD",
        status="ENABLED",
    )
    db.add(stale_false_positive)
    db.commit()

    warnings = []
    monkeypatch.setattr(
        GoogleAdsService,
        "_log_negative_positive_guard",
        staticmethod(lambda *args, **kwargs: warnings.append((args, kwargs))),
    )

    service = GoogleAdsService()
    service.client = FakeClient(
        QueueSearchService(
            responses=[[
                SimpleNamespace(
                    campaign=SimpleNamespace(id="camp-live"),
                    ad_group=SimpleNamespace(id="ag-live"),
                    ad_group_criterion=SimpleNamespace(
                        criterion_id="kw-negative",
                        keyword=SimpleNamespace(text="negative keyword", match_type=FakeEnum("BROAD")),
                        status=FakeEnum("ENABLED"),
                        negative=True,
                        final_urls=[],
                        effective_cpc_bid_micros=0,
                        quality_info=SimpleNamespace(quality_score=None),
                    ),
                    metrics=SimpleNamespace(
                        clicks=0,
                        impressions=0,
                        ctr=0.0,
                        conversions=0,
                        conversions_value=0.0,
                        cost_micros=0,
                        average_cpc=0,
                        search_impression_share=None,
                        search_top_impression_share=None,
                        search_absolute_top_impression_share=None,
                        search_rank_lost_impression_share=None,
                        search_rank_lost_top_impression_share=None,
                        search_rank_lost_absolute_top_impression_share=None,
                        search_exact_match_impression_share=None,
                        historical_quality_score=None,
                        historical_creative_quality_score=None,
                        historical_landing_page_quality_score=None,
                        historical_search_predicted_ctr=None,
                        all_conversions=None,
                        all_conversions_value=None,
                        cross_device_conversions=None,
                        value_per_conversion=None,
                        conversions_value_per_cost=None,
                        absolute_top_impression_percentage=None,
                        top_impression_percentage=None,
                    ),
                )
            ]]
        )
    )

    synced = service.sync_keywords(db, "123-456-7890")

    db.refresh(stale_false_positive)

    assert synced == 0
    assert stale_false_positive.status == "REMOVED"
    assert warnings, "Expected warning log when negative row enters positive path"
    assert warnings[0][1]["path_label"] == "sync_keywords"


def test_negative_keyword_sync_persists_campaign_and_ad_group_negatives(db):
    client, campaign, ad_group = seed_client_tree_with_keyword_cache(db)
    local_negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        text="campaign negative",
        match_type="BROAD",
        negative_scope="CAMPAIGN",
        status="ENABLED",
        source="LOCAL_ACTION",
    )
    db.add(local_negative)
    db.commit()

    service = GoogleAdsService()
    service.client = FakeClient(
        QueueSearchService(
            responses=[
                [build_negative_ad_group_row(text="negative keyword")],
                [build_negative_campaign_row(text="campaign negative")],
            ]
        )
    )

    synced = service.sync_negative_keywords(db, "123-456-7890")

    ad_group_negative = db.query(NegativeKeyword).filter(NegativeKeyword.google_criterion_id == "neg-ag-1").one()
    campaign_negative = db.query(NegativeKeyword).filter(NegativeKeyword.text == "campaign negative").one()

    assert synced == 2
    assert ad_group_negative.criterion_kind == "NEGATIVE"
    assert ad_group_negative.negative_scope == "AD_GROUP"
    assert ad_group_negative.ad_group_id == ad_group.id
    assert ad_group_negative.source == "GOOGLE_ADS_SYNC"
    assert campaign_negative.google_criterion_id == "neg-camp-1"
    assert campaign_negative.negative_scope == "CAMPAIGN"
    assert campaign_negative.source == "LOCAL_ACTION"


def test_negative_keyword_sync_does_not_cleanup_when_phase_fails(db):
    client, campaign, _ = seed_client_tree_with_keyword_cache(db)
    stale_negative = NegativeKeyword(
        client_id=client.id,
        campaign_id=campaign.id,
        google_criterion_id="neg-stale",
        criterion_kind="NEGATIVE",
        text="stale negative",
        match_type="PHRASE",
        negative_scope="CAMPAIGN",
        status="ENABLED",
        source="GOOGLE_ADS_SYNC",
    )
    db.add(stale_negative)
    db.commit()

    service = GoogleAdsService()
    service.client = FakeClient(
        QueueSearchService(
            responses=[
                [],
                RuntimeError("negative sync failed"),
            ]
        )
    )

    with pytest.raises(RuntimeError):
        service.sync_negative_keywords(db, "123-456-7890")

    db.refresh(stale_negative)
    assert stale_negative.status == "ENABLED"


def test_add_negative_action_uses_canonical_negative_keyword_model(db):
    client, campaign, _ = seed_client_tree_with_keyword_cache(db)
    service = GoogleAdsService()
    service.client = None

    result = service.apply_action(
        db=db,
        action_type="ADD_NEGATIVE",
        entity_id=campaign.id,
        params={
            "text": "free",
            "match_type": "PHRASE",
            "negative_level": "CAMPAIGN",
            "campaign_id": campaign.id,
        },
        target={"campaign_id": campaign.id},
        client_id=client.id,
    )

    negative = db.query(NegativeKeyword).filter(NegativeKeyword.campaign_id == campaign.id, NegativeKeyword.text == "free").one()

    assert result["status"] == "success"
    assert negative.criterion_kind == "NEGATIVE"
    assert negative.negative_scope == "CAMPAIGN"
    assert negative.status == "ENABLED"
    assert negative.source == "LOCAL_ACTION"


def test_reset_and_resync_do_not_restore_negative_into_positive_keywords(api_client, db):
    client, campaign, ad_group = seed_client_tree_with_keyword_cache(db)
    db.add(
        Keyword(
            ad_group_id=ad_group.id,
            google_keyword_id="neg-ag-1",
            criterion_kind="POSITIVE",
            text="negative keyword",
            match_type="PHRASE",
            status="ENABLED",
        )
    )
    db.commit()

    before_reset = db.query(Keyword).filter(Keyword.google_keyword_id == "neg-ag-1").count()
    assert before_reset == 1

    reset_response = api_client.post(f"/api/v1/clients/{client.id}/hard-reset")
    assert reset_response.status_code == 200
    assert db.query(Keyword).count() == 0
    assert db.query(NegativeKeyword).count() == 0

    service = GoogleAdsService()
    service.client = FakeClient(
        QueueSearchService(
            responses=[
                [build_campaign_row(campaign_id="camp-live", name="Brand Search")],
                [build_ad_group_row(campaign_id="camp-live", ad_group_id="ag-live", name="Core Group")],
                [build_positive_keyword_row(keyword_id="kw-fresh", text="fresh keyword")],
                [build_negative_ad_group_row(criterion_id="neg-ag-1", text="negative keyword")],
                [],
            ]
        )
    )

    assert service.sync_campaigns(db, "123-456-7890") == 1
    assert service.sync_ad_groups(db, "123-456-7890") == 1
    assert service.sync_keywords(db, "123-456-7890") == 1
    assert service.sync_negative_keywords(db, "123-456-7890") == 1

    assert db.query(Keyword).filter(Keyword.google_keyword_id == "neg-ag-1").count() == 0
    negative = db.query(NegativeKeyword).filter(NegativeKeyword.google_criterion_id == "neg-ag-1").one()
    assert negative.text == "negative keyword"
    assert negative.negative_scope == "AD_GROUP"


def test_keywords_endpoint_excludes_removed_by_default_and_exposes_positive_kind(api_client, db):
    client, campaign, ad_group = seed_client_tree_with_keyword_cache(db)
    db.add_all(
        [
            Keyword(
                ad_group_id=ad_group.id,
                google_keyword_id="kw-enabled",
                criterion_kind="POSITIVE",
                text="active keyword",
                match_type="EXACT",
                status="ENABLED",
                serving_status="LOW_SEARCH_VOLUME",
            ),
            Keyword(
                ad_group_id=ad_group.id,
                google_keyword_id="kw-removed",
                criterion_kind="POSITIVE",
                text="removed keyword",
                match_type="PHRASE",
                status="REMOVED",
            ),
        ]
    )
    db.commit()

    response = api_client.get("/api/v1/keywords/", params={"client_id": client.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["text"] for item in payload["items"]] == ["active keyword"]
    assert payload["items"][0]["campaign_id"] == campaign.id
    assert payload["items"][0]["campaign_name"] == "Brand Search"
    assert payload["items"][0]["ad_group_name"] == "Core Group"
    assert payload["items"][0]["status"] == "ENABLED"
    assert payload["items"][0]["criterion_kind"] == "POSITIVE"

    removed_response = api_client.get(
        "/api/v1/keywords/",
        params={"client_id": client.id, "include_removed": True},
    )

    assert removed_response.status_code == 200
    removed_payload = removed_response.json()
    assert removed_payload["total"] == 2
    assert {item["status"] for item in removed_payload["items"]} == {"ENABLED", "REMOVED"}


def test_negative_keywords_endpoint_returns_only_negative_rows(api_client, db):
    client, campaign, ad_group = seed_client_tree_with_keyword_cache(db)
    db.add(
        NegativeKeyword(
            client_id=client.id,
            campaign_id=campaign.id,
            ad_group_id=ad_group.id,
            google_criterion_id="neg-ag-1",
            criterion_kind="NEGATIVE",
            text="negative keyword",
            match_type="PHRASE",
            negative_scope="AD_GROUP",
            status="ENABLED",
            source="GOOGLE_ADS_SYNC",
        )
    )
    db.add(
        Keyword(
            ad_group_id=ad_group.id,
            google_keyword_id="kw-positive",
            criterion_kind="POSITIVE",
            text="positive keyword",
            match_type="EXACT",
            status="ENABLED",
        )
    )
    db.commit()

    response = api_client.get("/api/v1/negative-keywords/", params={"client_id": client.id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["text"] == "negative keyword"
    assert payload["items"][0]["criterion_kind"] == "NEGATIVE"
    assert payload["items"][0]["negative_scope"] == "AD_GROUP"
    assert payload["items"][0]["status"] == "ENABLED"
