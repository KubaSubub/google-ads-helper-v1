"""Tests for MCC overview service and router."""

from datetime import date, datetime, timedelta, timezone

from app.models import (
    Alert, Campaign, ChangeEvent, Client, MccLink, MetricDaily,
    NegativeKeywordList, NegativeKeywordListItem,
    PlacementExclusionList, PlacementExclusionListItem,
    Recommendation, SyncLog,
)
from app.services.mcc_service import MCCService


def _client(db, name="Test", cid="111-222-3333") -> Client:
    c = Client(name=name, google_customer_id=cid)
    db.add(c)
    db.commit()
    return c


def _campaign(db, client_id, name="Camp", budget_micros=10_000_000) -> Campaign:
    c = Campaign(
        client_id=client_id,
        name=name,
        google_campaign_id=f"g{client_id}_{name}",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=budget_micros,
    )
    db.add(c)
    db.commit()
    return c


def test_mcc_overview_returns_all_clients(db):
    _client(db, "A", "100")
    _client(db, "B", "200")
    svc = MCCService(db)
    result = svc.get_overview()
    assert len(result["accounts"]) == 2
    names = {a["client_name"] for a in result["accounts"]}
    assert names == {"A", "B"}


def test_mcc_overview_empty_when_no_clients(db):
    svc = MCCService(db)
    result = svc.get_overview()
    assert result["accounts"] == []


