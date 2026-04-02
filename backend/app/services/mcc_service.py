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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_account_data(self, client: Client) -> dict:
        cid = client.id
        today = date.today()

        # 1. Spend + conversions 30d
        start_30d = today - timedelta(days=30)
        start_60d = today - timedelta(days=60)
        spend_30d = self._sum_spend(cid, start_30d, today)
        spend_prev_30d = self._sum_spend(cid, start_60d, start_30d)
        conversions_30d = self._sum_conversions(cid, start_30d, today)
        conv_value_30d = self._sum_conv_value(cid, start_30d, today)
        cpa = round(spend_30d / conversions_30d, 2) if conversions_30d > 0 else None
        roas = round(conv_value_30d / spend_30d * 100, 1) if spend_30d > 0 else None

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

        return {
            "client_id": cid,
            "client_name": client.name,
            "google_customer_id": client.google_customer_id,
            "spend_30d_usd": round(spend_30d, 2),
            "spend_prev_30d_usd": round(spend_prev_30d, 2),
            "spend_change_pct": (
                round((spend_30d - spend_prev_30d) / spend_prev_30d * 100, 1)
                if spend_prev_30d > 0
                else None
            ),
            "conversions_30d": round(conversions_30d, 1),
            "cpa_usd": cpa,
            "roas_pct": roas,
            "pacing": pacing,
            "health": health,
            "total_changes_30d": total_changes,
            "external_changes_30d": external_changes,
            "google_recs_pending": google_recs_pending,
            "unresolved_alerts": unresolved_alerts,
            "last_synced_at": last_sync,
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

    def _sum_spend(self, client_id: int, start: date, end: date) -> float:
        total = (
            self._campaign_metrics_query(client_id, start, end)
            .with_entities(func.sum(MetricDaily.cost_micros))
            .scalar()
        ) or 0
        return micros_to_currency(total)

    def _sum_conversions(self, client_id: int, start: date, end: date) -> float:
        total = (
            self._campaign_metrics_query(client_id, start, end)
            .with_entities(func.sum(MetricDaily.conversions))
            .scalar()
        ) or 0
        return float(total)

    def _sum_conv_value(self, client_id: int, start: date, end: date) -> float:
        total = (
            self._campaign_metrics_query(client_id, start, end)
            .with_entities(func.sum(MetricDaily.conversion_value_micros))
            .scalar()
        ) or 0
        return micros_to_currency(total)

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

    def get_negative_keyword_lists_overview(self) -> list[dict]:
        """Return all NKL across all clients, grouped by client."""
        lists = (
            self.db.query(NegativeKeywordList)
            .join(Client, NegativeKeywordList.client_id == Client.id)
            .order_by(Client.name, NegativeKeywordList.name)
            .all()
        )

        # Build client name lookup
        client_ids = {nkl.client_id for nkl in lists}
        clients = {
            c.id: c.name
            for c in self.db.query(Client).filter(Client.id.in_(client_ids)).all()
        } if client_ids else {}

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
