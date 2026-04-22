"""MCC + misc endpoints — accounts, offline conversions, value rules, bid modifiers,
topic performance, audiences list, Google-native recommendations."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Client
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/mcc-accounts")
def mcc_accounts(
    manager_customer_id: str = Query(..., description="Manager account CID"),
    db: Session = Depends(get_db),
):
    """List child accounts under an MCC manager."""
    from app.models.mcc_link import MccLink
    links = db.query(MccLink).filter(
        MccLink.manager_customer_id == manager_customer_id.replace("-", ""),
        MccLink.is_hidden == False,
    ).order_by(MccLink.client_descriptive_name).all()

    return {
        "accounts": [
            {
                "customer_id": l.client_customer_id,
                "name": l.client_descriptive_name,
                "status": l.status,
                "is_manager": l.is_manager,
                "local_client_id": l.local_client_id,
            }
            for l in links
        ],
        "total": len(links),
    }


@router.post("/offline-conversions/upload")
def upload_offline_conversions(
    client_id: int = Query(...),
    conversions: list[dict] = [],
    allow_demo_write: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Upload offline conversions via Google Ads API.

    Goes through canonical safety pipeline: demo guard → audit log.
    """
    from app.demo_guard import ensure_demo_write_allowed
    from app.services.google_ads import google_ads_service
    from app.services.write_safety import record_write_action

    ensure_demo_write_allowed(db, client_id, allow_demo_write=allow_demo_write, operation="Upload konwersji offline")

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if not conversions:
        return {
            "status": "info",
            "message": "Send POST with JSON body: [{gclid, conversion_action_id, conversion_time, conversion_value, currency_code}, ...]",
            "endpoint": "/analytics/offline-conversions/upload",
        }

    result = google_ads_service.upload_offline_conversions(
        db, client.google_customer_id, conversions
    )

    record_write_action(
        db,
        client_id=client_id,
        action_type="UPLOAD_OFFLINE_CONVERSIONS",
        entity_type="offline_conversion",
        entity_id=client_id,
        status="SUCCESS" if result.get("status") != "error" else "FAILED",
        execution_mode="LIVE" if google_ads_service.is_connected else "LOCAL",
        new_value={"conversion_count": len(conversions), "uploaded": result.get("uploaded", 0)},
        error_message=result.get("message") if result.get("status") == "error" else None,
    )
    db.commit()

    return result


@router.get("/offline-conversions")
def list_offline_conversions(
    client_id: int = Query(...),
    status: str = Query(None, description="PENDING, UPLOADED, FAILED"),
    db: Session = Depends(get_db),
):
    """List offline conversions for a client."""
    from app.models.offline_conversion import OfflineConversion

    query = db.query(OfflineConversion).filter(OfflineConversion.client_id == client_id)
    if status:
        query = query.filter(OfflineConversion.upload_status == status)
    convs = query.order_by(OfflineConversion.created_at.desc()).limit(100).all()

    return {
        "conversions": [
            {
                "id": c.id,
                "gclid": c.gclid,
                "conversion_name": c.conversion_name,
                "conversion_time": str(c.conversion_time),
                "conversion_value": c.conversion_value,
                "status": c.upload_status,
                "error": c.error_message,
                "uploaded_at": str(c.uploaded_at) if c.uploaded_at else None,
            }
            for c in convs
        ],
        "total": len(convs),
    }


