"""Keywords and Ads endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Keyword, Ad, AdGroup, Campaign
from app.schemas import KeywordResponse, AdResponse, PaginatedResponse

router = APIRouter(tags=["Keywords & Ads"])


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

@router.get("/keywords/", response_model=PaginatedResponse)
def list_keywords(
    client_id: int = Query(None),
    campaign_id: int = Query(None),
    ad_group_id: int = Query(None),
    status: str = Query(None),
    match_type: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("cost", description="cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List keywords with filtering."""
    query = db.query(Keyword)

    if client_id or campaign_id:
        query = query.join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        if campaign_id:
            query = query.filter(AdGroup.campaign_id == campaign_id)
        if client_id:
            query = query.join(Campaign, AdGroup.campaign_id == Campaign.id).filter(
                Campaign.client_id == client_id
            )
    if ad_group_id:
        query = query.filter(Keyword.ad_group_id == ad_group_id)
    if status:
        query = query.filter(Keyword.status == status.upper())
    if match_type:
        query = query.filter(Keyword.match_type == match_type.upper())
    if search:
        query = query.filter(Keyword.text.ilike(f"%{search}%"))

    _kw_sort_map = {"cost": "cost_micros", "bid": "bid_micros", "avg_cpc": "avg_cpc_micros", "cpa": "cpa_micros"}
    sort_field = _kw_sort_map.get(sort_by, sort_by)
    sort_col = getattr(Keyword, sort_field, Keyword.cost_micros)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[KeywordResponse.model_validate(k) for k in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ---------------------------------------------------------------------------
# Ads
# ---------------------------------------------------------------------------

@router.get("/ads/", response_model=PaginatedResponse)
def list_ads(
    client_id: int = Query(None),
    campaign_id: int = Query(None),
    ad_group_id: int = Query(None),
    status: str = Query(None),
    sort_by: str = Query("cost"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List ads with filtering."""
    query = db.query(Ad)

    if client_id or campaign_id:
        query = query.join(AdGroup, Ad.ad_group_id == AdGroup.id)
        if campaign_id:
            query = query.filter(AdGroup.campaign_id == campaign_id)
        if client_id:
            query = query.join(Campaign, AdGroup.campaign_id == Campaign.id).filter(
                Campaign.client_id == client_id
            )
    if ad_group_id:
        query = query.filter(Ad.ad_group_id == ad_group_id)
    if status:
        query = query.filter(Ad.status == status.upper())

    _ad_sort_map = {"cost": "cost_micros"}
    ad_sort_field = _ad_sort_map.get(sort_by, sort_by)
    sort_col = getattr(Ad, ad_sort_field, Ad.cost_micros)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[AdResponse.model_validate(a) for a in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
