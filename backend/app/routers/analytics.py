"""Analytics endpoints — KPIs, anomaly detection, correlation, forecasting."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from app.database import get_db
from app.models import MetricDaily, Campaign, Keyword, AdGroup, Alert, MetricSegmented
from app.schemas import PeriodComparisonRequest, PeriodComparisonResponse, CorrelationRequest
from app.services.analytics_service import AnalyticsService
from app.utils.formatters import micros_to_currency

router = APIRouter(prefix="/analytics", tags=["Analytics"])

VALID_METRICS = {"clicks", "impressions", "ctr", "conversions", "conversion_rate", "cost_micros", "roas", "avg_cpc_micros"}


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
    db: Session = Depends(get_db),
):
    """Mark an anomaly alert as resolved."""
    from datetime import datetime

    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.client_id == client_id,
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.resolved_at:
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.resolved_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "message": f"Alert {alert_id} resolved"}


@router.post("/detect")
def run_anomaly_detection(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Run anomaly detection rules and create alerts."""
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
    """Calculate Pearson correlation matrix between selected metrics."""
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

    df = pd.DataFrame([{m: getattr(r, m) for m in data.metrics} for r in rows])
    corr = df.corr(method="pearson")

    return {
        "matrix": corr.fillna(0).round(3).to_dict(),
        "metrics": data.metrics,
        "data_points": len(rows),
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
    campaign_type: str = Query("ALL"),
    status: str = Query("ALL"),
    db: Session = Depends(get_db),
):
    """Aggregated KPIs with period-over-period comparison."""
    today = date.today()
    current_start = today - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    q = db.query(Campaign).filter(Campaign.client_id == client_id)
    if campaign_type and campaign_type != "ALL":
        q = q.filter(Campaign.campaign_type == campaign_type)
    if status and status != "ALL":
        q = q.filter(Campaign.status == status)
    campaign_ids = [c.id for c in q.all()]
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

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost_usd": micros_to_currency(total_cost_micros),
            "conversions": total_conversions,
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": round((total_conversions * 150 / micros_to_currency(total_cost_micros)) if total_cost_micros else 0, 2),
        }

    current = _agg(current_start, today)
    previous = _agg(previous_start, current_start - timedelta(days=1))

    def _pct(c, p):
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)

    change = {k: _pct(current[k], previous[k]) for k in current}

    return {"current": current, "previous": previous, "change_pct": change, "period_days": days}


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

    low_qs = []
    for kw in keywords:
        if kw.quality_score >= qs_threshold:
            continue

        campaign = (
            db.query(Campaign)
            .join(AdGroup, Campaign.id == AdGroup.campaign_id)
            .filter(AdGroup.id == kw.ad_group_id)
            .first()
        )

        issues = []
        kw_ctr_pct = (kw.ctr or 0) / 10_000  # micros to %
        if kw_ctr_pct < 2.0:
            issues.append("Low CTR - ad copy may not match keyword intent")
        if kw.quality_score <= 3:
            issues.append("Very low QS - check ad relevance + landing page")
        if (kw.cost_micros or 0) > 50_000_000 and (kw.conversions or 0) == 0:
            issues.append("High spend, no conversions - landing page issue?")

        low_qs.append({
            "keyword": kw.text,
            "quality_score": kw.quality_score,
            "campaign": campaign.name if campaign else "Unknown",
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
    if metric not in VALID_METRICS:
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
        return {"error": "Need at least 7 data points for forecast", "data_points": len(rows)}

    dates = [r.date for r in rows]
    values = [getattr(r, metric) or 0 for r in rows]

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
    campaign_type: str = Query("ALL", description="ALL | SEARCH | PERFORMANCE_MAX | DISPLAY | SHOPPING"),
    status: str = Query("ALL", description="ALL | ENABLED | PAUSED"),
    db: Session = Depends(get_db),
):
    """Daily aggregated metrics for TrendExplorer chart.

    Returns time-series data per day. Falls back to mock data if no MetricDaily rows exist.
    """
    allowed = {"cost", "clicks", "impressions", "conversions", "ctr", "cpc", "roas", "cpa", "cvr"}
    metric_list = [m.strip() for m in metrics.split(",") if m.strip() in allowed]
    if not metric_list:
        metric_list = ["cost", "clicks"]

    service = AnalyticsService(db)
    return service.get_trends(
        client_id=client_id,
        metrics=metric_list,
        days=days,
        campaign_type=campaign_type,
        status=status,
    )


@router.get("/health-score")
def get_health_score(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Account health score (0–100) with issue breakdown.

    Lightweight — uses only MetricDaily + Alert + Campaign queries.
    Does NOT invoke recommendations engine.
    """
    service = AnalyticsService(db)
    return service.get_health_score(client_id)


@router.get("/campaign-trends")
def get_campaign_trends(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=3, le=30, description="Trend window in days"),
    db: Session = Depends(get_db),
):
    """Per-campaign cost trend for sparkline display in campaigns table.

    Returns cost values for each of the last `days` days.
    Falls back to mock data based on budget if no MetricDaily rows.
    """
    service = AnalyticsService(db)
    return service.get_campaign_trends(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# Budget Pacing — underspend / overspend tracking
# ---------------------------------------------------------------------------


@router.get("/budget-pacing")
def get_budget_pacing(
    client_id: int = Query(..., description="Client ID"),
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

    campaigns = (
        db.query(Campaign)
        .filter(Campaign.client_id == client_id, Campaign.status == "ENABLED")
        .all()
    )

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
    campaign_id: int = Query(None, description="Optional campaign filter"),
    db: Session = Depends(get_db),
):
    """Daily impression share trends for SEARCH campaigns."""
    service = AnalyticsService(db)
    return service.get_impression_share_trends(
        client_id=client_id, days=days, campaign_id=campaign_id,
    )


# ---------------------------------------------------------------------------
# Device Breakdown
# ---------------------------------------------------------------------------


@router.get("/device-breakdown")
def get_device_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=90, description="Lookback period"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by device (Mobile/Desktop/Tablet)."""
    service = AnalyticsService(db)
    return service.get_device_breakdown(
        client_id=client_id, days=days, campaign_id=campaign_id,
    )


# ---------------------------------------------------------------------------
# Geo Breakdown
# ---------------------------------------------------------------------------


@router.get("/geo-breakdown")
def get_geo_breakdown(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=30, description="Lookback period"),
    campaign_id: int = Query(None, description="Optional campaign filter"),
    limit: int = Query(20, ge=1, le=50, description="Max cities"),
    db: Session = Depends(get_db),
):
    """Performance breakdown by city/geography."""
    service = AnalyticsService(db)
    return service.get_geo_breakdown(
        client_id=client_id, days=days, campaign_id=campaign_id, limit=limit,
    )


# ---------------------------------------------------------------------------
# Dayparting — day-of-week performance
# ---------------------------------------------------------------------------


@router.get("/dayparting")
def get_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """SEARCH campaign performance by day of week."""
    service = AnalyticsService(db)
    return service.get_dayparting(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# RSA Analysis — ad copy performance
# ---------------------------------------------------------------------------


@router.get("/rsa-analysis")
def get_rsa_analysis(
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """RSA ad performance comparison per ad group."""
    service = AnalyticsService(db)
    return service.get_rsa_analysis(client_id=client_id)


# ---------------------------------------------------------------------------
# N-gram Analysis — word-level search term breakdown
# ---------------------------------------------------------------------------


@router.get("/ngram-analysis")
def get_ngram_analysis(
    client_id: int = Query(..., description="Client ID"),
    ngram_size: int = Query(1, ge=1, le=3, description="1=words, 2=bigrams, 3=trigrams"),
    min_occurrences: int = Query(2, ge=1, description="Min occurrences to include"),
    db: Session = Depends(get_db),
):
    """Search term word/n-gram aggregation by performance."""
    service = AnalyticsService(db)
    return service.get_ngram_analysis(
        client_id=client_id, ngram_size=ngram_size, min_occurrences=min_occurrences,
    )


# ---------------------------------------------------------------------------
# Match Type Analysis — EXACT vs PHRASE vs BROAD
# ---------------------------------------------------------------------------


@router.get("/match-type-analysis")
def get_match_type_analysis(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Keyword performance comparison by match type."""
    service = AnalyticsService(db)
    return service.get_match_type_analysis(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# Landing Page Analysis — performance by URL
# ---------------------------------------------------------------------------


@router.get("/landing-pages")
def get_landing_pages(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Keyword metrics aggregated by landing page URL."""
    service = AnalyticsService(db)
    return service.get_landing_page_analysis(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# Wasted Spend — zero-conversion waste summary
# ---------------------------------------------------------------------------


@router.get("/wasted-spend")
def get_wasted_spend(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Total wasted spend on keywords, search terms, and ads with 0 conversions."""
    service = AnalyticsService(db)
    return service.get_wasted_spend(client_id=client_id, days=days)


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
    db: Session = Depends(get_db),
):
    """Bidding strategy recommendations based on conversion volume."""
    service = AnalyticsService(db)
    return service.get_bidding_advisor(client_id=client_id, days=days)


# ---------------------------------------------------------------------------
# Hourly Dayparting — performance by hour of day
# ---------------------------------------------------------------------------


@router.get("/hourly-dayparting")
def get_hourly_dayparting(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(7, ge=1, le=30, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """SEARCH campaign performance by hour of day."""
    service = AnalyticsService(db)
    return service.get_hourly_dayparting(client_id=client_id, days=days)
