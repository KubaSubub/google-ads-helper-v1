"""Recommendations endpoint — generates optimization suggestions from Playbook rules."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendations import recommendations_engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/")
def get_recommendations(
    client_id: int = Query(..., description="Client ID to generate recommendations for"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """
    Generate all optimization recommendations for a client.
    Runs all 7 Playbook rules and returns prioritized suggestions.
    """
    results = recommendations_engine.generate_all(db, client_id, days)

    # Group by type for summary
    summary = {}
    for r in results:
        rtype = r["type"]
        summary[rtype] = summary.get(rtype, 0) + 1

    high_count = sum(1 for r in results if r["priority"] == "HIGH")
    medium_count = sum(1 for r in results if r["priority"] == "MEDIUM")
    low_count = sum(1 for r in results if r["priority"] == "LOW")

    return {
        "total": len(results),
        "by_priority": {"HIGH": high_count, "MEDIUM": medium_count, "LOW": low_count},
        "by_type": summary,
        "recommendations": results,
    }


@router.get("/summary")
def get_recommendations_summary(
    client_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Quick summary — just counts, no details. Good for sidebar badges."""
    results = recommendations_engine.generate_all(db, client_id, days)
    high_count = sum(1 for r in results if r["priority"] == "HIGH")
    return {
        "total": len(results),
        "high_priority": high_count,
    }
