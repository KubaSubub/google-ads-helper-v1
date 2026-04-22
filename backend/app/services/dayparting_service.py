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
from app.models.client import Client as ClientModel
from app.models.metric_daily import MetricDaily
from app.models.metric_segmented import MetricSegmented

DOW_NAMES_PL = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]
DOW_NAMES_PL_FULL = ["poniedziałek", "wtorek", "środę", "czwartek", "piątek", "sobotę", "niedzielę"]


def _safe_div(num: float, den: float) -> float:
    return (num / den) if den else 0.0


def _client_currency(db: Session, client_id: int) -> str:
    c = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    return c.currency if c else "PLN"


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


# ---------------------------------------------------------------------------
# Day-of-week bid suggestions (analogue to hourly)
# ---------------------------------------------------------------------------


def dow_bid_schedule_suggestions(
    db: Session,
    client_id: int,
    days: int = 30,
    min_cost: float = 50.0,
    campaign_type: str | None = None,
    campaign_status: str | None = None,
) -> dict:
    """Return suggested per-day bid adjustments based on CPA vs account average.

    Uses MetricDaily so the recommendation reflects observed weekday patterns
    even when hour_of_day segmentation is missing. Mirrors hourly logic:
    DECREASE for CPA >= 1.5x avg, INCREASE for CPA <= 0.75x avg, REVIEW for
    high-spend zero-conversion days.
    """
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)
    currency = _client_currency(db, client_id)

    q = (
        db.query(
            MetricDaily.date,
            func.sum(MetricDaily.clicks).label("clicks"),
            func.sum(MetricDaily.cost_micros).label("cost_micros"),
            func.sum(MetricDaily.conversions).label("conversions"),
            func.sum(MetricDaily.conversion_value_micros).label("cv_micros"),
        )
        .join(Campaign, MetricDaily.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id, MetricDaily.date >= cutoff)
    )
    if campaign_type and campaign_type != "ALL":
        q = q.filter(Campaign.campaign_type == campaign_type)
    if campaign_status and campaign_status != "ALL":
        q = q.filter(Campaign.status == campaign_status)
    rows = q.group_by(MetricDaily.date).all()

    dow_bucket: dict[int, dict] = {i: {"cost": 0.0, "conv": 0.0, "cv": 0.0, "clicks": 0, "obs": 0} for i in range(7)}
    for r in rows:
        dow = r.date.weekday()
        dow_bucket[dow]["cost"] += (r.cost_micros or 0) / 1_000_000
        dow_bucket[dow]["conv"] += float(r.conversions or 0)
        dow_bucket[dow]["cv"] += (r.cv_micros or 0) / 1_000_000
        dow_bucket[dow]["clicks"] += int(r.clicks or 0)
        dow_bucket[dow]["obs"] += 1

    total_cost = sum(b["cost"] for b in dow_bucket.values())
    total_conv = sum(b["conv"] for b in dow_bucket.values())
    overall_cpa = (total_cost / total_conv) if total_conv > 0 else None

    suggestions: list[dict] = []
    if overall_cpa:
        for dow, b in dow_bucket.items():
            if b["cost"] < min_cost:
                continue
            cpa = (b["cost"] / b["conv"]) if b["conv"] > 0 else None

            if cpa is None:
                if b["cost"] >= min_cost * 2:
                    suggestions.append({
                        "day_of_week": dow,
                        "day_name": DOW_NAMES_PL[dow],
                        "suggestion_type": "REVIEW",
                        "bid_adjustment_pct": None,
                        "cost": round(b["cost"], 2),
                        "conversions": round(b["conv"], 2),
                        "currency": currency,
                        "reason": (
                            f"{DOW_NAMES_PL_FULL[dow].capitalize()}: "
                            f"{b['cost']:.2f} {currency} wydane, 0 konwersji w {b['obs']} obs. "
                            f"Sprawdź czy wyłączyć (lub pauzować kampanie) na {DOW_NAMES_PL_FULL[dow]}."
                        ),
                        "confidence": "MEDIUM",
                    })
                continue

            ratio = cpa / overall_cpa
            if ratio >= 1.5:
                adj = -25 if ratio >= 1.8 else -15
                suggestion_type = "DECREASE"
                confidence = "HIGH" if ratio >= 1.8 else "MEDIUM"
                reason = (
                    f"{DOW_NAMES_PL[dow]}: CPA {cpa:.2f} {currency} to "
                    f"{(ratio - 1) * 100:+.0f}% od średniej {overall_cpa:.2f} {currency}. Zmniejsz stawkę."
                )
            elif ratio <= 0.75:
                adj = 20 if ratio <= 0.6 else 10
                suggestion_type = "INCREASE"
                confidence = "HIGH" if ratio <= 0.6 else "MEDIUM"
                reason = (
                    f"{DOW_NAMES_PL[dow]}: CPA {cpa:.2f} {currency} to "
                    f"{(ratio - 1) * 100:+.0f}% od średniej {overall_cpa:.2f} {currency}. Zwiększ stawkę."
                )
            else:
                continue

            suggestions.append({
                "day_of_week": dow,
                "day_name": DOW_NAMES_PL[dow],
                "suggestion_type": suggestion_type,
                "bid_adjustment_pct": adj,
                "cpa": round(cpa, 2),
                "overall_cpa": round(overall_cpa, 2),
                "cost": round(b["cost"], 2),
                "conversions": round(b["conv"], 2),
                "currency": currency,
                "reason": reason,
                "confidence": confidence,
            })

    return {
        "window_days": days,
        "currency": currency,
        "overall_cpa": round(overall_cpa, 2) if overall_cpa else None,
        "min_cost": min_cost,
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# 7×24 (day-of-week × hour-of-day) heatmap
# ---------------------------------------------------------------------------


def dow_hour_heatmap(
    db: Session,
    client_id: int,
    days: int = 30,
    campaign_type: str | None = None,
    campaign_status: str | None = None,
) -> dict:
    """Return a 7x24 grid (day_of_week × hour_of_day) of cost/conv/CPA + meta.

    Uses MetricSegmented where both `day_of_week` and `hour_of_day` are present
    (account-level segments only — `device is None`, `geo_city is None`).
    """
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)
    currency = _client_currency(db, client_id)

    q = (
        db.query(
            MetricSegmented.date,
            MetricSegmented.hour_of_day,
            func.sum(MetricSegmented.clicks).label("clicks"),
            func.sum(MetricSegmented.impressions).label("impressions"),
            func.sum(MetricSegmented.cost_micros).label("cost_micros"),
            func.sum(MetricSegmented.conversions).label("conversions"),
            func.sum(MetricSegmented.conversion_value_micros).label("cv_micros"),
        )
        .join(Campaign, MetricSegmented.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            MetricSegmented.date >= cutoff,
            MetricSegmented.hour_of_day.isnot(None),
            MetricSegmented.device.is_(None),
            MetricSegmented.geo_city.is_(None),
        )
    )
    if campaign_type and campaign_type != "ALL":
        q = q.filter(Campaign.campaign_type == campaign_type)
    if campaign_status and campaign_status != "ALL":
        q = q.filter(Campaign.status == campaign_status)
    rows = q.group_by(MetricSegmented.date, MetricSegmented.hour_of_day).all()

    # Aggregate into 7×24 grid (dow is derived from date.weekday())
    cells: list[dict] = []
    buckets: dict[tuple[int, int], dict] = {}
    for r in rows:
        dow = r.date.weekday()
        hour = int(r.hour_of_day)
        if hour < 0 or hour > 23:
            continue
        key = (dow, hour)
        if key not in buckets:
            buckets[key] = {"clicks": 0, "impressions": 0, "cost_micros": 0,
                            "conversions": 0.0, "cv_micros": 0}
        buckets[key]["clicks"] += int(r.clicks or 0)
        buckets[key]["impressions"] += int(r.impressions or 0)
        buckets[key]["cost_micros"] += int(r.cost_micros or 0)
        buckets[key]["conversions"] += float(r.conversions or 0)
        buckets[key]["cv_micros"] += int(r.cv_micros or 0)

    grid: dict[tuple[int, int], dict] = {}
    for (dow, hour), b in buckets.items():
        cost = b["cost_micros"] / 1_000_000
        cv = b["cv_micros"] / 1_000_000
        conv = b["conversions"]
        clicks = b["clicks"]
        impressions = b["impressions"]
        grid[(dow, hour)] = {
            "day_of_week": dow,
            "day_name": DOW_NAMES_PL[dow],
            "hour": hour,
            "clicks": clicks,
            "impressions": impressions,
            "cost": round(cost, 2),
            "conversions": round(conv, 2),
            "conversion_value": round(cv, 2),
            "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
            "cpc": round(cost / clicks, 2) if clicks else 0,
            "cpa": round(cost / conv, 2) if conv > 0 else None,
            "roas": round(cv / cost, 2) if cost > 0 else 0,
            "cvr": round(conv / clicks * 100, 2) if clicks else 0,
        }

    # Materialize 7x24 (fill empties so UI doesn't have to pad)
    for dow in range(7):
        for hour in range(24):
            cell = grid.get((dow, hour))
            if cell is None:
                cells.append({
                    "day_of_week": dow,
                    "day_name": DOW_NAMES_PL[dow],
                    "hour": hour,
                    "clicks": 0, "impressions": 0, "cost": 0.0,
                    "conversions": 0.0, "conversion_value": 0.0,
                    "ctr": 0, "cpc": 0, "cpa": None, "roas": 0, "cvr": 0,
                })
            else:
                cells.append(cell)

    total_cost = sum(c["cost"] for c in cells)
    total_conv = sum(c["conversions"] for c in cells)
    overall_cpa = (total_cost / total_conv) if total_conv > 0 else None

    return {
        "window_days": days,
        "currency": currency,
        "overall_cpa": round(overall_cpa, 2) if overall_cpa else None,
        "cells": cells,
    }
