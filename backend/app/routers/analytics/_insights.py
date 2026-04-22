"""Statistical insights — correlation, period comparison, forecasting, Pareto,
scaling opportunities, change-impact. Uses numpy/pandas/scipy."""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

try:
    import numpy as np
    import pandas as pd
    from scipy.stats import ttest_ind
except ImportError as _import_err:
    raise ImportError(
        "Analytics insights router requires numpy, pandas, and scipy. "
        "Install them with: pip install numpy pandas scipy"
    ) from _import_err

from app.database import get_db
from app.models import MetricDaily
from app.routers.analytics._legacy import (
    CORRELATION_LEGACY_ALIASES,
    FORECAST_METRIC_ALIASES,
    FORECAST_MICROS_METRICS,
    LEGACY_COLUMN_METRICS,
    TREND_METRICS,
)
from app.schemas import (
    CorrelationRequest,
    PeriodComparisonRequest,
    PeriodComparisonResponse,
)
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.post("/correlation")
def correlation_matrix(data: CorrelationRequest, db: Session = Depends(get_db)):
    """Calculate Pearson correlation matrix between selected metrics.

    Aggregates MetricDaily per day first (same as /trends), then computes
    correlation on the daily aggregates.
    """
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

    def _fresh():
        return {
            "clicks": 0, "impressions": 0, "cost_micros": 0,
            "conversions": 0.0, "conv_value_micros": 0,
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

    n = len(values)
    se = float(np.sqrt(ss_res / max(n - 2, 1)))
    x_mean = np.mean(x)
    x_var = np.sum((x - x_mean) ** 2)

    forecast = []
    for i in range(1, forecast_days + 1):
        forecast_x = len(values) - 1 + i
        predicted = max(0, slope * forecast_x + intercept)
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


@router.get("/change-impact")
def get_change_impact(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(60, ge=14, le=180, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """Post-change performance delta analysis — 7-day before/after comparison."""
    service = AnalyticsService(db)
    return service.get_change_impact_analysis(client_id=client_id, days=days)
