"""MCC (My Client Center) service — aggregate data across all client accounts."""

import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
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
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency


def _specialist_emails() -> list[str]:
    raw = settings.specialist_emails
    if not raw:
        return []
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


class MCCService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_overview(self, date_from: date | None = None, date_to: date | None = None) -> dict:
        today = date.today()
        if not date_from:
            date_from = today.replace(day=1)  # 1st of current month
        if not date_to:
            date_to = today

        # Filter out demo client
        demo_cid = settings.demo_google_customer_id
        clients = self.db.query(Client).all()
        if demo_cid:
            clients = [c for c in clients if c.google_customer_id != demo_cid]

        accounts = []
        for client in clients:
            accounts.append(self._build_account_data(client, date_from, date_to))

        return {
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "accounts": accounts,
        }

    def detect_new_access(self, client_id: int, days: int = 30) -> list[str]:
        specialist = _specialist_emails()
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(days=days)
        older_cutoff = now - timedelta(days=90)

        recent_emails = set(
            row[0].lower()
            for row in self.db.query(ChangeEvent.user_email)
            .filter(
                ChangeEvent.client_id == client_id,
                ChangeEvent.user_email.isnot(None),
                ChangeEvent.change_date_time >= recent_cutoff,
            )
            .distinct()
            .all()
            if row[0]
        )

        older_emails = set(
            row[0].lower()
            for row in self.db.query(ChangeEvent.user_email)
            .filter(
                ChangeEvent.client_id == client_id,
                ChangeEvent.user_email.isnot(None),
                ChangeEvent.change_date_time >= older_cutoff,
                ChangeEvent.change_date_time < recent_cutoff,
            )
            .distinct()
            .all()
            if row[0]
        )

        new_emails = recent_emails - older_emails - set(specialist)
        return sorted(new_emails)

    def dismiss_google_recommendations(
        self,
        client_id: int,
        recommendation_ids: list[int] | None = None,
        dismiss_all: bool = False,
    ) -> dict:
        q = self.db.query(Recommendation).filter(
            Recommendation.client_id == client_id,
            Recommendation.source == "GOOGLE_ADS_API",
            Recommendation.status == "pending",
        )
        if not dismiss_all and recommendation_ids:
            q = q.filter(Recommendation.id.in_(recommendation_ids))

        count = q.update({"status": "dismissed"}, synchronize_session="fetch")
        self.db.commit()
        return {"dismissed": count}

    def get_mcc_shared_lists(self) -> dict:
        """Return MCC-level exclusion lists: negative keywords + placement exclusions.

        MCC-level lists are identified by ownership_level='mcc' (synced from manager account).
        Falls back to source='GOOGLE_ADS_SYNC' if no ownership_level set yet.
        """
        from app.models import MccLink

        manager_client_ids = self._get_manager_client_ids()

        # --- Negative keyword lists (MCC-level) ---
        kw_filter = NegativeKeywordList.ownership_level == "mcc"
        if manager_client_ids:
            kw_filter = kw_filter | NegativeKeywordList.client_id.in_(manager_client_ids)

        kw_lists = (
            self.db.query(NegativeKeywordList)
            .filter(kw_filter, NegativeKeywordList.status != "REMOVED")
            .order_by(NegativeKeywordList.name)
            .all()
        )

        kw_item_counts = self._count_nkl_items([nkl.id for nkl in kw_lists])

        # --- Placement exclusion lists (MCC-level) ---
        pl_filter = PlacementExclusionList.ownership_level == "mcc"
        if manager_client_ids:
            pl_filter = pl_filter | PlacementExclusionList.client_id.in_(manager_client_ids)

        pl_lists = (
            self.db.query(PlacementExclusionList)
            .filter(pl_filter, PlacementExclusionList.status != "REMOVED")
            .order_by(PlacementExclusionList.name)
            .all()
        )

        pl_item_counts = {}
        if pl_lists:
            rows = (
                self.db.query(
                    PlacementExclusionListItem.list_id,
                    func.count(PlacementExclusionListItem.id),
                )
                .filter(PlacementExclusionListItem.list_id.in_([p.id for p in pl_lists]))
                .group_by(PlacementExclusionListItem.list_id)
                .all()
            )
            pl_item_counts = {r[0]: r[1] for r in rows}

        return {
            "keyword_lists": [
                {
                    "id": nkl.id,
                    "name": nkl.name,
                    "description": nkl.description,
                    "source": nkl.source,
                    "status": nkl.status,
                    "item_count": kw_item_counts.get(nkl.id, 0),
                    "ownership_level": nkl.ownership_level or "mcc",
                }
                for nkl in kw_lists
            ],
            "placement_lists": [
                {
                    "id": pel.id,
                    "name": pel.name,
                    "description": pel.description,
                    "source": pel.source,
                    "status": pel.status,
                    "item_count": pl_item_counts.get(pel.id, 0),
                    "ownership_level": pel.ownership_level or "mcc",
                }
                for pel in pl_lists
            ],
        }

    def get_shared_list_items(self, list_id: int, list_type: str = "keyword") -> dict:
        """Return items (drill-down) for a specific shared list."""
        if list_type == "placement":
            pel = self.db.query(PlacementExclusionList).filter(PlacementExclusionList.id == list_id).first()
            if not pel:
                return {"error": "List not found"}
            items = (
                self.db.query(PlacementExclusionListItem)
                .filter(PlacementExclusionListItem.list_id == list_id)
                .order_by(PlacementExclusionListItem.url)
                .all()
            )
            return {
                "id": pel.id,
                "name": pel.name,
                "description": pel.description,
                "type": "placement",
                "item_count": len(items),
                "items": [
                    {"id": i.id, "url": i.url, "placement_type": i.placement_type}
                    for i in items
                ],
            }
        else:
            nkl = self.db.query(NegativeKeywordList).filter(NegativeKeywordList.id == list_id).first()
            if not nkl:
                return {"error": "List not found"}
            items = (
                self.db.query(NegativeKeywordListItem)
                .filter(NegativeKeywordListItem.list_id == list_id)
                .order_by(NegativeKeywordListItem.text)
                .all()
            )
            return {
                "id": nkl.id,
                "name": nkl.name,
                "description": nkl.description,
                "type": "keyword",
                "item_count": len(items),
                "items": [
                    {"id": i.id, "text": i.text, "match_type": i.match_type}
                    for i in items
                ],
            }

    def get_negative_keyword_lists_overview(self) -> list[dict]:
        """Return all NKL across all clients, grouped by client."""
        lists = (
            self.db.query(NegativeKeywordList)
            .join(Client, NegativeKeywordList.client_id == Client.id)
            .order_by(Client.name, NegativeKeywordList.name)
            .all()
        )

        client_ids = {nkl.client_id for nkl in lists}
        clients = {
            c.id: c.name
            for c in self.db.query(Client).filter(Client.id.in_(client_ids)).all()
        } if client_ids else {}

        item_counts = self._count_nkl_items([nkl.id for nkl in lists])

        return [
            {
                "id": nkl.id,
                "client_id": nkl.client_id,
                "client_name": clients.get(nkl.client_id, "?"),
                "name": nkl.name,
                "description": nkl.description,
                "source": nkl.source,
                "status": nkl.status,
                "member_count": item_counts.get(nkl.id, 0),
                "ownership_level": nkl.ownership_level or "account",
            }
            for nkl in lists
        ]

    def _get_manager_client_ids(self) -> set[int]:
        """Find local Client IDs that are manager (MCC) accounts."""
        from app.models import MccLink
        manager_ids = set()
        for row in self.db.query(MccLink.manager_customer_id).distinct().all():
            if row[0]:
                manager_ids.add(row[0])
        if not manager_ids:
            return set()
        result = set()
        for c in self.db.query(Client).all():
            normalized = c.google_customer_id.replace("-", "") if c.google_customer_id else ""
            if normalized in manager_ids:
                result.add(c.id)
        return result

    def _count_nkl_items(self, list_ids: list[int]) -> dict[int, int]:
        """Count NegativeKeywordListItem per list."""
        if not list_ids:
            return {}
        rows = (
            self.db.query(
                NegativeKeywordListItem.list_id,
                func.count(NegativeKeywordListItem.id),
            )
            .filter(NegativeKeywordListItem.list_id.in_(list_ids))
            .group_by(NegativeKeywordListItem.list_id)
            .all()
        )
        return {r[0]: r[1] for r in rows}

    def get_billing_status(self, customer_id: str) -> dict:
        """Try to fetch billing/payment status from Google Ads API.

        Returns payment status info or 'unknown' if API access insufficient.
        """
        try:
            from app.services.google_ads import google_ads_service

            if not google_ads_service.is_connected:
                return {"status": "unknown", "reason": "API not connected"}

            client = google_ads_service.client
            ga_service = client.get_service("GoogleAdsService")

            # Try billing_setup query
            query = """
                SELECT
                    billing_setup.id,
                    billing_setup.status,
                    billing_setup.payments_account_info.payments_account_name
                FROM billing_setup
                WHERE billing_setup.status = 'APPROVED'
                LIMIT 1
            """
            clean_id = customer_id.replace("-", "")
            response = ga_service.search(customer_id=clean_id, query=query)

            for row in response:
                return {
                    "status": "ok",
                    "billing_status": str(row.billing_setup.status.name),
                    "payments_account": row.billing_setup.payments_account_info.payments_account_name or None,
                }

            return {"status": "no_billing", "reason": "No approved billing setup found"}

        except Exception as e:
            error_msg = str(e).lower()
            if "authorization" in error_msg or "permission" in error_msg:
                return {"status": "no_access", "reason": "Billing API access not available"}
            return {"status": "unknown", "reason": str(e)[:100]}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_account_data(self, client: Client, period_start: date, period_end: date) -> dict:
        cid = client.id
        today = date.today()
        period_days = (period_end - period_start).days or 1

        # 1. Full metrics for the requested period + previous period
        metrics = self._aggregate_metrics(cid, period_start, period_end)
        prev_start = period_start - timedelta(days=period_days)
        prev_metrics = self._aggregate_metrics(cid, prev_start, period_start)

        spend = metrics["cost_usd"]
        prev_spend = prev_metrics["cost_usd"]
        conversions = metrics["conversions"]
        conv_value = metrics["conversion_value_usd"]
        clicks = metrics["clicks"]
        impressions = metrics["impressions"]

        cpa = round(spend / conversions, 2) if conversions > 0 else None
        roas = round(conv_value / spend * 100, 1) if spend > 0 and conv_value > 0 else None
        ctr = round(clicks / impressions * 100, 2) if impressions > 0 else None
        avg_cpc = round(spend / clicks, 2) if clicks > 0 else None
        conv_rate = round(conversions / clicks * 100, 2) if clicks > 0 else None
        is_pct = round(metrics["search_impression_share"] * 100, 1) if metrics.get("search_impression_share") is not None else None

        # 2. Budget pacing (aggregated per client)
        pacing = self._compute_pacing(cid, today)

        # 3. Change activity (within period)
        cutoff = datetime.combine(period_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        total_changes = (
            self.db.query(func.count(ChangeEvent.id))
            .filter(ChangeEvent.client_id == cid, ChangeEvent.change_date_time >= cutoff)
            .scalar()
        ) or 0

        specialist = _specialist_emails()
        external_q = self.db.query(func.count(ChangeEvent.id)).filter(
            ChangeEvent.client_id == cid,
            ChangeEvent.change_date_time >= cutoff,
        )
        if specialist:
            external_q = external_q.filter(
                ~ChangeEvent.user_email.in_(specialist),
                ChangeEvent.client_type != "GOOGLE_ADS_API",
            )
        else:
            external_q = external_q.filter(ChangeEvent.client_type != "GOOGLE_ADS_API")
        external_changes = external_q.scalar() or 0

        # Change type breakdown
        change_types = dict(
            self.db.query(ChangeEvent.resource_change_operation, func.count(ChangeEvent.id))
            .filter(ChangeEvent.client_id == cid, ChangeEvent.change_date_time >= cutoff)
            .group_by(ChangeEvent.resource_change_operation)
            .all()
        )

        # 4. Google recommendations pending
        google_recs_pending = (
            self.db.query(func.count(Recommendation.id))
            .filter(
                Recommendation.client_id == cid,
                Recommendation.source == "GOOGLE_ADS_API",
                Recommendation.status == "pending",
            )
            .scalar()
        ) or 0

        # 5. Last sync
        last_sync = (
            self.db.query(func.max(SyncLog.finished_at))
            .filter(
                SyncLog.client_id == cid,
                SyncLog.status.in_(["success", "partial"]),
            )
            .scalar()
        )

        # 6. Unresolved alerts with details
        alerts = (
            self.db.query(Alert.title, Alert.severity, Alert.alert_type)
            .filter(Alert.client_id == cid, Alert.resolved_at.is_(None))
            .order_by(Alert.created_at.desc())
            .limit(5)
            .all()
        )
        alert_details = [
            {"title": a.title, "severity": a.severity, "type": a.alert_type}
            for a in alerts
        ]

        # 7. New access detection
        new_access = self.detect_new_access(cid, days=30)

        # 8. Health score
        health = self._get_health_score(cid)

        # 9. Daily spend trend (for sparkline)
        spend_trend = self._get_daily_spend_trend(cid, period_start, period_end)

        return {
            "client_id": cid,
            "client_name": client.name,
            "google_customer_id": client.google_customer_id,
            "currency": client.currency or "PLN",
            # Full metrics
            "clicks": clicks,
            "impressions": impressions,
            "ctr_pct": ctr,
            "avg_cpc": avg_cpc,
            "spend": round(spend, 2),
            "spend_prev": round(prev_spend, 2),
            "spend_change_pct": (
                round((spend - prev_spend) / prev_spend * 100, 1)
                if prev_spend > 0
                else None
            ),
            "conversions": round(conversions, 1),
            "conversion_rate_pct": conv_rate,
            "conversion_value": round(conv_value, 2),
            "cpa": cpa,
            "roas_pct": roas,
            "search_impression_share_pct": is_pct,
            # Pacing
            "pacing": pacing,
            # Activity
            "total_changes": total_changes,
            "external_changes": external_changes,
            "change_breakdown": change_types,
            "new_access_emails": new_access,
            # Recs & alerts
            "google_recs_pending": google_recs_pending,
            "unresolved_alerts": len(alert_details),
            "alert_details": alert_details,
            # Sync
            "last_synced_at": last_sync,
            # Health
            "health_score": health.get("score") if health else None,
            # Spend trend (for sparkline)
            "spend_trend": spend_trend,
        }

    def _aggregate_metrics(self, client_id: int, start: date, end: date) -> dict:
        """Aggregate all key metrics for a client over a date range."""
        row = (
            self._campaign_metrics_query(client_id, start, end)
            .with_entities(
                func.sum(MetricDaily.clicks),
                func.sum(MetricDaily.impressions),
                func.sum(MetricDaily.cost_micros),
                func.sum(MetricDaily.conversions),
                func.sum(MetricDaily.conversion_value_micros),
                func.avg(MetricDaily.search_impression_share),
            )
            .first()
        )
        clicks = int(row[0] or 0)
        impressions = int(row[1] or 0)
        cost_micros = int(row[2] or 0)
        conversions = float(row[3] or 0)
        conv_value_micros = int(row[4] or 0)
        avg_is = round(float(row[5]), 4) if row[5] is not None else None

        return {
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": micros_to_currency(cost_micros),
            "conversions": conversions,
            "conversion_value_usd": micros_to_currency(conv_value_micros),
            "search_impression_share": avg_is,
        }

    def _campaign_metrics_query(self, client_id: int, start: date, end: date):
        return (
            self.db.query(MetricDaily)
            .join(Campaign, MetricDaily.campaign_id == Campaign.id)
            .filter(
                Campaign.client_id == client_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
        )

    def _compute_pacing(self, client_id: int, today: date) -> dict:
        month_start = today.replace(day=1)
        days_elapsed = (today - month_start).days + 1
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        pacing_ratio = days_elapsed / days_in_month

        campaigns = (
            self.db.query(Campaign)
            .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
            .all()
        )

        if not campaigns:
            return {"status": "no_data", "pacing_pct": 0, "budget": 0, "spent": 0,
                    "month_progress_pct": round(days_elapsed / days_in_month * 100, 1),
                    "days_elapsed": days_elapsed, "days_in_month": days_in_month}

        total_monthly_budget = sum(
            micros_to_currency(c.budget_micros or 0) * days_in_month for c in campaigns
        )

        campaign_ids = [c.id for c in campaigns]
        actual_spend_micros = (
            self.db.query(func.sum(MetricDaily.cost_micros))
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= month_start,
                MetricDaily.date <= today,
            )
            .scalar()
        ) or 0
        actual_spend = micros_to_currency(actual_spend_micros)

        expected = total_monthly_budget * pacing_ratio
        if expected == 0:
            status = "no_data"
            pct = 0
        else:
            pct = actual_spend / expected
            if pct < 0.75:
                status = "underspend"
            elif pct > 1.20:
                status = "overspend"
            else:
                status = "on_track"

        month_progress_pct = round(days_elapsed / days_in_month * 100, 1)

        return {
            "status": status,
            "pacing_pct": round(pct * 100, 1),
            "budget": round(total_monthly_budget, 2),
            "spent": round(actual_spend, 2),
            "month_progress_pct": month_progress_pct,
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        }

    def _get_health_score(self, client_id: int) -> dict | None:
        try:
            svc = AnalyticsService(self.db)
            result = svc.get_health_score(client_id, days=30)
            breakdown = result.get("breakdown", {})
            return {
                "score": result.get("score"),
                "pillars": {
                    k: v.get("score") for k, v in breakdown.items()
                } if breakdown else {},
            }
        except Exception:
            return None

    def _get_daily_spend_trend(self, client_id: int, start: date, end: date) -> list[dict]:
        """Daily spend breakdown for sparkline chart."""
        rows = (
            self._campaign_metrics_query(client_id, start, end)
            .with_entities(MetricDaily.date, func.sum(MetricDaily.cost_micros))
            .group_by(MetricDaily.date)
            .order_by(MetricDaily.date)
            .all()
        )
        return [
            {"date": str(r[0]), "spend": micros_to_currency(int(r[1] or 0))}
            for r in rows
        ]
