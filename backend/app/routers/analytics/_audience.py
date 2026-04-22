"""Audience overlap / redundancy detection."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/audience-overlap")
def audience_overlap(
    client_id: int = Query(..., description="Client ID"),
    days: int = Query(30, ge=7, le=90),
    severity: str = Query("ALL", description="HIGH / MEDIUM / ALL"),
    db: Session = Depends(get_db),
):
    """Flag audience pairs on the same campaign that are likely redundant.

    Signals used: same audience_type, Jaccard name similarity, similar CVR/CPA
    profile. Requires >= 2 signals to fire. Review queue, not auto-apply.
    """
    from app.services.audience_overlap_service import detect_audience_redundancy

    items = detect_audience_redundancy(db, client_id, window_days=days)
    if severity != "ALL":
        items = [i for i in items if i["severity"] == severity.upper()]
    return {"total": len(items), "items": items}
