"""Recommendations endpoints — generate, apply, dismiss."""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.models.recommendation import Recommendation as RecommendationModel
from app.services.recommendations import recommendations_engine
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _build_suggested_action(rec_dict: dict) -> str:
    """Build suggested_action JSON from engine-generated rec dict for ActionExecutor."""
    action = {
        "type": rec_dict["type"],
        "entity_type": rec_dict["entity_type"],
        "entity_id": rec_dict["entity_id"],
        "entity_name": rec_dict["entity_name"],
    }
    meta = rec_dict.get("metadata") or {}
    if rec_dict["type"] == "INCREASE_BID":
        action["params"] = {"change_pct": meta.get("bid_increase_pct", 20)}
    elif rec_dict["type"] == "DECREASE_BID":
        action["params"] = {"change_pct": meta.get("bid_decrease_pct", 20)}
    elif rec_dict["type"] == "ADD_KEYWORD":
        action["params"] = {"match_type": meta.get("match_type", "EXACT"), "keyword_text": rec_dict["entity_name"]}
    elif rec_dict["type"] == "ADD_NEGATIVE":
        action["params"] = {"keyword_text": rec_dict["entity_name"]}
    elif rec_dict["type"] == "REALLOCATE_BUDGET":
        action["params"] = {"move_amount": meta.get("move_amount", 0)}
    return json.dumps(action)


def _unique_key(rec_dict: dict) -> str:
    """Build a unique key for deduplication: rule_type + entity_type + entity_id + entity_name."""
    return f"{rec_dict['type']}|{rec_dict['entity_type']}|{rec_dict['entity_id']}|{rec_dict['entity_name']}"


def _persist_recommendations(db: Session, client_id: int, generated: list[dict]) -> list[dict]:
    """Upsert generated recs into DB. Skip already applied/dismissed. Return list with DB ids."""

    # Get existing recs for this client that are not stale
    existing = db.query(RecommendationModel).filter(
        RecommendationModel.client_id == client_id,
    ).all()

    existing_map = {}
    for e in existing:
        key = f"{e.rule_id}|{e.entity_type}|{e.entity_id}|{e.entity_name or ''}"
        existing_map[key] = e

    result = []

    for rec_dict in generated:
        key = _unique_key(rec_dict)

        db_rec = existing_map.get(key)

        if db_rec:
            if db_rec.status in ("applied", "dismissed"):
                # Skip — already processed
                continue
            # Update reason/priority if changed
            db_rec.reason = rec_dict["reason"]
            db_rec.priority = rec_dict["priority"]
            db_rec.suggested_action = _build_suggested_action(rec_dict)
        else:
            # Create new
            db_rec = RecommendationModel(
                client_id=client_id,
                rule_id=rec_dict["type"],
                entity_type=rec_dict["entity_type"],
                entity_id=str(rec_dict["entity_id"]),
                entity_name=rec_dict["entity_name"],
                priority=rec_dict["priority"],
                reason=rec_dict["reason"],
                suggested_action=_build_suggested_action(rec_dict),
                status="pending",
            )
            db.add(db_rec)

        db.flush()

        # Build response dict with DB id
        out = dict(rec_dict)
        out["id"] = db_rec.id
        out["status"] = db_rec.status
        result.append(out)

    db.commit()
    return result


@router.get("/")
def get_recommendations(
    client_id: int = Query(..., description="Client ID"),
    priority: str = Query(None, description="Filter by priority: HIGH, MEDIUM"),
    status: str = Query(None, description="Filter by status: pending, applied, dismissed"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    db: Session = Depends(get_db),
):
    """Generate optimization recommendations for a client and persist to DB."""
    try:
        generated = recommendations_engine.generate_all(db, client_id, days)
        results = _persist_recommendations(db, client_id, generated)
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
    generated = recommendations_engine.generate_all(db, client_id, days)
    # Also persist so counts are accurate
    results = _persist_recommendations(db, client_id, generated)
    high_count = sum(1 for r in results if r["priority"] == "HIGH")
    medium_count = sum(1 for r in results if r["priority"] == "MEDIUM")
    return {
        "total": len(results),
        "high_priority": high_count,
        "medium": medium_count,
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
    rec = db.query(RecommendationModel).filter(
        RecommendationModel.id == recommendation_id,
        RecommendationModel.client_id == client_id,
        RecommendationModel.status == "pending",
    ).first()

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")

    rec.status = "dismissed"
    db.commit()

    return {"status": "success", "message": f"Recommendation {recommendation_id} dismissed"}
