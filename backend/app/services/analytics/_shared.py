"""Shared base for analytics mixins.

Owns the DB session and helpers used by 5+ domain methods:
- `_filter_campaigns` / `_filter_campaign_ids` — canonical Campaign filter
- `_aggregate_metric_daily` — per-campaign MetricDaily rollup
- `_create_alert` — deduplicating Alert writer

Domain mixins (kpi, health, ...) assume `self.db` and these helpers are present
via MRO; never instantiate a mixin without `AnalyticsBase` in its bases.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.campaign import Campaign
from app.models.metric_daily import MetricDaily


class AnalyticsBase:
    """Base class owning the DB session and cross-domain helpers."""

    def __init__(self, db: Session):
        self.db = db

    def _filter_campaigns(
        self,
        client_id: int,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ):
        """Build filtered Campaign query. Reusable across all analytics methods."""
        q = self.db.query(Campaign).filter(Campaign.client_id == client_id)
        if campaign_type and campaign_type != "ALL":
            q = q.filter(Campaign.campaign_type == campaign_type)
        if campaign_status and campaign_status != "ALL":
            q = q.filter(Campaign.status == campaign_status)
        return q

    def _filter_campaign_ids(
        self,
        client_id: int,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
    ) -> list[int]:
        """Return list of campaign IDs matching filters."""
        return [
            c.id
            for c in self._filter_campaigns(client_id, campaign_type, campaign_status).all()
        ]

    def _aggregate_metric_daily(
        self, campaign_id: int, start: date, end: date
    ) -> dict | None:
        """Aggregate MetricDaily for a campaign over a date range.

        Returns None when the campaign had no clicks in the window.
        """
        result = (
            self.db.query(
                func.sum(MetricDaily.cost_micros).label("cost"),
                func.sum(MetricDaily.conversions).label("conv"),
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.impressions).label("impr"),
                func.sum(MetricDaily.conversion_value_micros).label("value"),
            )
            .filter(
                MetricDaily.campaign_id == campaign_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .first()
        )
        if not result or not result.clicks:
            return None

        cost = (result.cost or 0) / 1_000_000
        conv = float(result.conv or 0)
        clicks = result.clicks or 0
        impr = result.impr or 0
        value = (result.value or 0) / 1_000_000

        return {
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "cpa_usd": round(cost / conv, 2) if conv > 0 else 0,
            "ctr": round(clicks / impr * 100, 2) if impr > 0 else 0,
            "roas": round(value / cost, 2) if cost > 0 else 0,
            "clicks": clicks,
            "impressions": impr,
        }

    def _create_alert(self, **kwargs) -> Alert | None:
        """Create an alert unless a matching unresolved one already exists."""
        existing = (
            self.db.query(Alert)
            .filter(
                Alert.client_id == kwargs["client_id"],
                Alert.campaign_id == kwargs.get("campaign_id"),
                Alert.alert_type == kwargs["alert_type"],
                Alert.resolved_at.is_(None),
            )
            .first()
        )

        if existing:
            return None

        alert = Alert(**kwargs)
        self.db.add(alert)
        return alert
