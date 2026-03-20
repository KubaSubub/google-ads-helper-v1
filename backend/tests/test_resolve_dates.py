"""Unit tests for resolve_dates utility and AnalyticsService filter helpers."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.utils.date_utils import resolve_dates
from app.models import Campaign, Client
from app.services.analytics_service import AnalyticsService


class TestResolveDates:
    def test_explicit_dates_override_days(self):
        start, end = resolve_dates(
            days=7,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 31)

    def test_days_fallback(self):
        start, end = resolve_dates(days=7)
        assert end == date.today()
        assert start == date.today() - timedelta(days=7)

    def test_default_days(self):
        start, end = resolve_dates()
        assert end == date.today()
        assert start == date.today() - timedelta(days=30)

    def test_custom_default_days(self):
        start, end = resolve_dates(default_days=14)
        assert start == date.today() - timedelta(days=14)

    def test_only_date_from(self):
        start, end = resolve_dates(date_from=date(2026, 3, 1))
        assert start == date(2026, 3, 1)
        assert end == date.today()

    def test_only_date_to(self):
        start, end = resolve_dates(date_to=date(2026, 3, 15), days=5)
        assert end == date(2026, 3, 15)
        assert start == date(2026, 3, 15) - timedelta(days=5)

    def test_days_none_uses_default(self):
        start, end = resolve_dates(days=None, default_days=60)
        assert start == date.today() - timedelta(days=60)

    def test_all_none(self):
        start, end = resolve_dates(days=None, date_from=None, date_to=None)
        assert end == date.today()
        assert start == date.today() - timedelta(days=30)


class TestFilterCampaigns:
    def _seed(self, db: Session):
        client = Client(name="Filter Test", google_customer_id="1111111111")
        db.add(client)
        db.flush()
        for name, ctype, status in [
            ("Search Active", "SEARCH", "ENABLED"),
            ("Display Active", "DISPLAY", "ENABLED"),
            ("Search Paused", "SEARCH", "PAUSED"),
            ("PMax Active", "PERFORMANCE_MAX", "ENABLED"),
        ]:
            db.add(Campaign(
                client_id=client.id,
                google_campaign_id=f"fc_{name}",
                name=name,
                campaign_type=ctype,
                status=status,
                budget_micros=10_000_000,
            ))
        db.commit()
        return client

    def test_no_filters_returns_all(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id)
        assert len(ids) == 4

    def test_filter_by_type(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_type="SEARCH")
        assert len(ids) == 2

    def test_filter_by_status(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_status="PAUSED")
        assert len(ids) == 1

    def test_filter_by_type_and_status(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_type="SEARCH", campaign_status="ENABLED")
        assert len(ids) == 1

    def test_all_type_returns_all(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_type="ALL")
        assert len(ids) == 4

    def test_all_status_returns_all(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_status="ALL")
        assert len(ids) == 4

    def test_nonexistent_type_returns_empty(self, db):
        client = self._seed(db)
        svc = AnalyticsService(db)
        ids = svc._filter_campaign_ids(client.id, campaign_type="SHOPPING")
        assert len(ids) == 0
