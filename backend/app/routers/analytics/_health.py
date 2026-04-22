"""Health score, anomaly detection, z-score anomalies, anomaly resolution."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.demo_guard import ensure_demo_write_allowed
from app.models import Alert, Campaign, MetricDaily
from app.services.analytics_service import AnalyticsService

router = APIRouter()


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
                "campaign_name": a.campaign.name if a.campaign else None,
                "metric_value": a.metric_value,
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
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Mark an anomaly alert as resolved."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Rozwiazywanie alertu",
    )

    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.client_id == client_id,
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.resolved_at:
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return {"status": "success", "message": f"Alert {alert_id} resolved"}


@router.post("/detect")
def run_anomaly_detection(
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Run anomaly detection rules and create alerts."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Wykrywanie anomalii",
    )
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


@router.get("/z-score-anomalies")
def get_zscore_anomalies(
    client_id: int = Query(..., description="Client ID"),
    metric: str = Query("cost", description="Metric to analyze: cost, clicks, impressions, conversions, ctr"),
    threshold: float = Query(2.0, description="Z-score threshold"),
    days: int = Query(90, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Detect z-score anomalies per campaign per day for a given metric."""
    campaign_ids = [c.id for c in db.query(Campaign.id).filter(
        Campaign.client_id == client_id, Campaign.status == "ENABLED"
    ).all()]

    if not campaign_ids:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": 0}

    cutoff = date.today() - timedelta(days=days)
    rows = db.query(MetricDaily).filter(
        MetricDaily.campaign_id.in_(campaign_ids),
        MetricDaily.date >= cutoff,
    ).all()

    if not rows:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": 0}

    camp_names = {c.id: c.name for c in db.query(Campaign.id, Campaign.name).filter(
        Campaign.id.in_(campaign_ids)
    ).all()}

    day_agg = defaultdict(lambda: {"clicks": 0, "impressions": 0, "cost": 0.0,
                                    "conversions": 0.0, "campaigns": set()})
    for r in rows:
        d = day_agg[r.date]
        d["clicks"] += r.clicks or 0
        d["impressions"] += r.impressions or 0
        d["cost"] += (r.cost_micros or 0) / 1_000_000
        d["conversions"] += r.conversions or 0
        d["campaigns"].add(r.campaign_id)

    metric_map = {
        "cost": lambda d: d["cost"],
        "clicks": lambda d: float(d["clicks"]),
        "impressions": lambda d: float(d["impressions"]),
        "conversions": lambda d: d["conversions"],
        "ctr": lambda d: d["clicks"] / d["impressions"] if d["impressions"] > 0 else 0,
    }
    extract = metric_map.get(metric, metric_map["cost"])

    daily_values = []
    for dt in sorted(day_agg.keys()):
        val = extract(day_agg[dt])
        daily_values.append((dt, val))

    if len(daily_values) < 7:
        return {"anomalies": [], "mean": 0, "std": 0, "total_days": len(daily_values)}

    values = [v for _, v in daily_values]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0

    anomalies = []
    if std > 0:
        for dt, val in daily_values:
            z = (val - mean) / std
            if abs(z) >= threshold:
                camp_rows = [r for r in rows if r.date == dt]
                top_camp_id = None
                top_val = 0
                for cr in camp_rows:
                    cv = extract({
                        "clicks": cr.clicks or 0,
                        "impressions": cr.impressions or 0,
                        "cost": (cr.cost_micros or 0) / 1_000_000,
                        "conversions": cr.conversions or 0,
                    })
                    if cv > top_val:
                        top_val = cv
                        top_camp_id = cr.campaign_id

                anomalies.append({
                    "date": str(dt),
                    "value": round(val, 2),
                    "z_score": round(z, 2),
                    "direction": "spike" if z > 0 else "drop",
                    "campaign_id": top_camp_id,
                    "campaign_name": camp_names.get(top_camp_id, "?"),
                })

    anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)

    return {
        "anomalies": anomalies,
        "mean": round(mean, 2),
        "std": round(std, 2),
        "total_days": len(daily_values),
        "metric": metric,
        "threshold": threshold,
    }


@router.get("/health-score")
def get_health_score(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(None, ge=7, le=365, description="Lookback period (optional)"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Campaign status filter"),
    status: str = Query(None, description="Alias for campaign_status (backward compat)"),
    db: Session = Depends(get_db),
):
    """Account health score (0–100) with issue breakdown."""
    effective_status = campaign_status or status
    service = AnalyticsService(db)
    return service.get_health_score(
        client_id, campaign_type=campaign_type, campaign_status=effective_status,
        date_from=date_from, date_to=date_to, days=days,
    )
