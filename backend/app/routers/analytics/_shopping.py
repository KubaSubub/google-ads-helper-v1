"""Shopping product groups + placement exclusions and performance.

Two distinct endpoints expose different slices:
- `/shopping-product-groups` — severity audit via product_group_service
- `/shopping-product-groups-tree` — raw ProductGroup performance tree (renamed
  from a duplicate `/shopping-product-groups` that used to shadow the audit).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Client
from app.utils.date_utils import resolve_dates

router = APIRouter()


@router.get("/shopping-product-groups")
def shopping_product_groups(
    client_id: int = Query(..., description="Client ID"),
    severity: str = Query("ALL", description="HIGH / MEDIUM / LOW / ALL"),
    db: Session = Depends(get_db),
):
    """Shopping UNIT/SUBDIVISION findings: zero-impression (feed issue), zero-conv waste,
    low-ROAS vs campaign avg, high-ROAS underserved, orphan subdivisions.
    """
    from app.services.shopping_product_group_service import product_group_report

    items = product_group_report(db, client_id)
    if severity != "ALL":
        items = [i for i in items if i["severity"] == severity.upper()]
    return {"total": len(items), "items": items}


@router.get("/shopping-product-groups-tree")
def shopping_product_groups_tree(
    client_id: int = Query(...),
    campaign_id: int = Query(None, description="Filter by campaign"),
    db: Session = Depends(get_db),
):
    """Shopping product group performance tree."""
    from app.models.product_group import ProductGroup

    query = (
        db.query(ProductGroup)
        .join(Campaign, ProductGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if campaign_id:
        query = query.filter(ProductGroup.campaign_id == campaign_id)

    groups = query.order_by(ProductGroup.cost_micros.desc()).all()

    items = []
    for g in groups:
        cost = (g.cost_micros or 0) / 1_000_000
        conv_val = (g.conversion_value_micros or 0) / 1_000_000
        items.append({
            "id": g.id,
            "campaign_id": g.campaign_id,
            "criterion_id": g.google_criterion_id,
            "parent_criterion_id": g.parent_criterion_id,
            "case_type": g.case_value_type,
            "case_value": g.case_value or "(All products)",
            "partition_type": g.partition_type,
            "bid_usd": round(g.bid_micros / 1_000_000, 2) if g.bid_micros else 0,
            "clicks": g.clicks or 0,
            "impressions": g.impressions or 0,
            "cost_usd": round(cost, 2),
            "conversions": round(g.conversions or 0, 2),
            "value_usd": round(conv_val, 2),
            "ctr": round(g.ctr or 0, 2),
            "roas": round(conv_val / cost, 2) if cost > 0 else 0,
            "cpa_usd": round(cost / g.conversions, 2) if g.conversions and g.conversions > 0 else None,
        })

    total_cost = sum(i["cost_usd"] for i in items)
    total_conv = sum(i["conversions"] for i in items)
    total_value = sum(i["value_usd"] for i in items)

    return {
        "product_groups": items,
        "summary": {
            "total_groups": len(items),
            "total_cost_usd": round(total_cost, 2),
            "total_conversions": round(total_conv, 2),
            "total_value_usd": round(total_value, 2),
            "avg_roas": round(total_value / total_cost, 2) if total_cost > 0 else 0,
        },
    }


@router.post("/placement-exclusion")
def add_placement_exclusion(
    client_id: int = Query(...),
    campaign_id: int = Query(...),
    placement_url: str = Query(..., description="URL to exclude"),
    allow_demo_write: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Add a placement exclusion to a Display/Video campaign."""
    from app.demo_guard import ensure_demo_write_allowed
    from app.services.google_ads import google_ads_service
    from app.services.write_safety import record_write_action

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    ensure_demo_write_allowed(db, client_id, allow_demo_write=allow_demo_write, operation="Dodanie wykluczenia miejsca")

    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    result = google_ads_service.add_placement_exclusion(
        db, client.google_customer_id, campaign.google_campaign_id, placement_url
    )

    record_write_action(
        db,
        client_id=client_id,
        action_type="ADD_PLACEMENT_EXCLUSION",
        entity_type="campaign",
        entity_id=campaign_id,
        status="SUCCESS" if result.get("status") != "error" else "FAILED",
        execution_mode="LIVE" if google_ads_service.is_connected else "LOCAL",
        new_value={"placement_url": placement_url, "campaign_id": campaign_id},
        error_message=result.get("message") if result.get("status") == "error" else None,
    )
    db.commit()

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/placement-performance")
def placement_performance(
    client_id: int = Query(...),
    campaign_id: int = Query(None),
    days: int = Query(30, ge=7, le=90),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: Session = Depends(get_db),
):
    """Placement performance for Display/Video campaigns."""
    from app.models.placement import Placement

    start, end = resolve_dates(days, date_from, date_to)

    query = (
        db.query(
            Placement.placement_url,
            Placement.placement_type,
            Placement.display_name,
            func.sum(Placement.clicks).label("clicks"),
            func.sum(Placement.impressions).label("impressions"),
            func.sum(Placement.cost_micros).label("cost"),
            func.sum(Placement.conversions).label("conv"),
            func.sum(Placement.conversion_value_micros).label("value"),
            func.sum(Placement.video_views).label("views"),
            func.avg(Placement.video_view_rate).label("avg_view_rate"),
        )
        .join(Campaign, Placement.campaign_id == Campaign.id)
        .filter(
            Campaign.client_id == client_id,
            Placement.date >= start,
            Placement.date <= end,
        )
    )
    if campaign_id:
        query = query.filter(Placement.campaign_id == campaign_id)

    results = (
        query
        .group_by(Placement.placement_url, Placement.placement_type, Placement.display_name)
        .order_by(func.sum(Placement.cost_micros).desc())
        .limit(100)
        .all()
    )

    placements = []
    for r in results:
        cost = int(r.cost or 0) / 1_000_000
        conv = float(r.conv or 0)
        value = int(r.value or 0) / 1_000_000
        placements.append({
            "placement_url": r.placement_url,
            "placement_type": r.placement_type,
            "display_name": r.display_name,
            "clicks": int(r.clicks or 0),
            "impressions": int(r.impressions or 0),
            "cost_usd": round(cost, 2),
            "conversions": round(conv, 2),
            "value_usd": round(value, 2),
            "roas": round(value / cost, 2) if cost > 0 else 0,
            "cpa_usd": round(cost / conv, 2) if conv > 0 else None,
            "video_views": int(r.views) if r.views else None,
            "avg_view_rate": round(float(r.avg_view_rate), 1) if r.avg_view_rate else None,
        })

    total_cost = sum(p["cost_usd"] for p in placements)
    return {
        "placements": placements,
        "total_placements": len(placements),
        "total_cost_usd": round(total_cost, 2),
        "period": {"from": str(start), "to": str(end)},
    }
