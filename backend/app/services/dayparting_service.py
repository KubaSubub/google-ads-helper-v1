"""Hourly / dayparting performance service.

Uses `metrics_segmented.hour_of_day` (already synced) to build a performance
heatmap per hour × (optionally) day-of-week, with bid-schedule recommendations.

Two views:

1. `hourly_breakdown(client_id, days)` — for a client, compute avg cost / conv /
   CPA / ROAS per hour across the window. Returns 24 rows with comparison vs
   overall average.

2. `bid_schedule_suggestions(client_id, days, min_cost_usd)` — identify hours
   where CPA is materially better or worse than average, output suggested bid
   adjustments (+/- 15-30%) that an operator can translate into an ad schedule.

Recommendations principles:
- Only suggest adjustments for hours with enough signal (>= min_cost_usd).
- Recommend -25% for worst-CPA hours (CPA > avg × 1.5), +20% for best (CPA < avg × 0.75).
- Never recommend a bid-up on zero-conversion hours (CPA undefined).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.metric_segmented import MetricSegmented


def _safe_div(num: float, den: float) -> float:
    return (num / den) if den else 0.0


def hourly_breakdown(db: Session, client_id: int, days: int = 30) -> dict:
    """Return {hours: [row per hour 0-23], overall: {...}}."""
    cutoff = date.today() - timedelta(days=days)

    rows = (
        db.query(
            MetricSegmented.hour_of_day,
            func.sum(MetricSegmented.clicks).label("clicks"),
            func.sum(MetricSegmented.impressions).label("impressions"),
            func.sum(MetricSegmented.cost_micros).label("cost_micros"),
            func.sum(MetricSegmented.conversions).label("conversions"),
            func.sum(MetricSegmented.conversion_value_micros).label("conv_value_micros"),
        )
        .join(Campaign, MetricSegmented.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            MetricSegmented.date >= cutoff,
            MetricSegmented.hour_of_day.isnot(None),
        )
        .group_by(MetricSegmented.hour_of_day)
        .order_by(MetricSegmented.hour_of_day)
        .all()
    )

    hours_data = []
    overall = {"clicks": 0, "impressions": 0, "cost_usd": 0.0,
               "conversions": 0.0, "conv_value_usd": 0.0}
    for r in rows:
        cost_usd = (r.cost_micros or 0) / 1_000_000
        conv_value_usd = (r.conv_value_micros or 0) / 1_000_000
        conv = float(r.conversions or 0)
        clicks = int(r.clicks or 0)
        impressions = int(r.impressions or 0)

        hours_data.append({
            "hour": r.hour_of_day,
            "clicks": clicks,
            "impressions": impressions,
            "cost_usd": round(cost_usd, 2),
            "conversions": round(conv, 2),
            "conversion_value_usd": round(conv_value_usd, 2),
            "ctr_pct": round(_safe_div(clicks, impressions) * 100, 2),
            "cvr_pct": round(_safe_div(conv, clicks) * 100, 2),
            "cpa_usd": round(_safe_div(cost_usd, conv), 2) if conv > 0 else None,
            "roas": round(_safe_div(conv_value_usd, cost_usd), 2),
        })
        overall["clicks"] += clicks
        overall["impressions"] += impressions
        overall["cost_usd"] += cost_usd
        overall["conversions"] += conv
        overall["conv_value_usd"] += conv_value_usd

    # Overall averages
    overall_cpa = _safe_div(overall["cost_usd"], overall["conversions"]) if overall["conversions"] > 0 else None
    overall_roas = _safe_div(overall["conv_value_usd"], overall["cost_usd"])
    overall_ctr = _safe_div(overall["clicks"], overall["impressions"]) * 100
    overall_cvr = _safe_div(overall["conversions"], overall["clicks"]) * 100

    # Indexed deltas vs overall
    for row in hours_data:
        row["cpa_vs_overall_pct"] = (
            round((row["cpa_usd"] - overall_cpa) / overall_cpa * 100, 1)
            if (overall_cpa and row["cpa_usd"] is not None)
            else None
        )
        row["roas_vs_overall_pct"] = (
            round((row["roas"] - overall_roas) / overall_roas * 100, 1)
            if overall_roas else None
        )

    return {
        "hours": hours_data,
        "overall": {
            "clicks": overall["clicks"],
            "impressions": overall["impressions"],
            "cost_usd": round(overall["cost_usd"], 2),
            "conversions": round(overall["conversions"], 2),
            "conversion_value_usd": round(overall["conv_value_usd"], 2),
            "ctr_pct": round(overall_ctr, 2),
            "cvr_pct": round(overall_cvr, 2),
            "cpa_usd": round(overall_cpa, 2) if overall_cpa is not None else None,
            "roas": round(overall_roas, 2),
        },
        "window_days": days,
    }


def bid_schedule_suggestions(
    db: Session, client_id: int, days: int = 30, min_cost_usd: float = 20.0
) -> list[dict]:
    """Return suggested hourly bid adjustments for an operator to apply as ad schedule."""
    breakdown = hourly_breakdown(db, client_id, days)
    overall_cpa = breakdown["overall"]["cpa_usd"]
    if not overall_cpa:
        return []

    out: list[dict] = []
    for row in breakdown["hours"]:
        if row["cost_usd"] < min_cost_usd:
            continue
        if row["cpa_usd"] is None:
            # Zero-conversion hour with meaningful spend — flag as "review",
            # never recommend bid-up (CPA undefined).
            if row["cost_usd"] >= min_cost_usd * 2:
                out.append({
                    "hour": row["hour"],
                    "suggestion_type": "REVIEW",
                    "bid_adjustment_pct": None,
                    "reason": (
                        f"{row['hour']:02d}:00 — ${row['cost_usd']:.2f} wydane, 0 konwersji. "
                        f"Sprawdź czy wyłączyć tę godzinę."
                    ),
                    "confidence": "MEDIUM",
                })
            continue

        ratio = row["cpa_usd"] / overall_cpa
        if ratio >= 1.5:
            adj = -25 if ratio >= 1.8 else -15
            suggestion = "DECREASE"
            reason = (
                f"{row['hour']:02d}:00 — CPA ${row['cpa_usd']:.2f} to "
                f"{(ratio - 1) * 100:+.0f}% od średniej ${overall_cpa:.2f}. "
                f"Zmniejsz stawkę."
            )
            confidence = "HIGH" if ratio >= 1.8 else "MEDIUM"
        elif ratio <= 0.75:
            adj = 20 if ratio <= 0.6 else 10
            suggestion = "INCREASE"
            reason = (
                f"{row['hour']:02d}:00 — CPA ${row['cpa_usd']:.2f} to "
                f"{(ratio - 1) * 100:+.0f}% od średniej ${overall_cpa:.2f}. "
                f"Zwiększ stawkę."
            )
            confidence = "HIGH" if ratio <= 0.6 else "MEDIUM"
        else:
            continue

        out.append({
            "hour": row["hour"],
            "suggestion_type": suggestion,
            "bid_adjustment_pct": adj,
            "cpa_usd": row["cpa_usd"],
            "overall_cpa_usd": overall_cpa,
            "cost_usd": row["cost_usd"],
            "conversions": row["conversions"],
            "reason": reason,
            "confidence": confidence,
        })

    return out
