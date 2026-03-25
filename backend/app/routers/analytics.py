"""Analytics endpoints — KPIs, anomaly detection, correlation, forecasting."""

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.models import MetricDaily, Campaign, Keyword, AdGroup, Alert, MetricSegmented
from app.schemas import PeriodComparisonRequest, PeriodComparisonResponse, CorrelationRequest
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency
from app.utils.date_utils import resolve_dates

router = APIRouter(prefix="/analytics", tags=["Analytics"])

VALID_METRICS = {"clicks", "impressions", "ctr", "conversions", "conversion_rate", "cost_micros", "roas", "avg_cpc_micros"}
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


# ---------------------------------------------------------------------------
# Advanced Analytics (correlation, period comparison, forecast)
# ---------------------------------------------------------------------------


@router.post("/correlation")
def correlation_matrix(data: CorrelationRequest, db: Session = Depends(get_db)):
    """Calculate Pearson correlation matrix between selected metrics.

    Aggregates MetricDaily per day first (same as /trends), then computes
    correlation on the daily aggregates. This avoids mixing campaign-level
    rows which would distort the time-series correlation.
    """
    invalid = set(data.metrics) - VALID_METRICS
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

    # Aggregate per day (same logic as get_trends) to get true time-series
    from collections import defaultdict
    day_map = defaultdict(lambda: {"clicks": 0, "impressions": 0, "cost_micros": 0,
                                    "conversions": 0.0, "conv_value_micros": 0})
    for r in rows:
        d = day_map[r.date]
        d["clicks"] += r.clicks or 0
        d["impressions"] += r.impressions or 0
        d["cost_micros"] += r.cost_micros or 0
        d["conversions"] += r.conversions or 0
        d["conv_value_micros"] += r.conversion_value_micros or 0

    if len(day_map) < 3:
        raise HTTPException(status_code=400, detail="Not enough daily data points for correlation (need at least 3 days)")

    # Derive metrics per day (matching /trends output)
    daily_rows = []
    for agg in day_map.values():
        clicks = agg["clicks"]
        impressions = agg["impressions"]
        cost_micros = agg["cost_micros"]
        conversions = agg["conversions"]
        conv_value = agg["conv_value_micros"] / 1_000_000
        cost = cost_micros / 1_000_000
        avg_cpc = cost / clicks if clicks else 0

        daily_rows.append({
            "clicks": clicks,
            "impressions": impressions,
            "cost_micros": cost_micros,
            "conversions": conversions,
            "ctr": clicks / impressions if impressions else 0,
            "roas": conv_value / cost if cost else 0,
            "avg_cpc_micros": int(cost_micros / clicks) if clicks else 0,
            "conversion_rate": conversions / clicks if clicks else 0,
        })

    df = pd.DataFrame(daily_rows)
    # Only keep requested metrics that exist in df
    valid_cols = [m for m in data.metrics if m in df.columns]
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
    if data.metric not in VALID_METRICS:
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
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query("ALL", description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Aggregated KPIs with period-over-period comparison."""
    effective_status = campaign_status or status
    current_start, today = resolve_dates(days, date_from, date_to)
    period_len = (today - current_start).days
    previous_start = current_start - timedelta(days=period_len)

    svc = AnalyticsService(db)
    campaign_ids = svc._filter_campaign_ids(client_id, campaign_type, effective_status)
    if not campaign_ids:
        return {"current": {}, "previous": {}, "change_pct": {}}

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
        if not rows:
            return {"clicks": 0, "impressions": 0, "cost_usd": 0, "conversions": 0, "ctr": 0, "roas": 0}

        total_clicks = sum(r.clicks or 0 for r in rows)
        total_impressions = sum(r.impressions or 0 for r in rows)
        total_cost_micros = sum(r.cost_micros or 0 for r in rows)
        total_conversions = sum(r.conversions or 0 for r in rows)
        total_conv_value_micros = sum(r.conversion_value_micros or 0 for r in rows)

        total_cost_usd = micros_to_currency(total_cost_micros)
        total_conv_value_usd = micros_to_currency(total_conv_value_micros)
        roas = round((total_conv_value_usd / total_cost_usd) if total_cost_usd else 0, 2)

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost_usd": total_cost_usd,
            "conversions": total_conversions,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": roas,
        }

    current = _agg(current_start, today)
    previous = _agg(previous_start, current_start - timedelta(days=1))

    def _pct(c, p):
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)

    change = {k: _pct(current[k], previous[k]) for k in current}

    return {"current": current, "previous": previous, "change_pct": change, "period_days": period_len}


# ---------------------------------------------------------------------------
# Quality Score Audit
# ---------------------------------------------------------------------------


@router.get("/quality-score-audit")
def quality_score_audit(
    client_id: int = Query(...),
    qs_threshold: int = Query(5, ge=1, le=10, description="Flag keywords with QS below this"),
    db: Session = Depends(get_db),
):
    """Identify keywords with low Quality Score."""
    keywords = (
        db.query(Keyword)
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Keyword.status == "ENABLED",
            Keyword.quality_score.isnot(None),
            Keyword.quality_score > 0,
        )
        .all()
    )

    if not keywords:
        return {"total_keywords": 0, "low_qs_keywords": [], "average_qs": 0}

    all_qs = [k.quality_score for k in keywords]
    avg_qs = sum(all_qs) / len(all_qs)

    # Pre-build ad_group_id → campaign_name lookup to avoid N+1 queries
    low_kw_ag_ids = {kw.ad_group_id for kw in keywords if kw.quality_score < qs_threshold and kw.ad_group_id}
    campaign_by_ag = {}
    if low_kw_ag_ids:
        rows = (
            db.query(AdGroup.id, Campaign.name)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(AdGroup.id.in_(low_kw_ag_ids))
            .all()
        )
        campaign_by_ag = {ag_id: cname for ag_id, cname in rows}

    low_qs = []
    for kw in keywords:
        if kw.quality_score >= qs_threshold:
            continue

        campaign_name = campaign_by_ag.get(kw.ad_group_id, "Unknown")

        issues = []
        kw_ctr_pct = kw.ctr or 0  # already percentage
        if kw_ctr_pct < 2.0:
            issues.append("Low CTR - ad copy may not match keyword intent")
        if kw.quality_score <= 3:
            issues.append("Very low QS - check ad relevance + landing page")
        if (kw.cost_micros or 0) > 50_000_000 and (kw.conversions or 0) == 0:
            issues.append("High spend, no conversions - landing page issue?")

        low_qs.append({
            "keyword": kw.text,
            "quality_score": kw.quality_score,
            "campaign": campaign_name,
            "match_type": kw.match_type,
            "ctr_pct": round(kw_ctr_pct, 2),
            "clicks": kw.clicks or 0,
            "cost_usd": micros_to_currency(kw.cost_micros),
            "issues": issues,
        })

    low_qs.sort(key=lambda x: x["quality_score"])

    return {
        "total_keywords": len(keywords),
        "average_qs": round(avg_qs, 1),
        "low_qs_count": len(low_qs),
        "qs_threshold": qs_threshold,
        "low_qs_keywords": low_qs,
        "qs_distribution": {
            f"qs_{i}": sum(1 for q in all_qs if q == i)
            for i in range(1, 11)
        },
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
    if normalized_metric not in VALID_METRICS:
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
    metrics: str = Query("cost,clicks", description="Comma-separated metrics: cost,clicks,ctr,cpc,conversions,roas,cpa,impressions,cvr"),
    days: int = Query(30, ge=7, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query("ALL", description="ALL | SEARCH | PERFORMANCE_MAX | DISPLAY | SHOPPING"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query("ALL", description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Daily aggregated metrics for TrendExplorer chart.

    Returns time-series data per day. Falls back to mock data if no MetricDaily rows exist.
    """
    effective_status = campaign_status or status
    start, end = resolve_dates(days, date_from, date_to)

    allowed = {"cost", "clicks", "impressions", "conversions", "ctr", "cpc", "roas", "cpa", "cvr"}
    metric_list = [m.strip() for m in metrics.split(",") if m.strip() in allowed]
    if not metric_list:
        metric_list = ["cost", "clicks"]

    service = AnalyticsService(db)
    return service.get_trends(
        client_id=client_id,
        metrics=metric_list,
        date_from=start,
        date_to=end,
        campaign_type=campaign_type,
        campaign_status=effective_status,
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
    """Total wasted spend on keywords, search terms, and ads with 0 conversions."""
    start, end = resolve_dates(days, date_from, date_to)
    service = AnalyticsService(db)
    return service.get_wasted_spend(
        client_id=client_id, date_from=start, date_to=end,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


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
