"""Analytics endpoints — KPIs, anomaly detection, correlation, forecasting."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime, timezone

try:
    import numpy as np
    import pandas as pd
    from scipy.stats import ttest_ind
except ImportError as _import_err:
    raise ImportError(
        "Analytics router requires numpy, pandas, and scipy. "
        "Install them with: pip install numpy pandas scipy"
    ) from _import_err

from app.demo_guard import ensure_demo_write_allowed
from app.database import get_db
from app.dependencies import CommonFilters, common_filters
from app.models import MetricDaily, Campaign, Client, Keyword, KeywordDaily, AdGroup, Alert, MetricSegmented
from app.schemas import PeriodComparisonRequest, PeriodComparisonResponse, CorrelationRequest
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency
from app.utils.date_utils import resolve_dates

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Unified metric names shared across /trends, /correlation, /wow-comparison.
# Frontend TrendExplorer uses these exact keys.
TREND_METRICS = {
    "cost", "clicks", "impressions", "conversions", "conversion_value",
    "ctr", "cpc", "cpa", "cvr", "roas",
    "search_impression_share", "search_top_impression_share", "search_abs_top_impression_share",
    "search_budget_lost_is", "search_rank_lost_is", "search_click_share",
    "abs_top_impression_pct", "top_impression_pct",
}
# Backward-compat aliases accepted by /correlation for clients sending legacy names.
CORRELATION_LEGACY_ALIASES = {
    "cost_micros": "cost",
    "avg_cpc_micros": "cpc",
    "conversion_rate": "cvr",
}
# Raw MetricDaily column names used by /compare-periods and /forecast (getattr-based).
# These are actual SQLAlchemy columns — do not mix with TREND_METRICS.
LEGACY_COLUMN_METRICS = {
    "clicks", "impressions", "ctr", "conversions", "conversion_rate",
    "cost_micros", "roas", "avg_cpc_micros",
}
VALID_METRICS = TREND_METRICS  # /correlation uses this set
FORECAST_METRIC_ALIASES = {
    "cost": "cost_micros",
    "cpc": "avg_cpc_micros",
}
FORECAST_MICROS_METRICS = {"cost_micros", "avg_cpc_micros"}


# ---------------------------------------------------------------------------
# KPIs & Anomaly Detection — delegated to AnalyticsService
# ---------------------------------------------------------------------------


@router.get("/kpis")
def get_kpis(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Aggregate KPIs across all campaigns for a client."""
    service = AnalyticsService(db)
    return service.get_kpis(client_id)


@router.get("/anomalies")
def get_anomalies(
    client_id: int = Query(..., description="Client ID"),
    status: str = Query("unresolved", description="Filter: unresolved or resolved"),
    db: Session = Depends(get_db),
):
    """List anomaly detection alerts for a client."""
    query = db.query(Alert).filter(Alert.client_id == client_id)

    if status == "unresolved":
        query = query.filter(Alert.resolved_at.is_(None))
    elif status == "resolved":
        query = query.filter(Alert.resolved_at.isnot(None))

    alerts = query.order_by(Alert.created_at.desc()).all()

    return {
        "total": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "campaign_id": a.campaign_id,
                "campaign_name": a.campaign.name if a.campaign else None,
                "metric_value": a.metric_value,
                "resolved_at": str(a.resolved_at) if a.resolved_at else None,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in alerts
        ],
    }


@router.post("/anomalies/{alert_id}/resolve")
def resolve_anomaly(
    alert_id: int,
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Mark an anomaly alert as resolved."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Rozwiazywanie alertu",
    )

    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.client_id == client_id,
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.resolved_at:
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return {"status": "success", "message": f"Alert {alert_id} resolved"}


@router.post("/detect")
def run_anomaly_detection(
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Run anomaly detection rules and create alerts."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Wykrywanie anomalii",
    )
    service = AnalyticsService(db)
    alerts = service.detect_anomalies(client_id)
    return {
        "status": "success",
        "alerts_created": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
            }
            for a in alerts
        ],
    }


