"""Tests for offline conversion lag tracking."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models import Client
from app.models.offline_conversion import OfflineConversion
from app.services.offline_conversion_lag_service import (
    _percentile,
    offline_conversion_lag,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_percentile_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(values, 0.5) == 3.0
    assert _percentile(values, 0.0) == 1.0
    assert _percentile(values, 1.0) == 5.0


def test_percentile_empty():
    assert _percentile([], 0.5) == 0.0


def test_percentile_p90():
    values = list(range(11))  # 0-10
    # p90 of 11 values → index round(0.9 * 10) = 9 → value 9
    assert _percentile(values, 0.9) == 9


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


def _mk(db):
    client = Client(name="c", google_customer_id="gc"); db.add(client); db.flush()
    return client


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_empty_state(db):
    client = _mk(db)
    result = offline_conversion_lag(db, client.id)
    assert result["total_conversions"] == 0
    assert result["uploaded_count"] == 0
    assert result["lag_stats_days"] is None
    assert result["health_flags"] == []


def test_healthy_recent_uploads_no_flags(db):
    client = _mk(db)
    now = _now()
    # 3 conversions uploaded within 2h of happening, last upload 1h ago
    for i in range(3):
        conv_time = now - timedelta(hours=3 + i)
        db.add(OfflineConversion(
            client_id=client.id,
            gclid=f"g{i}",
            conversion_action_id="a1",
            conversion_name="purchase",
            conversion_time=conv_time,
            upload_status="UPLOADED",
            uploaded_at=now - timedelta(hours=1),
        ))
    db.commit()

    result = offline_conversion_lag(db, client.id)
    assert result["total_conversions"] == 3
    assert result["uploaded_count"] == 3
    assert result["upload_success_rate_pct"] == 100.0
    assert result["health_flags"] == []
    assert result["lag_stats_days"] is not None
    assert result["lag_stats_days"]["min"] >= 0


def test_stale_upload_flagged(db):
    client = _mk(db)
    now = _now()
    db.add(OfflineConversion(
        client_id=client.id,
        gclid="g1",
        conversion_time=now - timedelta(days=10),
        upload_status="UPLOADED",
        uploaded_at=now - timedelta(days=5),  # last upload 5 days ago
    ))
    db.commit()

    result = offline_conversion_lag(db, client.id)
    assert any(flag.startswith("STALE_UPLOAD_") for flag in result["health_flags"])


def test_high_failure_rate_flagged(db):
    client = _mk(db)
    now = _now()
    # 2 uploaded, 8 failed → 80% failure rate
    for i in range(2):
        db.add(OfflineConversion(
            client_id=client.id, gclid=f"ok{i}",
            conversion_time=now - timedelta(hours=4),
            upload_status="UPLOADED",
            uploaded_at=now - timedelta(hours=1),
        ))
    for i in range(8):
        db.add(OfflineConversion(
            client_id=client.id, gclid=f"fail{i}",
            conversion_time=now - timedelta(hours=4),
            upload_status="FAILED",
            error_message="API error",
        ))
    db.commit()

    result = offline_conversion_lag(db, client.id)
    assert result["failed_count"] == 8
    assert any(flag.startswith("FAILURE_RATE_") for flag in result["health_flags"])


def test_per_action_breakdown(db):
    client = _mk(db)
    now = _now()
    db.add(OfflineConversion(
        client_id=client.id, gclid="g1",
        conversion_name="purchase", conversion_time=now - timedelta(hours=4),
        upload_status="UPLOADED", uploaded_at=now - timedelta(hours=1),
    ))
    db.add(OfflineConversion(
        client_id=client.id, gclid="g2",
        conversion_name="lead", conversion_time=now - timedelta(hours=4),
        upload_status="FAILED",
    ))
    db.commit()

    result = offline_conversion_lag(db, client.id)
    assert "purchase" in result["per_action"]
    assert "lead" in result["per_action"]
    assert result["per_action"]["purchase"]["uploaded"] == 1
    assert result["per_action"]["lead"]["failed"] == 1


def test_lag_stats_aggregate(db):
    client = _mk(db)
    now = _now()
    # 3 uploads with known lags: 1 day, 2 days, 4 days → median 2
    for i, lag_days in enumerate([1, 2, 4]):
        db.add(OfflineConversion(
            client_id=client.id, gclid=f"g{i}",
            conversion_time=now - timedelta(days=lag_days + 1),
            upload_status="UPLOADED",
            uploaded_at=now - timedelta(days=1),  # normalized to 1 day ago
        ))
    db.commit()

    result = offline_conversion_lag(db, client.id)
    lag = result["lag_stats_days"]
    assert lag is not None
    assert lag["sample_size"] == 3
    assert lag["min"] <= lag["median"] <= lag["max"]
