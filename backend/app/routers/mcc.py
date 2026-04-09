"""MCC overview router — cross-account aggregation endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mcc_service import MCCService

router = APIRouter(prefix="/mcc", tags=["mcc"])


class DismissRequest(BaseModel):
    client_id: int
    recommendation_ids: list[int] | None = None
    dismiss_all: bool = False


@router.get("/overview")
def mcc_overview(
    date_from: str = Query(None, description="Start date YYYY-MM-DD (default: 1st of current month)"),
    date_to: str = Query(None, description="End date YYYY-MM-DD (default: today)"),
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
    d_from = date_type.fromisoformat(date_from) if date_from else None
    d_to = date_type.fromisoformat(date_to) if date_to else None
    return MCCService(db).get_overview(date_from=d_from, date_to=d_to)


@router.get("/new-access")
def mcc_new_access(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return MCCService(db).detect_new_access(client_id, days)


@router.post("/dismiss-google-recommendations")
def mcc_dismiss_google_recommendations(
    body: DismissRequest,
    db: Session = Depends(get_db),
):
    return MCCService(db).dismiss_google_recommendations(
        client_id=body.client_id,
        recommendation_ids=body.recommendation_ids,
        dismiss_all=body.dismiss_all,
    )


@router.get("/negative-keyword-lists")
def mcc_negative_keyword_lists(db: Session = Depends(get_db)):
    return MCCService(db).get_negative_keyword_lists_overview()


@router.get("/shared-lists")
def mcc_shared_lists(db: Session = Depends(get_db)):
    """MCC-level exclusion lists: negative keywords + placement exclusions."""
    return MCCService(db).get_mcc_shared_lists()


@router.get("/shared-lists/{list_id}/items")
def mcc_shared_list_items(
    list_id: int,
    list_type: str = Query("keyword", description="keyword or placement"),
    db: Session = Depends(get_db),
):
    """Drill-down: return items of a specific MCC shared list."""
    return MCCService(db).get_shared_list_items(list_id, list_type)


@router.get("/billing-status")
def mcc_billing_status(
    customer_id: str = Query(..., description="Google customer ID (e.g. 123-456-7890)"),
    db: Session = Depends(get_db),
):
    """Check billing/payment status for a specific account."""
    return MCCService(db).get_billing_status(customer_id)
