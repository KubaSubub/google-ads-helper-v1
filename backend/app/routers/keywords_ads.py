"""Keywords and Ads endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Keyword, Ad, AdGroup, Campaign, KeywordDaily
from app.schemas import KeywordResponse, AdResponse, PaginatedResponse

router = APIRouter(tags=["Keywords & Ads"])


def _apply_keyword_filters(query, client_id, campaign_id, ad_group_id,
                           status, match_type, campaign_type, campaign_status, search):
    """Apply common keyword filters (client, campaign, ad_group, status, match_type, search)."""
    needs_campaign_join = client_id or campaign_type or campaign_status
    needs_adgroup_join = campaign_id or needs_campaign_join

    if needs_adgroup_join:
        query = query.join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        if campaign_id:
            query = query.filter(AdGroup.campaign_id == campaign_id)
        if needs_campaign_join:
            query = query.join(Campaign, AdGroup.campaign_id == Campaign.id)
            if client_id:
                query = query.filter(Campaign.client_id == client_id)
            if campaign_type and campaign_type != "ALL":
                query = query.filter(Campaign.campaign_type == campaign_type)
            if campaign_status and campaign_status != "ALL":
                query = query.filter(Campaign.status == campaign_status)
    if ad_group_id:
        query = query.filter(Keyword.ad_group_id == ad_group_id)
    if status:
        query = query.filter(Keyword.status == status.upper())
    if match_type:
        query = query.filter(Keyword.match_type == match_type.upper())
    if search:
        query = query.filter(Keyword.text.ilike(f"%{search}%"))
    return query


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
    campaign_type: str = Query(None, description="Filter by campaign type: SEARCH, PERFORMANCE_MAX, etc."),
    campaign_status: str = Query(None, description="Filter by campaign status: ENABLED, PAUSED"),
    date_from: date = Query(None, description="Aggregate daily metrics from this date"),
    date_to: date = Query(None, description="Aggregate daily metrics to this date"),
    search: str = Query(None),
    sort_by: str = Query("cost", description="cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List keywords with filtering. When date_from/date_to provided, metrics
    are aggregated from KeywordDaily; otherwise snapshot values from Keyword."""

    # ── Aggregated daily path ──
    if date_from is not None and date_to is not None:
        agg = (
            db.query(
                KeywordDaily.keyword_id,
                func.coalesce(func.sum(KeywordDaily.clicks), 0).label("agg_clicks"),
                func.coalesce(func.sum(KeywordDaily.impressions), 0).label("agg_impressions"),
                func.coalesce(func.sum(KeywordDaily.cost_micros), 0).label("agg_cost_micros"),
                func.coalesce(func.sum(KeywordDaily.conversions), 0.0).label("agg_conversions"),
                func.coalesce(func.sum(KeywordDaily.conversion_value_micros), 0).label("agg_cv_micros"),
            )
            .filter(KeywordDaily.date >= date_from, KeywordDaily.date <= date_to)
            .group_by(KeywordDaily.keyword_id)
            .subquery()
        )

        query = (
            db.query(Keyword)
            .outerjoin(agg, Keyword.id == agg.c.keyword_id)
            .add_columns(
                func.coalesce(agg.c.agg_clicks, 0),
                func.coalesce(agg.c.agg_impressions, 0),
                func.coalesce(agg.c.agg_cost_micros, 0),
                func.coalesce(agg.c.agg_conversions, 0.0),
                func.coalesce(agg.c.agg_cv_micros, 0),
            )
        )

        query = _apply_keyword_filters(
            query, client_id, campaign_id, ad_group_id,
            status, match_type, campaign_type, campaign_status, search,
        )

        # Sorting on aggregated columns
        _agg_sort = {
            "cost": func.coalesce(agg.c.agg_cost_micros, 0),
            "cost_micros": func.coalesce(agg.c.agg_cost_micros, 0),
            "clicks": func.coalesce(agg.c.agg_clicks, 0),
            "impressions": func.coalesce(agg.c.agg_impressions, 0),
            "conversions": func.coalesce(agg.c.agg_conversions, 0),
            "ctr": case(
                (func.coalesce(agg.c.agg_impressions, 0) > 0,
                 func.coalesce(agg.c.agg_clicks, 0) * 1000000
                 / func.coalesce(agg.c.agg_impressions, 1)),
                else_=0,
            ),
        }
        sort_col = _agg_sort.get(sort_by, func.coalesce(agg.c.agg_cost_micros, 0))
        query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for row in rows:
            kw = row[0]
            clicks = row[1] or 0
            impressions = row[2] or 0
            cost_micros = row[3] or 0
            conversions = float(row[4] or 0)
            cv_micros = row[5] or 0

            kw_dict = {c.name: getattr(kw, c.name) for c in Keyword.__table__.columns}
            kw_dict.update({
                "clicks": clicks,
                "impressions": impressions,
                "cost_micros": cost_micros,
                "conversions": conversions,
                "conversion_value_micros": cv_micros,
                "ctr": int(clicks / impressions * 1_000_000) if impressions > 0 else 0,
                "avg_cpc_micros": int(cost_micros / clicks) if clicks > 0 else 0,
                "cpa_micros": int(cost_micros / conversions) if conversions > 0 else 0,
            })
            items.append(KeywordResponse.model_validate(kw_dict))

        return PaginatedResponse(
            items=items,
            total=total, page=page, page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    # ── Snapshot path (no dates — backward compatible) ──
    query = db.query(Keyword)
    query = _apply_keyword_filters(
        query, client_id, campaign_id, ad_group_id,
        status, match_type, campaign_type, campaign_status, search,
    )

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
