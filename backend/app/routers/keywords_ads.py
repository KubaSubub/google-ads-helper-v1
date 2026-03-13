"""Keywords and Ads endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ad, AdGroup, Campaign, Keyword, KeywordDaily, NegativeKeyword
from app.schemas import AdResponse, KeywordResponse, NegativeKeywordResponse, PaginatedResponse

router = APIRouter(tags=["Keywords & Ads"])


def _apply_keyword_filters(
    query,
    client_id,
    campaign_id,
    ad_group_id,
    status,
    match_type,
    campaign_type,
    campaign_status,
    search,
    include_removed,
):
    """Apply common keyword filters (client, campaign, ad_group, status, match_type, search)."""
    if client_id:
        query = query.filter(Campaign.client_id == client_id)
    if campaign_id:
        query = query.filter(AdGroup.campaign_id == campaign_id)
    if ad_group_id:
        query = query.filter(Keyword.ad_group_id == ad_group_id)
    if status:
        query = query.filter(Keyword.status == status.upper())
    elif not include_removed:
        query = query.filter(Keyword.status.in_(("ENABLED", "PAUSED")))
    if match_type:
        query = query.filter(Keyword.match_type == match_type.upper())
    if campaign_type and campaign_type != "ALL":
        query = query.filter(Campaign.campaign_type == campaign_type)
    if campaign_status and campaign_status != "ALL":
        query = query.filter(Campaign.status == campaign_status)
    if search:
        query = query.filter(Keyword.text.ilike(f"%{search}%"))
    return query


def _serialize_keyword(keyword: Keyword, campaign_id: int, campaign_name: str, ad_group_name: str, metrics: dict | None = None):
    keyword_data = {column.name: getattr(keyword, column.name) for column in Keyword.__table__.columns}
    keyword_data["criterion_kind"] = keyword_data.get("criterion_kind") or "POSITIVE"
    keyword_data.update(
        {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "ad_group_name": ad_group_name,
        }
    )
    if metrics:
        keyword_data.update(metrics)
    return KeywordResponse.model_validate(keyword_data)


def _apply_negative_keyword_filters(
    query,
    client_id,
    campaign_id,
    ad_group_id,
    status,
    negative_scope,
    search,
    include_removed,
):
    if client_id:
        query = query.filter(NegativeKeyword.client_id == client_id)
    if campaign_id:
        query = query.filter(NegativeKeyword.campaign_id == campaign_id)
    if ad_group_id:
        query = query.filter(NegativeKeyword.ad_group_id == ad_group_id)
    if status:
        query = query.filter(NegativeKeyword.status == status.upper())
    elif not include_removed:
        query = query.filter(NegativeKeyword.status != "REMOVED")
    if negative_scope:
        query = query.filter(NegativeKeyword.negative_scope == negative_scope.upper())
    if search:
        query = query.filter(NegativeKeyword.text.ilike(f"%{search}%"))
    return query


def _serialize_negative_keyword(
    keyword: NegativeKeyword,
    campaign_name: str | None,
    ad_group_name: str | None,
):
    payload = {column.name: getattr(keyword, column.name) for column in NegativeKeyword.__table__.columns}
    payload["criterion_kind"] = payload.get("criterion_kind") or "NEGATIVE"
    payload["negative_scope"] = payload.get("negative_scope") or "CAMPAIGN"
    payload["source"] = payload.get("source") or "LOCAL_ACTION"
    payload.update(
        {
            "campaign_name": campaign_name,
            "ad_group_name": ad_group_name,
        }
    )
    return NegativeKeywordResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


@router.get("/keywords/", response_model=PaginatedResponse[KeywordResponse])
def list_keywords(
    client_id: int = Query(None),
    campaign_id: int = Query(None),
    ad_group_id: int = Query(None),
    status: str = Query(None),
    match_type: str = Query(None),
    campaign_type: str = Query(None, description="Filter by campaign type: SEARCH, PERFORMANCE_MAX, etc."),
    campaign_status: str = Query(None, description="Filter by campaign status: ENABLED, PAUSED, REMOVED"),
    include_removed: bool = Query(False, description="Include keywords marked as REMOVED in local cache"),
    date_from: date = Query(None, description="Aggregate daily metrics from this date"),
    date_to: date = Query(None, description="Aggregate daily metrics to this date"),
    search: str = Query(None),
    sort_by: str = Query("cost", description="cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List keywords with filtering. When date_from/date_to provided, metrics are aggregated from KeywordDaily."""

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
            db.query(
                Keyword,
                Campaign.id.label("campaign_id"),
                Campaign.name.label("campaign_name"),
                AdGroup.name.label("ad_group_name"),
            )
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .outerjoin(agg, Keyword.id == agg.c.keyword_id)
            .add_columns(
                func.coalesce(agg.c.agg_clicks, 0).label("agg_clicks"),
                func.coalesce(agg.c.agg_impressions, 0).label("agg_impressions"),
                func.coalesce(agg.c.agg_cost_micros, 0).label("agg_cost_micros"),
                func.coalesce(agg.c.agg_conversions, 0.0).label("agg_conversions"),
                func.coalesce(agg.c.agg_cv_micros, 0).label("agg_cv_micros"),
            )
        )

        query = _apply_keyword_filters(
            query,
            client_id,
            campaign_id,
            ad_group_id,
            status,
            match_type,
            campaign_type,
            campaign_status,
            search,
            include_removed,
        )

        sort_map = {
            "cost": func.coalesce(agg.c.agg_cost_micros, 0),
            "cost_micros": func.coalesce(agg.c.agg_cost_micros, 0),
            "clicks": func.coalesce(agg.c.agg_clicks, 0),
            "impressions": func.coalesce(agg.c.agg_impressions, 0),
            "conversions": func.coalesce(agg.c.agg_conversions, 0),
            "ctr": case(
                (
                    func.coalesce(agg.c.agg_impressions, 0) > 0,
                    func.coalesce(agg.c.agg_clicks, 0) * 1_000_000 / func.coalesce(agg.c.agg_impressions, 1),
                ),
                else_=0,
            ),
        }
        sort_col = sort_map.get(sort_by, func.coalesce(agg.c.agg_cost_micros, 0))
        query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for row in rows:
            keyword, row_campaign_id, row_campaign_name, row_ad_group_name, clicks, impressions, cost_micros, conversions, cv_micros = row
            clicks = clicks or 0
            impressions = impressions or 0
            cost_micros = cost_micros or 0
            conversions = float(conversions or 0)
            cv_micros = cv_micros or 0
            metrics = {
                "clicks": clicks,
                "impressions": impressions,
                "cost_micros": cost_micros,
                "conversions": conversions,
                "conversion_value_micros": cv_micros,
                "ctr": int(clicks / impressions * 1_000_000) if impressions > 0 else 0,
                "avg_cpc_micros": int(cost_micros / clicks) if clicks > 0 else 0,
                "cpa_micros": int(cost_micros / conversions) if conversions > 0 else 0,
            }
            items.append(_serialize_keyword(keyword, row_campaign_id, row_campaign_name, row_ad_group_name, metrics))

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    query = (
        db.query(
            Keyword,
            Campaign.id.label("campaign_id"),
            Campaign.name.label("campaign_name"),
            AdGroup.name.label("ad_group_name"),
        )
        .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
    )
    query = _apply_keyword_filters(
        query,
        client_id,
        campaign_id,
        ad_group_id,
        status,
        match_type,
        campaign_type,
        campaign_status,
        search,
        include_removed,
    )

    sort_map = {"cost": "cost_micros", "bid": "bid_micros", "avg_cpc": "avg_cpc_micros", "cpa": "cpa_micros"}
    sort_field = sort_map.get(sort_by, sort_by)
    sort_col = getattr(Keyword, sort_field, Keyword.cost_micros)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[_serialize_keyword(keyword, row_campaign_id, row_campaign_name, row_ad_group_name) for keyword, row_campaign_id, row_campaign_name, row_ad_group_name in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/negative-keywords/", response_model=PaginatedResponse[NegativeKeywordResponse])
def list_negative_keywords(
    client_id: int = Query(None),
    campaign_id: int = Query(None),
    ad_group_id: int = Query(None),
    status: str = Query(None),
    negative_scope: str = Query(None, description="Filter by negative scope: CAMPAIGN or AD_GROUP"),
    include_removed: bool = Query(False),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            NegativeKeyword,
            Campaign.name.label("campaign_name"),
            AdGroup.name.label("ad_group_name"),
        )
        .outerjoin(Campaign, NegativeKeyword.campaign_id == Campaign.id)
        .outerjoin(AdGroup, NegativeKeyword.ad_group_id == AdGroup.id)
    )
    query = _apply_negative_keyword_filters(
        query,
        client_id,
        campaign_id,
        ad_group_id,
        status,
        negative_scope,
        search,
        include_removed,
    )
    query = query.order_by(Campaign.name.asc(), AdGroup.name.asc(), NegativeKeyword.text.asc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[
            _serialize_negative_keyword(keyword, campaign_name, ad_group_name)
            for keyword, campaign_name, ad_group_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ---------------------------------------------------------------------------
# Ads
# ---------------------------------------------------------------------------


@router.get("/ads/", response_model=PaginatedResponse[AdResponse])
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
            query = query.join(Campaign, AdGroup.campaign_id == Campaign.id).filter(Campaign.client_id == client_id)
    if ad_group_id:
        query = query.filter(Ad.ad_group_id == ad_group_id)
    if status:
        query = query.filter(Ad.status == status.upper())

    sort_map = {"cost": "cost_micros"}
    sort_field = sort_map.get(sort_by, sort_by)
    sort_col = getattr(Ad, sort_field, Ad.cost_micros)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[AdResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
