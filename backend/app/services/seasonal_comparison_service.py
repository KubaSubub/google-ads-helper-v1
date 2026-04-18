"""Year-over-year and seasonal comparison.

Compares account KPIs for a user-selected window against the same window from a
year ago (or N months ago). Useful for e-commerce accounts with clear seasonal
patterns — you don't want to compare "November CPA" against "October CPA" when
November is Black Friday season.

Usage:
    yoy_comparison(client_id, date_from, date_to)            # same window last year
    rolling_comparison(client_id, date_from, date_to, months=3)   # same window 3 months ago

Returns current vs comparison KPIs with percentage deltas and an interpretation
for each KPI (better / worse / same with %-change thresholds).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.metric_daily import MetricDaily


def _delta_pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


def _delta_label(delta_pct: float | None, higher_is_better: bool) -> str:
    if delta_pct is None:
        return "NO_BASELINE"
    if abs(delta_pct) < 5:
        return "FLAT"
    if (delta_pct > 0) == higher_is_better:
        return "BETTER"
    return "WORSE"


def _aggregate(db: Session, client_id: int, start: date, end: date) -> dict:
    campaign_ids = [
        c.id for c in db.query(Campaign).filter(Campaign.client_id == client_id).all()
    ]
    if not campaign_ids:
        return _empty_agg()

    row = (
        db.query(
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
        .first()
    )

    clicks = int(row.clicks or 0)
    impressions = int(row.impressions or 0)
    cost_usd = (row.cost_micros or 0) / 1_000_000
    conversions = float(row.conversions or 0)
    conv_value_usd = (row.conv_value_micros or 0) / 1_000_000

    return {
        "clicks": clicks,
        "impressions": impressions,
        "cost_usd": round(cost_usd, 2),
        "conversions": round(conversions, 2),
        "conversion_value_usd": round(conv_value_usd, 2),
        "ctr_pct": round(clicks / impressions * 100, 2) if impressions else 0.0,
        "cvr_pct": round(conversions / clicks * 100, 2) if clicks else 0.0,
        "cpa_usd": round(cost_usd / conversions, 2) if conversions > 0 else None,
        "roas": round(conv_value_usd / cost_usd, 2) if cost_usd else None,
    }


def _empty_agg() -> dict:
    return {
        "clicks": 0, "impressions": 0, "cost_usd": 0.0,
        "conversions": 0.0, "conversion_value_usd": 0.0,
        "ctr_pct": 0.0, "cvr_pct": 0.0,
        "cpa_usd": None, "roas": None,
    }


def _compare(current: dict, previous: dict) -> dict:
    """Merge into unified response with deltas and interpretations."""
    # per-KPI "higher is better" flags
    higher_is_better = {
        "clicks": True,
        "impressions": True,
        "conversions": True,
        "conversion_value_usd": True,
        "ctr_pct": True,
        "cvr_pct": True,
        "roas": True,
        "cost_usd": False,    # spend is neutral but most operators read "up" as concerning
        "cpa_usd": False,
    }
    result: dict = {"current": current, "previous": previous, "deltas": {}, "labels": {}}
    for kpi in current.keys():
        if current[kpi] is None or previous[kpi] is None:
            result["deltas"][kpi] = None
            result["labels"][kpi] = "NO_BASELINE"
            continue
        delta = _delta_pct(current[kpi], previous[kpi])
        result["deltas"][kpi] = delta
        result["labels"][kpi] = _delta_label(delta, higher_is_better.get(kpi, True))
    return result


def yoy_comparison(
    db: Session, client_id: int, date_from: date, date_to: date
) -> dict:
    """Compare current window against the same window one year ago."""
    window_days = (date_to - date_from).days
    prev_from = date_from.replace(year=date_from.year - 1)
    prev_to = prev_from + timedelta(days=window_days)
    current = _aggregate(db, client_id, date_from, date_to)
    previous = _aggregate(db, client_id, prev_from, prev_to)
    return {
        "period": {
            "current_from": str(date_from), "current_to": str(date_to),
            "previous_from": str(prev_from), "previous_to": str(prev_to),
        },
        "comparison_type": "year_over_year",
        **_compare(current, previous),
    }


def rolling_comparison(
    db: Session, client_id: int, date_from: date, date_to: date, months: int = 3
) -> dict:
    """Compare current window against same-length window N months earlier."""
    # Approximate months as 30 days * months — clean, avoids calendar edge cases.
    offset = timedelta(days=30 * months)
    prev_from = date_from - offset
    prev_to = date_to - offset
    current = _aggregate(db, client_id, date_from, date_to)
    previous = _aggregate(db, client_id, prev_from, prev_to)
    return {
        "period": {
            "current_from": str(date_from), "current_to": str(date_to),
            "previous_from": str(prev_from), "previous_to": str(prev_to),
            "offset_months": months,
        },
        "comparison_type": "rolling",
        **_compare(current, previous),
    }
