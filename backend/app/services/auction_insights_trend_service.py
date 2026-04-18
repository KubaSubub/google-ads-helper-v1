"""Auction Insights trend analysis.

Google Ads exposes a snapshot of competitor visibility (impression share, overlap,
outranking, top-of-page) per campaign per day. Staring at the snapshot tells you
who's around today; the trend tells you who's *gaining on you* and how fast.

This service computes, per competitor domain within a campaign:
    - current-window avg IS / outranking / overlap
    - previous-window avg (same length, immediately prior)
    - delta (pp = percentage points, already on the 0-100 display scale)
    - slope per day across the full current window (simple linear regression)
    - rising_fast flag when outranking/IS delta exceeds a threshold over 7 days

Trend interpretation (surfaced as `trend_label`):
    - RISING_FAST:  outranking or IS delta >= +5 pp over the window.
                    Competitor is taking market share from you; budget up, bid up,
                    or improve QS before it gets worse.
    - RISING:       delta >= +2 pp.
    - STABLE:       |delta| < 2 pp.
    - FALLING:      delta <= -2 pp.
    - FALLING_FAST: delta <= -5 pp (you're gaining on them).

Window default is 14 days — long enough to smooth auction noise, short enough
to catch a fresh competitor campaign ramp-up.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.auction_insight import AuctionInsight
from app.models.campaign import Campaign


RISING_FAST_DELTA_PP = 5.0
RISING_DELTA_PP = 2.0


def _avg(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _linear_slope(pairs: list[tuple[int, float]]) -> float:
    """Slope of y vs x using least-squares. Returns 0 when fewer than 2 points."""
    n = len(pairs)
    if n < 2:
        return 0.0
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return (num / den) if den else 0.0


def _label(delta_pp: float) -> str:
    if delta_pp >= RISING_FAST_DELTA_PP:
        return "RISING_FAST"
    if delta_pp >= RISING_DELTA_PP:
        return "RISING"
    if delta_pp <= -RISING_FAST_DELTA_PP:
        return "FALLING_FAST"
    if delta_pp <= -RISING_DELTA_PP:
        return "FALLING"
    return "STABLE"


def _collect(db: Session, client_id: int, window_days: int) -> dict:
    today = date.today()
    current_start = today - timedelta(days=window_days)
    previous_start = current_start - timedelta(days=window_days)

    rows = (
        db.query(AuctionInsight, Campaign.name)
        .join(Campaign, AuctionInsight.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            AuctionInsight.date >= previous_start,
            AuctionInsight.date < today,
        )
        .all()
    )

    # Group by (campaign_id, domain) -> list[(date, AuctionInsight, campaign_name)]
    groups: dict[tuple[int, str], dict] = defaultdict(
        lambda: {"current": [], "previous": [], "campaign_name": None}
    )
    for insight, camp_name in rows:
        key = (insight.campaign_id, insight.display_domain)
        bucket = groups[key]
        bucket["campaign_name"] = camp_name
        if insight.date >= current_start:
            bucket["current"].append(insight)
        else:
            bucket["previous"].append(insight)
    return groups


def compute_trends(
    db: Session, client_id: int, window_days: int = 14
) -> list[dict]:
    """Return per-competitor trend entries, sorted by outranking_delta_pp desc."""
    groups = _collect(db, client_id, window_days)
    out: list[dict] = []

    today = date.today()
    current_start = today - timedelta(days=window_days)

    for (campaign_id, domain), bucket in groups.items():
        cur = bucket["current"]
        prev = bucket["previous"]
        if not cur:
            continue

        cur_is = _avg([i.impression_share or 0.0 for i in cur]) * 100
        prev_is = _avg([i.impression_share or 0.0 for i in prev]) * 100 if prev else cur_is

        cur_outrank = _avg([i.outranking_share or 0.0 for i in cur]) * 100
        prev_outrank = _avg([i.outranking_share or 0.0 for i in prev]) * 100 if prev else cur_outrank

        cur_overlap = _avg([i.overlap_rate or 0.0 for i in cur]) * 100
        prev_overlap = _avg([i.overlap_rate or 0.0 for i in prev]) * 100 if prev else cur_overlap

        # Slope on outranking over the current window (pp/day)
        pairs = [
            ((i.date - current_start).days, (i.outranking_share or 0.0) * 100)
            for i in sorted(cur, key=lambda x: x.date)
        ]
        slope = _linear_slope(pairs)

        outrank_delta = cur_outrank - prev_outrank
        is_delta = cur_is - prev_is
        overlap_delta = cur_overlap - prev_overlap

        # Label driven by the stronger signal — outranking is the most actionable.
        driver_delta = outrank_delta if abs(outrank_delta) >= abs(is_delta) else is_delta
        label = _label(driver_delta)

        out.append({
            "campaign_id": campaign_id,
            "campaign_name": bucket["campaign_name"],
            "competitor_domain": domain,
            "window_days": window_days,
            "current_impression_share_pct": round(cur_is, 2),
            "previous_impression_share_pct": round(prev_is, 2),
            "impression_share_delta_pp": round(is_delta, 2),
            "current_outranking_share_pct": round(cur_outrank, 2),
            "previous_outranking_share_pct": round(prev_outrank, 2),
            "outranking_share_delta_pp": round(outrank_delta, 2),
            "current_overlap_rate_pct": round(cur_overlap, 2),
            "previous_overlap_rate_pct": round(prev_overlap, 2),
            "overlap_rate_delta_pp": round(overlap_delta, 2),
            "outranking_slope_pp_per_day": round(slope, 3),
            "trend_label": label,
            "data_points_current": len(cur),
            "data_points_previous": len(prev),
        })

    out.sort(key=lambda r: r["outranking_share_delta_pp"], reverse=True)
    return out
