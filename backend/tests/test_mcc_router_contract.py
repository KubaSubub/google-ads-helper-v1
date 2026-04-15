"""MCC Overview router — contract + behavioural tests.

This suite is a **regression shield** for the MCC Overview view. Any change
elsewhere in the codebase (MCCService refactor, model field rename, etc.)
that alters the shape or semantics the frontend depends on MUST break one
of these tests.

Frontend consumers:
- MCCOverviewPage.jsx reads nearly every field in `accounts[]`
- ClientDrawer.jsx / Settings.jsx read billing-status
- MCC exclusions UI reads shared-lists + drill-down

These tests lock:
1. Response KEY shape (required fields present on every account)
2. TYPE shape (numbers are numbers, lists are lists, etc.)
3. Top-level envelope (synced_at, date_from, date_to, accounts[])
4. Behavioural invariants (demo client excluded, date filtering, etc.)
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import (
    Alert,
    Campaign,
    ChangeEvent,
    Client,
    MetricDaily,
    NegativeKeywordList,
    NegativeKeywordListItem,
    PlacementExclusionList,
    PlacementExclusionListItem,
    Recommendation,
    SyncLog,
)


# ─── Required account envelope fields ──────────────────────────────────
# Every field below is referenced directly by MCCOverviewPage.jsx. Removing
# or renaming any of them silently breaks the UI — hence the lock.

REQUIRED_ACCOUNT_KEYS = {
    # identity
    "client_id",
    "client_name",
    "google_customer_id",
    "currency",
    # metrics
    "clicks",
    "impressions",
    "ctr_pct",
    "avg_cpc",
    "spend",
    "spend_prev",
    "spend_change_pct",
    "conversions",
    "conversion_rate_pct",
    "conversion_value",
    "cpa",
    "roas",
    "search_impression_share_pct",
    # pacing
    "pacing",
    # activity
    "total_changes",
    "external_changes",
    "change_breakdown",
    "new_access_emails",
    # recs/alerts
    "google_recs_pending",
    "unresolved_alerts",
    "alert_details",
    # sync
    "last_synced_at",
    # health
    "health_score",
    # sparkline
    "spend_trend",
}

REQUIRED_PACING_KEYS = {"status", "pacing_pct", "month_progress_pct", "days_elapsed", "days_in_month"}

REQUIRED_OVERVIEW_TOP_KEYS = {"synced_at", "date_from", "date_to", "accounts"}


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def _seed_client(db, name="Test Account", gcid="1112223334", currency="PLN"):
    c = Client(name=name, google_customer_id=gcid, currency=currency)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_campaign_with_metrics(db, client, spend_micros=100_000_000, conversions=5.0):
    """Seed a campaign + today's metrics so pacing/spend/etc are non-zero."""
    campaign = Campaign(
        client_id=client.id,
        google_campaign_id=f"c_{client.id}",
        name=f"Campaign {client.id}",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=200_000_000,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    today = date.today()
    metric = MetricDaily(
        campaign_id=campaign.id,
        date=today,
        clicks=100,
        impressions=2000,
        cost_micros=spend_micros,
        conversions=conversions,
        conversion_value_micros=spend_micros * 3,
    )
    db.add(metric)
    db.commit()
    return campaign


# ─── /mcc/overview — envelope + account shape ──────────────────────────


def test_overview_returns_envelope_shape(api_client, db):
    _seed_client(db)
    resp = api_client.get("/api/v1/mcc/overview")
    assert resp.status_code == 200
    body = resp.json()

    assert REQUIRED_OVERVIEW_TOP_KEYS.issubset(body.keys()), (
        f"missing envelope keys: {REQUIRED_OVERVIEW_TOP_KEYS - body.keys()}"
    )
    assert isinstance(body["accounts"], list)
    # synced_at must be ISO 8601
    datetime.fromisoformat(body["synced_at"].replace("Z", "+00:00"))
    date.fromisoformat(body["date_from"])
    date.fromisoformat(body["date_to"])


def test_overview_account_has_all_required_keys(api_client, db):
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client)

    body = api_client.get("/api/v1/mcc/overview").json()
    assert len(body["accounts"]) == 1
    account = body["accounts"][0]

    missing = REQUIRED_ACCOUNT_KEYS - account.keys()
    assert not missing, f"account missing keys required by MCCOverviewPage.jsx: {missing}"


