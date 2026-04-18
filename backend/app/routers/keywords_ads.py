"""Keywords and Ads endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.demo_guard import ensure_demo_write_allowed
from app.dependencies import CommonFilters, common_filters
from app.models import Ad, AdGroup, Campaign, Keyword, KeywordDaily, NegativeKeyword
from app.models.action_log import ActionLog
from app.models.negative_keyword_list import NegativeKeywordList, NegativeKeywordListItem
from app.schemas import AdResponse, KeywordResponse, NegativeKeywordResponse, PaginatedResponse
from app.schemas.negative_keyword import (
    ApplyListRequest,
    NegativeKeywordCreate,
    NegativeKeywordListAddItems,
    NegativeKeywordListCreate,
    NegativeKeywordListDetailResponse,
    NegativeKeywordListItemResponse,
    NegativeKeywordListResponse,
)

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
    # campaign_type / campaign_status come pre-normalized by common_filters (None = no filter, no "ALL" sentinel)
    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type)
    if campaign_status:
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
    filters: CommonFilters = Depends(common_filters),
    keyword_status: str = Query(None, alias="status", description="Keyword status: ENABLED, PAUSED, REMOVED"),
    match_type: str = Query(None),
    include_removed: bool = Query(False, description="Include keywords marked as REMOVED in local cache"),
    search: str = Query(None),
    sort_by: str = Query("cost", description="cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List keywords with filtering. When date_from/date_to provided, metrics are aggregated from KeywordDaily."""

    if filters.client_id is None and filters.campaign_id is None:
        raise HTTPException(status_code=400, detail="client_id or campaign_id is required")

    client_id = filters.client_id
    campaign_id = filters.campaign_id
    ad_group_id = filters.ad_group_id
    status = keyword_status
    campaign_type = filters.campaign_type
    campaign_status = filters.campaign_status
    date_from = filters.date_from
    date_to = filters.date_to

    # Aggregation path when caller supplied a date range; snapshot path otherwise.
    if filters.dates_explicit:
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
                    func.coalesce(agg.c.agg_clicks, 0) * 100.0 / func.coalesce(agg.c.agg_impressions, 1),
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
                "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
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