@router.get("/z-score-anomalies")
def get_zscore_anomalies(
    client_id: int = Query(..., description="Client ID"),
    metric: str = Query("cost", description="Metric to analyze: cost, clicks, impressions, conversions, ctr"),
    threshold: float = Query(2.0, description="Z-score threshold"),
    days: int = Query(90, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Detect z-score anomalies per campaign per day for a given metric."""
    from collections import defaultdict
    import math

    campaign_ids = [c.id for c in db.query(Campaign.id).filter(
        Campaign.client_id == client_id, Campaign.status == "ENABLED"
    ).all()]

    if not campaign_ids:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": 0}

    cutoff = date.today() - timedelta(days=days)
    rows = db.query(MetricDaily).filter(
        MetricDaily.campaign_id.in_(campaign_ids),
        MetricDaily.date >= cutoff,
    ).all()

    if not rows:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": 0}

    # Build campaign name map
    camp_names = {c.id: c.name for c in db.query(Campaign.id, Campaign.name).filter(
        Campaign.id.in_(campaign_ids)
    ).all()}

    # Aggregate by date
    day_agg = defaultdict(lambda: {"clicks": 0, "impressions": 0, "cost": 0.0,
                                    "conversions": 0.0, "campaigns": set()})
    for r in rows:
        d = day_agg[r.date]
        d["clicks"] += r.clicks or 0
        d["impressions"] += r.impressions or 0
        d["cost"] += (r.cost_micros or 0) / 1_000_000
        d["conversions"] += r.conversions or 0
        d["campaigns"].add(r.campaign_id)

    # Extract metric values per day
    metric_map = {
        "cost": lambda d: d["cost"],
        "clicks": lambda d: float(d["clicks"]),
        "impressions": lambda d: float(d["impressions"]),
        "conversions": lambda d: d["conversions"],
        "ctr": lambda d: d["clicks"] / d["impressions"] if d["impressions"] > 0 else 0,
    }
    extract = metric_map.get(metric, metric_map["cost"])

    daily_values = []
    for dt in sorted(day_agg.keys()):
        val = extract(day_agg[dt])
        daily_values.append((dt, val))

    if len(daily_values) < 7:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": len(daily_values)}

    values = [v for _, v in daily_values]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0

    anomalies = []
    if std > 0:
        for dt, val in daily_values:
            z = (val - mean) / std
            if abs(z) >= threshold:
                # Find which campaign contributed most on this anomaly day
                camp_rows = [r for r in rows if r.date == dt]
                top_camp_id = None
                top_val = 0
                for cr in camp_rows:
                    cv = extract({
                        "clicks": cr.clicks or 0,
                        "impressions": cr.impressions or 0,
                        "cost": (cr.cost_micros or 0) / 1_000_000,
                        "conversions": cr.conversions or 0,
                    })
                    if cv > top_val:
                        top_val = cv
                        top_camp_id = cr.campaign_id

                anomalies.append({
                    "date": str(dt),
                    "value": round(val, 2),
                    "z_score": round(z, 2),
                    "direction": "spike" if z > 0 else "drop",
                    "campaign_id": top_camp_id,
                    "campaign_name": camp_names.get(top_camp_id, "?"),
                })

    anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)

    return {
        "anomalies": anomalies,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "total_days": len(daily_values),
        "metric": metric,
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# Advanced Analytics (correlation, period comparison, forecast)
# ---------------------------------------------------------------------------


@router.post("/correlation")
def correlation_matrix(data: CorrelationRequest, db: Session = Depends(get_db)):
    """Calculate Pearson correlation matrix between selected metrics.

    Aggregates MetricDaily per day first (same as /trends), then computes
    correlation on the daily aggregates. This avoids mixing campaign-level
    rows which would distort the time-series correlation.

    Accepts unified metric names (cost, cpc, cpa, cvr, roas, search_impression_share, ...).
    Legacy names (cost_micros, avg_cpc_micros, conversion_rate) are auto-aliased for
    backward compatibility with older clients.
    """
    # Normalize legacy names to unified ones
    requested = [CORRELATION_LEGACY_ALIASES.get(m, m) for m in data.metrics]
    invalid = set(requested) - TREND_METRICS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid metrics: {invalid}")

    query = db.query(MetricDaily)
    if data.campaign_ids:
        query = query.filter(MetricDaily.campaign_id.in_(data.campaign_ids))
    if data.date_from:
        query = query.filter(MetricDaily.date >= data.date_from)
    if data.date_to:
        query = query.filter(MetricDaily.date <= data.date_to)

    rows = query.all()
    if len(rows) < 3:
        raise HTTPException(status_code=400, detail="Not enough data points for correlation (need at least 3)")

    # Aggregate per day with weighted share accumulators
    from collections import defaultdict
    def _fresh():
        return {
            "clicks": 0, "impressions": 0, "cost_micros": 0,
            "conversions": 0.0, "conv_value_micros": 0,
            # numerators for impression-weighted shares
            "_sis_num": 0.0, "_stis_num": 0.0, "_satis_num": 0.0,
            "_blis_num": 0.0, "_rlis_num": 0.0, "_scs_num": 0.0,
            "_atip_num": 0.0, "_tip_num": 0.0,
            "_share_weight": 0,
        }
    day_map: dict = defaultdict(_fresh)
    for r in rows:
        d = day_map[r.date]
        imp = r.impressions or 0
        d["clicks"] += r.clicks or 0
        d["impressions"] += imp
        d["cost_micros"] += r.cost_micros or 0
        d["conversions"] += r.conversions or 0
        d["conv_value_micros"] += r.conversion_value_micros or 0
        if imp > 0:
            d["_share_weight"] += imp
            if r.search_impression_share is not None:       d["_sis_num"]  += r.search_impression_share * imp
            if r.search_top_impression_share is not None:   d["_stis_num"] += r.search_top_impression_share * imp
            if r.search_abs_top_impression_share is not None: d["_satis_num"] += r.search_abs_top_impression_share * imp
            if r.search_budget_lost_is is not None:         d["_blis_num"] += r.search_budget_lost_is * imp
            if r.search_rank_lost_is is not None:           d["_rlis_num"] += r.search_rank_lost_is * imp
            if r.search_click_share is not None:            d["_scs_num"]  += r.search_click_share * imp
            if r.abs_top_impression_pct is not None:        d["_atip_num"] += r.abs_top_impression_pct * imp
            if r.top_impression_pct is not None:            d["_tip_num"]  += r.top_impression_pct * imp

    if len(day_map) < 3:
        raise HTTPException(status_code=400, detail="Not enough daily data points for correlation (need at least 3 days)")

    daily_rows = []
    for agg in day_map.values():
        clicks = agg["clicks"]
        impressions = agg["impressions"]
        cost_micros = agg["cost_micros"]
        conversions = agg["conversions"]
        conv_value = agg["conv_value_micros"] / 1_000_000
        cost = cost_micros / 1_000_000
        w = agg["_share_weight"] or 1

        daily_rows.append({
            "cost": cost,
            "clicks": clicks,
            "impressions": impressions,
            "conversions": conversions,
            "conversion_value": conv_value,
            "ctr": (clicks / impressions * 100) if impressions else 0,
            "cpc": (cost / clicks) if clicks else 0,
            "cpa": (cost / conversions) if conversions else 0,
            "cvr": (conversions / clicks * 100) if clicks else 0,
            "roas": (conv_value / cost) if cost else 0,
            "search_impression_share": (agg["_sis_num"] / w * 100) if agg["_share_weight"] else 0,
            "search_top_impression_share": (agg["_stis_num"] / w * 100) if agg["_share_weight"] else 0,
            "search_abs_top_impression_share": (agg["_satis_num"] / w * 100) if agg["_share_weight"] else 0,
            "search_budget_lost_is": (agg["_blis_num"] / w * 100) if agg["_share_weight"] else 0,
            "search_rank_lost_is": (agg["_rlis_num"] / w * 100) if agg["_share_weight"] else 0,
            "search_click_share": (agg["_scs_num"] / w * 100) if agg["_share_weight"] else 0,
            "abs_top_impression_pct": (agg["_atip_num"] / w * 100) if agg["_share_weight"] else 0,
            "top_impression_pct": (agg["_tip_num"] / w * 100) if agg["_share_weight"] else 0,
        })

    df = pd.DataFrame(daily_rows)
    valid_cols = [m for m in requested if m in df.columns]
    if len(valid_cols) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 valid metrics for correlation")

    corr = df[valid_cols].corr(method="pearson")

    return {
        "matrix": corr.fillna(0).round(3).to_dict(),
        "metrics": valid_cols,
        "data_points": len(day_map),
    }


@router.post("/compare-periods", response_model=PeriodComparisonResponse)
def compare_periods(data: PeriodComparisonRequest, db: Session = Depends(get_db)):
    """Compare a metric across two time periods for a campaign."""
    if data.metric not in LEGACY_COLUMN_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {data.metric}")

    def _get_values(start: date, end: date) -> list[float]:
        rows = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id == data.campaign_id,
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        return [getattr(r, data.metric) for r in rows]

    values_a = _get_values(data.period_a_start, data.period_a_end)
    values_b = _get_values(data.period_b_start, data.period_b_end)

    if not values_a or not values_b:
        raise HTTPException(status_code=400, detail="Not enough data for one or both periods")

    mean_a = float(np.mean(values_a))
    mean_b = float(np.mean(values_b))
    pct_change = ((mean_b - mean_a) / mean_a * 100) if mean_a != 0 else 0.0

    if len(values_a) >= 2 and len(values_b) >= 2:
        _, p_value = ttest_ind(values_a, values_b, equal_var=False)
    else:
        p_value = 1.0

    trend = "stable"
    if abs(pct_change) > 5:
        trend = "up" if mean_b > mean_a else "down"

    return PeriodComparisonResponse(
        metric=data.metric,
        period_a_mean=round(mean_a, 4),
        period_b_mean=round(mean_b, 4),
        change_pct=round(pct_change, 2),
        trend=trend,
        is_significant=bool(p_value < 0.05),
        p_value=round(float(p_value), 6),
    )


@router.get("/dashboard-kpis")
def dashboard_kpis(
    filters: CommonFilters = Depends(common_filters),
    db: Session = Depends(get_db),
):
    """Aggregated KPIs with period-over-period comparison."""
    if filters.client_id is None:
        raise HTTPException(status_code=400, detail="client_id is required")
    client_id = filters.client_id
    current_start, today = filters.date_from, filters.date_to
    period_len = (today - current_start).days
    previous_start = current_start - timedelta(days=period_len)

    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(
        client_id,
        filters.campaign_type,
        filters.campaign_status,
    )
    if not campaign_ids:
        return {"current": {}, "previous": {}, "change_pct": {}}

    # Count active campaigns for the KPI grid
    active_campaigns = (
        db.query(func.count(Campaign.id))
        .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
        .scalar()
    ) or 0

    def _agg(start: date, end: date) -> dict:
        rows = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        empty = {
            "clicks": 0, "impressions": 0, "cost_usd": 0, "conversions": 0,
            "ctr": 0, "roas": 0, "cpa": 0, "conversion_value_usd": 0,
            "cvr": 0, "avg_cpc_usd": 0, "all_conversions": 0,
            "all_conversions_value_usd": 0, "cross_device_conversions": 0,
            "value_per_conversion_usd": 0,
            "search_impression_share": None, "search_top_impression_share": None,
            "search_abs_top_impression_share": None,
            "search_budget_lost_is": None, "search_rank_lost_is": None,
            "search_click_share": None,
            "abs_top_impression_pct": None, "top_impression_pct": None,
            "active_campaigns": active_campaigns,
        }
        if not rows:
            return empty

        total_clicks = sum(r.clicks or 0 for r in rows)
        total_impressions = sum(r.impressions or 0 for r in rows)
        total_cost_micros = sum(r.cost_micros or 0 for r in rows)
        total_conversions = sum(r.conversions or 0 for r in rows)
        total_conv_value_micros = sum(r.conversion_value_micros or 0 for r in rows)
        total_all_conversions = sum(r.all_conversions or 0 for r in rows)
        total_all_conv_value_micros = sum(r.all_conversions_value_micros or 0 for r in rows)
        total_cross_device = sum(r.cross_device_conversions or 0 for r in rows)

        total_cost_usd = micros_to_currency(total_cost_micros)
        total_conv_value_usd = micros_to_currency(total_conv_value_micros)
        total_all_conv_value_usd = micros_to_currency(total_all_conv_value_micros)
        roas = round((total_conv_value_usd / total_cost_usd) if total_cost_usd else 0, 2)
        cpa = round((total_cost_usd / total_conversions) if total_conversions else 0, 2)
        cvr = round((total_conversions / total_clicks * 100) if total_clicks else 0, 2)
        avg_cpc_usd = round((total_cost_usd / total_clicks) if total_clicks else 0, 2)
        vpc_usd = round((total_conv_value_usd / total_conversions) if total_conversions else 0, 2)

        # Impression share — weighted average by impressions (only rows with data)
        def _weighted_avg(attr):
            pairs = [(getattr(r, attr), r.impressions or 0) for r in rows if getattr(r, attr) is not None]
            if not pairs:
                return None
            total_w = sum(w for _, w in pairs)
            if total_w == 0:
                return None
            return round(sum(v * w for v, w in pairs) / total_w, 4)

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost_usd": total_cost_usd,
            "conversions": total_conversions,
            "conversion_value_usd": total_conv_value_usd,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": roas,
            "cpa": cpa,
            "cvr": cvr,
            "avg_cpc_usd": avg_cpc_usd,
            "all_conversions": round(total_all_conversions, 2),
            "all_conversions_value_usd": round(total_all_conv_value_usd, 2),
            "cross_device_conversions": round(total_cross_device, 2),
            "value_per_conversion_usd": vpc_usd,
            "search_impression_share": _weighted_avg("search_impression_share"),
            "search_top_impression_share": _weighted_avg("search_top_impression_share"),
            "search_abs_top_impression_share": _weighted_avg("search_abs_top_impression_share"),
            "search_budget_lost_is": _weighted_avg("search_budget_lost_is"),
            "search_rank_lost_is": _weighted_avg("search_rank_lost_is"),
            "search_click_share": _weighted_avg("search_click_share"),
            "abs_top_impression_pct": _weighted_avg("abs_top_impression_pct"),
            "top_impression_pct": _weighted_avg("top_impression_pct"),
            "active_campaigns": active_campaigns,
        }

    current = _agg(current_start, today)
    previous = _agg(previous_start, current_start - timedelta(days=1))

    def _pct(c, p):
        if c is None or p is None:
            return None
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)

    change = {k: _pct(current[k], previous[k]) for k in current}

    return {"current": current, "previous": previous, "change_pct": change, "period_days": period_len}


# ---------------------------------------------------------------------------
# Quality Score Audit
# ---------------------------------------------------------------------------


from app.utils.quality_score import build_subcomponent_issues, get_primary_issue, build_recommendation

# Backward-compatible aliases (used by export.py and internally)
_build_subcomponent_issues = build_subcomponent_issues
_get_primary_issue = get_primary_issue
_build_recommendation = build_recommendation


@router.get("/quality-score-audit")
def quality_score_audit(
    client_id: int = Query(...),
    qs_threshold: int = Query(5, ge=1, le=10, description="Flag keywords with QS below this"),
    campaign_id: int = Query(None, description="Filter by campaign ID"),
    match_type: str = Query(None, description="Filter by match type: EXACT, PHRASE, BROAD"),
    sort_by: str = Query("quality_score", description="Sort field"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    date_from: date = Query(None, description="Start date for cost aggregation"),
    date_to: date = Query(None, description="End date for cost aggregation"),
    db: Session = Depends(get_db),
):
    """Quality Score audit with subcomponent diagnostics."""
    query = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Keyword.status == "ENABLED",
            Keyword.quality_score.isnot(None),
            Keyword.quality_score > 0,
        )
    )
    if campaign_id is not None:
        query = query.filter(Campaign.id == campaign_id)
    if match_type is not None:
        query = query.filter(Keyword.match_type == match_type)

    keywords = query.all()

    if not keywords:
        return {
            "total_keywords": 0, "low_qs_keywords": [], "keywords": [],
            "average_qs": 0, "qs_distribution": {},
            "available_campaigns": [], "issue_breakdown": {},
        }

    all_qs = [k.quality_score for k in keywords]
    avg_qs = sum(all_qs) / len(all_qs)

    # Pre-build ad_group_id → (campaign_id, campaign_name) lookup
    all_ag_ids = {kw.ad_group_id for kw in keywords if kw.ad_group_id}
    campaign_by_ag = {}
    campaign_id_by_ag = {}
    ag_name_by_ag = {}
    if all_ag_ids:
        rows = (
            db.query(AdGroup.id, AdGroup.name, Campaign.id, Campaign.name)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(AdGroup.id.in_(all_ag_ids))
            .all()
        )
        campaign_by_ag = {ag_id: cname for ag_id, ag_name, cid, cname in rows}
        campaign_id_by_ag = {ag_id: cid for ag_id, ag_name, cid, cname in rows}
        ag_name_by_ag = {ag_id: ag_name for ag_id, ag_name, cid, cname in rows}

    # Available campaigns for filter dropdown
    seen_campaigns = {}
    for ag_id, ag_name, cid, cname in rows if all_ag_ids else []:
        if cid not in seen_campaigns:
            seen_campaigns[cid] = cname
    available_campaigns = [{"id": cid, "name": cname} for cid, cname in seen_campaigns.items()]

    # Date-range aggregation from KeywordDaily (when dates provided)
    daily_agg = {}
    use_daily = date_from is not None and date_to is not None
    if use_daily:
        kw_ids = [kw.id for kw in keywords]
        if kw_ids:
            agg_rows = (
                db.query(
                    KeywordDaily.keyword_id,
                    func.sum(KeywordDaily.clicks).label("clicks"),
                    func.sum(KeywordDaily.impressions).label("impressions"),
                    func.sum(KeywordDaily.cost_micros).label("cost_micros"),
                    func.sum(KeywordDaily.conversions).label("conversions"),
                    func.sum(KeywordDaily.conversion_value_micros).label("conv_value_micros"),
                )
                .filter(
                    KeywordDaily.keyword_id.in_(kw_ids),
                    KeywordDaily.date >= date_from,
                    KeywordDaily.date <= date_to,
                )
                .group_by(KeywordDaily.keyword_id)
                .all()
            )
            for row in agg_rows:
                daily_agg[row.keyword_id] = {
                    "clicks": row.clicks or 0,
                    "impressions": row.impressions or 0,
                    "cost_micros": row.cost_micros or 0,
                    "conversions": row.conversions or 0,
                    "conv_value_micros": row.conv_value_micros or 0,
                }

    # Build keyword list with full diagnostics
    all_kw_dicts = []
    low_qs = []
    issue_counts = {"expected_ctr": 0, "ad_relevance": 0, "landing_page": 0}

    for kw in keywords:
        campaign_name = campaign_by_ag.get(kw.ad_group_id, "Unknown")
        primary_issue = _get_primary_issue(kw)

        # Use date-range aggregated metrics when available, else snapshot
        d = daily_agg.get(kw.id) if use_daily else None
        kw_clicks = d["clicks"] if d else (kw.clicks or 0)
        kw_impressions = d["impressions"] if d else (kw.impressions or 0)
        kw_cost_micros = d["cost_micros"] if d else (kw.cost_micros or 0)
        kw_conversions = d["conversions"] if d else (kw.conversions or 0)
        kw_conv_value_micros = d["conv_value_micros"] if d else (kw.conversion_value_micros or 0)
        kw_ctr = round((kw_clicks / kw_impressions * 100) if kw_impressions > 0 else 0, 2) if use_daily else round(kw.ctr or 0, 2)

        kw_dict = {
            "keyword": kw.text,
            "keyword_id": kw.id,
            "google_keyword_id": kw.google_keyword_id,
            "quality_score": kw.quality_score,
            "campaign": campaign_name,
            "campaign_id": campaign_id_by_ag.get(kw.ad_group_id),
            "ad_group": ag_name_by_ag.get(kw.ad_group_id, "Unknown"),
            "match_type": kw.match_type,
            "ctr_pct": kw_ctr,
            "clicks": kw_clicks,
            "impressions": kw_impressions,
            "cost_usd": micros_to_currency(kw_cost_micros),
            "conversions": round(kw_conversions, 1),
            "conversion_value_usd": micros_to_currency(kw_conv_value_micros),
            # Subcomponents (enum 1-3 or None)
            "ad_relevance": kw.historical_creative_quality,
            "landing_page": kw.historical_landing_page_quality,
            "expected_ctr": kw.historical_search_predicted_ctr,
            # Impression share
            "search_impression_share": kw.search_impression_share,
            "search_rank_lost_is": kw.search_rank_lost_is,
            # Diagnostics
            "serving_status": kw.serving_status,
            "primary_issue": primary_issue,
            "issues": _build_subcomponent_issues(kw),
            "recommendation": _build_recommendation(kw),
        }
        all_kw_dicts.append(kw_dict)

        if kw.quality_score < qs_threshold:
            low_qs.append(kw_dict)

        if primary_issue and primary_issue in issue_counts:
            issue_counts[primary_issue] += 1

    # Sort
    reverse = sort_dir == "desc"
    sort_key = sort_by if sort_by in ("quality_score", "clicks", "impressions", "ctr_pct") else "quality_score"
    all_kw_dicts.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)
    low_qs.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    # Aggregate metrics (use daily when date-range active)
    def _kw_cost(kw):
        if use_daily:
            d = daily_agg.get(kw.id)
            return d["cost_micros"] if d else 0
        return kw.cost_micros or 0
    low_spend = sum(_kw_cost(kw) for kw in keywords if kw.quality_score < qs_threshold)
    total_spend = sum(_kw_cost(kw) for kw in keywords)
    rank_lost_vals = [kw.search_rank_lost_is for kw in keywords if kw.search_rank_lost_is is not None]
    high_qs_count = sum(1 for q in all_qs if q >= 8)

    # Get google_customer_id for deep links
    client_obj = db.get(Client, client_id)
    google_customer_id = client_obj.google_customer_id if client_obj else None

    return {
        "total_keywords": len(keywords),
        "google_customer_id": google_customer_id,
        "average_qs": round(avg_qs, 1),
        "low_qs_count": len(low_qs),
        "high_qs_count": high_qs_count,
        "qs_threshold": qs_threshold,
        "low_qs_spend_usd": micros_to_currency(low_spend),
        "low_qs_spend_pct": round(low_spend / total_spend * 100, 1) if total_spend > 0 else 0,
        "avg_rank_lost_is": round(sum(rank_lost_vals) / len(rank_lost_vals) * 100, 1) if rank_lost_vals else None,
        "issue_breakdown": issue_counts,
        "available_campaigns": available_campaigns,
        "qs_distribution": {
            f"qs_{i}": sum(1 for q in all_qs if q == i)
            for i in range(1, 11)
        },
        "keywords": all_kw_dicts,
        "low_qs_keywords": low_qs,
    }


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


@router.get("/forecast")
def forecast_metric(
    campaign_id: int = Query(...),
    metric: str = Query("cost_micros", description="Metric to forecast"),
    history_days: int = Query(60, ge=14, le=365),
    forecast_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Simple linear regression forecast for a campaign metric."""
    normalized_metric = FORECAST_METRIC_ALIASES.get(metric, metric)
    if normalized_metric not in LEGACY_COLUMN_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    cutoff = date.today() - timedelta(days=history_days)
    rows = (
        db.query(MetricDaily)
        .filter(
            MetricDaily.campaign_id == campaign_id,
            MetricDaily.date >= cutoff,
        )
        .order_by(MetricDaily.date)
        .all()
    )

    if len(rows) < 7:
        raise HTTPException(status_code=400, detail=f"Need at least 7 data points for forecast (got {len(rows)})")

    dates = [r.date for r in rows]
    raw_values = [getattr(r, normalized_metric) or 0 for r in rows]
    metric_divisor = 1_000_000 if normalized_metric in FORECAST_MICROS_METRICS else 1
    values = [float(v) / metric_divisor for v in raw_values]

    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)

    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])

    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0

    # Standard error for confidence intervals
    n = len(values)
    se = float(np.sqrt(ss_res / max(n - 2, 1)))  # residual standard error
    x_mean = np.mean(x)
    x_var = np.sum((x - x_mean) ** 2)

    forecast = []
    for i in range(1, forecast_days + 1):
        forecast_x = len(values) - 1 + i
        predicted = max(0, slope * forecast_x + intercept)
        # 95% prediction interval
        leverage = 1 + 1 / n + (forecast_x - x_mean) ** 2 / max(x_var, 1e-9)
        margin = 1.96 * se * float(np.sqrt(leverage))
        forecast_date = dates[-1] + timedelta(days=i)
        forecast.append({
            "date": str(forecast_date),
            "predicted": round(predicted, 2),
            "ci_lower": round(max(0, predicted - margin), 2),
            "ci_upper": round(predicted + margin, 2),
        })

    recent_avg = float(np.mean(values[-7:]))
    forecast_avg = float(np.mean([f["predicted"] for f in forecast]))
    trend_pct = ((forecast_avg - recent_avg) / recent_avg * 100) if recent_avg > 0 else 0

    return {
        "metric": metric,
        "metric_source": normalized_metric,
        "campaign_id": campaign_id,
        "historical": [
            {"date": str(dates[i]), "value": round(float(values[i]), 2)}
            for i in range(len(values))
        ],
        "forecast": forecast,
        "model": {
            "slope_per_day": round(slope, 4),
            "r_squared": round(r_squared, 4),
            "confidence": "high" if r_squared > 0.7 else "medium" if r_squared > 0.4 else "low",
        },
        "trend": {
            "recent_7d_avg": round(recent_avg, 2),
            "forecast_avg": round(forecast_avg, 2),
            "change_pct": round(trend_pct, 1),
            "direction": "up" if trend_pct > 2 else "down" if trend_pct < -2 else "stable",
        },
    }


