"""Daily Audit endpoint - aggregates all morning PPC checks into one view."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Ad,
    AdGroup,
    Alert,
    Campaign,
    Keyword,
    MetricDaily,
    Recommendation,
    SearchTerm,
)
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency

router = APIRouter(prefix="/daily-audit", tags=["Daily Audit"])


# ---------------------------------------------------------------------------
# Helper: priority sort key for recommendations
# ---------------------------------------------------------------------------

_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ---------------------------------------------------------------------------
# GET /daily-audit/  -  single aggregated morning audit
# ---------------------------------------------------------------------------


@router.get("/")
def daily_audit(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Aggregate all daily audit checks into a single response.

    Returns budget pacing, anomalies, disapproved ads, budget-capped
    high-performers, wasteful search terms, pending recommendations,
    health summary, and today-vs-yesterday KPI snapshot.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    twenty_four_hours_ago = now_utc - timedelta(hours=24)
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)

    # Pre-fetch enabled campaigns for this client (used by several sections).
    enabled_campaigns = (
        db.query(Campaign)
        .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
        .all()
    )
    enabled_campaign_ids = [c.id for c in enabled_campaigns]

    # All campaigns for the client (any status).
    all_campaigns = (
        db.query(Campaign).filter(Campaign.client_id == client_id).all()
    )
    campaign_lookup = {c.id: c.name for c in all_campaigns}

    # ------------------------------------------------------------------
    # 1. budget_pacing
    # ------------------------------------------------------------------
    budget_pacing = _build_budget_pacing(db, enabled_campaigns, today)

    # ------------------------------------------------------------------
    # 2. anomalies_24h
    # ------------------------------------------------------------------
    anomalies_24h = _build_anomalies_24h(db, client_id, twenty_four_hours_ago, campaign_lookup)

    # ------------------------------------------------------------------
    # 3. disapproved_ads
    # ------------------------------------------------------------------
    disapproved_ads = _build_disapproved_ads(db, client_id)

    # ------------------------------------------------------------------
    # 4. budget_capped_performers
    # ------------------------------------------------------------------
    budget_capped_performers = _build_budget_capped_performers(
        db, enabled_campaigns, enabled_campaign_ids, thirty_days_ago, today,
    )

    # ------------------------------------------------------------------
    # 5. search_terms_needing_action
    # ------------------------------------------------------------------
    search_terms_needing_action = _build_search_terms_needing_action(
        db, client_id, seven_days_ago, today, campaign_lookup,
    )

    # ------------------------------------------------------------------
    # 6. pending_recommendations
    # ------------------------------------------------------------------
    pending_recommendations = _build_pending_recommendations(db, client_id)

    # ------------------------------------------------------------------
    # 7. health_summary
    # ------------------------------------------------------------------
    health_summary = _build_health_summary(db, client_id, enabled_campaign_ids)

    # ------------------------------------------------------------------
    # 8. kpi_snapshot
    # ------------------------------------------------------------------
    kpi_snapshot = _build_kpi_snapshot(db, enabled_campaign_ids, today, yesterday)

    return {
        "client_id": client_id,
        "audit_date": str(today),
        "budget_pacing": budget_pacing,
        "anomalies_24h": anomalies_24h,
        "disapproved_ads": disapproved_ads,
        "budget_capped_performers": budget_capped_performers,
        "search_terms_needing_action": search_terms_needing_action,
        "pending_recommendations": pending_recommendations,
        "health_summary": health_summary,
        "kpi_snapshot": kpi_snapshot,
    }


# ======================================================================
# Section builders
# ======================================================================


def _build_budget_pacing(
    db: Session,
    enabled_campaigns: list[Campaign],
    today: date,
) -> list[dict]:
    """Budget status for every enabled campaign."""
    results: list[dict] = []

    for camp in enabled_campaigns:
        daily_budget = micros_to_currency(camp.budget_micros)

        # Today's spend estimate from MetricDaily.
        spent_today_micros = (
            db.query(func.sum(MetricDaily.cost_micros))
            .filter(
                MetricDaily.campaign_id == camp.id,
                MetricDaily.date == today,
            )
            .scalar()
        ) or 0
        spent_today = micros_to_currency(spent_today_micros)

        pacing_pct = round((spent_today / daily_budget * 100), 1) if daily_budget > 0 else 0.0

        # Budget-limited flag based on IS lost to budget.
        is_limited = bool(
            (camp.search_budget_lost_is or 0) > 0
            or (camp.search_budget_lost_top_is or 0) > 0
            or (camp.search_budget_lost_abs_top_is or 0) > 0
        )

        results.append({
            "campaign_id": camp.id,
            "campaign_name": camp.name,
            "daily_budget": round(daily_budget, 2),
            "spent_today": round(spent_today, 2),
            "pacing_pct": pacing_pct,
            "is_limited": is_limited,
        })

    return results


def _build_anomalies_24h(
    db: Session,
    client_id: int,
    since: datetime,
    campaign_lookup: dict[int, str],
) -> list[dict]:
    """Unresolved alerts created in the last 24 hours."""
    alerts = (
        db.query(Alert)
        .filter(
            Alert.client_id == client_id,
            Alert.resolved_at.is_(None),
            Alert.created_at >= since,
        )
        .order_by(Alert.created_at.desc())
        .all()
    )
    return [
        {
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.description or a.title,
            "campaign_name": campaign_lookup.get(a.campaign_id, "Unknown") if a.campaign_id else None,
            "created_at": str(a.created_at) if a.created_at else None,
        }
        for a in alerts
    ]


def _build_disapproved_ads(db: Session, client_id: int) -> list[dict]:
    """Ads with DISAPPROVED or APPROVED_LIMITED approval status."""
    rows = (
        db.query(Ad, AdGroup, Campaign)
        .join(AdGroup, Ad.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Ad.approval_status.in_(["DISAPPROVED", "APPROVED_LIMITED"]),
        )
        .all()
    )
    return [
        {
            "ad_id": ad.id,
            "headline_1": ad.headline_1,
            "status": ad.status,
            "approval_status": ad.approval_status,
            "campaign_name": campaign.name,
            "ad_group_name": ad_group.name,
        }
        for ad, ad_group, campaign in rows
    ]


def _build_budget_capped_performers(
    db: Session,
    enabled_campaigns: list[Campaign],
    enabled_campaign_ids: list[int],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Campaigns with budget constraints but below-average CPA."""
    if not enabled_campaign_ids:
        return []

    # Aggregate cost + conversions per campaign over last 30 days.
    campaign_metrics = (
        db.query(
            MetricDaily.campaign_id,
            func.sum(MetricDaily.cost_micros).label("total_cost_micros"),
            func.sum(MetricDaily.conversions).label("total_conversions"),
        )
        .filter(
            MetricDaily.campaign_id.in_(enabled_campaign_ids),
            MetricDaily.date >= start_date,
            MetricDaily.date <= end_date,
        )
        .group_by(MetricDaily.campaign_id)
        .all()
    )

    # Compute per-campaign CPA.
    cpa_by_campaign: dict[int, float] = {}
    total_cost_all = 0
    total_conv_all = 0.0
    for row in campaign_metrics:
        cost = row.total_cost_micros or 0
        conv = row.total_conversions or 0.0
        total_cost_all += cost
        total_conv_all += conv
        if conv > 0:
            cpa_by_campaign[row.campaign_id] = micros_to_currency(cost) / conv

    account_avg_cpa = (
        micros_to_currency(total_cost_all) / total_conv_all
        if total_conv_all > 0
        else 0.0
    )

    # Build lookup for campaign objects.
    camp_map = {c.id: c for c in enabled_campaigns}

    results: list[dict] = []
    for cid, cpa in cpa_by_campaign.items():
        camp = camp_map.get(cid)
        if camp is None:
            continue

        has_budget_constraint = bool(
            (camp.search_budget_lost_is or 0) > 0
            or (camp.search_budget_lost_top_is or 0) > 0
            or (camp.search_budget_lost_abs_top_is or 0) > 0
        )
        if not has_budget_constraint:
            continue
        if cpa >= account_avg_cpa:
            continue

        results.append({
            "campaign_id": cid,
            "campaign_name": camp.name,
            "cpa_usd": round(cpa, 2),
            "account_avg_cpa_usd": round(account_avg_cpa, 2),
            "budget_lost_is_pct": round((camp.search_budget_lost_is or 0) * 100, 1),
            "daily_budget_usd": round(micros_to_currency(camp.budget_micros), 2),
        })

    # Sort by biggest gap (lowest CPA relative to average first).
    results.sort(key=lambda r: r["cpa_usd"])
    return results


