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
def mcc_overview(db: Session = Depends(get_db)):
    return MCCService(db).get_overview()


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
