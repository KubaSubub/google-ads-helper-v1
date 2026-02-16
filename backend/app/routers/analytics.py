"""Analytics endpoints — correlation matrix, period comparison, anomaly detection."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind

from app.database import get_db
from app.models import MetricDaily, Campaign
from app.schemas import PeriodComparisonRequest, PeriodComparisonResponse, CorrelationRequest

router = APIRouter(prefix="/analytics", tags=["Analytics"])

VALID_METRICS = {"clicks", "impressions", "ctr", "conversions", "conversion_rate", "cost", "cost_per_conversion", "roas", "avg_cpc"}


@router.post("/correlation")
def correlation_matrix(data: CorrelationRequest, db: Session = Depends(get_db)):
    """
    Calculate Pearson correlation matrix between selected metrics
    across campaigns. Returns a matrix suitable for heatmap rendering.
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

    df = pd.DataFrame([{m: getattr(r, m) for m in data.metrics} for r in rows])
    corr = df.corr(method="pearson")

    # Return as {metric_a: {metric_b: value, ...}, ...}
    return {
        "matrix": corr.fillna(0).round(3).to_dict(),
        "metrics": data.metrics,
        "data_points": len(rows),
    }


@router.post("/compare-periods", response_model=PeriodComparisonResponse)
def compare_periods(data: PeriodComparisonRequest, db: Session = Depends(get_db)):
    """
    Compare a metric across two time periods for a campaign.
    Returns means, % change, and statistical significance (t-test).
    """
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

    # Welch's t-test (does not assume equal variance)
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


@router.get("/anomalies")
def detect_anomalies(
    campaign_id: int = Query(None, description="Filter by campaign (optional)"),
    metric: str = Query("cost", description="Metric to check for anomalies"),
    threshold: float = Query(2.0, ge=1.0, description="Z-score threshold"),
    days: int = Query(90, ge=7, le=365, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """
    Detect anomalous days where a metric deviates significantly from the mean.
    Uses z-score: |value - mean| / std > threshold.
    """
    if metric not in VALID_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    cutoff = date.today() - timedelta(days=days)
    query = db.query(MetricDaily).filter(MetricDaily.date >= cutoff)
    if campaign_id:
        query = query.filter(MetricDaily.campaign_id == campaign_id)

    rows = query.order_by(MetricDaily.date).all()
    if len(rows) < 5:
        return {"anomalies": [], "message": "Not enough data points"}

    values = np.array([getattr(r, metric) for r in rows])
    mean = float(np.mean(values))
    std = float(np.std(values))

    if std == 0:
        return {"anomalies": [], "message": "Zero variance — no anomalies possible"}

    anomalies = []
    for i, row in enumerate(rows):
        val = values[i]
        z = abs(val - mean) / std
        if z > threshold:
            anomalies.append({
                "date": str(row.date),
                "campaign_id": row.campaign_id,
                "value": round(float(val), 2),
                "z_score": round(float(z), 2),
                "direction": "spike" if val > mean else "drop",
            })

    return {
        "metric": metric,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "threshold": threshold,
        "anomalies": anomalies,
    }


@router.get("/dashboard-kpis")
def dashboard_kpis(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Aggregated KPIs across ALL campaigns for a client.
    Returns current period vs previous period with % change.
    """
    today = date.today()
    current_start = today - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    campaign_ids = [
        c.id for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()
    ]
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
            return {"clicks": 0, "impressions": 0, "cost": 0, "conversions": 0, "ctr": 0, "roas": 0}

        total_clicks = sum(r.clicks for r in rows)
        total_impressions = sum(r.impressions for r in rows)
        total_cost = sum(r.cost for r in rows)
        total_conversions = sum(r.conversions for r in rows)

        return {
            "clicks": total_clicks,
            "impressions": total_impressions,
            "cost": round(total_cost, 2),
            "conversions": round(total_conversions, 2),
            "ctr": round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            "roas": round((total_conversions / total_cost) if total_cost else 0, 2),
        }

    current = _agg(current_start, today)
    previous = _agg(previous_start, current_start - timedelta(days=1))

    def _pct(c, p):
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)

    change = {k: _pct(current[k], previous[k]) for k in current}

    return {"current": current, "previous": previous, "change_pct": change, "period_days": days}


# --------------------------------------------------------------------------
# Quality Score Audit (Playbook: Monthly QS Optimization)
# --------------------------------------------------------------------------
from app.models import Keyword, AdGroup  # noqa: E402


@router.get("/quality-score-audit")
def quality_score_audit(
    client_id: int = Query(...),
    qs_threshold: int = Query(5, ge=1, le=10, description="Flag keywords with QS below this"),
    db: Session = Depends(get_db),
):
    """
    Identify keywords with low Quality Score and suggest improvements.
    Playbook rule: QS < 5 → investigate ad relevance, landing page, CTR.
    """
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

        # Diagnose the problem
        issues = []
        if kw.ctr < 2.0:
            issues.append("Low CTR — ad copy may not match keyword intent")
        if kw.quality_score <= 3:
            issues.append("Very low QS — check ad relevance + landing page")
        if kw.cost > 50 and kw.conversions == 0:
            issues.append("High spend, no conversions — landing page issue?")

        low_qs.append({
            "keyword": kw.text,
            "quality_score": kw.quality_score,
            "campaign": campaign.name if campaign else "Unknown",
            "match_type": kw.match_type,
            "ctr": round(kw.ctr, 2),
            "clicks": kw.clicks,
            "cost": round(kw.cost, 2),
            "issues": issues,
            "recommendation": (
                "Rewrite ad to include keyword, "
                "improve landing page relevance, "
                "consider tighter match type"
            ),
        })

    # Sort by QS ascending (worst first)
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


# --------------------------------------------------------------------------
# Forecast (Playbook: Predictive Analytics)
# --------------------------------------------------------------------------


@router.get("/forecast")
def forecast_metric(
    campaign_id: int = Query(...),
    metric: str = Query("cost", description="Metric to forecast"),
    history_days: int = Query(60, ge=14, le=365),
    forecast_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Simple linear regression forecast for a campaign metric.
    Uses historical data to predict the next N days.
    """
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

    # Prepare data
    dates = [r.date for r in rows]
    values = [getattr(r, metric) for r in rows]

    # Convert to numeric (day index)
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)

    # Linear regression
    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])

    # R² for confidence
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0

    # Generate forecast
    forecast = []
    for i in range(1, forecast_days + 1):
        forecast_x = len(values) - 1 + i
        predicted = max(0, slope * forecast_x + intercept)
        forecast_date = dates[-1] + timedelta(days=i)
        forecast.append({
            "date": str(forecast_date),
            "predicted": round(predicted, 2),
        })

    # Trend info
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
