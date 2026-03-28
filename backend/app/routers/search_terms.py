"""Search terms endpoints — list, filter, and segmented view."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.demo_guard import ensure_demo_write_allowed
from app.models import SearchTerm, AdGroup, Campaign
from app.models.negative_keyword import NegativeKeyword
from app.models.keyword import Keyword
from app.models.action_log import ActionLog
from app.schemas import SearchTermResponse, PaginatedResponse
from app.services.search_terms_service import SearchTermsService
from app.utils.formatters import micros_to_currency, currency_to_micros

router = APIRouter(prefix="/search-terms", tags=["Search Terms"])


# Column name mapping for sort_by (frontend uses display names)
_SORT_FIELD_MAP = {
    "cost": "cost_micros",
    "cost_micros": "cost_micros",
    "clicks": "clicks",
    "impressions": "impressions",
    "ctr": "ctr",
    "conversions": "conversions",
}


@router.get("/", response_model=PaginatedResponse[SearchTermResponse])
def list_search_terms(
    client_id: int = Query(None, description="Filter by client"),
    campaign_id: int = Query(None, description="Filter by campaign"),
    ad_group_id: int = Query(None, description="Filter by ad group"),
    min_clicks: int = Query(None, ge=0, description="Minimum clicks"),
    min_cost: float = Query(None, ge=0, description="Minimum cost in USD"),
    min_impressions: int = Query(None, ge=0, description="Minimum impressions"),
    campaign_type: str = Query(None, description="Filter by campaign type: SEARCH, PERFORMANCE_MAX, etc."),
    campaign_status: str = Query(None, description="Filter by campaign status: ENABLED, PAUSED"),
    date_from: date = Query(None),
    date_to: date = Query(None),
    search: str = Query(None, description="Full-text search in term text"),
    sort_by: str = Query("cost", description="Sort field: cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List search terms with filtering, sorting, and pagination."""
    query = db.query(SearchTerm)

    # Join through ad_group -> campaign for Search terms, OR direct campaign link for PMax
    if client_id or campaign_id:
        query = (
            query.outerjoin(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
            .outerjoin(
                Campaign,
                or_(
                    AdGroup.campaign_id == Campaign.id,
                    SearchTerm.campaign_id == Campaign.id,
                ),
            )
        )
        if campaign_id:
            query = query.filter(
                or_(
                    AdGroup.campaign_id == campaign_id,
                    SearchTerm.campaign_id == campaign_id,
                )
            )
        if client_id:
            query = query.filter(Campaign.client_id == client_id)
        if campaign_type and campaign_type != "ALL":
            query = query.filter(Campaign.campaign_type == campaign_type)
        if campaign_status and campaign_status != "ALL":
            query = query.filter(Campaign.status == campaign_status)

    if ad_group_id:
        query = query.filter(SearchTerm.ad_group_id == ad_group_id)
    if min_clicks is not None:
        query = query.filter(SearchTerm.clicks >= min_clicks)
    if min_cost is not None:
        # Convert USD to micros for DB comparison
        query = query.filter(SearchTerm.cost_micros >= currency_to_micros(min_cost))
    if min_impressions is not None:
        query = query.filter(SearchTerm.impressions >= min_impressions)
    # Overlap logic: show terms whose reporting period overlaps the selected range
    if date_from:
        query = query.filter(SearchTerm.date_to >= date_from)
    if date_to:
        query = query.filter(SearchTerm.date_from <= date_to)
    if search:
        query = query.filter(SearchTerm.text.ilike(f"%{search}%"))

    # Sorting — map frontend field names to actual DB columns
    db_field = _SORT_FIELD_MAP.get(sort_by, "cost_micros")
    sort_column = getattr(SearchTerm, db_field, SearchTerm.cost_micros)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[SearchTermResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/summary")
def search_terms_summary(
    campaign_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregated summary of search terms for a campaign."""
    cutoff = date.today() - timedelta(days=days)

    query = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .filter(AdGroup.campaign_id == campaign_id, SearchTerm.date_from >= cutoff)
    )

    terms = query.all()
    if not terms:
        return {"total_terms": 0, "total_cost_usd": 0, "total_clicks": 0, "top_by_cost": []}

    total_cost_micros = sum(t.cost_micros or 0 for t in terms)
    total_clicks = sum(t.clicks or 0 for t in terms)
    total_conversions = sum(t.conversions or 0 for t in terms)

    sorted_by_cost = sorted(terms, key=lambda t: t.cost_micros or 0, reverse=True)[:10]

    return {
        "total_terms": len(terms),
        "total_cost_usd": micros_to_currency(total_cost_micros),
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "top_by_cost": [
            {
                "text": t.text,
                "cost_usd": micros_to_currency(t.cost_micros),
                "clicks": t.clicks or 0,
                "conversions": t.conversions or 0,
                "ctr_pct": round(t.ctr or 0, 2),
            }
            for t in sorted_by_cost
        ],
    }


# ---------------------------------------------------------------------------
# Segmented Search Terms — delegates to SearchTermsService
# ---------------------------------------------------------------------------


@router.get("/segmented")
def segmented_search_terms(
    client_id: int = Query(..., description="Client ID"),
    date_from: date = Query(None),
    date_to: date = Query(None),
    campaign_type: str = Query(None, description="Filter by campaign type"),
    campaign_status: str = Query(None, description="Filter by campaign status"),
    db: Session = Depends(get_db),
):
    """Return search terms grouped by segment (HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER)."""
    service = SearchTermsService(db)
    return service.get_segmented_search_terms(
        client_id, date_from=date_from, date_to=date_to,
        campaign_type=campaign_type, campaign_status=campaign_status,
    )


# ---------------------------------------------------------------------------
# Bulk Action Endpoints
# ---------------------------------------------------------------------------


class BulkAddNegativeRequest(BaseModel):
    search_term_ids: list[int]
    level: str = "campaign"       # "campaign" or "ad_group"
    match_type: str = "EXACT"     # EXACT, PHRASE, BROAD
    client_id: int


class BulkAddKeywordRequest(BaseModel):
    search_term_ids: list[int]
    ad_group_id: int              # Target ad group for new keywords
    match_type: str = "EXACT"     # EXACT, PHRASE, BROAD
    client_id: int


class BulkPreviewRequest(BaseModel):
    search_term_ids: list[int]
    client_id: int


@router.post("/bulk-add-negative")
def bulk_add_negative(
    body: BulkAddNegativeRequest,
    db: Session = Depends(get_db),
):
    """Add selected search terms as negative keywords (campaign- or ad-group-level)."""
    ensure_demo_write_allowed(db, body.client_id)

    if not body.search_term_ids:
        raise HTTPException(status_code=400, detail="search_term_ids must not be empty")

    if body.level not in ("campaign", "ad_group"):
        raise HTTPException(status_code=400, detail="level must be 'campaign' or 'ad_group'")

    if body.match_type not in ("EXACT", "PHRASE", "BROAD"):
        raise HTTPException(status_code=400, detail="match_type must be EXACT, PHRASE, or BROAD")

    terms = db.query(SearchTerm).filter(SearchTerm.id.in_(body.search_term_ids)).all()
    if not terms:
        raise HTTPException(status_code=400, detail="No search terms found for the given IDs")

    added = 0
    skipped = 0
    items: list[str] = []

    try:
        for term in terms:
            # Resolve campaign_id: direct (PMax) or through ad_group (Search)
            campaign_id = term.campaign_id
            if campaign_id is None and term.ad_group_id:
                ad_group = db.query(AdGroup).filter(AdGroup.id == term.ad_group_id).first()
                if ad_group:
                    campaign_id = ad_group.campaign_id

            if campaign_id is None:
                skipped += 1
                continue

            # Determine ad_group_id for the negative keyword
            neg_ad_group_id = term.ad_group_id if body.level == "ad_group" else None

            # Check for duplicates (only ENABLED — REMOVED should not block re-add)
            dup_query = db.query(NegativeKeyword).filter(
                NegativeKeyword.text == term.text,
                NegativeKeyword.campaign_id == campaign_id,
                NegativeKeyword.match_type == body.match_type,
                NegativeKeyword.client_id == body.client_id,
                NegativeKeyword.status != "REMOVED",
            )
            if neg_ad_group_id is not None:
                dup_query = dup_query.filter(NegativeKeyword.ad_group_id == neg_ad_group_id)
            if dup_query.first():
                skipped += 1
                continue

            neg_kw = NegativeKeyword(
                client_id=body.client_id,
                campaign_id=campaign_id,
                ad_group_id=neg_ad_group_id,
                text=term.text,
                match_type=body.match_type,
                negative_scope="AD_GROUP" if body.level == "ad_group" else "CAMPAIGN",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(neg_kw)
            added += 1
            items.append(term.text)

        db.commit()

        # Log bulk action
        if added > 0:
            action = ActionLog(
                client_id=body.client_id,
                action_type="BULK_ADD_NEGATIVE",
                entity_type="negative_keyword",
                entity_id=str(added),
                status="APPLIED",
                execution_mode="LOCAL",
                new_value_json=f'{{"texts": {items}, "level": "{body.level}", "match_type": "{body.match_type}"}}',
            )
            db.add(action)
            db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(exc)}")

    return {
        "added": added,
        "skipped_duplicates": skipped,
        "items": items,
    }


@router.post("/bulk-add-keyword")
def bulk_add_keyword(
    body: BulkAddKeywordRequest,
    db: Session = Depends(get_db),
):
    """Promote selected search terms as new positive keywords in a target ad group."""
    ensure_demo_write_allowed(db, body.client_id)

    if not body.search_term_ids:
        raise HTTPException(status_code=400, detail="search_term_ids must not be empty")

    if body.match_type not in ("EXACT", "PHRASE", "BROAD"):
        raise HTTPException(status_code=400, detail="match_type must be EXACT, PHRASE, or BROAD")

    # Verify target ad group exists
    target_ad_group = db.query(AdGroup).filter(AdGroup.id == body.ad_group_id).first()
    if not target_ad_group:
        raise HTTPException(status_code=400, detail=f"Ad group {body.ad_group_id} not found")

    terms = db.query(SearchTerm).filter(SearchTerm.id.in_(body.search_term_ids)).all()
    if not terms:
        raise HTTPException(status_code=400, detail="No search terms found for the given IDs")

    added = 0
    skipped = 0
    items: list[str] = []

    try:
        for term in terms:
            # Check for duplicates in the target ad group
            existing = (
                db.query(Keyword)
                .filter(
                    Keyword.text == term.text,
                    Keyword.ad_group_id == body.ad_group_id,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            kw = Keyword(
                ad_group_id=body.ad_group_id,
                text=term.text,
                match_type=body.match_type,
                status="ENABLED",
                bid_micros=0,
            )
            db.add(kw)
            added += 1
            items.append(term.text)

        db.commit()

        # Log bulk action
        if added > 0:
            action = ActionLog(
                client_id=body.client_id,
                action_type="BULK_ADD_KEYWORD",
                entity_type="keyword",
                entity_id=str(body.ad_group_id),
                status="APPLIED",
                execution_mode="LOCAL",
                new_value_json=f'{{"texts": {items}, "ad_group_id": {body.ad_group_id}, "match_type": "{body.match_type}"}}',
            )
            db.add(action)
            db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(exc)}")

    return {
        "added": added,
        "skipped_duplicates": skipped,
        "items": items,
    }


@router.post("/bulk-preview")
def bulk_preview(
    body: BulkPreviewRequest,
    db: Session = Depends(get_db),
):
    """Return detailed preview data for selected search terms before a bulk action."""
    if not body.search_term_ids:
        raise HTTPException(status_code=400, detail="search_term_ids must not be empty")

    terms = db.query(SearchTerm).filter(SearchTerm.id.in_(body.search_term_ids)).all()
    if not terms:
        raise HTTPException(status_code=400, detail="No search terms found for the given IDs")

    result = []
    for term in terms:
        # Resolve campaign name
        campaign_name = None
        ad_group_name = None

        if term.ad_group_id:
            ad_group = db.query(AdGroup).filter(AdGroup.id == term.ad_group_id).first()
            if ad_group:
                ad_group_name = ad_group.name
                campaign = db.query(Campaign).filter(Campaign.id == ad_group.campaign_id).first()
                if campaign:
                    campaign_name = campaign.name

        if campaign_name is None and term.campaign_id:
            campaign = db.query(Campaign).filter(Campaign.id == term.campaign_id).first()
            if campaign:
                campaign_name = campaign.name

        result.append({
            "id": term.id,
            "text": term.text,
            "clicks": term.clicks or 0,
            "cost_usd": micros_to_currency(term.cost_micros or 0),
            "conversions": term.conversions or 0,
            "campaign_name": campaign_name,
            "ad_group_name": ad_group_name,
        })

    return result
