"""Recommendations endpoints — generate, apply, dismiss."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.recommendation import Recommendation
from app.services.recommendations import recommendations_engine
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/")
def get_recommendations(
    client_id: int = Query(..., description="Client ID"),
    priority: str = Query(None, description="Filter by priority: HIGH, MEDIUM"),
    status: str = Query(None, description="Filter by status: pending, applied, dismissed"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Generate optimization recommendations for a client."""
    try:
        results = recommendations_engine.generate_all(db, client_id, days)
    except Exception as e:
        logger.exception(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Apply filters
    if priority:
        results = [r for r in results if r["priority"] == priority]
    if status:
        results = [r for r in results if r.get("status", "pending") == status]

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
    """Quick summary for sidebar badges."""
    results = recommendations_engine.generate_all(db, client_id, days)
    high_count = sum(1 for r in results if r["priority"] == "HIGH")
    return {
        "total": len(results),
        "high_priority": high_count,
    }


@router.post("/{recommendation_id}/apply")
def apply_recommendation(
    recommendation_id: int,
    client_id: int = Query(..., description="Client ID"),
    dry_run: bool = Query(False, description="Preview only, don't execute"),
    db: Session = Depends(get_db),
):
    """Apply a recommendation via ActionExecutor (with circuit breaker).

    Pass dry_run=true to preview the action without executing it.
    """
    executor = ActionExecutor(db)
    result = executor.apply_recommendation(recommendation_id, client_id, dry_run=dry_run)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    if result["status"] == "blocked":
        raise HTTPException(status_code=422, detail=result["reason"])

    return result


@router.post("/{recommendation_id}/dismiss")
def dismiss_recommendation(
    recommendation_id: int,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Dismiss a recommendation (mark as dismissed)."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.client_id == client_id,
        Recommendation.status == "pending",
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")

    rec.status = "dismissed"
    db.commit()

    return {"status": "success", "message": f"Recommendation {recommendation_id} dismissed"}