def test_mcc_overview_spend_and_conversions(db):
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()
    month_start = today.replace(day=1)

    # Seed data within current month
    days_in_month = (today - month_start).days + 1
    for i in range(min(days_in_month, 5)):
        db.add(MetricDaily(
            campaign_id=camp.id,
            date=today - timedelta(days=i),
            cost_micros=1_000_000,  # $1 each
            clicks=10,
            impressions=100,
            conversions=2.0,
            conversion_value_micros=5_000_000,  # $5 each
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    expected_days = min(days_in_month, 5)
    assert acc["spend"] == expected_days * 1.0
    assert acc["conversions"] == expected_days * 2.0


def test_mcc_overview_pacing_status(db):
    client = _client(db)
    camp = _campaign(db, client.id, budget_micros=10_000_000)  # $10/day
    today = date.today()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1

    # Spend exactly on track
    expected_daily = 10.0
    for i in range(days_elapsed):
        d = month_start + timedelta(days=i)
        db.add(MetricDaily(
            campaign_id=camp.id,
            date=d,
            cost_micros=int(expected_daily * 1_000_000),
            clicks=10,
            impressions=100,
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    assert pacing["status"] == "on_track"


def test_dismiss_google_recommendations_bulk(db):
    client = _client(db)
    for i in range(3):
        db.add(Recommendation(
            client_id=client.id,
            rule_id=f"google_{i}",
            entity_type="CAMPAIGN",
            entity_id=str(i),
            source="GOOGLE_ADS_API",
            status="pending",
            reason="test",
            suggested_action="test",
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.dismiss_google_recommendations(client.id, dismiss_all=True)
    assert result["dismissed"] == 3

    # Verify all dismissed
    pending = db.query(Recommendation).filter(
        Recommendation.client_id == client.id,
        Recommendation.status == "pending",
    ).count()
    assert pending == 0


def test_new_access_detection(db):
    client = _client(db)
    now = datetime.now(timezone.utc)

    # Recent email (last 30 days)
    db.add(ChangeEvent(
        client_id=client.id,
        resource_name="res_new",
        change_date_time=now - timedelta(days=5),
        user_email="new_person@agency.com",
        client_type="GOOGLE_ADS_WEB_CLIENT",
        change_resource_type="CAMPAIGN",
        resource_change_operation="UPDATE",
    ))

    # Old email (31-90 days ago)
    db.add(ChangeEvent(
        client_id=client.id,
        resource_name="res_old",
        change_date_time=now - timedelta(days=45),
        user_email="old_person@agency.com",
        client_type="GOOGLE_ADS_WEB_CLIENT",
        change_resource_type="CAMPAIGN",
        resource_change_operation="UPDATE",
    ))
    db.commit()

    svc = MCCService(db)
    new_emails = svc.detect_new_access(client.id, days=30)
    assert "new_person@agency.com" in new_emails
    assert "old_person@agency.com" not in new_emails


def test_negative_keyword_lists_overview(db):
    c1 = _client(db, "Alpha", "111")
    c2 = _client(db, "Beta", "222")

    nkl1 = NegativeKeywordList(client_id=c1.id, name="Brand Terms", source="LOCAL")
    nkl2 = NegativeKeywordList(client_id=c2.id, name="Competitor Terms", source="GOOGLE_ADS_SYNC")
    db.add_all([nkl1, nkl2])
    db.commit()

    # Add items to first list
    db.add(NegativeKeywordListItem(list_id=nkl1.id, text="brand x"))
    db.add(NegativeKeywordListItem(list_id=nkl1.id, text="brand y"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_negative_keyword_lists_overview()
    assert len(result) == 2

    alpha_list = next(r for r in result if r["client_name"] == "Alpha")
    assert alpha_list["name"] == "Brand Terms"
    assert alpha_list["member_count"] == 2

    beta_list = next(r for r in result if r["client_name"] == "Beta")
    assert beta_list["member_count"] == 0


def test_negative_keyword_lists_overview_empty(db):
    svc = MCCService(db)
    result = svc.get_negative_keyword_lists_overview()
    assert result == []


def test_mcc_overview_health_score_in_response(db):
    """Health score should be present in account data (may be None if no data)."""
    client = _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert "health_score" in acc
    assert "pacing" in acc
    assert "total_changes" in acc


def test_mcc_overview_alerts_count(db):
    client = _client(db)
    # Add unresolved alerts
    for i in range(3):
        db.add(Alert(
            client_id=client.id,
            alert_type="ANOMALY",
            severity="HIGH",
            title=f"Alert {i}",
        ))
    # Add one resolved alert
    db.add(Alert(
        client_id=client.id,
        alert_type="ANOMALY",
        severity="MEDIUM",
        title="Resolved",
        resolved_at=datetime.now(timezone.utc),
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["unresolved_alerts"] == 3


def test_mcc_overview_full_metrics(db):
    """Overview should include all account-level metrics with explicit date range."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    for i in range(3):
        db.add(MetricDaily(
            campaign_id=camp.id,
            date=today - timedelta(days=i),
            clicks=100,
            impressions=2000,
            cost_micros=5_000_000,  # $5
            conversions=10.0,
            conversion_value_micros=50_000_000,  # $50
        ))
    db.commit()

    svc = MCCService(db)
    # Use explicit date range to ensure all 3 days are included
    result = svc.get_overview(date_from=today - timedelta(days=5), date_to=today)
    acc = result["accounts"][0]

    assert acc["clicks"] == 300
    assert acc["impressions"] == 6000
    assert acc["ctr_pct"] == 5.0
    assert acc["avg_cpc"] == 0.05
    assert acc["conversions"] == 30.0
    assert acc["conversion_rate_pct"] == 10.0
    assert acc["conversion_value"] == 150.0
    assert acc["cpa"] == 0.5
    # ROAS as multiplier: 150 conv_value / 15 spend = 10.0x (was 1000% before)
    assert acc["roas"] == 10.0


def test_mcc_overview_new_access_in_response(db):
    """Overview should include new_access_emails per account."""
    client = _client(db)
    now = datetime.now(timezone.utc)

    db.add(ChangeEvent(
        client_id=client.id,
        resource_name="res_intruder",
        change_date_time=now - timedelta(days=2),
        user_email="intruder@other.com",
        client_type="GOOGLE_ADS_WEB_CLIENT",
        change_resource_type="CAMPAIGN",
        resource_change_operation="UPDATE",
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert "intruder@other.com" in acc["new_access_emails"]


def test_mcc_shared_lists_empty(db):
    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()
    assert isinstance(result, dict)
    assert result["keyword_lists"] == []
    assert result["placement_lists"] == []


def test_mcc_shared_lists_from_manager(db):
    """MCC shared lists should return keyword lists from manager account."""
    manager = _client(db, "MCC Manager", "999-000-0001")
    child = _client(db, "Child Account", "999-000-0002")

    db.add(MccLink(
        manager_customer_id="9990000001",
        client_customer_id="9990000002",
        client_descriptive_name="Child Account",
        local_client_id=child.id,
    ))
    db.commit()

    # MCC-level negative keyword list
    mcc_nkl = NegativeKeywordList(
        client_id=manager.id, name="MCC Exclusions",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(mcc_nkl)
    db.commit()

    db.add(NegativeKeywordListItem(list_id=mcc_nkl.id, text="spam"))
    db.add(NegativeKeywordListItem(list_id=mcc_nkl.id, text="free"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()

    assert len(result["keyword_lists"]) >= 1
    mcc_list = next(r for r in result["keyword_lists"] if r["name"] == "MCC Exclusions")
    assert mcc_list["item_count"] == 2
    assert mcc_list["ownership_level"] == "mcc"


def test_mcc_placement_exclusion_lists(db):
    """MCC shared lists should include placement exclusion lists."""
    manager = _client(db, "MCC Manager", "888-000-0001")
    child = _client(db, "Child", "888-000-0002")

    db.add(MccLink(
        manager_customer_id="8880000001",
        client_customer_id="8880000002",
        local_client_id=child.id,
    ))
    db.commit()

    pel = PlacementExclusionList(
        client_id=manager.id, name="Spam Sites",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(pel)
    db.commit()

    db.add(PlacementExclusionListItem(list_id=pel.id, url="spammy-site.com", placement_type="WEBSITE"))
    db.add(PlacementExclusionListItem(list_id=pel.id, url="youtube.com/channel/UCfake", placement_type="YOUTUBE_CHANNEL"))
    db.add(PlacementExclusionListItem(list_id=pel.id, url="play.google.com/store/apps/details?id=com.bad", placement_type="MOBILE_APP"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()

    assert len(result["placement_lists"]) >= 1
    pl = next(r for r in result["placement_lists"] if r["name"] == "Spam Sites")
    assert pl["item_count"] == 3
    assert pl["ownership_level"] == "mcc"


def test_mcc_shared_list_items_drilldown_keywords(db):
    """Drill-down into a keyword list should return all items."""
    client = _client(db)
    nkl = NegativeKeywordList(
        client_id=client.id, name="Test KW List",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(nkl)
    db.commit()

    db.add(NegativeKeywordListItem(list_id=nkl.id, text="spam", match_type="BROAD"))
    db.add(NegativeKeywordListItem(list_id=nkl.id, text="free", match_type="PHRASE"))
    db.add(NegativeKeywordListItem(list_id=nkl.id, text="cheap", match_type="EXACT"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_shared_list_items(nkl.id, "keyword")

    assert result["name"] == "Test KW List"
    assert result["type"] == "keyword"
    assert result["item_count"] == 3
    assert len(result["items"]) == 3
    texts = {i["text"] for i in result["items"]}
    assert texts == {"spam", "free", "cheap"}


def test_mcc_shared_list_items_drilldown_placements(db):
    """Drill-down into a placement list should return all items."""
    client = _client(db)
    pel = PlacementExclusionList(
        client_id=client.id, name="Test Placements",
        source="MCC_SYNC", ownership_level="mcc",
    )
    db.add(pel)
    db.commit()

    db.add(PlacementExclusionListItem(list_id=pel.id, url="bad-site.com", placement_type="WEBSITE"))
    db.add(PlacementExclusionListItem(list_id=pel.id, url="youtube.com/channel/UCbad", placement_type="YOUTUBE_CHANNEL"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_shared_list_items(pel.id, "placement")

    assert result["name"] == "Test Placements"
    assert result["type"] == "placement"
    assert result["item_count"] == 2
    urls = {i["url"] for i in result["items"]}
    assert "bad-site.com" in urls


def test_mcc_shared_list_items_not_found(db):
    """Drill-down with invalid ID should return error."""
    svc = MCCService(db)
    result = svc.get_shared_list_items(99999, "keyword")
    assert "error" in result


def test_mcc_shared_lists_excludes_account_level(db):
    """MCC shared lists should NOT include account-level lists."""
    client = _client(db)
    # Account-level list (default ownership_level='account')
    account_nkl = NegativeKeywordList(
        client_id=client.id, name="Account Level List",
        source="GOOGLE_ADS_SYNC", ownership_level="account",
    )
    db.add(account_nkl)
    db.commit()

    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()

    # Should not appear in MCC lists
    kw_names = [r["name"] for r in result["keyword_lists"]]
    assert "Account Level List" not in kw_names


def test_billing_status_without_api(db):
    """Billing status should return 'unknown' when API not connected."""
    svc = MCCService(db)
    result = svc.get_billing_status("123-456-7890")
    assert result["status"] in ("unknown", "no_access")


def test_billing_status_endpoint_returns_dict(db):
    """GET /mcc/billing-status should return a dict with status field."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/mcc/billing-status", params={"customer_id": "123-456-7890"})
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_mcc_overview_impression_share(db):
    """Overview should include avg search_impression_share per account."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    for i in range(3):
        db.add(MetricDaily(
            campaign_id=camp.id,
            date=today - timedelta(days=i),
            clicks=10,
            impressions=100,
            cost_micros=1_000_000,
            search_impression_share=0.45,
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=5), date_to=today)
    acc = result["accounts"][0]
    assert acc["search_impression_share_pct"] == 45.0


def test_mcc_overview_custom_period(db):
    """Overview with different date ranges should return different metrics."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    # Data 3 days ago
    db.add(MetricDaily(
        campaign_id=camp.id,
        date=today - timedelta(days=3),
        clicks=100,
        impressions=1000,
        cost_micros=10_000_000,
    ))
    # Data 20 days ago
    db.add(MetricDaily(
        campaign_id=camp.id,
        date=today - timedelta(days=20),
        clicks=50,
        impressions=500,
        cost_micros=5_000_000,
    ))
    db.commit()

    svc = MCCService(db)

    # 7-day range should only include recent data
    result_7d = svc.get_overview(date_from=today - timedelta(days=6), date_to=today)
    acc_7d = result_7d["accounts"][0]

    # 30-day range should include both
    result_30d = svc.get_overview(date_from=today - timedelta(days=29), date_to=today)
    acc_30d = result_30d["accounts"][0]

    assert acc_7d["clicks"] == 100
    assert acc_30d["clicks"] == 150


# ===================================================================
# LOCK TESTS — MCC Overview schema + edge case regression guards
# These tests ensure the MCC Overview response shape does not change
# and edge cases remain handled correctly after future modifications.
# ===================================================================

# -- Required fields in every account response --

_REQUIRED_ACCOUNT_FIELDS = {
    "client_id", "client_name", "google_customer_id",
    "currency",
    "clicks", "impressions", "ctr_pct", "avg_cpc",
    "spend", "spend_prev", "spend_change_pct",
    "conversions", "conversion_rate_pct", "conversion_value",
    "cpa", "roas", "search_impression_share_pct",
    "pacing",
    "total_changes", "external_changes", "change_breakdown",
    "new_access_emails",
    "google_recs_pending", "unresolved_alerts", "alert_details",
    "last_synced_at",
    "health_score",
    "spend_trend",
}

_REQUIRED_PACING_FIELDS = {
    "status", "pacing_pct", "budget", "spent",
    "month_progress_pct", "days_elapsed", "days_in_month",
}

_REQUIRED_OVERVIEW_FIELDS = {"synced_at", "date_from", "date_to", "accounts"}


def test_lock_overview_response_shape(db):
    """LOCK: overview response must contain exactly the expected top-level keys."""
    _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    assert set(result.keys()) == _REQUIRED_OVERVIEW_FIELDS


def test_lock_account_schema_all_fields_present(db):
    """LOCK: every account dict must contain all required fields."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()
    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=10, impressions=100, cost_micros=1_000_000,
        conversions=1.0, conversion_value_micros=5_000_000,
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    missing = _REQUIRED_ACCOUNT_FIELDS - set(acc.keys())
    assert missing == set(), f"Missing fields in account response: {missing}"


def test_lock_pacing_schema_all_fields_present(db):
    """LOCK: pacing dict must contain all required subfields."""
    client = _client(db)
    _campaign(db, client.id)  # Need at least one campaign for pacing
    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    missing = _REQUIRED_PACING_FIELDS - set(pacing.keys())
    assert missing == set(), f"Missing pacing fields: {missing}"


def test_lock_roas_none_when_no_conversions(db):
    """LOCK Z1: ROAS must be None when conv_value is 0, even if spend > 0."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=50, impressions=500,
        cost_micros=10_000_000,  # $10 spend
        conversions=0.0,
        conversion_value_micros=0,  # No conversion value
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    assert acc["roas"] is None, "ROAS must be None when conv_value=0"
    assert acc["cpa"] is None, "CPA must be None when conversions=0"


def test_lock_roas_calculated_when_both_positive(db):
    """LOCK Z1: ROAS must be calculated when both spend > 0 AND conv_value > 0."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=50, impressions=500,
        cost_micros=10_000_000,  # $10
        conversions=5.0,
        conversion_value_micros=50_000_000,  # $50
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    assert acc["roas"] == 5.0, "ROAS = 50/10 = 5.0x (multiplier, not percent)"
    assert acc["cpa"] == 2.0, "CPA = 10/5 = 2.0"


def test_lock_roas_none_when_no_spend(db):
    """LOCK: ROAS must be None when spend is 0."""
    client = _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["roas"] is None
    assert acc["spend"] == 0


def test_lock_pacing_no_data_when_no_campaigns(db):
    """LOCK: pacing status is 'no_data' when client has no campaigns."""
    _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    assert pacing["status"] == "no_data"
    assert pacing["budget"] == 0
    assert pacing["spent"] == 0


def test_lock_pacing_underspend(db):
    """LOCK: pacing detects underspend (spent < 75% of expected)."""
    client = _client(db)
    camp = _campaign(db, client.id, budget_micros=100_000_000)  # $100/day
    today = date.today()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1

    # Spend very little (only $1 per day instead of $100)
    for i in range(days_elapsed):
        d = month_start + timedelta(days=i)
        db.add(MetricDaily(
            campaign_id=camp.id, date=d,
            clicks=1, impressions=10,
            cost_micros=1_000_000,  # $1 per day
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    assert pacing["status"] == "underspend"
    assert pacing["budget"] > 0
    assert pacing["spent"] > 0
    assert pacing["spent"] < pacing["budget"]


def test_lock_pacing_overspend(db):
    """LOCK: pacing detects overspend (spent > 120% of expected)."""
    client = _client(db)
    camp = _campaign(db, client.id, budget_micros=1_000_000)  # $1/day
    today = date.today()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1

    # Spend way more than budget ($100 per day instead of $1)
    for i in range(days_elapsed):
        d = month_start + timedelta(days=i)
        db.add(MetricDaily(
            campaign_id=camp.id, date=d,
            clicks=100, impressions=1000,
            cost_micros=100_000_000,  # $100 per day
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    assert pacing["status"] == "overspend"


def test_lock_pacing_budget_and_spent_amounts(db):
    """LOCK N3: pacing must include budget and spent numerical values."""
    client = _client(db)
    camp = _campaign(db, client.id, budget_micros=10_000_000)  # $10/day
    today = date.today()
    month_start = today.replace(day=1)

    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=10, impressions=100,
        cost_micros=5_000_000,  # $5
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    pacing = result["accounts"][0]["pacing"]
    assert isinstance(pacing["budget"], (int, float))
    assert isinstance(pacing["spent"], (int, float))
    assert pacing["budget"] > 0
    assert pacing["spent"] == 5.0


def test_lock_zero_metrics_yields_none_ratios(db):
    """LOCK: when all metrics are 0, derived ratios must be None."""
    _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["ctr_pct"] is None
    assert acc["avg_cpc"] is None
    assert acc["conversion_rate_pct"] is None
    assert acc["cpa"] is None
    assert acc["roas"] is None
    assert acc["search_impression_share_pct"] is None


def test_lock_alert_details_structure(db):
    """LOCK: alert_details must be a list of dicts with title/severity/type."""
    client = _client(db)
    db.add(Alert(
        client_id=client.id,
        alert_type="BUDGET_DEPLETION",
        severity="HIGH",
        title="Budget running out",
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["unresolved_alerts"] == 1
    detail = acc["alert_details"][0]
    assert set(detail.keys()) == {"title", "severity", "type"}
    assert detail["title"] == "Budget running out"
    assert detail["severity"] == "HIGH"
    assert detail["type"] == "BUDGET_DEPLETION"


def test_lock_change_breakdown_structure(db):
    """LOCK: change_breakdown must be a dict mapping operation -> count."""
    client = _client(db)
    now = datetime.now(timezone.utc)
    today = date.today()

    for i, op in enumerate(["CREATE", "UPDATE", "UPDATE"]):
        db.add(ChangeEvent(
            client_id=client.id,
            resource_name=f"res_breakdown_{i}",
            change_date_time=now - timedelta(hours=1, minutes=i),
            user_email="user@test.com",
            client_type="GOOGLE_ADS_WEB_CLIENT",
            change_resource_type="CAMPAIGN",
            resource_change_operation=op,
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    assert acc["total_changes"] == 3
    assert acc["change_breakdown"]["UPDATE"] == 2
    assert acc["change_breakdown"]["CREATE"] == 1


def test_lock_shared_lists_schema(db):
    """LOCK: shared lists response must have keyword_lists + placement_lists."""
    manager = _client(db, "Manager", "777-000-0001")
    child = _client(db, "Child", "777-000-0002")
    db.add(MccLink(
        manager_customer_id="7770000001",
        client_customer_id="7770000002",
        local_client_id=child.id,
    ))
    nkl = NegativeKeywordList(client_id=manager.id, name="KW Lock Test", source="MCC_SYNC", ownership_level="mcc")
    pel = PlacementExclusionList(client_id=manager.id, name="PL Lock Test", source="MCC_SYNC", ownership_level="mcc")
    db.add_all([nkl, pel])
    db.commit()

    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()
    assert "keyword_lists" in result
    assert "placement_lists" in result
    kw = next(r for r in result["keyword_lists"] if r["name"] == "KW Lock Test")
    pl = next(r for r in result["placement_lists"] if r["name"] == "PL Lock Test")
    for lst in [kw, pl]:
        assert "id" in lst
        assert "name" in lst
        assert "item_count" in lst
        assert "source" in lst
        assert "ownership_level" in lst


def test_lock_drilldown_keyword_item_schema(db):
    """LOCK: drill-down keyword items must have id/text/match_type."""
    client = _client(db)
    nkl = NegativeKeywordList(client_id=client.id, name="Schema Test", source="MCC_SYNC", ownership_level="mcc")
    db.add(nkl)
    db.commit()
    db.add(NegativeKeywordListItem(list_id=nkl.id, text="test", match_type="BROAD"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_shared_list_items(nkl.id, "keyword")
    item = result["items"][0]
    assert "id" in item
    assert "text" in item
    assert "match_type" in item
    assert item["text"] == "test"
    assert item["match_type"] == "BROAD"


def test_lock_drilldown_placement_item_schema(db):
    """LOCK: drill-down placement items must have id/url/placement_type."""
    client = _client(db)
    pel = PlacementExclusionList(client_id=client.id, name="PL Schema", source="MCC_SYNC", ownership_level="mcc")
    db.add(pel)
    db.commit()
    db.add(PlacementExclusionListItem(list_id=pel.id, url="evil.com", placement_type="WEBSITE"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_shared_list_items(pel.id, "placement")
    item = result["items"][0]
    assert "id" in item
    assert "url" in item
    assert "placement_type" in item
    assert item["url"] == "evil.com"
    assert item["placement_type"] == "WEBSITE"


# -- Router endpoint LOCK tests --

def test_lock_router_overview_endpoint(db):
    """LOCK: GET /mcc/overview must return 200 with proper shape."""
    from fastapi.testclient import TestClient
    from app.main import app

    _client(db)
    tc = TestClient(app)
    resp = tc.get("/api/v1/mcc/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == _REQUIRED_OVERVIEW_FIELDS
    assert isinstance(data["accounts"], list)


def test_lock_router_shared_lists_endpoint(db):
    """LOCK: GET /mcc/shared-lists must return 200 with keyword_lists + placement_lists."""
    from fastapi.testclient import TestClient
    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/api/v1/mcc/shared-lists")
    assert resp.status_code == 200
    data = resp.json()
    assert "keyword_lists" in data
    assert "placement_lists" in data


def test_lock_router_shared_list_items_endpoint(db):
    """LOCK: GET /mcc/shared-lists/{id}/items must return 200 or error for invalid id."""
    from fastapi.testclient import TestClient
    from app.main import app

    tc = TestClient(app)
    resp = tc.get("/api/v1/mcc/shared-lists/99999/items", params={"list_type": "keyword"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data  # Not found


def test_lock_router_dismiss_recs_endpoint(db):
    """LOCK: POST /mcc/dismiss-google-recommendations must return 200."""
    from fastapi.testclient import TestClient
    from app.main import app

    tc = TestClient(app)
    resp = tc.post("/api/v1/mcc/dismiss-google-recommendations",
                   json={"client_id": 1, "dismiss_all": True})
    assert resp.status_code == 200
    data = resp.json()
    assert "dismissed" in data


def test_lock_spend_change_pct_positive(db):
    """LOCK: spend_change_pct must be positive when current > previous period."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    # Current period: $10/day for 3 days
    for i in range(3):
        db.add(MetricDaily(
            campaign_id=camp.id, date=today - timedelta(days=i),
            clicks=10, impressions=100, cost_micros=10_000_000,
        ))
    # Previous period: $1/day for 3 days
    for i in range(3, 6):
        db.add(MetricDaily(
            campaign_id=camp.id, date=today - timedelta(days=i),
            clicks=1, impressions=10, cost_micros=1_000_000,
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=2), date_to=today)
    acc = result["accounts"][0]
    assert acc["spend_change_pct"] is not None
    assert acc["spend_change_pct"] > 0


def test_lock_spend_change_pct_none_when_no_prev(db):
    """LOCK: spend_change_pct must be None when no previous period spend."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    # Data only in current period — prev period (equal range before) has no data
    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=10, impressions=100, cost_micros=10_000_000,
    ))
    db.commit()

    svc = MCCService(db)
    # Use a wide range where prev period definitely has no data
    date_from = today - timedelta(days=3)
    result = svc.get_overview(date_from=date_from, date_to=today)
    acc = result["accounts"][0]
    # prev period: date_from-3 to date_from — no data there
    assert acc["spend_change_pct"] is None


# ===================================================================
# LOCK TESTS — Sprint 2: Currency (N2) + Spend Trend (N5)
# ===================================================================

def test_lock_currency_field_default(db):
    """LOCK N2: Client without explicit currency should default to PLN."""
    client = _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["currency"] == "PLN"


def test_lock_currency_respects_client_setting(db):
    """LOCK N2: Client with explicit currency should return that currency."""
    client = _client(db)
    client.currency = "EUR"
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["currency"] == "EUR"


def test_lock_currency_per_account(db):
    """LOCK N2: different clients can have different currencies."""
    c1 = _client(db, "PLN Client", "100")
    c2 = _client(db, "EUR Client", "200")
    c1.currency = "PLN"
    c2.currency = "EUR"
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview()
    currencies = {a["client_name"]: a["currency"] for a in result["accounts"]}
    assert currencies["PLN Client"] == "PLN"
    assert currencies["EUR Client"] == "EUR"


def test_lock_spend_trend_is_list(db):
    """LOCK N5: spend_trend must be a list in every account response."""
    _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert isinstance(acc["spend_trend"], list)


def test_lock_spend_trend_daily_data(db):
    """LOCK N5: spend_trend must return daily spend breakdown."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()

    for i in range(5):
        db.add(MetricDaily(
            campaign_id=camp.id,
            date=today - timedelta(days=i),
            clicks=10, impressions=100,
            cost_micros=(i + 1) * 1_000_000,
        ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=6), date_to=today)
    acc = result["accounts"][0]
    trend = acc["spend_trend"]

    assert len(trend) == 5
    for item in trend:
        assert "date" in item
        assert "spend" in item
        assert isinstance(item["spend"], (int, float))
    # Should be sorted by date ascending
    dates = [item["date"] for item in trend]
    assert dates == sorted(dates)


def test_lock_spend_trend_empty_when_no_data(db):
    """LOCK N5: spend_trend must be empty list when no metrics."""
    _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    assert acc["spend_trend"] == []


def test_lock_spend_trend_aggregates_across_campaigns(db):
    """LOCK N5: spend_trend must aggregate spend across all campaigns."""
    client = _client(db)
    camp1 = _campaign(db, client.id, name="Camp1")
    camp2 = _campaign(db, client.id, name="Camp2")
    today = date.today()

    db.add(MetricDaily(campaign_id=camp1.id, date=today, clicks=10, impressions=100, cost_micros=3_000_000))
    db.add(MetricDaily(campaign_id=camp2.id, date=today, clicks=5, impressions=50, cost_micros=2_000_000))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    trend = acc["spend_trend"]

    assert len(trend) == 1
    assert trend[0]["spend"] == 5.0  # $3 + $2 = $5


# ===================================================================
# Sprint 1-3 LOCK TESTS — sprint scope from prezes (2026-04-15)
# ===================================================================


def test_mcc_overview_IS_none_when_no_data(db):
    """LOCK Sprint 1: search_impression_share_pct must be None (not 0) when no IS rows.

    Frontend renders '—' when None, but would render '0.0%' if backend returned 0.
    """
    client = _client(db, "NoIS", "999")
    camp = _campaign(db, client.id)
    today = date.today()
    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=10, impressions=100, cost_micros=1_000_000,
        # search_impression_share intentionally None
    ))
    db.commit()

    svc = MCCService(db)
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    acc = result["accounts"][0]
    assert acc["search_impression_share_pct"] is None, "IS must be None, not 0, when no data"


def test_mcc_overview_active_only_filters_zero_spend(db):
    """LOCK Sprint 2: active_only=True excludes accounts with 0 spend in the period."""
    a = _client(db, "Active", "1001")
    b = _client(db, "Idle", "1002")
    today = date.today()
    camp_a = _campaign(db, a.id)
    db.add(MetricDaily(
        campaign_id=camp_a.id, date=today,
        clicks=10, impressions=100, cost_micros=5_000_000,
    ))
    db.commit()

    svc = MCCService(db)
    # Without filter: both accounts present
    all_result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    names = {acc["client_name"] for acc in all_result["accounts"]}
    assert names == {"Active", "Idle"}

    # With active_only: only the spending account
    active_result = svc.get_overview(
        date_from=today - timedelta(days=1), date_to=today, active_only=True,
    )
    names = {acc["client_name"] for acc in active_result["accounts"]}
    assert names == {"Active"}


def test_mcc_overview_roas_is_multiplier_not_percent(db):
    """LOCK Sprint 2: ROAS must be a multiplier (e.g. 4.20) not a percent (420)."""
    client = _client(db)
    camp = _campaign(db, client.id)
    today = date.today()
    db.add(MetricDaily(
        campaign_id=camp.id, date=today,
        clicks=10, impressions=100,
        cost_micros=10_000_000,        # $10 spend
        conversions=5.0,
        conversion_value_micros=42_000_000,  # $42 conv value -> 4.2x ROAS
    ))
    db.commit()

    svc = MCCService(db)
    acc = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)["accounts"][0]
    assert acc["roas"] == 4.2, f"expected 4.20 (multiplier), got {acc['roas']}"
    assert acc["roas"] < 100, "ROAS must be a multiplier, not a percent"
    assert "roas_pct" not in acc, "Legacy roas_pct field must be removed from response"


def test_mcc_overview_IS_weighted_by_spend(db):
    """LOCK Sprint 3: IS aggregation must be cost-weighted, not a plain mean.

    A 100k zł campaign at 80% IS should outweigh a 1k zł campaign at 10% IS —
    a plain mean would give ~45%, but weighted should give ~79%.
    """
    client = _client(db)
    big = _campaign(db, client.id, name="Big")
    small = _campaign(db, client.id, name="Small")
    today = date.today()
    # Big: 100k spend, 80% IS
    db.add(MetricDaily(
        campaign_id=big.id, date=today,
        clicks=1000, impressions=10000, cost_micros=100_000_000_000,  # 100k
        search_impression_share=0.80,
    ))
    # Small: 1k spend, 10% IS
    db.add(MetricDaily(
        campaign_id=small.id, date=today,
        clicks=10, impressions=100, cost_micros=1_000_000_000,  # 1k
        search_impression_share=0.10,
    ))
    db.commit()

    svc = MCCService(db)
    acc = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)["accounts"][0]
    # Weighted: (0.80 * 100000 + 0.10 * 1000) / (100000 + 1000) = 80100/101000 = 0.7931
    # Expected display: ~79.3%
    assert acc["search_impression_share_pct"] is not None
    assert 78 < acc["search_impression_share_pct"] < 81, (
        f"weighted IS should be ~79.3%, got {acc['search_impression_share_pct']}"
    )


def test_mcc_overview_active_only_default_false(db):
    """LOCK: active_only param defaults to False — no behavior change without explicit opt-in."""
    a = _client(db, "Active", "2001")
    b = _client(db, "Idle", "2002")
    today = date.today()
    camp_a = _campaign(db, a.id)
    db.add(MetricDaily(
        campaign_id=camp_a.id, date=today,
        clicks=10, impressions=100, cost_micros=1_000_000,
    ))
    db.commit()

    svc = MCCService(db)
    # Calling without the kwarg must include both accounts
    result = svc.get_overview(date_from=today - timedelta(days=1), date_to=today)
    assert len(result["accounts"]) == 2
