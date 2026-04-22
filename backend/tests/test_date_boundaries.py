"""Date boundary & cross-month regression tests.

These tests specifically target bugs where date calculations silently
produce wrong numbers when a reporting window crosses a month boundary.
The original bug: days_elapsed=45 with days_in_month=28 because the
pacing calculation counted days from Feb 1 to Mar 17.

Strategy: freeze date.today() via monkeypatch and set up MetricDaily
rows in specific months to verify that:
 - days_elapsed never exceeds days_in_month
 - spend queries don't leak across month boundaries
 - past months use full-month elapsed days
 - current month uses actual elapsed days
"""

import calendar
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.campaign import Campaign
from app.models.client import Client
from app.models.metric_daily import MetricDaily
from app.services.agent_service import AgentService

# We need TestClient only for the analytics router tests
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_client(db) -> Client:
    client = Client(name="Boundary Test", google_customer_id="000-000-0000")
    db.add(client)
    db.flush()
    return client


def _make_campaign(db, client_id: int, budget_micros: int = 10_000_000) -> Campaign:
    camp = Campaign(
        client_id=client_id,
        google_campaign_id="boundary-camp-1",
        name="Boundary Campaign",
        status="ENABLED",
        campaign_type="SEARCH",
        budget_micros=budget_micros,
    )
    db.add(camp)
    db.flush()
    return camp


def _seed_metrics(db, campaign_id: int, start: date, end: date,
                  cost_micros_per_day: int = 5_000_000):
    """Seed one MetricDaily row per day in [start, end] inclusive."""
    d = start
    while d <= end:
        db.add(MetricDaily(
            campaign_id=campaign_id,
            date=d,
            clicks=10,
            impressions=100,
            cost_micros=cost_micros_per_day,
            conversions=1.0,
            conversion_value_micros=20_000_000,
        ))
        d += timedelta(days=1)
    db.commit()


# ===========================================================================
# AgentService._get_budget_pacing — cross-month boundary tests
# ===========================================================================


