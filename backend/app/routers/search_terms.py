"""Search terms endpoints — list, filter, and segmented view."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.models import SearchTerm, AdGroup, Campaign
from app.schemas import SearchTermResponse, PaginatedResponse
from app.services.search_terms_service import SearchTermsService
from app.utils.formatters import micros_to_currency

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
    from sqlalchemy import or_

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
        from app.utils.formatters import currency_to_micros
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
                "ctr_pct": round((t.ctr or 0) / 10_000, 2),
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