def test_overview_account_types_are_stable(api_client, db):
    """Types that the frontend relies on for formatting/sorting."""
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client)

    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]

    assert isinstance(account["client_id"], int)
    assert isinstance(account["client_name"], str)
    assert isinstance(account["google_customer_id"], str)
    assert isinstance(account["currency"], str) and account["currency"]
    assert isinstance(account["clicks"], int)
    assert isinstance(account["impressions"], int)
    assert isinstance(account["spend"], (int, float))
    assert isinstance(account["conversions"], (int, float))
    assert isinstance(account["change_breakdown"], dict)
    assert isinstance(account["new_access_emails"], list)
    assert isinstance(account["alert_details"], list)
    assert isinstance(account["spend_trend"], list)
    assert isinstance(account["pacing"], dict)


def test_overview_pacing_has_required_keys(api_client, db):
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client)
    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]
    missing = REQUIRED_PACING_KEYS - account["pacing"].keys()
    assert not missing, f"pacing missing keys: {missing}"


def test_overview_conversions_are_floats_not_ints(api_client, db):
    """Google Ads returns fractional conversions — frontend must receive
    them as floats (see CLAUDE.md architecture note)."""
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client, conversions=3.7)

    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]
    assert isinstance(account["conversions"], float)
    # Also: conversions must be rounded to 1 decimal place (see mcc_service.py:467)
    assert account["conversions"] == round(account["conversions"], 1)


def test_overview_spend_trend_is_list_of_date_value_pairs(api_client, db):
    """Sparkline contract: `spend_trend` must be list of {date, spend} dicts."""
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client)
    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]

    for point in account["spend_trend"]:
        assert "date" in point
        assert "spend" in point
        date.fromisoformat(point["date"])
        assert isinstance(point["spend"], (int, float))


def test_overview_alert_details_have_title_severity_type(api_client, db):
    client = _seed_client(db)
    alert = Alert(
        client_id=client.id,
        title="Budget burn",
        severity="high",
        alert_type="BUDGET",
    )
    db.add(alert)
    db.commit()

    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]
    assert account["unresolved_alerts"] == 1
    assert len(account["alert_details"]) == 1
    alert_d = account["alert_details"][0]
    assert set(alert_d.keys()) == {"title", "severity", "type"}


def test_overview_excludes_demo_client(api_client, db, monkeypatch):
    """The demo client must never appear in MCC overview (would pollute
    aggregate metrics and trigger false bulk-sync attempts)."""
    from app.config import settings

    _seed_client(db, name="Demo", gcid="1234567890")
    _seed_client(db, name="Real", gcid="9999999999")

    monkeypatch.setattr(settings, "demo_google_customer_id", "1234567890")

    body = api_client.get("/api/v1/mcc/overview").json()
    names = [a["client_name"] for a in body["accounts"]]
    assert "Real" in names
    assert "Demo" not in names


def test_overview_respects_date_from_date_to_query_params(api_client, db):
    client = _seed_client(db)
    _seed_campaign_with_metrics(db, client)

    body = api_client.get(
        "/api/v1/mcc/overview?date_from=2026-01-01&date_to=2026-01-31"
    ).json()
    assert body["date_from"] == "2026-01-01"
    assert body["date_to"] == "2026-01-31"


def test_overview_defaults_to_current_month_when_no_dates(api_client, db):
    _seed_client(db)
    body = api_client.get("/api/v1/mcc/overview").json()
    today = date.today()
    assert body["date_from"] == today.replace(day=1).isoformat()
    assert body["date_to"] == today.isoformat()


def test_overview_returns_empty_accounts_list_not_null(api_client, db):
    """Frontend does `data?.accounts?.length` — must be a list, not null."""
    body = api_client.get("/api/v1/mcc/overview").json()
    assert body["accounts"] == []
    assert isinstance(body["accounts"], list)


