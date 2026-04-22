"""One-shot backfill for hourly MetricSegmented rows.

Context: the seed populates hour_of_day segments only for the demo client
(id=1). Real clients discovered via MCC have no hourly data because there is
no `hourly_metrics` phase in sync_config.PHASE_REGISTRY yet, so the
HourlyDaypartingWidget and DowHourHeatmapWidget fall back to their empty
state. This script synthesises realistic hourly rows for every client that
has SEARCH/SHOPPING/PMax campaigns but no hour_of_day coverage — so the
widgets can be verified visually until a proper API-backed phase is added.

Idempotent: skips any client that already has hour_of_day rows.
Run from repo root: `python backend/backfill_hourly_segments.py`.
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure we resolve `app.*` when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Campaign, MetricSegmented

# Same profile as seed.py — peak mornings + lunchtime + late afternoon
HOUR_PROFILE = {
    0: 0.05, 1: 0.03, 2: 0.02, 3: 0.02, 4: 0.03, 5: 0.05,
    6: 0.10, 7: 0.30, 8: 0.70, 9: 0.90, 10: 1.00, 11: 0.95,
    12: 0.80, 13: 0.75, 14: 0.85, 15: 0.90, 16: 0.95, 17: 1.00,
    18: 0.85, 19: 0.70, 20: 0.55, 21: 0.40, 22: 0.25, 23: 0.12,
}

# Dayparting-capable campaign types (Google Ads supports hour segmentation
# on Search/Shopping/Performance Max).
CAPABLE_TYPES = {"SEARCH", "SHOPPING", "PERFORMANCE_MAX"}

WINDOW_DAYS = 30


def backfill(dry_run: bool = False) -> None:
    db = SessionLocal()
    rng = random.Random(42)
    try:
        client_ids = [cid for (cid,) in db.query(Campaign.client_id).distinct().all()]
        total_added = 0

        for client_id in sorted(client_ids):
            existing = (
                db.query(func.count(MetricSegmented.id))
                .join(Campaign, MetricSegmented.campaign_id == Campaign.id)
                .filter(
                    Campaign.client_id == client_id,
                    MetricSegmented.hour_of_day.isnot(None),
                )
                .scalar()
            )
            if existing:
                print(f"[skip] client {client_id}: already has {existing} hourly rows")
                continue

            campaigns = (
                db.query(Campaign)
                .filter(
                    Campaign.client_id == client_id,
                    Campaign.campaign_type.in_(CAPABLE_TYPES),
                    Campaign.status != "REMOVED",
                )
                .all()
            )
            if not campaigns:
                print(f"[skip] client {client_id}: no Search/Shopping/PMax campaigns")
                continue

            added_here = 0
            for campaign in campaigns:
                for day_offset in range(WINDOW_DAYS):
                    d = date.today() - timedelta(days=day_offset)
                    dow_factor = 0.7 if d.weekday() >= 5 else 1.0
                    total_daily_clicks = int(rng.randint(60, 200) * dow_factor)

                    for hour, weight in HOUR_PROFILE.items():
                        hour_clicks = max(0, int(total_daily_clicks * weight * rng.uniform(0.7, 1.3)))
                        if hour_clicks == 0:
                            continue
                        hour_impressions = int(hour_clicks * rng.uniform(8, 20))
                        hour_cost = round(hour_clicks * rng.uniform(0.8, 3.5), 2)
                        conv_rate = 0.05 if 9 <= hour <= 18 else 0.01
                        hour_conv = round(max(0, hour_clicks * conv_rate * rng.uniform(0.5, 1.5)), 2)
                        hour_cv = round(hour_conv * rng.uniform(100, 250), 2)

                        if not dry_run:
                            db.add(MetricSegmented(
                                campaign_id=campaign.id,
                                date=d,
                                device=None,
                                geo_city=None,
                                hour_of_day=hour,
                                clicks=hour_clicks,
                                impressions=hour_impressions,
                                ctr=round(hour_clicks / hour_impressions * 100, 2) if hour_impressions else 0,
                                conversions=hour_conv,
                                conversion_value_micros=int(hour_cv * 1_000_000),
                                cost_micros=int(hour_cost * 1_000_000),
                                avg_cpc_micros=int((hour_cost / hour_clicks) * 1_000_000) if hour_clicks else 0,
                            ))
                        added_here += 1

            if not dry_run:
                db.commit()
            print(f"[done] client {client_id}: +{added_here} hourly rows across {len(campaigns)} campaigns")
            total_added += added_here

        print(f"\nBackfill complete: +{total_added} rows{'  (DRY-RUN)' if dry_run else ''}")
    finally:
        db.close()


if __name__ == "__main__":
    backfill(dry_run="--dry" in sys.argv)
