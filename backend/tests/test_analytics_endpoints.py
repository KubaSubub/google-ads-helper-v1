"""Tests for analytics router endpoints — coverage for all /analytics/* endpoints."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Campaign, Client, MetricDaily, Keyword, AdGroup, Alert, Ad, SearchTerm, MetricSegmented


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_full(db):
    """Seed client with campaign, ad group, keywords, metrics, search terms, ads."""
    client = Client(name="Analytics Test", google_customer_id="9999999999")
    db.add(client)
    db.flush()

    campaign = Campaign(
        client_id=client.id,
        google_campaign_id="ac1",
        name="Search Analytics",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=50_000_000,
    )
    db.add(campaign)
    db.flush()

    ag = AdGroup(campaign_id=campaign.id, google_ad_group_id="aag1", name="Group A", status="ENABLED")
    db.add(ag)
    db.flush()

    # Keywords with varied match types and quality scores
    for i, (text, mt, qs) in enumerate([
        ("buty sportowe", "EXACT", 8),
        ("buty zimowe", "PHRASE", 3),
        ("obuwie", "BROAD", 6),
    ]):
        kw = Keyword(
            ad_group_id=ag.id,
            google_keyword_id=f"kw{i}",
            text=text,
            match_type=mt,
            status="ENABLED",
            quality_score=qs,
        )
        db.add(kw)
    db.flush()

    # Ads
    ad = Ad(
        ad_group_id=ag.id,
        google_ad_id="ad1",
        ad_type="RESPONSIVE_SEARCH_AD",
        status="ENABLED",
        headlines=[{"text": "Kup buty"}, {"text": "Tanie buty"}],
        descriptions=[{"text": "Najlepsze buty"}],
        clicks=50,
        impressions=500,
        cost_micros=5_000_000,
        conversions=2.0,
    )
    db.add(ad)

    # Search terms
    today = date.today()
    week_ago = today - timedelta(days=7)
    for text, clicks, cost, conv in [
        ("buty sportowe nike", 30, 3_000_000, 2.0),
        ("tanie kalosze", 10, 2_000_000, 0),
    ]:
        db.add(SearchTerm(
            ad_group_id=ag.id,
            campaign_id=campaign.id,
            text=text,
            clicks=clicks,
            impressions=clicks * 10,
            cost_micros=cost,
            conversions=conv,
            ctr=10.0,
            date_from=week_ago,
            date_to=today,
        ))

    # MetricDaily — 14 days
    for i in range(14):
        d = today - timedelta(days=i)
        db.add(MetricDaily(
            campaign_id=campaign.id,
            date=d,
            clicks=100 + i * 5,
            impressions=1000 + i * 50,
            cost_micros=5_000_000 + i * 100_000,
            conversions=2.0 + (i % 3) * 0.5,
            conversion_value_micros=10_000_000,
        ))

    # MetricSegmented for device/geo
    for device in ["MOBILE", "DESKTOP", "TABLET"]:
        db.add(MetricSegmented(
            campaign_id=campaign.id,
            date=today,
            device=device,
            clicks=30,
            impressions=300,
            cost_micros=2_000_000,
            conversions=1.0,
        ))

    for city in ["Warsaw", "Krakow", "Wroclaw"]:
        db.add(MetricSegmented(
            campaign_id=campaign.id,
            date=today,
            geo_city=city,
            clicks=25,
            impressions=250,
            cost_micros=1_500_000,
            conversions=0.8,
        ))

    db.commit()
    return client, campaign, ag


# ─── Core Analytics ──────────────────────────────────────────────────


class TestKPIs:
    def test_kpis_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/kpis?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_spend_usd" in data
        assert "total_clicks" in data

    def test_kpis_empty_client(self, api_client, db):
        c = Client(name="Empty", google_customer_id="0000")
        db.add(c)
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/kpis?client_id={c.id}")
        assert resp.status_code == 200


class TestDashboardKPIs:
    def test_dashboard_kpis_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/dashboard-kpis?client_id={client.id}&days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "current" in data
        assert "previous" in data


class TestAnomalies:
    def test_anomalies_list(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/anomalies?client_id={client.id}")
        assert resp.status_code == 200

    def test_resolve_anomaly(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        alert = Alert(
            client_id=client.id, campaign_id=campaign.id,
            alert_type="SPEND_SPIKE", severity="HIGH",
            title="Test", description="Spike",
        )
        db.add(alert)
        db.commit()
        resp = api_client.post(
            f"/api/v1/analytics/anomalies/{alert.id}/resolve?client_id={client.id}"
        )
        assert resp.status_code == 200

    def test_detect_anomalies(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.post(f"/api/v1/analytics/detect?client_id={client.id}")
        assert resp.status_code == 200


# ─── Advanced Analytics ──────────────────────────────────────────────


class TestCorrelation:
    def test_correlation_returns_200(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        resp = api_client.post("/api/v1/analytics/correlation", json={
            "client_id": client.id,
            "campaign_id": campaign.id,
            "days": 14,
        })
        assert resp.status_code == 200


class TestComparePeriods:
    def test_compare_periods_returns_200(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        today = date.today()
        resp = api_client.post("/api/v1/analytics/compare-periods", json={
            "client_id": client.id,
            "campaign_id": campaign.id,
            "metric": "clicks",
            "period_a_start": str(today - timedelta(days=14)),
            "period_a_end": str(today - timedelta(days=8)),
            "period_b_start": str(today - timedelta(days=7)),
            "period_b_end": str(today),
        })
        assert resp.status_code == 200


class TestTrends:
    def test_trends_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/trends?client_id={client.id}&metrics=cost,clicks&days=14"
        )
        assert resp.status_code == 200

    def test_trends_invalid_metric_falls_back(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/trends?client_id={client.id}&metrics=invalid_metric&days=7"
        )
        assert resp.status_code == 200


class TestHealthScore:
    def test_health_score_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/health-score?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert 0 <= data["score"] <= 100

    def test_health_score_has_pillar_breakdown(self, api_client, db):
        """Breakdown contains 6 weighted pillars."""
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/health-score?client_id={client.id}")
        data = resp.json()
        assert "breakdown" in data
        bd = data["breakdown"]
        for pillar in ("performance", "quality", "efficiency", "coverage", "stability", "structure"):
            assert pillar in bd, f"Missing pillar: {pillar}"
            assert "score" in bd[pillar]
            assert "weight" in bd[pillar]
            assert 0 <= bd[pillar]["score"] <= 100
        # Weights must sum to 100
        assert sum(p["weight"] for p in bd.values()) == 100

    def test_many_high_alerts_score_not_negative(self, api_client, db):
        """10 HIGH alerts — score stays >= 0, stability pillar drops but overall capped."""
        client, _, _ = _seed_full(db)
        for i in range(10):
            db.add(Alert(
                client_id=client.id,
                alert_type="SPEND_SPIKE",
                severity="HIGH",
                title=f"Alert {i}",
                description=f"High alert {i}",
            ))
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/health-score?client_id={client.id}")
        data = resp.json()
        assert data["score"] >= 0
        # Stability pillar should be heavily penalized (alerts cap at -40)
        assert data["breakdown"]["stability"]["score"] <= 60

    def test_pmax_no_ctr_penalty(self, api_client, db):
        """PMax campaign with CTR drop should NOT trigger CTR penalty in stability."""
        client = Client(name="PMax Test", google_customer_id="pm1")
        db.add(client)
        db.flush()
        pmax = Campaign(
            client_id=client.id,
            google_campaign_id="pmax1",
            name="PMax Campaign",
            status="ENABLED",
            campaign_type="PERFORMANCE_MAX",
            budget_micros=50_000_000,
        )
        db.add(pmax)
        db.flush()
        today = date.today()
        for i in range(30):
            d = today - timedelta(days=29 - i)
            clicks = 100 if i < 15 else 10
            db.add(MetricDaily(
                campaign_id=pmax.id,
                date=d,
                clicks=clicks,
                impressions=1000,
                ctr=clicks / 1000,
                conversions=5.0,
                conversion_value_micros=50_000_000,
                cost_micros=10_000_000,
                roas=5.0,
            ))
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/health-score?client_id={client.id}&days=30")
        data = resp.json()
        # PMax excluded from CTR check → stability.ctr_drop_pct should be 0
        assert data["breakdown"]["stability"]["details"].get("ctr_drop_pct", 0) == 0

    def test_brand_campaign_no_roas_penalty(self, api_client, db):
        """Brand campaign with ROAS < 1 should NOT trigger low ROAS in performance."""
        client = Client(name="Brand Test", google_customer_id="br1")
        db.add(client)
        db.flush()
        brand = Campaign(
            client_id=client.id,
            google_campaign_id="brand1",
            name="[GSN] - Brand",
            status="ENABLED",
            campaign_type="SEARCH",
            campaign_role_final="BRAND",
            budget_micros=50_000_000,
        )
        db.add(brand)
        db.flush()
        today = date.today()
        for i in range(7):
            db.add(MetricDaily(
                campaign_id=brand.id,
                date=today - timedelta(days=i),
                clicks=50,
                impressions=1000,
                ctr=0.05,
                conversions=1.0,
                conversion_value_micros=5_000_000,
                cost_micros=20_000_000,
                roas=0.25,
            ))
        db.commit()
        resp = api_client.get(f"/api/v1/analytics/health-score?client_id={client.id}&days=7")
        data = resp.json()
        # Brand excluded from low ROAS check
        assert data["breakdown"]["performance"]["details"]["low_roas_campaigns"] == 0

    def _seed_two_campaigns_one_zero_conv(self, db, bad_cost_per_day_micros: int):
        """Helper: one healthy campaign + one zero-conv campaign with tunable spend."""
        import uuid
        tag = uuid.uuid4().hex[:8]
        client = Client(name=f"CW-{tag}", google_customer_id=f"cw-{tag}")
        db.add(client)
        db.flush()
        good = Campaign(
            client_id=client.id, google_campaign_id=f"g-{tag}",
            name="Healthy", status="ENABLED", campaign_type="SEARCH",
            budget_micros=50_000_000,
        )
        bad = Campaign(
            client_id=client.id, google_campaign_id=f"b-{tag}",
            name="ZeroConv", status="ENABLED", campaign_type="SEARCH",
            budget_micros=50_000_000,
        )
        db.add_all([good, bad])
        db.flush()
        today = date.today()
        for i in range(7):
            d = today - timedelta(days=i)
            db.add(MetricDaily(
                campaign_id=good.id, date=d,
                clicks=100, impressions=1000,
                cost_micros=10_000_000, conversions=5.0,
                conversion_value_micros=60_000_000,  # ROAS 6
            ))
            db.add(MetricDaily(
                campaign_id=bad.id, date=d,
                clicks=50, impressions=1000,
                cost_micros=bad_cost_per_day_micros, conversions=0,
                conversion_value_micros=0,
            ))
        db.commit()
        return client, good, bad

    def test_cost_weighted_penalty_smaller_for_tiny_campaign(self, api_client, db):
        """A zero-conv campaign with trivial spend penalizes less than one with large spend.

        Cost share, not campaign count, drives the penalty magnitude.
        """
        # Tiny zero-conv: $2/day × 7 = $14 out of ~$84 total (~17% share)
        c_small, _, _ = self._seed_two_campaigns_one_zero_conv(db, 2_000_000)
        # Large zero-conv: $20/day × 7 = $140 out of ~$210 total (~67% share)
        c_large, _, _ = self._seed_two_campaigns_one_zero_conv(db, 20_000_000)

        r_small = api_client.get(f"/api/v1/analytics/health-score?client_id={c_small.id}&days=7").json()
        r_large = api_client.get(f"/api/v1/analytics/health-score?client_id={c_large.id}&days=7").json()

        perf_small = r_small["breakdown"]["performance"]["score"]
        perf_large = r_large["breakdown"]["performance"]["score"]

        # Both flag one zero-conv campaign, but large share → larger penalty → lower score
        assert r_small["breakdown"]["performance"]["details"]["zero_conv_campaigns"] == 1
        assert r_large["breakdown"]["performance"]["details"]["zero_conv_campaigns"] == 1
        assert perf_small > perf_large, (
            f"small-share penalty should be lighter: small={perf_small}, large={perf_large}"
        )
        # Cost share is exposed as a diagnostic
        assert r_small["breakdown"]["performance"]["details"]["zero_conv_cost_share"] < \
               r_large["breakdown"]["performance"]["details"]["zero_conv_cost_share"]

    def test_root_cause_dedup_no_stacking_on_efficiency(self, api_client, db):
        """Zero-conv campaign's keywords AND search terms must NOT penalize Efficiency.

        Performance owns the root cause; Efficiency stays clean unless
        waste appears in OTHER (healthy) campaigns. Covers both 3a (keyword
        waste) and 3b (search term waste) dedup paths.
        """
        client = Client(name="Dedup Test", google_customer_id="dd1")
        db.add(client)
        db.flush()
        # Single campaign: zero-conv with spending keywords (the classic double-penalty case)
        bad = Campaign(
            client_id=client.id, google_campaign_id="bd1",
            name="Zero conv with waste", status="ENABLED", campaign_type="SEARCH",
            budget_micros=50_000_000,
        )
        db.add(bad)
        db.flush()
        ag = AdGroup(campaign_id=bad.id, google_ad_group_id="bdag1", name="AG", status="ENABLED")
        db.add(ag)
        db.flush()
        # Keywords with cost but zero conversions (would trigger "wasted spend" pillar 3a)
        for i in range(3):
            db.add(Keyword(
                ad_group_id=ag.id, google_keyword_id=f"bk{i}",
                text=f"term{i}", match_type="EXACT", status="ENABLED",
                quality_score=7, cost_micros=5_000_000, conversions=0,
            ))
        today = date.today()
        week_ago = today - timedelta(days=7)
        # Search terms with cost but zero conversions (would trigger pillar 3b)
        for i in range(3):
            db.add(SearchTerm(
                ad_group_id=ag.id, campaign_id=bad.id,
                text=f"wasted query {i}",
                clicks=20, impressions=200,
                cost_micros=3_000_000, conversions=0,
                ctr=10.0, date_from=week_ago, date_to=today,
            ))
        for i in range(7):
            db.add(MetricDaily(
                campaign_id=bad.id, date=today - timedelta(days=i),
                clicks=50, impressions=1000,
                cost_micros=15_000_000, conversions=0, conversion_value_micros=0,
            ))
        db.commit()
        data = api_client.get(
            f"/api/v1/analytics/health-score?client_id={client.id}&days=7"
        ).json()

        # Performance penalty fires (primary signal)
        assert data["breakdown"]["performance"]["details"]["zero_conv_campaigns"] == 1
        # Efficiency stays clean — the keywords AND search terms belong to the
        # already-flagged campaign; neither 3a nor 3b double-penalizes.
        assert data["breakdown"]["efficiency"]["details"]["wasted_spend_pct"] == 0
        assert data["breakdown"]["efficiency"]["details"]["search_term_waste_pct"] == 0

    def test_primary_problem_campaigns_exposed(self, api_client, db):
        """primary_problem_campaigns diagnostic is exposed in performance.details."""
        client, _, _ = _seed_full(db)
        data = api_client.get(
            f"/api/v1/analytics/health-score?client_id={client.id}"
        ).json()
        assert "primary_problem_campaigns" in data["breakdown"]["performance"]["details"]
        assert "zero_conv_cost_share" in data["breakdown"]["performance"]["details"]
        assert "low_roas_cost_share" in data["breakdown"]["performance"]["details"]


class TestCampaignTrends:
    def test_campaign_trends_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/campaign-trends?client_id={client.id}&days=7")
        assert resp.status_code == 200


class TestBudgetPacing:
    def test_budget_pacing_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/budget-pacing?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "campaigns" in data
        assert "month" in data
        assert "days_elapsed" in data

    def test_budget_pacing_has_campaign_data(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/budget-pacing?client_id={client.id}")
        data = resp.json()
        assert len(data["campaigns"]) >= 1
        camp = data["campaigns"][0]
        assert "campaign_name" in camp
        assert "pacing_pct" in camp
        assert "status" in camp


class TestImpressionShare:
    def test_impression_share_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/impression-share?client_id={client.id}")
        assert resp.status_code == 200


class TestDeviceBreakdown:
    def test_device_breakdown_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/device-breakdown?client_id={client.id}&days=7")
        assert resp.status_code == 200


class TestGeoBreakdown:
    def test_geo_breakdown_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/geo-breakdown?client_id={client.id}&days=7")
        assert resp.status_code == 200


# ─── Search Optimization ─────────────────────────────────────────────


class TestDayparting:
    def test_dayparting_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/dayparting?client_id={client.id}&days=14")
        assert resp.status_code == 200

    def test_dayparting_unique_route(self):
        """Guard: ensure only one handler registered for GET /analytics/dayparting."""
        matching = [
            r for r in app.routes
            if getattr(r, "path", None) == "/api/v1/analytics/dayparting"
            and "GET" in getattr(r, "methods", set())
        ]
        assert len(matching) == 1, (
            f"Expected exactly 1 handler for GET /api/v1/analytics/dayparting, got {len(matching)}. "
            "Duplicate @router.get('/dayparting') would silently shadow the first registration."
        )

    def test_dayparting_response_shape(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/dayparting?client_id={client.id}&days=14")
        assert resp.status_code == 200
        data = resp.json()
        assert "currency" in data and "campaign_type_used" in data and "period_days" in data
        assert data["campaign_type_used"] == "ALL", "Default should be ALL (not SEARCH)"
        assert data["days"], "expected 7 day buckets"
        row = data["days"][0]
        for key in [
            "day_of_week", "day_name", "observations",
            "cost_amount", "avg_cost_amount",
            "conversion_value_amount", "aov",
            "avg_cpa", "avg_roas", "avg_cvr", "avg_cpc",
        ]:
            assert key in row, f"missing key {key}"

    def test_dayparting_dow_suggestions_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/dayparting-dow-suggestions?client_id={client.id}&days=30"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "suggestions" in body and "currency" in body

    def test_dayparting_heatmap_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/dayparting-heatmap?client_id={client.id}&days=30"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body.get("cells", [])) == 7 * 24

    def test_dayparting_heatmap_respects_campaign_type_filter(self, api_client, db):
        """Passing campaign_type must exclude rows from other types (was silently ignored)."""
        client, _, _ = _seed_full(db)
        # Seeded data is SEARCH only; DISPLAY filter must return an empty grid
        resp_display = api_client.get(
            f"/api/v1/analytics/dayparting-heatmap?client_id={client.id}&days=30&campaign_type=DISPLAY"
        )
        assert resp_display.status_code == 200
        cells = resp_display.json().get("cells", [])
        assert len(cells) == 7 * 24
        non_zero = [c for c in cells if (c.get("clicks") or 0) > 0]
        assert non_zero == [], "DISPLAY filter must exclude SEARCH-only data"

    def test_dayparting_dow_suggestions_respects_campaign_type_filter(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/dayparting-dow-suggestions"
            f"?client_id={client.id}&days=30&campaign_type=DISPLAY"
        )
        assert resp.status_code == 200
        body = resp.json()
        # No DISPLAY data seeded → no cost → no suggestions
        assert body.get("suggestions") == []
        assert body.get("overall_cpa") in (None, 0)

    def test_dayparting_hourly_suggestions_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/dayparting-hourly-suggestions?client_id={client.id}&days=30"
        )
        assert resp.status_code == 200


class TestRSAAnalysis:
    def test_rsa_analysis_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/rsa-analysis?client_id={client.id}")
        assert resp.status_code == 200


class TestNgramAnalysis:
    def test_ngram_analysis_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/ngram-analysis?client_id={client.id}&ngram_size=1&min_occurrences=1"
        )
        assert resp.status_code == 200

    def test_ngram_bigrams(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/ngram-analysis?client_id={client.id}&ngram_size=2&min_occurrences=1"
        )
        assert resp.status_code == 200


class TestMatchTypeAnalysis:
    def test_match_type_analysis_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/match-type-analysis?client_id={client.id}&days=14")
        assert resp.status_code == 200


class TestLandingPages:
    def test_landing_pages_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/landing-pages?client_id={client.id}&days=14")
        assert resp.status_code == 200


class TestWastedSpend:
    def test_wasted_spend_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/wasted-spend?client_id={client.id}&days=14")
        assert resp.status_code == 200


class TestAccountStructure:
    def test_account_structure_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/account-structure?client_id={client.id}")
        assert resp.status_code == 200


class TestBiddingAdvisor:
    def test_bidding_advisor_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/bidding-advisor?client_id={client.id}&days=14")
        assert resp.status_code == 200


class TestHourlyDayparting:
    def test_hourly_dayparting_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/hourly-dayparting?client_id={client.id}&days=7")
        assert resp.status_code == 200

    def test_hourly_dayparting_response_shape(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/hourly-dayparting?client_id={client.id}&days=7")
        data = resp.json()
        assert "currency" in data and "campaign_type_used" in data and "period_days" in data
        assert data["campaign_type_used"] == "ALL", "Default should be ALL (not SEARCH)"


# ─── Forecast ────────────────────────────────────────────────────────


class TestForecast:
    def test_forecast_clicks(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/forecast?campaign_id={campaign.id}&metric=clicks&forecast_days=7"
        )
        assert resp.status_code == 200

    def test_forecast_cost_alias(self, api_client, db):
        client, campaign, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/forecast?campaign_id={campaign.id}&metric=cost&forecast_days=7"
        )
        assert resp.status_code == 200


class TestQualityScoreAudit:
    def test_quality_score_audit_returns_200(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(f"/api/v1/analytics/quality-score-audit?client_id={client.id}")
        assert resp.status_code == 200

    def test_quality_score_with_threshold(self, api_client, db):
        client, _, _ = _seed_full(db)
        resp = api_client.get(
            f"/api/v1/analytics/quality-score-audit?client_id={client.id}&qs_threshold=5"
        )
        assert resp.status_code == 200
