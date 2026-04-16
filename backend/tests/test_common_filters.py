"""Unit tests for CommonFilters dependency — contract guard."""

from datetime import date, timedelta

from app.dependencies.filters import CommonFilters, common_filters


def test_defaults_resolve_dates_to_last_30_days():
    f = common_filters()
    today = date.today()
    assert f.date_to == today
    assert f.date_from == today - timedelta(days=30)
    assert f.client_id is None
    assert f.campaign_type is None
    assert f.campaign_status is None
    assert f.dates_explicit is False


def test_dates_explicit_flag_tracks_caller_intent():
    assert common_filters().dates_explicit is False
    assert common_filters(days=7).dates_explicit is True
    assert common_filters(date_from=date(2026, 1, 1)).dates_explicit is True
    assert common_filters(date_to=date(2026, 1, 31)).dates_explicit is True


def test_explicit_dates_override_days():
    f = common_filters(days=7, date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))
    assert f.date_from == date(2026, 1, 1)
    assert f.date_to == date(2026, 1, 31)
    assert f.period_days == 30


def test_days_resolves_when_no_explicit_dates():
    f = common_filters(days=7)
    assert (f.date_to - f.date_from).days == 7


def test_all_sentinel_normalized_to_none():
    f = common_filters(campaign_type="ALL", campaign_status="all")
    assert f.campaign_type is None
    assert f.campaign_status is None


def test_enum_uppercased():
    f = common_filters(campaign_type="search", campaign_status="enabled")
    assert f.campaign_type == "SEARCH"
    assert f.campaign_status == "ENABLED"


def test_status_is_deprecated_alias_for_campaign_status():
    f = common_filters(status="ENABLED")
    assert f.campaign_status == "ENABLED"


def test_campaign_status_wins_over_status_alias():
    f = common_filters(campaign_status="PAUSED", status="ENABLED")
    assert f.campaign_status == "PAUSED"


def test_client_id_and_campaign_id_passthrough():
    f = common_filters(client_id=42, campaign_id=7, ad_group_id=3)
    assert f.client_id == 42
    assert f.campaign_id == 7
    assert f.ad_group_id == 3


def test_returned_value_is_frozen():
    f = common_filters()
    assert isinstance(f, CommonFilters)
    try:
        f.client_id = 999  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("CommonFilters must be immutable")