class TestBudgetPacingCrossMonth:
    """The original bug: monthly report for February generated in March
    produced days_elapsed=45, days_in_month=28."""

    def test_past_month_days_elapsed_equals_days_in_month(self, db):
        """When reporting on a past month, days_elapsed must equal days_in_month."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # Seed February 2026 data only
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 2, 28))

        service = AgentService(db, client.id)
        # Simulate a monthly report for February, viewed in March
        service._period_start = date(2026, 2, 1)
        service._period_end = date(2026, 2, 28)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 17)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_in_month"] == 28
        assert result["days_elapsed"] == 28, (
            f"Past month should have days_elapsed=days_in_month, got {result['days_elapsed']}"
        )
        assert result["days_elapsed"] <= result["days_in_month"]
        assert result["month"] == "2026-02"

    def test_current_month_days_elapsed_within_month(self, db):
        """When reporting on the current month, days_elapsed <= days_in_month."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        _seed_metrics(db, camp.id, date(2026, 3, 1), date(2026, 3, 17))

        service = AgentService(db, client.id)
        service._period_start = date(2026, 3, 1)
        service._period_end = date(2026, 3, 31)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 17)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_elapsed"] == 17
        assert result["days_in_month"] == 31
        assert result["days_elapsed"] <= result["days_in_month"]

    def test_days_elapsed_never_exceeds_days_in_month(self, db):
        """Invariant: days_elapsed <= days_in_month regardless of date window."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # Seed data spanning Feb + March
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 3, 31))

        service = AgentService(db, client.id)
        # _date_window(30) from March 17 gives window_start ~ Feb 16
        # So report_month = Feb 1, but today = Mar 17

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 17)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_elapsed"] <= result["days_in_month"], (
            f"days_elapsed ({result['days_elapsed']}) > days_in_month ({result['days_in_month']})"
        )


class TestBudgetPacingSpendIsolation:
    """Spend must not leak across month boundaries."""

    def test_spend_excludes_next_month_data(self, db):
        """Feb pacing must not include March spend."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id, budget_micros=10_000_000)
        # Feb: $5/day = $140 total; March: $50/day (much higher)
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 2, 28),
                      cost_micros_per_day=5_000_000)
        _seed_metrics(db, camp.id, date(2026, 3, 1), date(2026, 3, 17),
                      cost_micros_per_day=50_000_000)

        service = AgentService(db, client.id)
        service._period_start = date(2026, 2, 1)
        service._period_end = date(2026, 2, 28)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 17)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        camp_result = result["campaigns"][0]
        # Feb total should be 28 * $5 = $140, NOT include March's $50/day
        assert camp_result["actual_spend_usd"] == 140.0, (
            f"Expected $140 (28 days * $5), got ${camp_result['actual_spend_usd']}"
        )

    def test_spend_excludes_previous_month_data(self, db):
        """March pacing must not include February spend."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id, budget_micros=10_000_000)
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 2, 28),
                      cost_micros_per_day=50_000_000)
        _seed_metrics(db, camp.id, date(2026, 3, 1), date(2026, 3, 17),
                      cost_micros_per_day=5_000_000)

        service = AgentService(db, client.id)
        service._period_start = date(2026, 3, 1)
        service._period_end = date(2026, 3, 31)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 17)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        camp_result = result["campaigns"][0]
        # March 1-31 total should be 17 * $5 = $85 (only seeded up to 17th)
        assert camp_result["actual_spend_usd"] == 85.0, (
            f"Expected $85 (17 days * $5), got ${camp_result['actual_spend_usd']}"
        )


class TestBudgetPacingEdgeDates:
    """Edge cases: first/last day of month, leap year, year boundary."""

    def test_first_day_of_month(self, db):
        """On the 1st, days_elapsed should be 1."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        _seed_metrics(db, camp.id, date(2026, 4, 1), date(2026, 4, 1))

        service = AgentService(db, client.id)
        service._period_start = date(2026, 4, 1)
        service._period_end = date(2026, 4, 30)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_elapsed"] == 1
        assert result["days_in_month"] == 30

    def test_last_day_of_month(self, db):
        """On the last day of the current month, days_elapsed == days_in_month."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        _seed_metrics(db, camp.id, date(2026, 4, 1), date(2026, 4, 30))

        service = AgentService(db, client.id)
        service._period_start = date(2026, 4, 1)
        service._period_end = date(2026, 4, 30)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 30)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_elapsed"] == 30
        assert result["days_in_month"] == 30

    def test_leap_year_february(self, db):
        """Feb in a leap year has 29 days — days_in_month must reflect that."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # 2028 is a leap year
        _seed_metrics(db, camp.id, date(2028, 2, 1), date(2028, 2, 29))

        service = AgentService(db, client.id)
        service._period_start = date(2028, 2, 1)
        service._period_end = date(2028, 2, 29)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2028, 3, 5)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["days_in_month"] == 29
        assert result["days_elapsed"] == 29

    def test_december_year_boundary(self, db):
        """December report viewed in January — must not cross year boundary."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        _seed_metrics(db, camp.id, date(2025, 12, 1), date(2025, 12, 31))
        # Also seed Jan data — must NOT be included
        _seed_metrics(db, camp.id, date(2026, 1, 1), date(2026, 1, 15),
                      cost_micros_per_day=99_000_000)

        service = AgentService(db, client.id)
        service._period_start = date(2025, 12, 1)
        service._period_end = date(2025, 12, 31)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        assert result["month"] == "2025-12"
        assert result["days_elapsed"] == 31
        assert result["days_in_month"] == 31
        camp_result = result["campaigns"][0]
        # 31 days * $5 = $155, must NOT include Jan's $99/day
        assert camp_result["actual_spend_usd"] == 155.0


class TestBudgetPacingPacingPctConsistency:
    """pacing_pct must be mathematically consistent with spend/budget/days."""

    def test_full_past_month_even_spend(self, db):
        """With even daily spend == budget, pacing should be ~100%."""
        daily_budget_micros = 10_000_000  # $10/day
        client = _make_client(db)
        camp = _make_campaign(db, client.id, budget_micros=daily_budget_micros)
        # Spend exactly $10/day for all of February
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 2, 28),
                      cost_micros_per_day=daily_budget_micros)

        service = AgentService(db, client.id)
        service._period_start = date(2026, 2, 1)
        service._period_end = date(2026, 2, 28)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 5)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = service._get_budget_pacing()

        camp_result = result["campaigns"][0]
        assert camp_result["pacing_pct"] == 100.0
        assert camp_result["status"] == "on_track"


# ===========================================================================
# Analytics router /budget-pacing — boundary tests
# ===========================================================================


class TestAnalyticsBudgetPacingEndpoint:
    """Analytics router always reports on the CURRENT month — verify
    that days_elapsed <= days_in_month even near month boundaries."""

    def test_days_elapsed_lte_days_in_month(self, db, api_client):
        """Invariant check on the REST endpoint."""
        client = _make_client(db)
        _make_campaign(db, client.id)
        db.commit()

        resp = api_client.get(f"/api/v1/analytics/budget-pacing?client_id={client.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["days_elapsed"] <= data["days_in_month"]

    def test_first_of_month_days_elapsed_is_1(self, db, api_client):
        """On day 1, endpoint must return days_elapsed=1."""
        client = _make_client(db)
        _make_campaign(db, client.id)
        db.commit()

        with patch("app.routers.analytics._pacing.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            resp = api_client.get(
                f"/api/v1/analytics/budget-pacing?client_id={client.id}"
            )

        data = resp.json()
        assert data["days_elapsed"] == 1
        assert data["days_in_month"] == 31

    def test_spend_stays_within_current_month(self, db, api_client):
        """Spend from previous month must not leak into current month pacing."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # Big spend in February, small in March
        _seed_metrics(db, camp.id, date(2026, 2, 1), date(2026, 2, 28),
                      cost_micros_per_day=90_000_000)
        _seed_metrics(db, camp.id, date(2026, 3, 1), date(2026, 3, 10),
                      cost_micros_per_day=5_000_000)
        db.commit()

        with patch("app.routers.analytics._pacing.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            resp = api_client.get(
                f"/api/v1/analytics/budget-pacing?client_id={client.id}"
            )

        data = resp.json()
        camp_data = data["campaigns"][0]
        # 10 days * $5 = $50, must NOT include Feb's $90/day
        assert camp_data["actual_spend_usd"] == 50.0


