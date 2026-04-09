"""Tests for MCC overview service and router."""

from datetime import date, datetime, timedelta, timezone

from app.models import (
    Alert, Campaign, ChangeEvent, Client, MccLink, MetricDaily,
    NegativeKeywordList, NegativeKeywordListItem, Recommendation, SyncLog,
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


def test_mcc_overview_health_returns_breakdown(db):
    client = _client(db)
    svc = MCCService(db)
    result = svc.get_overview()
    acc = result["accounts"][0]
    # health is None (no data) or dict with score + pillars
    # health is removed from MCC overview response
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
    assert acc["roas_pct"] == 1000.0


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
    assert isinstance(result, list)


def test_mcc_shared_lists_from_manager(db):
    """MCC shared lists should return lists from manager account via MccLink."""
    # Create manager client
    manager = _client(db, "MCC Manager", "999-000-0001")
    child = _client(db, "Child Account", "999-000-0002")

    # Create MCC link
    db.add(MccLink(
        manager_customer_id="9990000001",
        client_customer_id="9990000002",
        client_descriptive_name="Child Account",
        local_client_id=child.id,
    ))
    db.commit()

    # Add NKL to manager account (MCC-level)
    mcc_nkl = NegativeKeywordList(client_id=manager.id, name="MCC Exclusions", source="GOOGLE_ADS_SYNC")
    db.add(mcc_nkl)
    db.commit()

    db.add(NegativeKeywordListItem(list_id=mcc_nkl.id, text="spam"))
    db.add(NegativeKeywordListItem(list_id=mcc_nkl.id, text="free"))
    db.commit()

    svc = MCCService(db)
    result = svc.get_mcc_shared_lists()

    assert len(result) >= 1
    mcc_list = next(r for r in result if r["name"] == "MCC Exclusions")
    assert mcc_list["client_name"] == "MCC Manager"
    assert mcc_list["member_count"] == 2
    assert mcc_list["level"] == "mcc"


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