def test_overview_last_synced_at_reflects_sync_logs(api_client, db):
    client = _seed_client(db)
    sync_time = datetime(2026, 4, 10, 8, 0, 0)
    log = SyncLog(
        client_id=client.id,
        status="success",
        days=30,
        phases={},
        started_at=sync_time,
        finished_at=sync_time,
    )
    db.add(log)
    db.commit()

    account = api_client.get("/api/v1/mcc/overview").json()["accounts"][0]
    assert account["last_synced_at"] is not None
    # Should be parseable as ISO datetime
    parsed = datetime.fromisoformat(account["last_synced_at"])
    assert parsed.year == 2026
    assert parsed.month == 4


# ─── /mcc/billing-status ───────────────────────────────────────────────


def test_billing_status_requires_customer_id(api_client):
    resp = api_client.get("/api/v1/mcc/billing-status")
    assert resp.status_code == 422


def test_billing_status_returns_unknown_when_api_not_connected(api_client, db):
    """Without Google Ads client, endpoint returns structured 'unknown'
    (not a crash) so the UI badge can render."""
    resp = api_client.get("/api/v1/mcc/billing-status?customer_id=1112223334")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    # Either: {"status": "unknown", "reason": "..."} or {"status": "ok", ...}
    assert body["status"] in ("unknown", "ok", "no_billing", "error")


# ─── /mcc/shared-lists ─────────────────────────────────────────────────


def test_shared_lists_envelope_has_keyword_and_placement_lists(api_client, db):
    body = api_client.get("/api/v1/mcc/shared-lists").json()
    assert "keyword_lists" in body
    assert "placement_lists" in body
    assert isinstance(body["keyword_lists"], list)
    assert isinstance(body["placement_lists"], list)


def test_shared_lists_keyword_list_has_required_keys(api_client, db):
    client = _seed_client(db)
    nkl = NegativeKeywordList(
        client_id=client.id,
        google_resource_name="customers/x/sharedSets/1",
        name="MCC Wulgaryzmy",
        source="GOOGLE_ADS_SYNC",
        status="ENABLED",
        ownership_level="mcc",
    )
    db.add(nkl)
    db.commit()
    db.refresh(nkl)

    db.add(NegativeKeywordListItem(list_id=nkl.id, text="kw1", match_type="PHRASE"))
    db.commit()

    body = api_client.get("/api/v1/mcc/shared-lists").json()
    assert len(body["keyword_lists"]) == 1
    kw = body["keyword_lists"][0]
    expected = {"id", "name", "description", "source", "status", "item_count", "ownership_level"}
    assert expected.issubset(kw.keys())
    assert kw["item_count"] == 1
    assert kw["ownership_level"] == "mcc"


# ─── /mcc/shared-lists/{id}/items ──────────────────────────────────────


def test_shared_list_items_keyword_drill_down_shape(api_client, db):
    client = _seed_client(db)
    nkl = NegativeKeywordList(
        client_id=client.id,
        google_resource_name="customers/x/sharedSets/1",
        name="list",
        source="GOOGLE_ADS_SYNC",
        status="ENABLED",
        ownership_level="mcc",
    )
    db.add(nkl)
    db.commit()
    db.refresh(nkl)

    db.add(NegativeKeywordListItem(list_id=nkl.id, text="darmowe", match_type="PHRASE"))
    db.add(NegativeKeywordListItem(list_id=nkl.id, text="crack", match_type="EXACT"))
    db.commit()

    body = api_client.get(f"/api/v1/mcc/shared-lists/{nkl.id}/items?list_type=keyword").json()
    assert body["id"] == nkl.id
    assert body["type"] == "keyword"
    assert body["item_count"] == 2
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert set(item.keys()) == {"id", "text", "match_type"}