def _build_search_terms_needing_action(
    db: Session,
    client_id: int,
    start_date: date,
    end_date: date,
    campaign_lookup: dict[int, str],
) -> list[dict]:
    """Search terms with wasted spend in the last 7 days (top 50 by cost)."""
    query = (
        db.query(SearchTerm)
        .join(Campaign, SearchTerm.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            SearchTerm.date_from >= start_date,
            SearchTerm.date_to <= end_date,
        )
        .filter(
            # Clicks >= 3 with zero conversions, OR cost > $5 with zero conversions.
            (
                (SearchTerm.clicks >= 3) & (SearchTerm.conversions == 0)
            )
            | (
                (SearchTerm.cost_micros > 5_000_000) & (SearchTerm.conversions == 0)
            )
        )
        .order_by(SearchTerm.cost_micros.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "term": st.text,
            "clicks": st.clicks or 0,
            "cost_usd": round(micros_to_currency(st.cost_micros), 2),
            "impressions": st.impressions or 0,
            "campaign_name": campaign_lookup.get(st.campaign_id, "Unknown") if st.campaign_id else "Unknown",
        }
        for st in query
    ]


def _build_pending_recommendations(db: Session, client_id: int) -> dict:
    """Count of pending recommendations plus top 5 by priority."""
    pending = (
        db.query(Recommendation)
        .filter(
            Recommendation.client_id == client_id,
            Recommendation.status == "pending",
        )
        .all()
    )
    total = len(pending)

    # Sort: HIGH first, then MEDIUM, then LOW.
    pending.sort(key=lambda r: _PRIORITY_ORDER.get(r.priority, 99))
    top_5 = pending[:5]

    items = []
    for rec in top_5:
        evidence = rec.evidence_json or {}
        items.append({
            "id": rec.id,
            "type": rec.rule_id,
            "priority": rec.priority,
            "reason": rec.reason,
            "campaign_name": evidence.get("campaign_name"),
            "keyword_text": evidence.get("keyword_text"),
        })

    return {
        "total_pending": total,
        "top_5": items,
    }


