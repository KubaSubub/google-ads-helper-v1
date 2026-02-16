"""Search terms endpoints — list, filter, and semantic analysis (placeholder)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.database import get_db
from app.models import SearchTerm, AdGroup, Campaign
from app.schemas import SearchTermResponse, PaginatedResponse

router = APIRouter(prefix="/search-terms", tags=["Search Terms"])


@router.get("/", response_model=PaginatedResponse)
def list_search_terms(
    client_id: int = Query(None, description="Filter by client"),
    campaign_id: int = Query(None, description="Filter by campaign"),
    ad_group_id: int = Query(None, description="Filter by ad group"),
    min_clicks: int = Query(None, ge=0, description="Minimum clicks"),
    min_cost: float = Query(None, ge=0, description="Minimum cost"),
    min_impressions: int = Query(None, ge=0, description="Minimum impressions"),
    date_from: date = Query(None),
    date_to: date = Query(None),
    search: str = Query(None, description="Full-text search in term text"),
    sort_by: str = Query("cost", description="Sort field: cost, clicks, impressions, ctr, conversions"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List search terms with extensive filtering, sorting, and pagination."""
    query = db.query(SearchTerm)

    # Join through ad_group → campaign when filtering by client or campaign
    if client_id or campaign_id:
        query = query.join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        if campaign_id:
            query = query.filter(AdGroup.campaign_id == campaign_id)
        if client_id:
            query = query.join(Campaign, AdGroup.campaign_id == Campaign.id).filter(
                Campaign.client_id == client_id
            )

    if ad_group_id:
        query = query.filter(SearchTerm.ad_group_id == ad_group_id)
    if min_clicks is not None:
        query = query.filter(SearchTerm.clicks >= min_clicks)
    if min_cost is not None:
        query = query.filter(SearchTerm.cost >= min_cost)
    if min_impressions is not None:
        query = query.filter(SearchTerm.impressions >= min_impressions)
    if date_from:
        query = query.filter(SearchTerm.date_from >= date_from)
    if date_to:
        query = query.filter(SearchTerm.date_to <= date_to)
    if search:
        query = query.filter(SearchTerm.text.ilike(f"%{search}%"))

    # Sorting
    sort_column = getattr(SearchTerm, sort_by, SearchTerm.cost)
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
    """
    Get aggregated summary of search terms for a campaign:
    total unique terms, total cost, top terms by cost, etc.
    """
    cutoff = date.today() - timedelta(days=days)

    query = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .filter(AdGroup.campaign_id == campaign_id, SearchTerm.date_from >= cutoff)
    )

    terms = query.all()
    if not terms:
        return {"total_terms": 0, "total_cost": 0, "total_clicks": 0, "top_by_cost": []}

    total_cost = sum(t.cost for t in terms)
    total_clicks = sum(t.clicks for t in terms)
    total_conversions = sum(t.conversions for t in terms)

    # Top 10 by cost (wasteful if no conversions)
    sorted_by_cost = sorted(terms, key=lambda t: t.cost, reverse=True)[:10]

    return {
        "total_terms": len(terms),
        "total_cost": round(total_cost, 2),
        "total_clicks": total_clicks,
        "total_conversions": round(total_conversions, 2),
        "top_by_cost": [
            {
                "text": t.text,
                "cost": t.cost,
                "clicks": t.clicks,
                "conversions": t.conversions,
                "ctr": t.ctr,
            }
            for t in sorted_by_cost
        ],
    }


# ---------------------------------------------------------------------------
# Segmented Search Terms (Playbook: Search Terms Intelligence)
# ---------------------------------------------------------------------------

# Words indicating irrelevant user intent
IRRELEVANT_WORDS = [
    "free", "cheap", "how to", "why", "what is", "download", "torrent",
    "darmowe", "za darmo", "jak", "dlaczego", "co to", "pobierz",
    "praca", "job", "salary", "wynagrodzenie", "opinie", "forum",
]


@router.get("/segmented")
def segmented_search_terms(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback period"),
    db: Session = Depends(get_db),
):
    """
    Classify search terms into 4 segments from the Playbook:
      - HIGH_PERFORMER: conv >= 3 AND CVR > campaign average
      - WASTE: clicks >= 5, conv = 0, CTR < 1%
      - TESTING: 1-5 clicks (insufficient data)
      - IRRELEVANT: contains disqualifying intent words
    """
    terms = (
        db.query(SearchTerm)
        .join(AdGroup, SearchTerm.ad_group_id == AdGroup.id)
        .join(Campaign, AdGroup.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
        .order_by(SearchTerm.cost.desc())
        .all()
    )

    if not terms:
        return {
            "segments": {
                "HIGH_PERFORMER": [], "WASTE": [], "TESTING": [], "IRRELEVANT": [], "OTHER": []
            },
            "summary": {"total": 0},
        }

    # Compute account-level average CVR
    total_clicks = sum(t.clicks for t in terms)
    total_conv = sum(t.conversions for t in terms)
    avg_cvr = (total_conv / total_clicks * 100) if total_clicks > 0 else 0

    segments = {
        "HIGH_PERFORMER": [],
        "WASTE": [],
        "TESTING": [],
        "IRRELEVANT": [],
        "OTHER": [],
    }

    for t in terms:
        text_lower = t.text.lower()
        cvr = (t.conversions / t.clicks * 100) if t.clicks > 0 else 0
        ctr = t.ctr if t.ctr else 0

        item = {
            "id": t.id,
            "text": t.text,
            "clicks": t.clicks,
            "impressions": t.impressions,
            "cost": round(t.cost, 2),
            "conversions": round(t.conversions, 1),
            "ctr": round(ctr, 2),
            "cvr": round(cvr, 2),
        }

        # 1. Irrelevant intent check (first — highest priority)
        matched = [w for w in IRRELEVANT_WORDS if w in text_lower]
        if matched:
            item["segment_reason"] = f"Contains: {', '.join(matched)}"
            segments["IRRELEVANT"].append(item)
            continue

        # 2. High performer
        if t.conversions >= 3 and cvr > avg_cvr:
            item["segment_reason"] = f"CVR {cvr:.1f}% > avg {avg_cvr:.1f}%, {t.conversions:.0f} conv"
            segments["HIGH_PERFORMER"].append(item)
            continue

        # 3. Waste
        if t.clicks >= 5 and t.conversions == 0 and ctr < 1.0:
            item["segment_reason"] = f"{t.clicks} clicks, 0 conv, CTR {ctr:.2f}%"
            segments["WASTE"].append(item)
            continue

        # 4. Testing (insufficient data)
        if 1 <= t.clicks <= 5:
            item["segment_reason"] = f"Only {t.clicks} clicks — need more data"
            segments["TESTING"].append(item)
            continue

        # 5. Everything else
        segments["OTHER"].append(item)

    # Summary stats
    total_waste_cost = sum(i["cost"] for i in segments["WASTE"])
    total_hp_conv = sum(i["conversions"] for i in segments["HIGH_PERFORMER"])

    return {
        "segments": segments,
        "summary": {
            "total": len(terms),
            "avg_cvr": round(avg_cvr, 2),
            "counts": {seg: len(items) for seg, items in segments.items()},
            "waste_cost": round(total_waste_cost, 2),
            "high_performer_conversions": round(total_hp_conv, 1),
        },
    }
