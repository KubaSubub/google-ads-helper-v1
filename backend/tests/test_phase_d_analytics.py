"""Tests for Phase D analytics endpoints — PMax, Audience, Extensions."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import Campaign, Client, MetricSegmented
from app.models.asset_group import AssetGroup
from app.models.asset_group_daily import AssetGroupDaily
from app.models.asset_group_asset import AssetGroupAsset
from app.models.asset_group_signal import AssetGroupSignal
from app.models.campaign_audience import CampaignAudienceMetric
from app.models.campaign_asset import CampaignAsset


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_pmax(db):
    """Seed PMax campaign with asset groups, daily metrics, assets, signals."""
    client = Client(name="PMax Test", google_customer_id="111-111-1111")
    db.add(client)
    db.flush()

    pmax = Campaign(
        client_id=client.id,
        google_campaign_id="pmax1",
        name="PMax - Test",
        status="ENABLED",
        campaign_type="PERFORMANCE_MAX",
        budget_micros=350_000_000,
    )
    db.add(pmax)
    db.flush()

    # PMax channel breakdown (MetricSegmented with ad_network_type)
    today = date.today()
    for d_offset in range(7):
        d = today - timedelta(days=d_offset)
        for net_type, clicks, impr, cost, conv in [
            ("SEARCH", 50, 500, 2_000_000, 3.0),
            ("CONTENT", 30, 400, 1_500_000, 1.0),
            ("YOUTUBE_WATCH", 20, 300, 1_000_000, 0.5),
            ("SHOPPING", 40, 350, 1_800_000, 2.5),
            ("CROSS_NETWORK", 10, 100, 500_000, 0.1),
        ]:
            db.add(MetricSegmented(
                campaign_id=pmax.id,
                date=d,
                ad_network_type=net_type,
                clicks=clicks,
                impressions=impr,
                cost_micros=cost,
                conversions=conv,
                conversion_value_micros=int(conv * 100_000_000),
            ))

    # Asset groups
    ag1 = AssetGroup(
        campaign_id=pmax.id,
        google_asset_group_id="5001",
        name="Meble - Ogólne",
        status="ENABLED",
        ad_strength="GOOD",
        final_url="https://test.pl/meble",
    )
    ag2 = AssetGroup(
        campaign_id=pmax.id,
        google_asset_group_id="5002",
        name="Kanapy Premium",
        status="ENABLED",
        ad_strength="EXCELLENT",
        final_url="https://test.pl/kanapy",
    )
    ag3 = AssetGroup(
        campaign_id=pmax.id,
        google_asset_group_id="5003",
        name="Promocje",
        status="ENABLED",
        ad_strength="POOR",
        final_url="https://test.pl/promo",
    )
    db.add_all([ag1, ag2, ag3])
    db.flush()

    # Daily metrics for asset groups
    for ag, mult in [(ag1, 1.0), (ag2, 1.3), (ag3, 0.5)]:
        for d_offset in range(7):
            d = today - timedelta(days=d_offset)
            db.add(AssetGroupDaily(
                asset_group_id=ag.id,
                date=d,
                clicks=int(40 * mult),
                impressions=int(400 * mult),
                ctr=10.0,
                conversions=round(2.0 * mult, 2),
                conversion_value_micros=int(200 * mult * 1_000_000),
                cost_micros=int(1.5 * mult * 1_000_000),
                avg_cpc_micros=int(0.0375 * 1_000_000),
            ))

    # Assets
    for ag in [ag1, ag2, ag3]:
        for i, (at, ft, text, perf) in enumerate([
            ("HEADLINE", "HEADLINE", "Test headline", "BEST"),
            ("HEADLINE", "HEADLINE", "Test headline 2", "GOOD"),
            ("DESCRIPTION", "DESCRIPTION", "Test description", "GOOD"),
            ("IMAGE", "MARKETING_IMAGE", None, "LEARNING"),
        ]):
            db.add(AssetGroupAsset(
                asset_group_id=ag.id,
                google_asset_id=f"{ag.id}_{i}",
                asset_type=at,
                field_type=ft,
                text_content=text,
                performance_label=perf,
            ))

    # Signals
    for ag in [ag1, ag2]:
        db.add(AssetGroupSignal(
            asset_group_id=ag.id,
            signal_type="SEARCH_THEME",
            search_theme_text="meble do domu",
            audience_resource_name="",
        ))
        db.add(AssetGroupSignal(
            asset_group_id=ag.id,
            signal_type="AUDIENCE",
            search_theme_text="",
            audience_resource_name="customers/123/userLists/1001",
            audience_name="Remarketing - Odwiedzający",
        ))

    db.commit()
    return client, pmax, [ag1, ag2, ag3]


def _seed_audience(db, client, campaign):
    """Seed audience metrics for a campaign."""
    today = date.today()
    audiences = [
        ("cust/123/ul/2001", "Remarketing - 30d", "REMARKETING"),
        ("cust/123/ul/2002", "In-Market - Meble", "IN_MARKET"),
        ("cust/123/ul/2003", "Custom - Premium", "CUSTOM"),
    ]
    for aud_rn, aud_name, aud_type in audiences:
        for d_offset in range(7):
            d = today - timedelta(days=d_offset)
            db.add(CampaignAudienceMetric(
                campaign_id=campaign.id,
                audience_resource_name=aud_rn,
                audience_name=aud_name,
                audience_type=aud_type,
                date=d,
                clicks=20,
                impressions=200,
                ctr=10.0,
                conversions=1.5,
                conversion_value_micros=150_000_000,
                cost_micros=1_000_000,
                avg_cpc_micros=50_000,
            ))
    db.commit()


def _seed_extensions(db, client):
    """Seed campaign assets (extensions) for SEARCH campaigns."""
    search = Campaign(
        client_id=client.id,
        google_campaign_id="s1",
        name="Search Full",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=150_000_000,
    )
    search2 = Campaign(
        client_id=client.id,
        google_campaign_id="s2",
        name="Search Partial",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=100_000_000,
    )
    db.add_all([search, search2])
    db.flush()

    # Full extensions for search
    aid = 8000
    for ext_type, count in [("SITELINK", 4), ("CALLOUT", 4), ("STRUCTURED_SNIPPET", 1)]:
        for i in range(count):
            aid += 1
            db.add(CampaignAsset(
                campaign_id=search.id,
                google_asset_id=str(aid),
                asset_type=ext_type,
                asset_name=f"{ext_type} #{i+1}",
                status="ENABLED",
                performance_label="GOOD",
                source="ADVERTISER",
                clicks=50,
                impressions=500,
                cost_micros=1_000_000,
                conversions=2.0,
                ctr=10.0,
            ))

    # Partial extensions for search2 — only 2 sitelinks, no callouts
    for i in range(2):
        aid += 1
        db.add(CampaignAsset(
            campaign_id=search2.id,
            google_asset_id=str(aid),
            asset_type="SITELINK",
            asset_name=f"Sitelink #{i+1}",
            status="ENABLED",
            performance_label="GOOD",
            source="ADVERTISER",
            clicks=20,
            impressions=200,
            cost_micros=500_000,
            conversions=1.0,
            ctr=10.0,
        ))

    db.commit()
    return search, search2


# ─── GAP 3A: PMax Channel Breakdown ────────────────────────────────


class TestPmaxChannels:
    def test_pmax_channels_returns_200(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/pmax-channels?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "channels" in data
        assert len(data["channels"]) == 5

    def test_pmax_channels_has_cost_share(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/pmax-channels?client_id={client.id}")
        data = resp.json()
        channels = data["channels"]
        total_share = sum(ch.get("cost_share_pct", 0) for ch in channels)
        assert 99 < total_share < 101  # shares sum to ~100%

    def test_pmax_channels_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/pmax-channels?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["channels"] == []

    def test_pmax_channels_with_date_filter(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        today = date.today()
        df = (today - timedelta(days=3)).isoformat()
        dt = today.isoformat()
        resp = api_client.get(
            f"/api/v1/analytics/pmax-channels?client_id={client.id}&date_from={df}&date_to={dt}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["channels"]) == 5


# ─── GAP 3B: Asset Group Performance ───────────────────────────────


class TestAssetGroupPerformance:
    def test_asset_group_performance_returns_200(self, api_client, db):
        client, pmax, ags = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/asset-group-performance?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "asset_groups" in data
        assert len(data["asset_groups"]) == 3

    def test_asset_group_has_ad_strength(self, api_client, db):
        client, pmax, ags = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/asset-group-performance?client_id={client.id}")
        data = resp.json()
        strengths = {g["ad_strength"] for g in data["asset_groups"]}
        assert "GOOD" in strengths
        assert "EXCELLENT" in strengths
        assert "POOR" in strengths

    def test_asset_group_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/asset-group-performance?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_groups"] == []

    def test_asset_group_metrics_present(self, api_client, db):
        client, pmax, ags = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/asset-group-performance?client_id={client.id}")
        data = resp.json()
        for g in data["asset_groups"]:
            assert "clicks" in g or "cost_micros" in g or "cpa_micros" in g


# ─── GAP 3C: Search Themes ─────────────────────────────────────────


class TestPmaxSearchThemes:
    def test_search_themes_returns_200(self, api_client, db):
        client, pmax, ags = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/pmax-search-themes?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "asset_groups" in data

    def test_search_themes_contains_themes(self, api_client, db):
        client, pmax, ags = _seed_pmax(db)
        resp = api_client.get(f"/api/v1/analytics/pmax-search-themes?client_id={client.id}")
        data = resp.json()
        # ag1 and ag2 have signals
        themes_found = False
        for ag_data in data["asset_groups"]:
            if ag_data.get("search_themes") or ag_data.get("signals"):
                themes_found = True
        assert themes_found

    def test_search_themes_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/pmax-search-themes?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_groups"] == []


# ─── GAP 4B: Audience Performance ──────────────────────────────────


class TestAudiencePerformance:
    def test_audience_performance_returns_200(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        _seed_audience(db, client, pmax)
        resp = api_client.get(f"/api/v1/analytics/audience-performance?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "audiences" in data
        assert len(data["audiences"]) == 3

    def test_audience_types_present(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        _seed_audience(db, client, pmax)
        resp = api_client.get(f"/api/v1/analytics/audience-performance?client_id={client.id}")
        data = resp.json()
        types = {a["audience_type"] for a in data["audiences"]}
        assert "REMARKETING" in types
        assert "IN_MARKET" in types

    def test_audience_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/audience-performance?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["audiences"] == []

    def test_audience_with_date_filter(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        _seed_audience(db, client, pmax)
        today = date.today()
        df = (today - timedelta(days=3)).isoformat()
        dt = today.isoformat()
        resp = api_client.get(
            f"/api/v1/analytics/audience-performance?client_id={client.id}&date_from={df}&date_to={dt}"
        )
        assert resp.status_code == 200


# ─── GAP 5A: Missing Extensions ────────────────────────────────────


class TestMissingExtensions:
    def test_missing_extensions_returns_200(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        search, search2 = _seed_extensions(db, client)
        resp = api_client.get(f"/api/v1/analytics/missing-extensions?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "campaigns" in data

    def test_full_extensions_campaign_passes(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        search, search2 = _seed_extensions(db, client)
        resp = api_client.get(f"/api/v1/analytics/missing-extensions?client_id={client.id}")
        data = resp.json()
        # search has full extensions, search2 is partial
        campaign_names = {c["campaign_name"] for c in data["campaigns"]}
        assert "Search Full" in campaign_names or "Search Partial" in campaign_names

    def test_missing_extensions_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/missing-extensions?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["campaigns"] == []


# ─── GAP 5B: Extension Performance ─────────────────────────────────


class TestExtensionPerformance:
    def test_extension_performance_returns_200(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        search, search2 = _seed_extensions(db, client)
        resp = api_client.get(f"/api/v1/analytics/extension-performance?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "by_type" in data

    def test_extension_types_present(self, api_client, db):
        client, pmax, _ = _seed_pmax(db)
        search, search2 = _seed_extensions(db, client)
        resp = api_client.get(f"/api/v1/analytics/extension-performance?client_id={client.id}")
        data = resp.json()
        type_names = {t["asset_type"] for t in data["by_type"]}
        assert "SITELINK" in type_names

    def test_extension_performance_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/extension-performance?client_id={c.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["by_type"] == []


# ─── Model Tests ────────────────────────────────────────────────────


class TestPhaseDModels:
    def test_asset_group_creation(self, db):
        client = Client(name="Model Test", google_customer_id="222-222-2222")
        db.add(client)
        db.flush()
        camp = Campaign(
            client_id=client.id,
            google_campaign_id="mc1",
            name="PMax Model",
            status="ENABLED",
            campaign_type="PERFORMANCE_MAX",
            budget_micros=100_000_000,
        )
        db.add(camp)
        db.flush()
        ag = AssetGroup(
            campaign_id=camp.id,
            google_asset_group_id="9001",
            name="Test AG",
            status="ENABLED",
            ad_strength="GOOD",
        )
        db.add(ag)
        db.commit()
        assert ag.id is not None
        assert ag.campaign_id == camp.id

    def test_asset_group_daily_creation(self, db):
        client = Client(name="Model Test 2", google_customer_id="333-333-3333")
        db.add(client)
        db.flush()
        camp = Campaign(
            client_id=client.id, google_campaign_id="mc2",
            name="PMax", status="ENABLED", campaign_type="PERFORMANCE_MAX",
            budget_micros=100_000_000,
        )
        db.add(camp)
        db.flush()
        ag = AssetGroup(
            campaign_id=camp.id, google_asset_group_id="9002",
            name="AG 2", status="ENABLED",
        )
        db.add(ag)
        db.flush()
        daily = AssetGroupDaily(
            asset_group_id=ag.id, date=date.today(),
            clicks=100, impressions=1000, ctr=10.0,
            conversions=5.0, cost_micros=5_000_000,
        )
        db.add(daily)
        db.commit()
        assert daily.id is not None

    def test_campaign_audience_metric_creation(self, db):
        client = Client(name="Audience Model", google_customer_id="444-444-4444")
        db.add(client)
        db.flush()
        camp = Campaign(
            client_id=client.id, google_campaign_id="mc3",
            name="Search", status="ENABLED", campaign_type="SEARCH",
            budget_micros=100_000_000,
        )
        db.add(camp)
        db.flush()
        aud = CampaignAudienceMetric(
            campaign_id=camp.id,
            audience_resource_name="test/audience/1",
            audience_name="Test Audience",
            audience_type="REMARKETING",
            date=date.today(),
            clicks=50, impressions=500, ctr=10.0,
            conversions=3.0, cost_micros=2_000_000,
        )
        db.add(aud)
        db.commit()
        assert aud.id is not None

    def test_campaign_asset_creation(self, db):
        client = Client(name="Asset Model", google_customer_id="555-555-5555")
        db.add(client)
        db.flush()
        camp = Campaign(
            client_id=client.id, google_campaign_id="mc4",
            name="Search", status="ENABLED", campaign_type="SEARCH",
            budget_micros=100_000_000,
        )
        db.add(camp)
        db.flush()
        ext = CampaignAsset(
            campaign_id=camp.id,
            google_asset_id="ext1",
            asset_type="SITELINK",
            asset_name="Test Sitelink",
            status="ENABLED",
            clicks=20, impressions=200,
        )
        db.add(ext)
        db.commit()
        assert ext.id is not None

    def test_metric_segmented_ad_network_type(self, db):
        client = Client(name="Network Model", google_customer_id="666-666-6666")
        db.add(client)
        db.flush()
        camp = Campaign(
            client_id=client.id, google_campaign_id="mc5",
            name="PMax", status="ENABLED", campaign_type="PERFORMANCE_MAX",
            budget_micros=100_000_000,
        )
        db.add(camp)
        db.flush()
        ms = MetricSegmented(
            campaign_id=camp.id,
            date=date.today(),
            ad_network_type="SEARCH",
            clicks=100,
            impressions=1000,
            cost_micros=5_000_000,
        )
        db.add(ms)
        db.commit()
        assert ms.ad_network_type == "SEARCH"


# ─── Sync Pipeline Tests ───────────────────────────────────────────


class TestSyncPhases:
    def test_phase_d_phases_in_phase_map(self):
        """Verify Phase D sync phases exist in sync_single_phase docstring."""
        from app.routers.sync import sync_single_phase
        doc = sync_single_phase.__doc__ or ""
        for phase in ["pmax_channel_metrics", "asset_groups", "asset_group_daily",
                       "asset_group_assets", "asset_group_signals",
                       "campaign_audiences", "campaign_assets"]:
            assert phase in doc, f"Phase '{phase}' not in sync_single_phase docstring"

    def test_google_ads_service_has_sync_methods(self):
        """Verify google_ads_service has all Phase D sync methods."""
        from app.services.google_ads import google_ads_service
        for method in ["sync_pmax_channel_metrics", "sync_asset_groups",
                       "sync_asset_group_daily", "sync_asset_group_assets",
                       "sync_asset_group_signals", "sync_campaign_audiences",
                       "sync_campaign_assets"]:
            assert hasattr(google_ads_service, method), f"Missing method: {method}"


# ─── Recommendation Rules Contract ─────────────────────────────────


class TestPhaseDRecommendationTypes:
    def test_phase_d_types_exist(self):
        from app.services.recommendations import RecommendationType
        assert hasattr(RecommendationType, "PMAX_CHANNEL_IMBALANCE")
        assert hasattr(RecommendationType, "ASSET_GROUP_AD_STRENGTH")
        assert hasattr(RecommendationType, "AUDIENCE_PERFORMANCE_ANOMALY")
        assert hasattr(RecommendationType, "MISSING_EXTENSIONS_ALERT")

    def test_enum_count_is_36(self):
        """v2.2 added ATTRIBUTION_MODEL_WARNING (R32) and NEGATIVE_KEYWORD_CONFLICT (R33)."""
        from app.services.recommendations import RecommendationType
        assert len(RecommendationType) == 36
        assert hasattr(RecommendationType, "ATTRIBUTION_MODEL_WARNING")
        assert hasattr(RecommendationType, "NEGATIVE_KEYWORD_CONFLICT")