@router.get("/conversion-value-rules")
def list_conversion_value_rules(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List conversion value rules."""
    from app.models.conversion_value_rule import ConversionValueRule

    rules = db.query(ConversionValueRule).filter(
        ConversionValueRule.client_id == client_id
    ).all()

    return {
        "rules": [
            {
                "id": r.id,
                "condition_type": r.condition_type,
                "condition_value": r.condition_value,
                "action_type": r.action_type,
                "action_value_micros": r.action_value_micros,
                "action_multiplier": r.action_multiplier,
                "status": r.status,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.get("/bid-modifiers")
def get_bid_modifiers(
    client_id: int = Query(...),
    campaign_id: int = Query(None),
    modifier_type: str = Query(None, description="DEVICE, LOCATION, AD_SCHEDULE"),
    db: Session = Depends(get_db),
):
    """List bid modifiers (device, location, ad schedule)."""
    from app.models.bid_modifier import BidModifier

    query = (
        db.query(BidModifier)
        .join(Campaign, BidModifier.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if campaign_id:
        query = query.filter(BidModifier.campaign_id == campaign_id)
    if modifier_type:
        query = query.filter(BidModifier.modifier_type == modifier_type)

    modifiers = query.order_by(BidModifier.modifier_type, BidModifier.campaign_id).all()

    items = []
    for m in modifiers:
        items.append({
            "id": m.id,
            "campaign_id": m.campaign_id,
            "modifier_type": m.modifier_type,
            "device_type": m.device_type,
            "location_id": m.location_id,
            "location_name": m.location_name,
            "day_of_week": m.day_of_week,
            "start_hour": m.start_hour,
            "end_hour": m.end_hour,
            "bid_modifier": m.bid_modifier,
        })
    return {"modifiers": items, "total": len(items)}


@router.get("/topic-performance")
def topic_performance(
    client_id: int = Query(...),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Topic targeting performance for Display/Video campaigns."""
    from app.models.topic import TopicPerformance

    start, end = resolve_dates(days, date_from, date_to)

    results = (
        db.query(
            TopicPerformance.topic_path,
            func.sum(TopicPerformance.clicks).label("clicks"),
            func.sum(TopicPerformance.impressions).label("impressions"),
            func.sum(TopicPerformance.cost_micros).label("cost"),
            func.sum(TopicPerformance.conversions).label("conv"),
            func.sum(TopicPerformance.conversion_value_micros).label("value"),
        )
        .join(Campaign, TopicPerformance.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id, TopicPerformance.date >= start, TopicPerformance.date <= end)
        .group_by(TopicPerformance.topic_path)
        .order_by(func.sum(TopicPerformance.cost_micros).desc())
        .limit(50)
        .all()
    )

    topics = []
    for r in results:
        cost = int(r.cost or 0) / 1_000_000
        conv = float(r.conv or 0)
        value = int(r.value or 0) / 1_000_000
        topics.append({
            "topic_path": r.topic_path,
            "clicks": int(r.clicks or 0),
            "impressions": int(r.impressions or 0),
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "value_usd": round(value, 2),
            "roas": round(value / cost, 2) if cost > 0 else 0,
        })
    return {"topics": topics, "total": len(topics)}


@router.get("/audiences-list")
def audiences_list(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List all synced audiences for a client."""
    from app.models.audience import Audience

    audiences = (
        db.query(Audience)
        .filter(Audience.client_id == client_id)
        .order_by(Audience.name)
        .all()
    )
    return {
        "audiences": [
            {
                "id": a.id,
                "google_audience_id": a.google_audience_id,
                "name": a.name,
                "type": a.audience_type,
                "status": a.status,
                "member_count": a.member_count,
            }
            for a in audiences
        ],
        "total": len(audiences),
    }


@router.get("/google-recommendations")
def google_recommendations_list(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List Google's native recommendations."""
    from app.models.google_recommendation import GoogleRecommendation

    recs = (
        db.query(GoogleRecommendation)
        .filter(GoogleRecommendation.client_id == client_id, GoogleRecommendation.dismissed == False)
        .order_by(GoogleRecommendation.recommendation_type)
        .all()
    )

    items = []
    for r in recs:
        items.append({
            "id": r.id,
            "type": r.recommendation_type,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
            "impact_estimate": r.impact_estimate,
            "status": r.status,
        })

    type_counts = {}
    for i in items:
        t = i["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "recommendations": items,
        "total": len(items),
        "by_type": type_counts,
    }