# ===========================================================================
# KPI period-over-period — date window symmetry
# ===========================================================================


class TestKPIPeriodSymmetry:
    """Current and previous periods must have the same length
    regardless of where the window lands across months."""

    def test_period_lengths_match_across_month_boundary(self, db):
        """KPI comparison window crossing a month boundary:
        both periods must be equal length."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # Seed 60 days of data to cover both periods
        _seed_metrics(db, camp.id,
                      date(2026, 1, 15), date(2026, 3, 17))

        service = AgentService(db, client.id)
        # 7-day window ending Mar 3 — straddles Feb/Mar
        service._period_start = date(2026, 2, 25)
        service._period_end = date(2026, 3, 3)

        kpis = service._get_kpis()
        current = kpis["current_7d"]
        previous = kpis["previous_7d"]
        # Both should have data (we seeded enough)
        assert current["clicks"] > 0
        assert previous["clicks"] > 0
        # With uniform 10 clicks/day, both should be equal
        assert current["clicks"] == previous["clicks"], (
            "Period-over-period comparison should use equal-length windows"
        )


# ===========================================================================
# _get_campaigns_summary — date range respects boundaries
# ===========================================================================


class TestCampaignsSummaryDateBoundary:
    """_get_campaigns_summary uses last 30 days — verify it doesn't
    miscalculate when the 30-day window crosses a month boundary."""

    def test_metrics_match_expected_30_day_sum(self, db):
        """Verify that 30-day aggregation sums correctly across months."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # Seed 60 days at $5/day ending today
        today = date(2026, 3, 17)
        start = today - timedelta(days=59)
        _seed_metrics(db, camp.id, start, today, cost_micros_per_day=5_000_000)

        service = AgentService(db, client.id)

        with patch("app.services.agent_service.date") as mock_date:
            mock_date.today.return_value = today
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            summary = service._get_campaigns_summary()

        # _get_campaigns_summary uses >= today - timedelta(30) = 31 days inclusive
        assert len(summary) == 1
        assert summary[0]["clicks_30d"] == 310
        assert summary[0]["cost_30d_usd"] == 155.0


# ===========================================================================
# _get_month_comparison — symmetric period check
# ===========================================================================


class TestMonthComparisonSymmetry:
    """month_comparison compares current period vs previous period of
    equal length. Verify delta calculation doesn't break at boundaries."""

    def test_equal_data_produces_zero_deltas(self, db):
        """With uniform data, deltas should be ~0%."""
        client = _make_client(db)
        camp = _make_campaign(db, client.id)
        # 90 days of uniform data
        _seed_metrics(db, camp.id,
                      date(2025, 12, 15), date(2026, 3, 17),
                      cost_micros_per_day=5_000_000)

        service = AgentService(db, client.id)
        service._period_start = date(2026, 2, 1)
        service._period_end = date(2026, 2, 28)

        comparison = service._get_month_comparison()
        # With identical daily metrics, delta should be 0%
        for key, val in comparison["deltas"].items():
            assert val == 0.0, (
                f"Delta for '{key}' should be 0% with uniform data, got {val}%"
            )


# ===========================================================================
# Parametrized invariant: days_elapsed ∈ [1, days_in_month]
# ===========================================================================


@pytest.mark.parametrize("report_month,today_str", [
    # Past month — various distances
    ((2026, 1), "2026-02-15"),
    ((2026, 2), "2026-03-17"),
    ((2025, 12), "2026-01-10"),
    # Current month — various days
    ((2026, 3), "2026-03-01"),
    ((2026, 3), "2026-03-15"),
    ((2026, 3), "2026-03-31"),
    # Leap year
    ((2028, 2), "2028-02-15"),
    ((2028, 2), "2028-03-01"),
])
def test_days_elapsed_invariant(db, report_month, today_str):
    """days_elapsed must always be in [1, days_in_month]."""
    client = _make_client(db)
    camp = _make_campaign(db, client.id)
    year, month = report_month
    dim = calendar.monthrange(year, month)[1]
    _seed_metrics(db, camp.id, date(year, month, 1), date(year, month, dim))

    today_date = date.fromisoformat(today_str)

    service = AgentService(db, client.id)
    service._period_start = date(year, month, 1)
    service._period_end = date(year, month, dim)

    with patch("app.services.agent_service.date") as mock_date:
        mock_date.today.return_value = today_date
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = service._get_budget_pacing()

    assert 1 <= result["days_elapsed"] <= result["days_in_month"], (
        f"For {year}-{month:02d} viewed on {today_str}: "
        f"days_elapsed={result['days_elapsed']}, days_in_month={result['days_in_month']}"
    )