def _build_health_summary(
    db: Session,
    client_id: int,
    enabled_campaign_ids: list[int],
) -> dict:
    """Health score plus active campaign/keyword counts."""
    service = AnalyticsService(db)
    health = service.get_health_score(client_id)

    total_enabled_keywords = (
        db.query(func.count(Keyword.id))
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Keyword.status == "ENABLED",
        )
        .scalar()
    ) or 0

    return {
        "health_score": health.get("score", 0),
        "health_issues": health.get("issues", []),
        "total_active_campaigns": len(enabled_campaign_ids),
        "total_enabled_keywords": total_enabled_keywords,
    }


def _build_kpi_snapshot(
    db: Session,
    campaign_ids: list[int],
    today: date,
    yesterday: date,
) -> dict:
    """Today vs yesterday aggregated spend, clicks, conversions."""
    if not campaign_ids:
        return {
            "today_spend": 0.0,
            "yesterday_spend": 0.0,
            "today_clicks": 0,
            "yesterday_clicks": 0,
            "today_conversions": 0.0,
            "yesterday_conversions": 0.0,
        }

    def _agg(target_date: date) -> dict:
        row = (
            db.query(
                func.sum(MetricDaily.cost_micros).label("cost"),
                func.sum(MetricDaily.clicks).label("clicks"),
                func.sum(MetricDaily.conversions).label("conversions"),
            )
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date == target_date,
            )
            .first()
        )
        return {
            "spend": round(micros_to_currency(row.cost or 0), 2) if row else 0.0,
            "clicks": int(row.clicks or 0) if row else 0,
            "conversions": round(float(row.conversions or 0), 2) if row else 0.0,
        }

    t = _agg(today)
    y = _agg(yesterday)

    return {
        "today_spend": t["spend"],
        "yesterday_spend": y["spend"],
        "today_clicks": t["clicks"],
        "yesterday_clicks": y["clicks"],
        "today_conversions": t["conversions"],
        "yesterday_conversions": y["conversions"],
    }
