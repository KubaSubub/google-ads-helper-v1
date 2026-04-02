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

    def get_overview(self) -> dict:
        clients = self.db.query(Client).all()
        accounts = []
        for client in clients:
            accounts.append(self._build_account_data(client))
        return {
            "synced_at": datetime.now(timezone.utc).isoformat(),
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

    def get_mcc_shared_lists(self) -> list[dict]:
        """Return MCC-level shared negative keyword lists (queried from manager account).

        MCC-level lists are stored with client_id=0 convention, or sourced from
        the manager account via sync_mcc_shared_sets(). Falls back to showing
        all GOOGLE_ADS_SYNC lists if no MCC-specific lists exist.
        """
        from app.models import MccLink

        # Find manager customer ID from config or MCC links
        manager_ids = set()
        mcc_links = self.db.query(MccLink.manager_customer_id).distinct().all()
        for row in mcc_links:
            if row[0]:
                manager_ids.add(row[0])

        # MCC-level lists: look for lists where source indicates they came from
        # manager account sync, or client_id matches a manager account
        manager_client_ids = set()
        if manager_ids:
            # Normalize: MccLink stores without dashes, Client may have dashes
            all_clients = self.db.query(Client).all()
            for mc in all_clients:
                normalized = mc.google_customer_id.replace("-", "") if mc.google_customer_id else ""
                if normalized in manager_ids:
                    manager_client_ids.add(mc.id)

        # Query: MCC-level lists (from manager clients) + fallback to all synced lists
        if manager_client_ids:
            lists = (
                self.db.query(NegativeKeywordList)
                .filter(NegativeKeywordList.client_id.in_(manager_client_ids))
                .order_by(NegativeKeywordList.name)
                .all()
            )
        else:
            # Fallback: show all Google-synced lists across all accounts
            lists = (
                self.db.query(NegativeKeywordList)
                .filter(NegativeKeywordList.source == "GOOGLE_ADS_SYNC")
                .order_by(NegativeKeywordList.name)
                .all()
            )

        # Count items per list
        item_counts = {}
        if lists:
            list_ids = [nkl.id for nkl in lists]
            rows = (
                self.db.query(
                    NegativeKeywordListItem.list_id,
                    func.count(NegativeKeywordListItem.id),
                )
                .filter(NegativeKeywordListItem.list_id.in_(list_ids))
                .group_by(NegativeKeywordListItem.list_id)
                .all()
            )
            item_counts = {r[0]: r[1] for r in rows}

        # Client name lookup
        client_ids = {nkl.client_id for nkl in lists}
        clients = {
            c.id: c.name
            for c in self.db.query(Client).filter(Client.id.in_(client_ids)).all()
        } if client_ids else {}

        return [
            {
                "id": nkl.id,
                "client_id": nkl.client_id,
                "client_name": clients.get(nkl.client_id, "MCC"),
                "name": nkl.name,
                "description": nkl.description,
                "source": nkl.source,
                "status": nkl.status,
                "member_count": item_counts.get(nkl.id, 0),
                "level": "mcc" if nkl.client_id in manager_client_ids else "account",
            }
            for nkl in lists
        ]

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

        item_counts = {}
        if lists:
            list_ids = [nkl.id for nkl in lists]
            rows = (
                self.db.query(
                    NegativeKeywordListItem.list_id,
                    func.count(NegativeKeywordListItem.id),
                )
                .filter(NegativeKeywordListItem.list_id.in_(list_ids))
                .group_by(NegativeKeywordListItem.list_id)
                .all()
            )
            item_counts = {r[0]: r[1] for r in rows}

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
            }
            for nkl in lists
        ]

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

    def _build_account_data(self, client: Client) -> dict:
        cid = client.id
        today = date.today()

        # 1. Full metrics 30d
        start_30d = today - timedelta(days=30)
        start_60d = today - timedelta(days=60)
        metrics = self._aggregate_metrics(cid, start_30d, today)
        prev_metrics = self._aggregate_metrics(cid, start_60d, start_30d)

        spend = metrics["cost_usd"]
        prev_spend = prev_metrics["cost_usd"]
        conversions = metrics["conversions"]
        conv_value = metrics["conversion_value_usd"]
        clicks = metrics["clicks"]
        impressions = metrics["impressions"]

        cpa = round(spend / conversions, 2) if conversions > 0 else None
        roas = round(conv_value / spend * 100, 1) if spend > 0 else None
        ctr = round(clicks / impressions * 100, 2) if impressions > 0 else None
        avg_cpc = round(spend / clicks, 2) if clicks > 0 else None
        conv_rate = round(conversions / clicks * 100, 2) if clicks > 0 else None

        # 2. Budget pacing (aggregated per client)
        pacing = self._compute_pacing(cid, today)

        # 3. Health score (with breakdown)
        health = self._get_health_score(cid)

        # 4. Change activity (30d)
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
        total_changes = (
            self.db.query(func.count(ChangeEvent.id))
            .filter(ChangeEvent.client_id == cid, ChangeEvent.change_date_time >= cutoff_30d)
            .scalar()
        ) or 0

        specialist = _specialist_emails()
        external_q = self.db.query(func.count(ChangeEvent.id)).filter(
            ChangeEvent.client_id == cid,
            ChangeEvent.change_date_time >= cutoff_30d,
        )
        if specialist:
            external_q = external_q.filter(
                ~ChangeEvent.user_email.in_(specialist),
                ChangeEvent.client_type != "GOOGLE_ADS_API",
            )
        else:
            external_q = external_q.filter(ChangeEvent.client_type != "GOOGLE_ADS_API")
        external_changes = external_q.scalar() or 0

        # 5. Google recommendations pending
        google_recs_pending = (
            self.db.query(func.count(Recommendation.id))
            .filter(
                Recommendation.client_id == cid,
                Recommendation.source == "GOOGLE_ADS_API",
                Recommendation.status == "pending",
            )
            .scalar()
        ) or 0

        # 6. Last sync
        last_sync = (
            self.db.query(func.max(SyncLog.finished_at))
            .filter(
                SyncLog.client_id == cid,
                SyncLog.status.in_(["success", "partial"]),
            )
            .scalar()
        )

        # 7. Unresolved alerts
        unresolved_alerts = (
            self.db.query(func.count(Alert.id))
            .filter(Alert.client_id == cid, Alert.resolved_at.is_(None))
            .scalar()
        ) or 0

        # 8. New access detection
        new_access = self.detect_new_access(cid, days=30)

        return {
            "client_id": cid,
            "client_name": client.name,
            "google_customer_id": client.google_customer_id,
            # Full metrics
            "clicks_30d": clicks,
            "impressions_30d": impressions,
            "ctr_pct": ctr,
            "avg_cpc_usd": avg_cpc,
            "spend_30d_usd": round(spend, 2),
            "spend_prev_30d_usd": round(prev_spend, 2),
            "spend_change_pct": (
                round((spend - prev_spend) / prev_spend * 100, 1)
                if prev_spend > 0
                else None
            ),
            "conversions_30d": round(conversions, 1),
            "conversion_rate_pct": conv_rate,
            "conversion_value_usd": round(conv_value, 2),
            "cpa_usd": cpa,
            "roas_pct": roas,
            # Pacing & health
            "pacing": pacing,
            "health": health,
            # Activity
            "total_changes_30d": total_changes,
            "external_changes_30d": external_changes,
            "new_access_emails": new_access,
            # Recs & alerts
            "google_recs_pending": google_recs_pending,
            "unresolved_alerts": unresolved_alerts,
            # Sync
            "last_synced_at": last_sync,
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
            )
            .first()
        )
        clicks = int(row[0] or 0)
        impressions = int(row[1] or 0)
        cost_micros = int(row[2] or 0)
        conversions = float(row[3] or 0)
        conv_value_micros = int(row[4] or 0)

        return {
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": micros_to_currency(cost_micros),
            "conversions": conversions,
            "conversion_value_usd": micros_to_currency(conv_value_micros),
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
            return {"status": "no_data", "pacing_pct": 0, "budget_usd": 0, "spent_usd": 0}

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

        return {
            "status": status,
            "pacing_pct": round(pct * 100, 1),
            "budget_usd": round(total_monthly_budget, 2),
            "spent_usd": round(actual_spend, 2),
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