def test_shared_list_items_placement_drill_down_shape(api_client, db):
    client = _seed_client(db)
    pel = PlacementExclusionList(
        client_id=client.id,
        google_resource_name="customers/x/sharedSets/2",
        name="Spam sites",
        source="GOOGLE_ADS_SYNC",
        status="ENABLED",
        ownership_level="mcc",
    )
    db.add(pel)
    db.commit()
    db.refresh(pel)

    db.add(PlacementExclusionListItem(list_id=pel.id, url="spam.com", placement_type="WEBSITE"))
    db.commit()

    body = api_client.get(f"/api/v1/mcc/shared-lists/{pel.id}/items?list_type=placement").json()
    assert body["id"] == pel.id
    assert body["type"] == "placement"
    assert body["item_count"] == 1
    assert len(body["items"]) == 1
    assert set(body["items"][0].keys()) == {"id", "url", "placement_type"}


def test_shared_list_items_returns_error_on_missing_list(api_client, db):
    body = api_client.get("/api/v1/mcc/shared-lists/99999/items?list_type=keyword").json()
    assert "error" in body


# ─── /mcc/new-access ───────────────────────────────────────────────────


def test_new_access_returns_list(api_client, db):
    client = _seed_client(db)
    resp = api_client.get(f"/api/v1/mcc/new-access?client_id={client.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


def test_new_access_requires_client_id(api_client):
    resp = api_client.get("/api/v1/mcc/new-access")
    assert resp.status_code == 422


# ─── /mcc/dismiss-google-recommendations ───────────────────────────────


def test_dismiss_google_recommendations_returns_count(api_client, db):
    client = _seed_client(db)
    for i in range(3):
        db.add(
            Recommendation(
                client_id=client.id,
                source="GOOGLE_ADS_API",
                status="pending",
                rule_id="GOOGLE_ADS_REC",
                entity_type="campaign",
                entity_id=f"rec_{i}",
                reason=f"rec {i}",
                suggested_action="dismiss me",
            )
        )
    db.commit()

    resp = api_client.post(
        "/api/v1/mcc/dismiss-google-recommendations",
        json={"client_id": client.id, "dismiss_all": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "dismissed" in body
    assert body["dismissed"] == 3

    # DB state updated
    remaining = (
        db.query(Recommendation)
        .filter(Recommendation.client_id == client.id, Recommendation.status == "pending")
        .count()
    )
    assert remaining == 0


def test_dismiss_google_recommendations_only_affects_google_source(api_client, db):
    """Must not dismiss PLAYBOOK_RULES recommendations (only GOOGLE_ADS_API)."""
    client = _seed_client(db)
    db.add(
        Recommendation(
            client_id=client.id,
            source="GOOGLE_ADS_API",
            status="pending",
            rule_id="GOOGLE_ADS_REC",
            entity_type="campaign",
            entity_id="g1",
            reason="google rec",
            suggested_action="dismiss me",
        )
    )
    db.add(
        Recommendation(
            client_id=client.id,
            source="PLAYBOOK_RULES",
            status="pending",
            rule_id="PLAYBOOK_RULE",
            entity_type="campaign",
            entity_id="p1",
            reason="playbook rec",
            suggested_action="apply me",
        )
    )
    db.commit()

    api_client.post(
        "/api/v1/mcc/dismiss-google-recommendations",
        json={"client_id": client.id, "dismiss_all": True},
    )

    # Google rec dismissed
    google_pending = (
        db.query(Recommendation)
        .filter(Recommendation.client_id == client.id, Recommendation.source == "GOOGLE_ADS_API", Recommendation.status == "pending")
        .count()
    )
    assert google_pending == 0

    # Playbook rec untouched
    playbook_pending = (
        db.query(Recommendation)
        .filter(Recommendation.client_id == client.id, Recommendation.source == "PLAYBOOK_RULES", Recommendation.status == "pending")
        .count()
    )
    assert playbook_pending == 1


# ─── /mcc/negative-keyword-lists ───────────────────────────────────────


def test_negative_keyword_lists_overview_returns_list_with_client_info(api_client, db):
    client = _seed_client(db, name="Klient A")
    nkl = NegativeKeywordList(
        client_id=client.id,
        google_resource_name="customers/x/sharedSets/42",
        name="Lista A",
        source="GOOGLE_ADS_SYNC",
        status="ENABLED",
        ownership_level="account",
    )
    db.add(nkl)
    db.commit()

    body = api_client.get("/api/v1/mcc/negative-keyword-lists").json()
    assert isinstance(body, list)
    assert len(body) == 1
    row = body[0]
    expected_keys = {
        "id",
        "client_id",
        "client_name",
        "name",
        "description",
        "source",
        "status",
        "member_count",
        "ownership_level",
    }
    assert expected_keys.issubset(row.keys())


# ─── /mcc/sync-history ─────────────────────────────────────────────────


def _seed_sync_logs(db, client, count=3):
    """Seed N SyncLog entries for a client, alternating success/partial."""
    logs = []
    for i in range(count):
        started = datetime.now(timezone.utc) - timedelta(hours=i * 2 + 1)
        finished = started + timedelta(minutes=3)
        log = SyncLog(
            client_id=client.id,
            status="success" if i % 2 == 0 else "partial",
            total_synced=100 + i * 10,
            total_errors=i,
            started_at=started,
            finished_at=finished,
        )
        db.add(log)
        logs.append(log)
    db.commit()
    return logs


def test_sync_history_returns_list_shape(api_client, db):
    """AC3: response is a list with all required fields."""
    client = _seed_client(db)
    _seed_sync_logs(db, client, count=2)

    resp = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2

    required_keys = {"id", "client_id", "status", "total_synced", "total_errors",
                     "started_at", "finished_at", "duration_s"}
    for entry in body:
        missing = required_keys - entry.keys()
        assert not missing, f"sync-history entry missing keys: {missing}"
        assert isinstance(entry["client_id"], int)
        assert entry["status"] in ("running", "success", "partial", "failed")
        assert isinstance(entry["total_synced"], int)
        assert isinstance(entry["total_errors"], int)


def test_sync_history_sorted_newest_first(api_client, db):
    """Entries ordered by finished_at DESC."""
    client = _seed_client(db)
    _seed_sync_logs(db, client, count=3)

    body = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}").json()
    finished_ats = [e["finished_at"] for e in body if e["finished_at"]]
    assert finished_ats == sorted(finished_ats, reverse=True)


def test_sync_history_duration_s_computed(api_client, db):
    """duration_s = finished_at - started_at in seconds."""
    client = _seed_client(db)
    _seed_sync_logs(db, client, count=1)

    entry = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}").json()[0]
    assert isinstance(entry["duration_s"], (int, float))
    assert entry["duration_s"] == 180  # 3 minutes per _seed_sync_logs


def test_sync_history_returns_200_empty_when_no_syncs(api_client, db):
    """AC7: 200 with [] when client exists but has no syncs."""
    client = _seed_client(db)

    resp = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sync_history_returns_404_for_missing_client(api_client, db):
    """AC7: 404 when client_id does not exist."""
    resp = api_client.get("/api/v1/mcc/sync-history?client_id=99999")
    assert resp.status_code == 404


def test_sync_history_limit_enforced(api_client, db):
    """limit param: default 5, respects custom value, rejects >20."""
    client = _seed_client(db)
    _seed_sync_logs(db, client, count=10)

    # default limit=5
    body = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}").json()
    assert len(body) == 5

    # custom limit=3
    body = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}&limit=3").json()
    assert len(body) == 3

    # limit=21 rejected
    resp = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}&limit=21")
    assert resp.status_code == 422


def test_sync_history_handles_null_finished_at(api_client, db):
    """Edge case: running sync has finished_at=None — duration_s=None, still returned."""
    from datetime import datetime, timezone
    client = _seed_client(db)
    log = SyncLog(
        client_id=client.id,
        status="running",
        total_synced=0,
        total_errors=0,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
    )
    db.add(log)
    db.commit()

    body = api_client.get(f"/api/v1/mcc/sync-history?client_id={client.id}").json()
    assert len(body) == 1
    assert body[0]["finished_at"] is None
    assert body[0]["duration_s"] is None
    assert body[0]["status"] == "running"
