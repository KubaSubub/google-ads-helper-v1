"""Offline-conversion import lag tracking.

If the business imports offline conversions (from a CRM or call tracking), those
conversions arrive with a delay relative to the click. The delay can be a few
hours or several weeks. Two things the operator needs to know:

1. Is the upload pipeline alive? "Last upload was 10 days ago, expected daily" = alert.
2. What's the typical conversion lag? "Clicks from day D get credit for their
   conversions on average 4 days later" — important for evaluating last-7-days metrics,
   which are always partial for accounts with offline imports.

This service reads the OfflineConversion table and returns:
    - Overall upload health (success rate, last upload age, pending/failed counts).
    - Lag distribution (min/avg/median/p90/max days between conversion_time and uploaded_at).
    - Per-conversion-action summary if multiple actions are used.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.offline_conversion import OfflineConversion


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    srt = sorted(values)
    k = int(round(pct * (len(srt) - 1)))
    return srt[k]


def offline_conversion_lag(db: Session, client_id: int, days: int = 90) -> dict:
    """Return health + lag stats for offline conversions in the last `days`."""
    rows = (
        db.query(OfflineConversion)
        .filter(OfflineConversion.client_id == client_id)
        .order_by(OfflineConversion.conversion_time.desc())
        .limit(50_000)  # hard cap — avoid blowing memory on multi-year histories
        .all()
    )

    total = len(rows)
    uploaded = [r for r in rows if r.upload_status == "UPLOADED" and r.uploaded_at]
    pending = [r for r in rows if r.upload_status == "PENDING"]
    failed = [r for r in rows if r.upload_status == "FAILED"]

    # Lag distribution (days between conversion_time and uploaded_at)
    lags_days: list[float] = []
    for r in uploaded:
        if r.uploaded_at and r.conversion_time:
            diff = r.uploaded_at - r.conversion_time
            lag_d = diff.total_seconds() / 86400
            if 0 <= lag_d <= 365:  # sanity filter
                lags_days.append(lag_d)

    # Last upload age
    last_upload = None
    if uploaded:
        last_upload = max(r.uploaded_at for r in uploaded if r.uploaded_at)
    last_upload_age_hours = None
    if last_upload:
        last_upload_age_hours = round(
            (datetime.now(timezone.utc).replace(tzinfo=None) - last_upload).total_seconds() / 3600,
            1,
        )

    # Per-action breakdown
    per_action: dict[str, dict] = {}
    for r in rows:
        name = r.conversion_name or r.conversion_action_id or "(unnamed)"
        a = per_action.setdefault(name, {"total": 0, "uploaded": 0, "failed": 0, "pending": 0})
        a["total"] += 1
        if r.upload_status == "UPLOADED":
            a["uploaded"] += 1
        elif r.upload_status == "FAILED":
            a["failed"] += 1
        elif r.upload_status == "PENDING":
            a["pending"] += 1

    # Health signal
    health_flags: list[str] = []
    if last_upload_age_hours is not None and last_upload_age_hours > 48:
        health_flags.append(f"STALE_UPLOAD_{int(last_upload_age_hours)}H")
    if failed and total > 0 and len(failed) / total > 0.1:
        health_flags.append(f"FAILURE_RATE_{round(len(failed) / total * 100)}PCT")
    if pending and last_upload_age_hours is not None and last_upload_age_hours > 24:
        health_flags.append(f"PENDING_BACKLOG_{len(pending)}")

    return {
        "total_conversions": total,
        "uploaded_count": len(uploaded),
        "pending_count": len(pending),
        "failed_count": len(failed),
        "upload_success_rate_pct": round((len(uploaded) / total * 100), 2) if total else None,
        "last_upload_at": last_upload.isoformat() + "Z" if last_upload else None,
        "last_upload_age_hours": last_upload_age_hours,
        "lag_stats_days": (
            {
                "min": round(min(lags_days), 2),
                "avg": round(sum(lags_days) / len(lags_days), 2),
                "median": round(median(lags_days), 2),
                "p90": round(_percentile(lags_days, 0.9), 2),
                "max": round(max(lags_days), 2),
                "sample_size": len(lags_days),
            }
            if lags_days else None
        ),
        "per_action": per_action,
        "health_flags": health_flags,
    }