@router.post("/negative-keywords/", response_model=list[NegativeKeywordResponse])
def create_negative_keywords(
    body: NegativeKeywordCreate,
    db: Session = Depends(get_db),
):
    """Create one or more negative keywords for a campaign or ad group.

    Goes through canonical safety pipeline: demo guard → validate_action → audit log.
    """
    from app.services.action_executor import SafetyViolationError, validate_action
    from app.services.write_safety import count_negatives_added_today, record_write_action

    ensure_demo_write_allowed(db, body.client_id)

    # Safety: check daily negative keyword limit
    negatives_today = count_negatives_added_today(db, body.client_id)
    try:
        validate_action("ADD_NEGATIVE", 0, 0, {"negatives_added_today": negatives_today})
    except SafetyViolationError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    scope = body.negative_scope.upper()
    if scope not in ("CAMPAIGN", "AD_GROUP"):
        raise HTTPException(400, "negative_scope must be CAMPAIGN or AD_GROUP")

    if scope == "CAMPAIGN":
        if not body.campaign_id:
            raise HTTPException(400, "campaign_id is required for CAMPAIGN scope")
        campaign = db.get(Campaign, body.campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign {body.campaign_id} not found")
    else:
        if not body.ad_group_id:
            raise HTTPException(400, "ad_group_id is required for AD_GROUP scope")
        ad_group = db.get(AdGroup, body.ad_group_id)
        if not ad_group:
            raise HTTPException(404, f"Ad group {body.ad_group_id} not found")
        if not body.campaign_id:
            body.campaign_id = ad_group.campaign_id

    created = []
    for raw_text in body.texts:
        text = raw_text.strip()
        if not text:
            continue

        existing = (
            db.query(NegativeKeyword)
            .filter(
                NegativeKeyword.client_id == body.client_id,
                NegativeKeyword.negative_scope == scope,
                func.lower(NegativeKeyword.text) == text.lower(),
                NegativeKeyword.match_type == body.match_type.upper(),
                NegativeKeyword.status != "REMOVED",
                NegativeKeyword.campaign_id == body.campaign_id if scope == "CAMPAIGN" else True,
                NegativeKeyword.ad_group_id == body.ad_group_id if scope == "AD_GROUP" else True,
            )
            .first()
        )
        if existing:
            continue

        negative = NegativeKeyword(
            client_id=body.client_id,
            campaign_id=body.campaign_id,
            ad_group_id=body.ad_group_id if scope == "AD_GROUP" else None,
            criterion_kind="NEGATIVE",
            text=text,
            match_type=body.match_type.upper(),
            negative_scope=scope,
            status="ENABLED",
            source="LOCAL_ACTION",
        )
        db.add(negative)
        db.flush()
        created.append(negative)

    db.commit()

    # Audit trail
    if created:
        record_write_action(
            db,
            client_id=body.client_id,
            action_type="ADD_NEGATIVE",
            entity_type="negative_keyword",
            entity_id=body.campaign_id or body.ad_group_id,
            new_value={
                "texts": [neg.text for neg in created],
                "scope": scope,
                "match_type": body.match_type,
                "count": len(created),
            },
        )
        db.commit()

    results = []
    for neg in created:
        campaign_name = db.query(Campaign.name).filter(Campaign.id == neg.campaign_id).scalar() if neg.campaign_id else None
        ad_group_name = db.query(AdGroup.name).filter(AdGroup.id == neg.ad_group_id).scalar() if neg.ad_group_id else None
        results.append(_serialize_negative_keyword(neg, campaign_name, ad_group_name))
    return results


@router.delete("/negative-keywords/{negative_keyword_id}")
def delete_negative_keyword(
    negative_keyword_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete a negative keyword (set status to REMOVED)."""
    neg = db.get(NegativeKeyword, negative_keyword_id)
    if not neg:
        raise HTTPException(404, "Negative keyword not found")
    ensure_demo_write_allowed(db, neg.client_id)
    neg.status = "REMOVED"
    db.commit()
    return {"status": "ok", "message": "Negative keyword removed"}


# ---------------------------------------------------------------------------
# Negative keyword lists
# ---------------------------------------------------------------------------


@router.get("/negative-keyword-lists/", response_model=list[NegativeKeywordListResponse])
def list_negative_keyword_lists(
    client_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List all negative keyword lists for a client."""
    rows = (
        db.query(
            NegativeKeywordList,
            func.count(NegativeKeywordListItem.id).label("item_count"),
        )
        .outerjoin(NegativeKeywordListItem, NegativeKeywordList.id == NegativeKeywordListItem.list_id)
        .filter(
            NegativeKeywordList.client_id == client_id,
            NegativeKeywordList.status != "REMOVED",
        )
        .group_by(NegativeKeywordList.id)
        .order_by(NegativeKeywordList.name.asc())
        .all()
    )
    return [
        NegativeKeywordListResponse(
            id=nkl.id,
            client_id=nkl.client_id,
            google_shared_set_id=nkl.google_shared_set_id,
            name=nkl.name,
            description=nkl.description,
            source=nkl.source or "LOCAL",
            status=nkl.status or "ENABLED",
            member_count=nkl.member_count or 0,
            item_count=item_count,
            created_at=nkl.created_at,
            updated_at=nkl.updated_at,
        )
        for nkl, item_count in rows
    ]


@router.post("/negative-keyword-lists/", response_model=NegativeKeywordListResponse)
def create_negative_keyword_list(
    body: NegativeKeywordListCreate,
    db: Session = Depends(get_db),
):
    """Create a new negative keyword list."""
    nkl = NegativeKeywordList(
        client_id=body.client_id,
        name=body.name,
        description=body.description,
    )
    db.add(nkl)
    db.commit()
    db.refresh(nkl)
    return NegativeKeywordListResponse(
        id=nkl.id,
        client_id=nkl.client_id,
        name=nkl.name,
        description=nkl.description,
        item_count=0,
        created_at=nkl.created_at,
        updated_at=nkl.updated_at,
    )


@router.get("/negative-keyword-lists/{list_id}", response_model=NegativeKeywordListDetailResponse)
def get_negative_keyword_list(
    list_id: int,
    db: Session = Depends(get_db),
):
    """Get a negative keyword list with all items."""
    nkl = db.get(NegativeKeywordList, list_id)
    if not nkl:
        raise HTTPException(404, "List not found")
    items = (
        db.query(NegativeKeywordListItem)
        .filter(NegativeKeywordListItem.list_id == list_id)
        .order_by(NegativeKeywordListItem.text.asc())
        .all()
    )
    return NegativeKeywordListDetailResponse(
        id=nkl.id,
        client_id=nkl.client_id,
        name=nkl.name,
        description=nkl.description,
        item_count=len(items),
        created_at=nkl.created_at,
        updated_at=nkl.updated_at,
        items=[
            NegativeKeywordListItemResponse(id=it.id, text=it.text, match_type=it.match_type, created_at=it.created_at)
            for it in items
        ],
    )


@router.delete("/negative-keyword-lists/{list_id}")
def delete_negative_keyword_list(
    list_id: int,
    db: Session = Depends(get_db),
):
    """Delete a negative keyword list and all its items."""
    nkl = db.get(NegativeKeywordList, list_id)
    if not nkl:
        raise HTTPException(404, "List not found")
    db.delete(nkl)
    db.commit()
    return {"status": "ok", "message": "List deleted"}


@router.post("/negative-keyword-lists/{list_id}/items", response_model=list[NegativeKeywordListItemResponse])
def add_items_to_list(
    list_id: int,
    body: NegativeKeywordListAddItems,
    db: Session = Depends(get_db),
):
    """Add keywords to a negative keyword list (duplicates are skipped)."""
    nkl = db.get(NegativeKeywordList, list_id)
    if not nkl:
        raise HTTPException(404, "List not found")

    created = []
    for raw_text in body.texts:
        text = raw_text.strip()
        if not text:
            continue
        exists = (
            db.query(NegativeKeywordListItem)
            .filter(
                NegativeKeywordListItem.list_id == list_id,
                func.lower(NegativeKeywordListItem.text) == text.lower(),
                NegativeKeywordListItem.match_type == body.match_type.upper(),
            )
            .first()
        )
        if exists:
            continue
        item = NegativeKeywordListItem(list_id=list_id, text=text, match_type=body.match_type.upper())
        db.add(item)
        db.flush()
        created.append(item)
    db.commit()
    return [
        NegativeKeywordListItemResponse(id=it.id, text=it.text, match_type=it.match_type, created_at=it.created_at)
        for it in created
    ]


@router.delete("/negative-keyword-lists/{list_id}/items/{item_id}")
def remove_item_from_list(
    list_id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    """Remove a single keyword from a list."""
    item = (
        db.query(NegativeKeywordListItem)
        .filter(NegativeKeywordListItem.id == item_id, NegativeKeywordListItem.list_id == list_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()
    return {"status": "ok", "message": "Item removed"}


@router.post("/negative-keyword-lists/{list_id}/apply")
def apply_negative_keyword_list(
    list_id: int,
    body: ApplyListRequest,
    db: Session = Depends(get_db),
):
    """Apply a negative keyword list to campaigns and/or ad groups.

    Creates NegativeKeyword records for each list item × target combination.
    Duplicates are silently skipped.
    """
    nkl = db.get(NegativeKeywordList, list_id)
    if not nkl:
        raise HTTPException(404, "List not found")
    ensure_demo_write_allowed(db, nkl.client_id)

    if not body.campaign_ids and not body.ad_group_ids:
        raise HTTPException(400, "Provide at least one campaign_id or ad_group_id")

    items = db.query(NegativeKeywordListItem).filter(NegativeKeywordListItem.list_id == list_id).all()
    if not items:
        return {"status": "ok", "created": 0, "skipped": 0}

    created_count = 0
    skipped_count = 0

    for campaign_id in body.campaign_ids:
        campaign = db.get(Campaign, campaign_id)
        if not campaign:
            continue
        for item in items:
            exists = (
                db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.client_id == nkl.client_id,
                    NegativeKeyword.campaign_id == campaign_id,
                    NegativeKeyword.negative_scope == "CAMPAIGN",
                    func.lower(NegativeKeyword.text) == item.text.lower(),
                    NegativeKeyword.match_type == item.match_type,
                    NegativeKeyword.status != "REMOVED",
                )
                .first()
            )
            if exists:
                skipped_count += 1
                continue
            neg = NegativeKeyword(
                client_id=nkl.client_id,
                campaign_id=campaign_id,
                criterion_kind="NEGATIVE",
                text=item.text,
                match_type=item.match_type,
                negative_scope="CAMPAIGN",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg)
            created_count += 1

    for ad_group_id in body.ad_group_ids:
        ad_group = db.get(AdGroup, ad_group_id)
        if not ad_group:
            continue
        for item in items:
            exists = (
                db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.client_id == nkl.client_id,
                    NegativeKeyword.ad_group_id == ad_group_id,
                    NegativeKeyword.negative_scope == "AD_GROUP",
                    func.lower(NegativeKeyword.text) == item.text.lower(),
                    NegativeKeyword.match_type == item.match_type,
                    NegativeKeyword.status != "REMOVED",
                )
                .first()
            )
            if exists:
                skipped_count += 1
                continue
            neg = NegativeKeyword(
                client_id=nkl.client_id,
                campaign_id=ad_group.campaign_id,
                ad_group_id=ad_group_id,
                criterion_kind="NEGATIVE",
                text=item.text,
                match_type=item.match_type,
                negative_scope="AD_GROUP",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg)
            created_count += 1

    db.commit()
    return {"status": "ok", "created": created_count, "skipped": skipped_count}


# ---------------------------------------------------------------------------
# Ad Groups (lightweight lookup)
# ---------------------------------------------------------------------------


@router.get("/ad-groups/")
def list_ad_groups(
    client_id: int = Query(None),
    campaign_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """Lightweight ad group lookup for dropdowns."""
    query = db.query(AdGroup.id, AdGroup.name, AdGroup.campaign_id).join(Campaign, AdGroup.campaign_id == Campaign.id)
    if client_id:
        query = query.filter(Campaign.client_id == client_id)
    if campaign_id:
        query = query.filter(AdGroup.campaign_id == campaign_id)
    query = query.filter(AdGroup.status != "REMOVED").order_by(AdGroup.name.asc())
    rows = query.all()
    return [{"id": r.id, "name": r.name, "campaign_id": r.campaign_id} for r in rows]


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


# ---------------------------------------------------------------------------
# RSA Ad-Group Health Report
# ---------------------------------------------------------------------------

@router.get("/rsa-health")
def rsa_health(
    client_id: int = Query(..., description="Client ID"),
    severity: str = Query("ALL", description="HIGH / MEDIUM / LOW / OK / ALL"),
    db: Session = Depends(get_db),
):
    """Per-ad-group RSA health report (SEARCH only). No new API sync — uses local cache.

    Flags single-RSA ad groups, ad groups without any GOOD/EXCELLENT ad, under-filled RSAs.
    For full asset-level performance (per-headline CTR / performance_label) a new sync
    of `ad_group_ad_asset_view` is required and is not yet implemented.
    """
    from app.services.rsa_health_service import ad_group_rsa_report

    items = ad_group_rsa_report(db, client_id)
    if severity != "ALL":
        items = [i for i in items if i["severity"] == severity.upper()]
    return {"total": len(items), "items": items}


# ---------------------------------------------------------------------------
# Keyword Cannibalization Detection
# ---------------------------------------------------------------------------

@router.get("/cannibalization")
def keyword_cannibalization(
    client_id: int = Query(..., description="Client ID"),
    severity: str = Query(
        "ALL",
        description="Filter by severity: HIGH, MEDIUM, LOW, ALL",
    ),
    limit: int = Query(100, ge=1, le=500),
    min_combined_cost_usd: float = Query(
        0.0,
        ge=0.0,
        description="Only return findings with combined keyword spend >= this amount",
    ),
    db: Session = Depends(get_db),
):
    """Surface keyword pairs that cannibalize each other.

    Three kinds: duplicate EXACT in same ad group (HIGH), EXACT vs PHRASE in same
    ad group (MEDIUM), cross-ad-group same text (MEDIUM). Results sorted by combined
    spend descending so high-impact cases surface first.
    """
    from app.services.keyword_cannibalization_service import detect_cannibalization

    findings = detect_cannibalization(db, client_id)
    if severity != "ALL":
        findings = [f for f in findings if f["severity"] == severity.upper()]
    findings = [f for f in findings if f["combined_cost_usd"] >= min_combined_cost_usd]
    return {
        "total": len(findings),
        "returned": min(len(findings), limit),
        "items": findings[:limit],
    }


# ---------------------------------------------------------------------------
# Negative Keyword ↔ Positive Keyword Conflict Detection
# ---------------------------------------------------------------------------

@router.get("/negative-conflicts")
def negative_keyword_conflicts(
    client_id: int = Query(..., description="Client ID"),
    limit: int = Query(100, ge=1, le=500, description="Max conflicts returned"),
    min_cost_usd: float = Query(
        0.0,
        ge=0.0,
        description="Only return conflicts where the blocked positive keyword's "
                    "spend is at least this amount in USD",
    ),
    db: Session = Depends(get_db),
):
    """Surface negative keywords that silently block positive keywords in the same scope.

    Example conflict: campaign-scoped phrase-match negative 'cheap shoes' blocks
    an ad-group exact-match positive 'cheap running shoes' — positive never serves.
    Sorted by blocked-positive spend descending so high-impact conflicts surface first.
    """
    from app.services.negative_conflict_service import detect_conflicts

    all_conflicts = detect_conflicts(db, client_id)
    filtered = [c for c in all_conflicts if (c["positive_cost_usd"] or 0) >= min_cost_usd]
    return {
        "total": len(filtered),
        "returned": min(len(filtered), limit),
        "items": filtered[:limit],
    }