# ---------------------------------------------------------------------------
# NEW V2 Endpoints — TrendExplorer, Health Score, Campaign Trends
# ---------------------------------------------------------------------------


@router.get("/trends")
def get_trends(
    client_id: int = Query(..., description="Client ID"),
    metrics: str = Query("cost,clicks", description="Comma-separated metrics from TREND_METRICS"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL", description="ALL | SEARCH | PERFORMANCE_MAX | DISPLAY | SHOPPING"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query("ALL", description="Alias for campaign_status (backward compat)"),
    campaign_ids: str = Query(None, description="Comma-separated campaign IDs — restrict aggregation to these"),
    db: Session = Depends(get_db),
):
    """Daily aggregated metrics for TrendExplorer chart.

    Returns time-series data per day. Falls back to mock data if no MetricDaily rows exist.
    When `campaign_ids` is provided, aggregation is restricted to those campaigns —
    used by the Campaigns tab to scope Trend Explorer to a single selected campaign.
    """
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)

    max_span = timedelta(days=365)
    if end - start > max_span:
        start = end - max_span

    metric_list = [m.strip() for m in metrics.split(",") if m.strip() in TREND_METRICS]
    if not metric_list:
        metric_list = ["cost", "clicks"]

    id_filter: list[int] | None = None
    if campaign_ids:
        try:
            id_filter = [int(x) for x in campaign_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    service = AnalyticsService(db)
    return service.get_trends(
        client_id=client_id,
        metrics=metric_list,
        date_from=start,
        date_to=end,
        campaign_type=campaign_type,
        campaign_status=effective_status,
        campaign_ids=id_filter,
    )


@router.get("/trends-by-device")
def get_trends_by_device(
    client_id: int = Query(..., description="Client ID"),
    metric: str = Query("clicks", description="Single metric to split by device"),
    days: int = Query(30, ge=7, le=365),
    date_from: date = Query(None),
    date_to: date = Query(None),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    campaign_ids: str = Query(None, description="Comma-separated campaign IDs"),
    db: Session = Depends(get_db),
):
    """Daily time-series for a single metric, split across device segments.

    Powers TrendExplorer's device-segmentation option. Returns one series per
    device (MOBILE, DESKTOP, TABLET, OTHER) for the selected metric over the
    requested period.
    """
    start, end = resolve_dates(days, date_from, date_to)
    max_span = timedelta(days=365)
    if end - start > max_span:
        start = end - max_span

    if metric not in TREND_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    id_filter: list[int] | None = None
    if campaign_ids:
        try:
            id_filter = [int(x) for x in campaign_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    service = AnalyticsService(db)
    return service.get_trends_by_device(
        client_id=client_id,
        metric=metric,
        date_from=start,
        date_to=end,
        campaign_ids=id_filter,
        campaign_type=campaign_type,
        campaign_status=campaign_status,
    )


@router.get("/health-score")
def get_health_score(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(None, ge=7, le=365, description="Lookback period (optional)"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Account health score (0–100) with issue breakdown."""
    effective_status = campaign_status or status
    service = AnalyticsService(db)
    return service.get_health_score(
        client_id, campaign_type=campaign_type, campaign_status=effective_status,
        date_from=date_from, date_to=date_to, days=days,
    )


@router.get("/campaign-trends")
def get_campaign_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=3, le=90, description="Trend window in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Per-campaign cost trend for sparkline display in campaigns table."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_campaign_trends(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


# ---------------------------------------------------------------------------
# WoW Comparison — current vs previous period, aligned by day-of-week
# ---------------------------------------------------------------------------


@router.get("/wow-comparison")
def wow_comparison(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=7, le=30, description="Period length (default 7 = week)"),
    date_from: date = Query(None, description="End of current period (overrides days)"),
    date_to: date = Query(None, description="End of current period"),
    metric: str = Query("cost", description="Metric: cost,clicks,impressions,conversions,ctr,cpc,roas,cpa"),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    status: str = Query("ALL"),
    db: Session = Depends(get_db),
):
    """Current period vs previous period with day-of-week alignment for overlay chart."""
    effective_status = campaign_status or status
    current_end = date_to or date.today()
    current_start = date_from or (current_end - timedelta(days=days - 1))
    period_len = (current_end - current_start).days + 1

    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_len - 1)

    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(client_id, campaign_type, effective_status)
    if not campaign_ids:
        return {"current": [], "previous": [], "metric": metric}

    allowed = {"cost", "clicks", "impressions", "conversions", "ctr", "cpc", "roas", "cpa"}
    if metric not in allowed:
        metric = "cost"

    def _aggregate(start: date, end: date) -> list[dict]:
        rows = (
            db.query(MetricDaily)
            .filter(
                MetricDaily.campaign_id.in_(campaign_ids),
                MetricDaily.date >= start,
                MetricDaily.date <= end,
            )
            .all()
        )
        day_map: dict[date, dict] = {}
        for r in rows:
            d = r.date
            if d not in day_map:
                day_map[d] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                              "conversions": 0.0, "conv_value_micros": 0}
            day_map[d]["clicks"] += r.clicks or 0
            day_map[d]["impressions"] += r.impressions or 0
            day_map[d]["cost_micros"] += r.cost_micros or 0
            day_map[d]["conversions"] += r.conversions or 0
            day_map[d]["conv_value_micros"] += r.conversion_value_micros or 0

        result = []
        for d in sorted(day_map.keys()):
            agg = day_map[d]
            clicks = agg["clicks"]
            impressions = agg["impressions"]
            cost_usd = agg["cost_micros"] / 1_000_000
            conversions = agg["conversions"]
            conv_value_usd = agg["conv_value_micros"] / 1_000_000

            values = {
                "cost": round(cost_usd, 2),
                "clicks": clicks,
                "impressions": impressions,
                "conversions": round(conversions, 1),
                "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
                "cpc": round(cost_usd / clicks, 2) if clicks else 0,
                "roas": round(conv_value_usd / cost_usd, 2) if cost_usd else 0,
                "cpa": round(cost_usd / conversions, 2) if conversions else 0,
            }
            DOW_LABELS = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
            result.append({
                "date": str(d),
                "dow": DOW_LABELS[d.weekday()],
                "day_index": (d - start).days,
                "value": values.get(metric, 0),
            })
        return result

    return {
        "metric": metric,
        "period_days": period_len,
        "current_range": [str(current_start), str(current_end)],
        "previous_range": [str(previous_start), str(previous_end)],
        "current": _aggregate(current_start, current_end),
        "previous": _aggregate(previous_start, previous_end),
    }


# ---------------------------------------------------------------------------
# Campaigns Summary — per-campaign aggregated metrics for dashboard table
# ---------------------------------------------------------------------------


@router.get("/campaigns-summary")
def campaigns_summary(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=365),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None),
    status: str = Query("ALL", description="Alias for campaign_status"),
    db: Session = Depends(get_db),
):
    """Per-campaign aggregated metrics (clicks, cost, conversions, roas) for a period."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)
    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(client_id, campaign_type, effective_status)
    if not campaign_ids:
        return {"campaigns": {}}

    rows = (
        db.query(
            MetricDaily.campaign_id,
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.impressions).label("impressions"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("conv_value_micros"),
        )
        .filter(
            MetricDaily.campaign_id.in_(campaign_ids),
            MetricDaily.date >= start,
            MetricDaily.date <= end,
        )
        .group_by(MetricDaily.campaign_id)
        .all()
    )

    # Fetch IS data from Campaign model
    is_map = {}
    camp_rows = db.query(Campaign.id, Campaign.search_impression_share).filter(Campaign.id.in_(campaign_ids)).all()
    for cr in camp_rows:
        is_map[cr.id] = cr.search_impression_share

    result = {}
    for r in rows:
        cost_usd = micros_to_currency(r.cost_micros or 0)
        conv_value_usd = micros_to_currency(r.conv_value_micros or 0)
        clicks = r.clicks or 0
        impressions = r.impressions or 0
        conversions = r.conversions or 0
        result[str(r.campaign_id)] = {
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": round(cost_usd, 2),
            "conversions": round(conversions, 1),
            "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
            "roas": round(conv_value_usd / cost_usd, 2) if cost_usd else 0,
            "impression_share": is_map.get(r.campaign_id),
        }

    return {"campaigns": result}


# ---------------------------------------------------------------------------
# Budget Pacing — underspend / overspend tracking
# ---------------------------------------------------------------------------


@router.get("/budget-pacing")
def get_budget_pacing(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Filter by campaign status"),
    db: Session = Depends(get_db),
):
    """Budget pacing for all campaigns: actual vs expected spend this month.

    Returns per-campaign pacing status (on_track / underspend / overspend)
    and a projected month-end spend.
    """
    from sqlalchemy import func

    today = date.today()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    pacing_ratio = days_elapsed / days_in_month  # expected fraction of budget spent

    campaign_q = db.query(Campaign).filter(Campaign.client_id == client_id)
    if campaign_type and campaign_type != "ALL":
        campaign_q = campaign_q.filter(Campaign.campaign_type == campaign_type)
    if campaign_status and campaign_status != "ALL":
        campaign_q = campaign_q.filter(Campaign.status == campaign_status)
    else:
        campaign_q = campaign_q.filter(Campaign.status == "ENABLED")
    campaigns = campaign_q.all()

    results = []
    for camp in campaigns:
        budget_monthly = micros_to_currency(camp.budget_micros) * days_in_month  # daily budget × days

        # Actual spend this month from MetricDaily
        actual_spend_micros = (
            db.query(func.sum(MetricDaily.cost_micros))
            .filter(
                MetricDaily.campaign_id == camp.id,
                MetricDaily.date >= month_start,
                MetricDaily.date <= today,
            )
            .scalar()
        ) or 0
        actual_spend = micros_to_currency(actual_spend_micros)

        expected_spend = budget_monthly * pacing_ratio
        projected_spend = (actual_spend / pacing_ratio) if pacing_ratio > 0 else 0

        # Determine status
        if expected_spend == 0:
            status = "no_data"
            pct = 0
        else:
            pct = actual_spend / expected_spend
            if pct < 0.8:
                status = "underspend"
            elif pct > 1.15:
                status = "overspend"
            else:
                status = "on_track"

        results.append({
            "campaign_id": camp.id,
            "campaign_name": camp.name,
            "daily_budget_usd": round(micros_to_currency(camp.budget_micros), 2),
            "monthly_budget_usd": round(budget_monthly, 2),
            "actual_spend_usd": round(actual_spend, 2),
            "expected_spend_usd": round(expected_spend, 2),
            "projected_spend_usd": round(projected_spend, 2),
            "pacing_pct": round(pct * 100, 1),
            "status": status,
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        })

    return {
        "month": today.strftime("%Y-%m"),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "campaigns": results,
    }


# ---------------------------------------------------------------------------
# Impression Share Trends
# ---------------------------------------------------------------------------


@router.get("/impression-share")
def get_impression_share(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Daily impression share trends for SEARCH campaigns."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_impression_share_trends(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Device Breakdown
# ---------------------------------------------------------------------------


@router.get("/device-breakdown")
def get_device_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by device (Mobile/Desktop/Tablet)."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_device_breakdown(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


# ---------------------------------------------------------------------------
# Geo Breakdown
# ---------------------------------------------------------------------------


@router.get("/geo-breakdown")
def get_geo_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    limit: int = Query(20, ge=1, le=50, description="Max cities"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by city/geography."""
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_geo_breakdown(
        client_id=client_id, date_from=start, date_to=end, campaign_id=campaign_id, limit=limit,
        campaign_type=campaign_type, campaign_status=effective_status,
    )


# ---------------------------------------------------------------------------
# Dayparting — day-of-week performance
# ---------------------------------------------------------------------------


@router.get("/dayparting")
def get_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Campaign performance by day of week."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_dayparting(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# RSA Analysis — ad copy performance
# ---------------------------------------------------------------------------


@router.get("/rsa-analysis")
def get_rsa_analysis(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """RSA ad performance comparison per ad group."""
    service = AnalyticsService(db)
    return service.get_rsa_analysis(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# N-gram Analysis — word-level search term breakdown
# ---------------------------------------------------------------------------


@router.get("/ngram-analysis")
def get_ngram_analysis(
    client_id: int = Query(..., description="Client ID"),
    ngram_size: int = Query(1, ge=1, le=3, description="1=words, 2=bigrams, 3=trigrams"),
    min_occurrences: int = Query(2, ge=1, description="Min occurrences to include"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Search term word/n-gram aggregation by performance."""
    service = AnalyticsService(db)
    return service.get_ngram_analysis(
        client_id=client_id, ngram_size=ngram_size, min_occurrences=min_occurrences,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Match Type Analysis — EXACT vs PHRASE vs BROAD
# ---------------------------------------------------------------------------


@router.get("/match-type-analysis")
def get_match_type_analysis(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword performance comparison by match type."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_match_type_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Landing Page Analysis — performance by URL
# ---------------------------------------------------------------------------


@router.get("/landing-pages")
def get_landing_pages(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword metrics aggregated by landing page URL."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_landing_page_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Wasted Spend — zero-conversion waste summary
# ---------------------------------------------------------------------------


@router.get("/wasted-spend")
def get_wasted_spend(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Total wasted spend on keywords, search terms, and ads with 0 conversions.
    Includes period-over-period change for dashboard KPI card."""
    start, end = resolve_dates(days, date_from, date_to)
    period_len = (end - start).days
    prev_start = start - timedelta(days=period_len)
    prev_end = start - timedelta(days=1)

    service = AnalyticsService(db)
    current = service.get_wasted_spend(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )
    previous = service.get_wasted_spend(
        client_id=client_id, date_from=prev_start, date_to=prev_end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )

    prev_waste = previous.get("total_waste_usd", 0)
    cur_waste = current.get("total_waste_usd", 0)
    if prev_waste == 0:
        change_pct = 100.0 if cur_waste > 0 else 0.0
    else:
        change_pct = round((cur_waste - prev_waste) / prev_waste * 100, 1)

    current["previous_waste_usd"] = prev_waste
    current["waste_change_pct"] = change_pct
    return current


# ---------------------------------------------------------------------------
# Account Structure Audit — cannibalization, oversized groups, match mixing
# ---------------------------------------------------------------------------


@router.get("/account-structure")
def get_account_structure(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Account structure audit: oversized ad groups, match type mixing, keyword cannibalization."""
    service = AnalyticsService(db)
    return service.get_account_structure_audit(client_id)


# ---------------------------------------------------------------------------
# Bidding Strategy Advisor — recommend optimal strategy per campaign
# ---------------------------------------------------------------------------


@router.get("/bidding-advisor")
def get_bidding_advisor(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Conversion lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Bidding strategy recommendations based on conversion volume."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_bidding_advisor(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Hourly Dayparting — performance by hour of day
# ---------------------------------------------------------------------------


@router.get("/hourly-dayparting")
def get_hourly_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Campaign performance by hour of day."""
    start, end = resolve_dates(days, date_from, date_to, default_days=7)
    service = AnalyticsService(db)
    return service.get_hourly_dayparting(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# B2: Search Terms Trend Analysis
# ---------------------------------------------------------------------------


@router.get("/search-term-trends")
def get_search_term_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(5, ge=1, description="Min clicks to include"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Search term trend analysis: rising, declining, and new terms."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_search_term_trends(
        client_id=client_id, date_from=start, date_to=end, min_clicks=min_clicks,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# B3: Close Variant Analysis
# ---------------------------------------------------------------------------


@router.get("/close-variants")
def get_close_variants(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Close variant analysis: search terms vs exact keywords."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_close_variant_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# A3: Conversion Tracking Health
# ---------------------------------------------------------------------------


@router.get("/conversion-health")
def get_conversion_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Conversion tracking health audit per campaign."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_conversion_tracking_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# G2: Keyword Expansion Suggestions
# ---------------------------------------------------------------------------


@router.get("/keyword-expansion")
def get_keyword_expansion(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(3, ge=1, description="Min clicks for suggestion"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Keyword expansion suggestions from high-performing search terms."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_keyword_expansion(
        client_id=client_id, date_from=start, date_to=end, min_clicks=min_clicks,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 1B: Smart Bidding Health
# ---------------------------------------------------------------------------

@router.get("/smart-bidding-health")
def get_smart_bidding_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Smart Bidding campaigns conversion volume health check."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_smart_bidding_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 7A: Pareto 80/20 Analysis
# ---------------------------------------------------------------------------

@router.get("/pareto-analysis")
def get_pareto_analysis(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Pareto 80/20 analysis of campaign value contribution."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pareto_analysis(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 7B: Scaling Opportunities
# ---------------------------------------------------------------------------

@router.get("/scaling-opportunities")
def get_scaling_opportunities(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Find hero campaigns with IS headroom to scale."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_scaling_opportunities(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 6A: Post-Change Performance Delta
# ---------------------------------------------------------------------------

@router.get("/change-impact")
def get_change_impact(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(60, ge=14, le=180, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Post-change performance delta analysis — 7-day before/after comparison."""
    service = AnalyticsService(db)
    return service.get_change_impact_analysis(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# GAP 6B: Bid Strategy Change Impact
# ---------------------------------------------------------------------------

@router.get("/bid-strategy-impact")
def get_bid_strategy_impact(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(90, ge=30, le=180, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Bid strategy change impact — 14-day before/after comparison."""
    service = AnalyticsService(db)
    return service.get_bid_strategy_change_impact(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# GAP 8: Ad Group Health Checks
# ---------------------------------------------------------------------------

@router.get("/ad-group-health")
def get_ad_group_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Ad group structural health: ad count, keyword count, zero-conv groups."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_ad_group_health(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 1D: Target CPA/ROAS vs. Actual
# ---------------------------------------------------------------------------

@router.get("/target-vs-actual")
def get_target_vs_actual(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Compare Smart Bidding targets with actual CPA/ROAS."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_target_vs_actual(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 10: Bid Strategy Performance Report (time series)
# ---------------------------------------------------------------------------

@router.get("/bid-strategy-report")
def get_bid_strategy_report(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    campaign_id: int = Query(None, description="Filter to specific campaign"),
    db: Session = Depends(get_db),
):
    """Daily time series of target vs actual CPA/ROAS per campaign."""
    service = AnalyticsService(db)
    return service.get_bid_strategy_performance_report(
        client_id=client_id, days=days, campaign_id=campaign_id,
    )


# ---------------------------------------------------------------------------
# GAP 1A: Learning Period Detection
# ---------------------------------------------------------------------------

@router.get("/learning-status")
def get_learning_status(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Detect campaigns in Smart Bidding learning period."""
    service = AnalyticsService(db)
    return service.get_learning_status(client_id=client_id)


# ---------------------------------------------------------------------------
# GAP 1E: Portfolio Bid Strategy Health
# ---------------------------------------------------------------------------

@router.get("/portfolio-health")
def get_portfolio_health(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Analyze health of portfolio bid strategies."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_portfolio_strategy_health(
        client_id=client_id, date_from=start, date_to=end,
    )


# ---------------------------------------------------------------------------
# GAP 2A-2D: Conversion Data Quality Audit
# ---------------------------------------------------------------------------

@router.get("/conversion-quality")
def get_conversion_quality(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Audit conversion action configuration for data quality issues."""
    service = AnalyticsService(db)
    return service.get_conversion_quality_audit(client_id=client_id)


# ---------------------------------------------------------------------------
# GAP 4A: Demographic Breakdown (Age/Gender)
# ---------------------------------------------------------------------------

@router.get("/demographics")
def get_demographics(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Aggregate metrics by age range and gender, flag CPA anomalies."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_demographic_breakdown(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 3A: PMax Channel Breakdown
# ---------------------------------------------------------------------------

@router.get("/pmax-channels")
def get_pmax_channels(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Show PMax budget distribution across Search, Display, Shopping, Video channels."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_channel_breakdown(
        client_id=client_id, date_from=start, date_to=end,
    )



@router.get("/pmax-channel-trends")
def get_pmax_channel_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Daily PMax cost/conversions per channel for trend charts."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_channel_trends(
        client_id=client_id, date_from=start, date_to=end,
    )


# ---------------------------------------------------------------------------
# GAP 3B: Asset Group Performance
# ---------------------------------------------------------------------------

@router.get("/asset-group-performance")
def get_asset_group_performance(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """PMax asset group performance with ad strength and asset breakdown."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_asset_group_performance(
        client_id=client_id, date_from=start, date_to=end,
    )


# ---------------------------------------------------------------------------
# GAP 3C: PMax Search Themes
# ---------------------------------------------------------------------------

@router.get("/pmax-search-themes")
def get_pmax_search_themes(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """PMax audience signals and search themes per asset group."""
    service = AnalyticsService(db)
    return service.get_pmax_search_themes(client_id=client_id)


# ---------------------------------------------------------------------------
# GAP 4B: Audience List Performance
# ---------------------------------------------------------------------------

@router.get("/audience-performance")
def get_audience_performance(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Audience segment performance with CPA anomaly flags."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_audience_performance(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 5A: Missing Extensions Audit
# ---------------------------------------------------------------------------

@router.get("/missing-extensions")
def get_missing_extensions(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Per-campaign extension compliance audit — sitelinks, callouts, structured snippets."""
    service = AnalyticsService(db)
    return service.get_missing_extensions_audit(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# GAP 5B: Extension Performance
# ---------------------------------------------------------------------------

@router.get("/extension-performance")
def get_extension_performance(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Campaign type filter"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """Extension performance metrics grouped by type and campaign."""
    service = AnalyticsService(db)
    return service.get_extension_performance(
        client_id=client_id,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# PMax vs Search Cannibalization (D3)
# ---------------------------------------------------------------------------

@router.get("/pmax-search-cannibalization")
def get_pmax_search_cannibalization(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    min_clicks: int = Query(2, ge=1, description="Min clicks to include"),
    db: Session = Depends(get_db),
):
    """Detect search terms appearing in both PMax and Search campaigns."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_pmax_search_cannibalization(
        client_id=client_id, date_from=start, date_to=end,
        min_clicks=min_clicks,
    )


@router.post("/placement-exclusion")
def add_placement_exclusion(
    client_id: int = Query(...),
    campaign_id: int = Query(...),
    placement_url: str = Query(..., description="URL to exclude"),
    allow_demo_write: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Add a placement exclusion to a Display/Video campaign.

    Goes through canonical safety pipeline: demo guard → audit log.
    """
    from app.demo_guard import ensure_demo_write_allowed
    from app.services.google_ads import google_ads_service
    from app.services.write_safety import record_write_action

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    ensure_demo_write_allowed(db, client_id, allow_demo_write=allow_demo_write, operation="Dodanie wykluczenia miejsca")

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    result = google_ads_service.add_placement_exclusion(
        db, client.google_customer_id, campaign.google_campaign_id, placement_url
    )

    # Audit trail
    record_write_action(
        db,
        client_id=client_id,
        action_type="ADD_PLACEMENT_EXCLUSION",
        entity_type="campaign",
        entity_id=campaign_id,
        status="SUCCESS" if result.get("status") != "error" else "FAILED",
        execution_mode="LIVE" if google_ads_service.is_connected else "LOCAL",
        new_value={"placement_url": placement_url, "campaign_id": campaign_id},
        error_message=result.get("message") if result.get("status") == "error" else None,
    )
    db.commit()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/placement-performance")
def placement_performance(
    client_id: int = Query(...),
    campaign_id: int = Query(None),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Placement performance for Display/Video campaigns."""
    from app.models.placement import Placement

    start, end = resolve_dates(days, date_from, date_to)

    query = (
        db.query(
            Placement.placement_url,
            Placement.placement_type,
            Placement.display_name,
            func.sum(Placement.clicks).label("clicks"),
            func.sum(Placement.impressions).label("impressions"),
            func.sum(Placement.cost_micros).label("cost"),
            func.sum(Placement.conversions).label("conv"),
            func.sum(Placement.conversion_value_micros).label("value"),
            func.sum(Placement.video_views).label("views"),
            func.avg(Placement.video_view_rate).label("avg_view_rate"),
        )
        .join(Campaign, Placement.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Placement.date >= start,
            Placement.date <= end,
        )
    )
    if campaign_id:
        query = query.filter(Placement.campaign_id == campaign_id)

    results = (
        query
        .group_by(Placement.placement_url, Placement.placement_type, Placement.display_name)
        .order_by(func.sum(Placement.cost_micros).desc())
        .limit(100)
        .all()
    )

    placements = []
    for r in results:
        cost = int(r.cost or 0) / 1_000_000
        conv = float(r.conv or 0)
        value = int(r.value or 0) / 1_000_000
        placements.append({
            "placement_url": r.placement_url,
            "placement_type": r.placement_type,
            "display_name": r.display_name,
            "clicks": int(r.clicks or 0),
            "impressions": int(r.impressions or 0),
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "value_usd": round(value, 2),
            "roas": round(value / cost, 2) if cost > 0 else 0,
            "cpa_usd": round(cost / conv, 2) if conv > 0 else None,
            "video_views": int(r.views) if r.views else None,
            "avg_view_rate": round(float(r.avg_view_rate), 1) if r.avg_view_rate else None,
        })

    total_cost = sum(p["cost_usd"] for p in placements)
    return {
        "placements": placements,
        "total_placements": len(placements),
        "total_cost_usd": round(total_cost, 2),
        "period": {"from": str(start), "to": str(end)},
    }


@router.get("/shopping-product-groups")
def shopping_product_groups(
    client_id: int = Query(...),
    campaign_id: int = Query(None, description="Filter by campaign"),
    db: Session = Depends(get_db),
):
    """Shopping product group performance tree."""
    from app.models.product_group import ProductGroup

    query = (
        db.query(ProductGroup)
        .join(Campaign, ProductGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if campaign_id:
        query = query.filter(ProductGroup.campaign_id == campaign_id)

    groups = query.order_by(ProductGroup.cost_micros.desc()).all()

    items = []
    for g in groups:
        cost = (g.cost_micros or 0) / 1_000_000
        conv_val = (g.conversion_value_micros or 0) / 1_000_000
        items.append({
            "id": g.id,
            "campaign_id": g.campaign_id,
            "criterion_id": g.google_criterion_id,
            "parent_criterion_id": g.parent_criterion_id,
            "case_type": g.case_value_type,
            "case_value": g.case_value or "(All products)",
            "partition_type": g.partition_type,
            "bid_usd": round(g.bid_micros / 1_000_000, 2) if g.bid_micros else 0,
            "clicks": g.clicks or 0,
            "impressions": g.impressions or 0,
            "cost_usd": round(cost, 2),
            "conversions": round(g.conversions or 0, 2),
            "value_usd": round(conv_val, 2),
            "ctr": round(g.ctr or 0, 2),
            "roas": round(conv_val / cost, 2) if cost > 0 else 0,
            "cpa_usd": round(cost / g.conversions, 2) if g.conversions and g.conversions > 0 else None,
        })

    # Summary
    total_cost = sum(i["cost_usd"] for i in items)
    total_conv = sum(i["conversions"] for i in items)
    total_value = sum(i["value_usd"] for i in items)

    return {
        "product_groups": items,
        "summary": {
            "total_groups": len(items),
            "total_cost_usd": round(total_cost, 2),
            "total_conversions": round(total_conv, 2),
            "total_value_usd": round(total_value, 2),
            "avg_roas": round(total_value / total_cost, 2) if total_cost > 0 else 0,
        },
    }


@router.get("/auction-insights")
def auction_insights(
    client_id: int = Query(...),
    campaign_id: int = Query(None, description="Filter by campaign"),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Auction insights — competitor visibility metrics."""
    from app.models.auction_insight import AuctionInsight

    start, end = resolve_dates(days, date_from, date_to)

    query = (
        db.query(
            AuctionInsight.display_domain,
            func.avg(AuctionInsight.impression_share).label("avg_impression_share"),
            func.avg(AuctionInsight.overlap_rate).label("avg_overlap_rate"),
            func.avg(AuctionInsight.position_above_rate).label("avg_position_above_rate"),
            func.avg(AuctionInsight.outranking_share).label("avg_outranking_share"),
            func.avg(AuctionInsight.top_of_page_rate).label("avg_top_of_page_rate"),
            func.avg(AuctionInsight.abs_top_of_page_rate).label("avg_abs_top_of_page_rate"),
            func.count(AuctionInsight.id).label("data_points"),
        )
        .join(Campaign, AuctionInsight.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            AuctionInsight.date >= start,
            AuctionInsight.date <= end,
        )
    )

    if campaign_id:
        query = query.filter(AuctionInsight.campaign_id == campaign_id)

    results = (
        query
        .group_by(AuctionInsight.display_domain)
        .order_by(func.avg(AuctionInsight.impression_share).desc())
        .all()
    )

    # Identify "self" domain from client website
    client = db.get(Client, client_id)
    your_domain = None
    if client and client.website:
        your_domain = client.website.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

    competitors = []
    for row in results:
        domain = row.display_domain
        is_self = (your_domain and domain and your_domain in domain) or False
        competitors.append({
            "display_domain": domain,
            "is_self": is_self,
            "impression_share": round((row.avg_impression_share or 0) * 100, 1),
            "overlap_rate": round((row.avg_overlap_rate or 0) * 100, 1),
            "position_above_rate": round((row.avg_position_above_rate or 0) * 100, 1),
            "outranking_share": round((row.avg_outranking_share or 0) * 100, 1),
            "top_of_page_rate": round((row.avg_top_of_page_rate or 0) * 100, 1),
            "abs_top_of_page_rate": round((row.avg_abs_top_of_page_rate or 0) * 100, 1),
            "data_points": row.data_points,
        })

    # Also get trend data per competitor (daily)
    trend_query = (
        db.query(
            AuctionInsight.date,
            AuctionInsight.display_domain,
            func.avg(AuctionInsight.impression_share).label("impression_share"),
            func.avg(AuctionInsight.outranking_share).label("outranking_share"),
        )
        .join(Campaign, AuctionInsight.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            AuctionInsight.date >= start,
            AuctionInsight.date <= end,
        )
    )
    if campaign_id:
        trend_query = trend_query.filter(AuctionInsight.campaign_id == campaign_id)

    # Only top 5 competitors for trend
    top_domains = [c["display_domain"] for c in competitors[:5]]
    trend_rows = (
        trend_query
        .filter(AuctionInsight.display_domain.in_(top_domains))
        .group_by(AuctionInsight.date, AuctionInsight.display_domain)
        .order_by(AuctionInsight.date)
        .all()
    )

    trends = {}
    for row in trend_rows:
        domain = row.display_domain
        if domain not in trends:
            trends[domain] = []
        trends[domain].append({
            "date": str(row.date),
            "impression_share": round((row.impression_share or 0) * 100, 1),
            "outranking_share": round((row.outranking_share or 0) * 100, 1),
        })

    return {
        "competitors": competitors,
        "trends": trends,
        "period": {"from": str(start), "to": str(end)},
        "total_competitors": len(competitors),
    }


@router.get("/mcc-accounts")
def mcc_accounts(
    manager_customer_id: str = Query(..., description="Manager account CID"),
    db: Session = Depends(get_db),
):
    """List child accounts under an MCC manager."""
    from app.models.mcc_link import MccLink
    links = db.query(MccLink).filter(
        MccLink.manager_customer_id == manager_customer_id.replace("-", ""),
        MccLink.is_hidden == False,
    ).order_by(MccLink.client_descriptive_name).all()

    return {
        "accounts": [
            {
                "customer_id": l.client_customer_id,
                "name": l.client_descriptive_name,
                "status": l.status,
                "is_manager": l.is_manager,
                "local_client_id": l.local_client_id,
            }
            for l in links
        ],
        "total": len(links),
    }


@router.post("/offline-conversions/upload")
def upload_offline_conversions(
    client_id: int = Query(...),
    conversions: list[dict] = [],
    allow_demo_write: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Upload offline conversions via Google Ads API.

    Body: JSON array of {gclid, conversion_action_id, conversion_time, conversion_value, currency_code}.
    Goes through canonical safety pipeline: demo guard → audit log.
    """
    from app.demo_guard import ensure_demo_write_allowed
    from app.services.google_ads import google_ads_service
    from app.services.write_safety import record_write_action

    ensure_demo_write_allowed(db, client_id, allow_demo_write=allow_demo_write, operation="Upload konwersji offline")

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not conversions:
        return {
            "status": "info",
            "message": "Send POST with JSON body: [{gclid, conversion_action_id, conversion_time, conversion_value, currency_code}, ...]",
            "endpoint": "/analytics/offline-conversions/upload",
        }

    result = google_ads_service.upload_offline_conversions(
        db, client.google_customer_id, conversions
    )

    # Audit trail
    record_write_action(
        db,
        client_id=client_id,
        action_type="UPLOAD_OFFLINE_CONVERSIONS",
        entity_type="offline_conversion",
        entity_id=client_id,
        status="SUCCESS" if result.get("status") != "error" else "FAILED",
        execution_mode="LIVE" if google_ads_service.is_connected else "LOCAL",
        new_value={"conversion_count": len(conversions), "uploaded": result.get("uploaded", 0)},
        error_message=result.get("message") if result.get("status") == "error" else None,
    )
    db.commit()

    return result


@router.get("/offline-conversions")
def list_offline_conversions(
    client_id: int = Query(...),
    status: str = Query(None, description="PENDING, UPLOADED, FAILED"),
    db: Session = Depends(get_db),
):
    """List offline conversions for a client."""
    from app.models.offline_conversion import OfflineConversion

    query = db.query(OfflineConversion).filter(OfflineConversion.client_id == client_id)
    if status:
        query = query.filter(OfflineConversion.upload_status == status)
    convs = query.order_by(OfflineConversion.created_at.desc()).limit(100).all()

    return {
        "conversions": [
            {
                "id": c.id,
                "gclid": c.gclid,
                "conversion_name": c.conversion_name,
                "conversion_time": str(c.conversion_time),
                "conversion_value": c.conversion_value,
                "status": c.upload_status,
                "error": c.error_message,
                "uploaded_at": str(c.uploaded_at) if c.uploaded_at else None,
            }
            for c in convs
        ],
        "total": len(convs),
    }


@router.get("/conversion-value-rules")
def list_conversion_value_rules(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List conversion value rules."""
    from app.models.conversion_value_rule import ConversionValueRule

    rules = db.query(ConversionValueRule).filter(
        ConversionValueRule.client_id == client_id
    ).all()

    return {
        "rules": [
            {
                "id": r.id,
                "condition_type": r.condition_type,
                "condition_value": r.condition_value,
                "action_type": r.action_type,
                "action_value_micros": r.action_value_micros,
                "action_multiplier": r.action_multiplier,
                "status": r.status,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.get("/bid-modifiers")
def get_bid_modifiers(
    client_id: int = Query(...),
    campaign_id: int = Query(None),
    modifier_type: str = Query(None, description="DEVICE, LOCATION, AD_SCHEDULE"),
    db: Session = Depends(get_db),
):
    """List bid modifiers (device, location, ad schedule)."""
    from app.models.bid_modifier import BidModifier

    query = (
        db.query(BidModifier)
        .join(Campaign, BidModifier.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if campaign_id:
        query = query.filter(BidModifier.campaign_id == campaign_id)
    if modifier_type:
        query = query.filter(BidModifier.modifier_type == modifier_type)

    modifiers = query.order_by(BidModifier.modifier_type, BidModifier.campaign_id).all()

    items = []
    for m in modifiers:
        items.append({
            "id": m.id,
            "campaign_id": m.campaign_id,
            "modifier_type": m.modifier_type,
            "device_type": m.device_type,
            "location_id": m.location_id,
            "location_name": m.location_name,
            "day_of_week": m.day_of_week,
            "start_hour": m.start_hour,
            "end_hour": m.end_hour,
            "bid_modifier": m.bid_modifier,
        })
    return {"modifiers": items, "total": len(items)}


@router.get("/topic-performance")
def topic_performance(
    client_id: int = Query(...),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Topic targeting performance for Display/Video campaigns."""
    from app.models.topic import TopicPerformance

    start, end = resolve_dates(days, date_from, date_to)

    results = (
        db.query(
            TopicPerformance.topic_path,
            func.sum(TopicPerformance.clicks).label("clicks"),
            func.sum(TopicPerformance.impressions).label("impressions"),
            func.sum(TopicPerformance.cost_micros).label("cost"),
            func.sum(TopicPerformance.conversions).label("conv"),
            func.sum(TopicPerformance.conversion_value_micros).label("value"),
        )
        .join(Campaign, TopicPerformance.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id, TopicPerformance.date >= start, TopicPerformance.date <= end)
        .group_by(TopicPerformance.topic_path)
        .order_by(func.sum(TopicPerformance.cost_micros).desc())
        .limit(50)
        .all()
    )

    topics = []
    for r in results:
        cost = int(r.cost or 0) / 1_000_000
        conv = float(r.conv or 0)
        value = int(r.value or 0) / 1_000_000
        topics.append({
            "topic_path": r.topic_path,
            "clicks": int(r.clicks or 0),
            "impressions": int(r.impressions or 0),
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "value_usd": round(value, 2),
            "roas": round(value / cost, 2) if cost > 0 else 0,
        })
    return {"topics": topics, "total": len(topics)}


@router.get("/audiences-list")
def audiences_list(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List all synced audiences for a client."""
    from app.models.audience import Audience

    audiences = (
        db.query(Audience)
        .filter(Audience.client_id == client_id)
        .order_by(Audience.name)
        .all()
    )
    return {
        "audiences": [
            {
                "id": a.id,
                "google_audience_id": a.google_audience_id,
                "name": a.name,
                "type": a.audience_type,
                "status": a.status,
                "member_count": a.member_count,
            }
            for a in audiences
        ],
        "total": len(audiences),
    }


@router.get("/google-recommendations")
def google_recommendations_list(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List Google's native recommendations."""
    from app.models.google_recommendation import GoogleRecommendation

    recs = (
        db.query(GoogleRecommendation)
        .filter(GoogleRecommendation.client_id == client_id, GoogleRecommendation.dismissed == False)
        .order_by(GoogleRecommendation.recommendation_type)
        .all()
    )

    items = []
    for r in recs:
        items.append({
            "id": r.id,
            "type": r.recommendation_type,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
            "impact_estimate": r.impact_estimate,
            "status": r.status,
        })

    # Group by type
    type_counts = {}
    for i in items:
        t = i["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "recommendations": items,
        "total": len(items),
        "by_type": type_counts,
    }


# ---------------------------------------------------------------------------
# G4: Cross-Campaign Analysis — keyword overlap, budget allocation, comparison
# ---------------------------------------------------------------------------


@router.get("/keyword-overlap")
def get_keyword_overlap(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Find keywords that appear in multiple campaigns (same text).

    Returns overlapping keyword texts with per-campaign breakdown
    and estimated waste from cannibalization.
    """
    service = AnalyticsService(db)
    return service.get_keyword_overlap(client_id)


@router.get("/budget-allocation")
def get_budget_allocation(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Compare CPA/ROAS across campaigns and suggest budget reallocation.

    Identifies donor (high CPA) and recipient (low CPA) campaigns,
    suggests budget moves to optimize overall account CPA.
    """
    service = AnalyticsService(db)
    return service.get_budget_allocation(
        client_id=client_id, days=days, date_from=date_from, date_to=date_to,
    )


@router.get("/campaign-comparison")
def get_campaign_comparison(
    client_id: int = Query(..., description="Client ID"),
    campaign_ids: str = Query(..., description="Comma-separated campaign IDs (e.g. 1,2,3)"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of selected campaigns.

    Aggregates MetricDaily for each campaign in date range,
    calculates derived metrics (CTR, CPC, CPA, ROAS, CVR).
    """
    # Parse campaign_ids from comma-separated string
    try:
        ids = [int(x.strip()) for x in campaign_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="campaign_ids must be comma-separated integers")

    if not ids:
        raise HTTPException(status_code=400, detail="At least one campaign_id is required")
    if len(ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 campaigns for comparison")

    service = AnalyticsService(db)
    return service.get_campaign_comparison(
        client_id=client_id, campaign_ids=ids, days=days,
        date_from=date_from, date_to=date_to,
    )


# ---------------------------------------------------------------------------
# H2: Industry Benchmarks
# ---------------------------------------------------------------------------

@router.get("/benchmarks")
def get_benchmarks(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Compare client metrics against industry benchmarks.

    Returns client CTR/CPC/CPA/CVR/ROAS vs hardcoded industry averages,
    with per-metric verdict (above / below / on_par).
    """
    service = AnalyticsService(db)
    return service.get_benchmarks(client_id=client_id, days=days)


@router.get("/client-comparison")
def get_client_comparison(
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """MCC view: compare ALL clients' KPIs side-by-side.

    Returns list of clients with aggregated metrics, sorted by ROAS desc.
    """
    service = AnalyticsService(db)
    return service.get_client_comparison(days=days)


# ---------------------------------------------------------------------------
# C1: DSA Targets Analysis
# ---------------------------------------------------------------------------

@router.get("/dsa-targets")
def get_dsa_targets(
    client_id: int = Query(..., description="Client ID"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """List DSA targets with performance metrics."""
    service = AnalyticsService(db)
    return service.get_dsa_targets(client_id, campaign_type=campaign_type,
                                    campaign_status=campaign_status)


@router.get("/dsa-coverage")
def get_dsa_coverage(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """DSA coverage: which campaigns are DSA, target counts."""
    service = AnalyticsService(db)
    return service.get_dsa_coverage(client_id)


# ---------------------------------------------------------------------------
# C2: DSA Headlines
# ---------------------------------------------------------------------------

@router.get("/dsa-headlines")
def get_dsa_headlines(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    db: Session = Depends(get_db),
):
    """List DSA auto-generated headlines with performance metrics."""
    service = AnalyticsService(db)
    return service.get_dsa_headlines(client_id, days=days, date_from=date_from,
                                     date_to=date_to, campaign_type=campaign_type,
                                     campaign_status=campaign_status)


# ---------------------------------------------------------------------------
# C3: DSA-Search Overlap
# ---------------------------------------------------------------------------

@router.get("/dsa-search-overlap")
def get_dsa_search_overlap(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date"),
    date_to: date = Query(None, description="End date"),
    db: Session = Depends(get_db),
):
    """Find search terms that appear in both DSA and standard Search campaigns."""
    service = AnalyticsService(db)
    return service.get_dsa_search_overlap(client_id, days=days,
                                           date_from=date_from, date_to=date_to)
