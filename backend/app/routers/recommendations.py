"""Recommendations endpoints - generation, filtering, apply and dismiss."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.demo_guard import ensure_demo_write_allowed
from app.database import get_db
from app.models.recommendation import Recommendation as RecommendationModel
from app.services.action_executor import ActionExecutor
from app.services.cache import invalidate_client, recommendations_cache
from app.services.google_ads import google_ads_service
from app.services.recommendation_contract import (
    ACTION,
    BLOCKED_BY_CONTEXT,
    GOOGLE_ADS_API,
    INSIGHT_ONLY,
    build_stable_key,
    normalize_reason_codes,
)
from app.services.recommendations import recommendations_engine

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_action_payload(model: RecommendationModel) -> dict:
    if isinstance(model.action_payload, dict) and model.action_payload:
        return model.action_payload
    if not model.suggested_action:
        return {}
    try:
        payload = json.loads(model.suggested_action)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    return {}


def _normalize_evidence(model: RecommendationModel) -> tuple[dict, dict, dict, dict]:
    evidence = model.evidence_json if isinstance(model.evidence_json, dict) else {}
    metadata = evidence.get("metadata") if isinstance(evidence.get("metadata"), dict) else evidence
    if not isinstance(metadata, dict):
        metadata = {}
    context = evidence.get("context") if isinstance(evidence.get("context"), dict) else {}
    explanation = evidence.get("explanation") if isinstance(evidence.get("explanation"), dict) else {}
    return evidence, metadata, context, explanation


def _serialize_row(model: RecommendationModel) -> dict:
    evidence, metadata, context, explanation = _normalize_evidence(model)
    action_payload = _normalize_action_payload(model)
    suggested_action = action_payload.get("action_type") or model.rule_id
    blocked_reasons = normalize_reason_codes(model.blocked_reasons or context.get("blocked_reasons"))
    downgrade_reasons = normalize_reason_codes(model.downgrade_reasons or context.get("downgrade_reasons"))
    context_outcome = model.context_outcome or context.get("context_outcome") or (ACTION if model.executable else INSIGHT_ONLY)
    why_allowed = explanation.get("why_allowed") if isinstance(explanation.get("why_allowed"), list) else []
    why_blocked = explanation.get("why_blocked") if isinstance(explanation.get("why_blocked"), list) else []
    tradeoffs = explanation.get("tradeoffs") if isinstance(explanation.get("tradeoffs"), list) else []
    return {
        "id": model.id,
        "client_id": model.client_id,
        "type": model.rule_id,
        "priority": model.priority,
        "entity_type": model.entity_type,
        "entity_id": int(model.entity_id) if str(model.entity_id).isdigit() else model.entity_id,
        "entity_name": model.entity_name,
        "campaign_name": metadata.get("campaign_name") or (model.entity_name if model.entity_type == "campaign" else None),
        "campaign_id": model.campaign_id,
        "ad_group_id": model.ad_group_id,
        "reason": model.reason,
        "category": model.category,
        "status": model.status,
        "source": model.source,
        "stable_key": model.stable_key,
        "action_payload": action_payload,
        "evidence_json": evidence,
        "impact_micros": model.impact_micros,
        "impact_score": model.impact_score,
        "confidence_score": model.confidence_score,
        "risk_score": model.risk_score,
        "score": model.score,
        "executable": bool(model.executable),
        "expires_at": model.expires_at,
        "google_resource_name": model.google_resource_name,
        "context_outcome": context_outcome,
        "blocked_reasons": blocked_reasons,
        "downgrade_reasons": downgrade_reasons,
        "context": context,
        "why_allowed": why_allowed,
        "why_blocked": why_blocked,
        "tradeoffs": tradeoffs,
        "risk_note": explanation.get("risk_note"),
        "next_best_action": explanation.get("next_best_action"),
        "suggested_action": suggested_action,
        "recommended_action": evidence.get("recommended_action"),
        "estimated_impact": evidence.get("estimated_impact"),
        "metadata": metadata,
        "created_at": model.created_at,
        "applied_at": model.applied_at,
    }


def _cached_google_recommendations(db: Session, client_id: int) -> list[dict]:
    now = _utcnow()
    rows = (
        db.query(RecommendationModel)
        .filter(
            RecommendationModel.client_id == client_id,
            RecommendationModel.source == GOOGLE_ADS_API,
            RecommendationModel.status == "pending",
        )
        .all()
    )
    result = []
    for row in rows:
        expires_at = row.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at < now:
            continue
        result.append(_serialize_row(row))
    return result


def _native_cache_fresh(db: Session, client_id: int) -> bool:
    latest = (
        db.query(RecommendationModel)
        .filter(
            RecommendationModel.client_id == client_id,
            RecommendationModel.source == GOOGLE_ADS_API,
        )
        .order_by(RecommendationModel.created_at.desc())
        .first()
    )
    if not latest or not latest.created_at:
        return False
    latest_created = latest.created_at
    if latest_created.tzinfo is None:
        latest_created = latest_created.replace(tzinfo=timezone.utc)
    return latest_created >= _utcnow() - timedelta(minutes=30)


def _get_native_recommendations(db: Session, client_id: int) -> list[dict]:
    if _native_cache_fresh(db, client_id):
        return _cached_google_recommendations(db, client_id)

    try:
        native = google_ads_service.fetch_native_recommendations(db, client_id)
        return native or _cached_google_recommendations(db, client_id)
    except Exception as exc:
        logger.warning(f"Native recommendations refresh failed: {exc}")
        return _cached_google_recommendations(db, client_id)


def _persist_recommendations(db: Session, client_id: int, generated: list[dict]) -> list[int]:
    existing = db.query(RecommendationModel).filter(RecommendationModel.client_id == client_id).all()
    existing_map = {
        (row.stable_key or build_stable_key(_serialize_row(row), client_id)): row
        for row in existing
    }

    # Collect rec objects to resolve IDs after a single flush at the end.
    # Avoid per-record db.flush() which causes 100+ individual SQL roundtrips
    # and greatly increases SQLite lock contention with concurrent sync writers.
    pending_refs: list[RecommendationModel] = []

    for rec_dict in generated:
        stable_key = rec_dict.get("stable_key") or build_stable_key(rec_dict, client_id)
        rec_dict = {**rec_dict, "stable_key": stable_key}
        db_rec = existing_map.get(stable_key)

        if db_rec and db_rec.status in {"applied", "dismissed"}:
            continue

        if not db_rec:
            db_rec = RecommendationModel(
                client_id=client_id,
                rule_id=rec_dict["type"],
                entity_type=rec_dict["entity_type"],
                entity_id=str(rec_dict["entity_id"]),
                entity_name=rec_dict.get("entity_name"),
                status="pending",
            )
            db.add(db_rec)
            existing_map[stable_key] = db_rec

        evidence_json = rec_dict.get("evidence_json") if isinstance(rec_dict.get("evidence_json"), dict) else {}
        metadata = rec_dict.get("metadata") if isinstance(rec_dict.get("metadata"), dict) else evidence_json.get("metadata", {})
        context = evidence_json.get("context") if isinstance(evidence_json.get("context"), dict) else rec_dict.get("context", {})
        explanation = evidence_json.get("explanation") if isinstance(evidence_json.get("explanation"), dict) else {}

        db_rec.rule_id = rec_dict["type"]
        db_rec.entity_type = rec_dict["entity_type"]
        db_rec.entity_id = str(rec_dict["entity_id"])
        db_rec.entity_name = rec_dict.get("entity_name")
        db_rec.priority = rec_dict.get("priority", "MEDIUM")
        db_rec.category = rec_dict.get("category", "RECOMMENDATION")
        db_rec.source = rec_dict.get("source", "PLAYBOOK_RULES")
        db_rec.stable_key = stable_key
        db_rec.campaign_id = rec_dict.get("campaign_id")
        db_rec.ad_group_id = rec_dict.get("ad_group_id")
        db_rec.reason = rec_dict["reason"]
        db_rec.suggested_action = json.dumps(rec_dict.get("action_payload") or {})
        db_rec.action_payload = rec_dict.get("action_payload") or {}
        db_rec.evidence_json = {
            **evidence_json,
            "metadata": metadata,
            "context": context,
            "explanation": explanation,
            "recommended_action": rec_dict.get("recommended_action"),
            "estimated_impact": rec_dict.get("estimated_impact"),
        }
        db_rec.impact_micros = rec_dict.get("impact_micros")
        db_rec.impact_score = rec_dict.get("impact_score")
        db_rec.confidence_score = rec_dict.get("confidence_score")
        db_rec.risk_score = rec_dict.get("risk_score")
        db_rec.score = rec_dict.get("score")
        db_rec.executable = bool(rec_dict.get("executable"))
        db_rec.expires_at = rec_dict.get("expires_at")
        db_rec.google_resource_name = rec_dict.get("google_resource_name")
        db_rec.context_outcome = rec_dict.get("context_outcome")
        db_rec.blocked_reasons = normalize_reason_codes(rec_dict.get("blocked_reasons"))
        db_rec.downgrade_reasons = normalize_reason_codes(rec_dict.get("downgrade_reasons"))
        pending_refs.append(db_rec)

    # Single flush assigns PKs to all new records, then one commit completes the transaction.
    db.flush()
    active_ids = [ref.id for ref in pending_refs]
    db.commit()
    return active_ids


def _load_rows_by_ids(db: Session, row_ids: list[int]) -> list[dict]:
    if not row_ids:
        return []
    rows = db.query(RecommendationModel).filter(RecommendationModel.id.in_(row_ids)).all()
    row_map = {row.id: row for row in rows}
    return [_serialize_row(row_map[row_id]) for row_id in row_ids if row_id in row_map]


def _load_historical_rows(db: Session, client_id: int, status: str | None) -> list[dict]:
    query = db.query(RecommendationModel).filter(RecommendationModel.client_id == client_id)
    if status:
        query = query.filter(RecommendationModel.status == status)
    rows = query.order_by(RecommendationModel.created_at.desc()).all()
    return [_serialize_row(row) for row in rows]


def _apply_filters(
    results: list[dict],
    priority: str | None,
    status: str | None,
    category: str | None,
    source: str | None,
    executable: bool | None,
) -> list[dict]:
    filtered = results
    if priority:
        filtered = [r for r in filtered if r.get("priority") == priority]
    if status:
        filtered = [r for r in filtered if r.get("status", "pending") == status]
    if category:
        filtered = [r for r in filtered if r.get("category", "RECOMMENDATION") == category]
    if source:
        filtered = [r for r in filtered if r.get("source") == source]
    if executable is not None:
        filtered = [r for r in filtered if bool(r.get("executable")) is executable]
    return filtered


def _build_summary(results: list[dict]) -> dict:
    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    by_outcome = {ACTION: 0, INSIGHT_ONLY: 0, BLOCKED_BY_CONTEXT: 0}
    by_priority = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_category = {"RECOMMENDATION": 0, "ALERT": 0}

    for rec in results:
        rec_type = rec["type"]
        by_type[rec_type] = by_type.get(rec_type, 0) + 1
        rec_source = rec.get("source", "PLAYBOOK_RULES")
        by_source[rec_source] = by_source.get(rec_source, 0) + 1
        outcome = rec.get("context_outcome") or INSIGHT_ONLY
        if outcome in by_outcome:
            by_outcome[outcome] += 1
        if rec.get("priority") in by_priority:
            by_priority[rec["priority"]] += 1
        if rec.get("category") in by_category:
            by_category[rec["category"]] += 1

    executable_total = sum(1 for rec in results if rec.get("executable"))

    return {
        "total": len(results),
        "high_priority": by_priority["HIGH"],
        "medium": by_priority["MEDIUM"],
        "low": by_priority["LOW"],
        "by_priority": by_priority,
        "by_category": by_category,
        "by_source": by_source,
        "by_context_outcome": by_outcome,
        "by_type": by_type,
        "executable_total": executable_total,
    }


@router.get("/")
def get_recommendations(
    client_id: int = Query(..., description="Client ID"),
    priority: str | None = Query(None, description="Filter by priority: HIGH, MEDIUM, LOW"),
    status: str | None = Query(None, description="Filter by status: pending, applied, dismissed"),
    category: str | None = Query(None, description="Filter by category: RECOMMENDATION, ALERT"),
    source: str | None = Query(None, description="Filter by source"),
    executable: bool | None = Query(None, description="Filter by executable recommendations"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Generate active recommendations for a client and expose historical states on demand."""
    from app.utils.date_utils import resolve_dates
    start, end = resolve_dates(days, date_from, date_to)
    effective_days = (end - start).days

    cache_key = (
        f"client={client_id}|recommendations"
        f"|priority={priority or ''}|status={status or ''}|category={category or ''}"
        f"|source={source or ''}|exec={executable if executable is not None else ''}"
        f"|from={start.isoformat()}|to={end.isoformat()}"
    )
    cached = recommendations_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        generated = recommendations_engine.generate_all(db, client_id, effective_days)
        generated.extend(_get_native_recommendations(db, client_id))
        active_ids = _persist_recommendations(db, client_id, generated)
    except Exception as exc:
        logger.exception(f"Error generating recommendations: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    if status in {None, "pending"}:
        results = _load_rows_by_ids(db, active_ids)
    else:
        results = _load_historical_rows(db, client_id, status)

    results = _apply_filters(results, priority, status, category, source, executable)
    summary = _build_summary(results)
    payload = {**summary, "recommendations": results}
    recommendations_cache[cache_key] = payload
    return payload


@router.get("/summary")
def get_recommendations_summary(
    client_id: int = Query(...),
    source: str | None = Query(None),
    category: str | None = Query(None),
    executable: bool | None = Query(None),
    status: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    date_from: date = Query(None, description="Start date (overrides days)"),
    date_to: date = Query(None, description="End date (overrides days)"),
    db: Session = Depends(get_db),
):
    """Quick recommendation summary for badges and overview widgets."""
    from app.utils.date_utils import resolve_dates
    start, end = resolve_dates(days, date_from, date_to)
    effective_days = (end - start).days
    generated = recommendations_engine.generate_all(db, client_id, effective_days)
    generated.extend(_get_native_recommendations(db, client_id))
    active_ids = _persist_recommendations(db, client_id, generated)

    if status in {None, "pending"}:
        results = _load_rows_by_ids(db, active_ids)
    else:
        results = _load_historical_rows(db, client_id, status)

    results = _apply_filters(results, None, status, category, source, executable)
    return _build_summary(results)


@router.post("/{recommendation_id}/apply")
def apply_recommendation(
    recommendation_id: int,
    client_id: int = Query(..., description="Client ID"),
    dry_run: bool = Query(False, description="Preview only, do not execute"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Apply a recommendation via ActionExecutor."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Zastosowanie rekomendacji",
    )

    executor = ActionExecutor(db)
    result = executor.apply_recommendation(
        recommendation_id,
        client_id,
        dry_run=dry_run,
        allow_demo_write=allow_demo_write,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    if result["status"] == "blocked":
        raise HTTPException(status_code=422, detail=result["reason"])

    if not dry_run:
        invalidate_client(client_id)
    return result


@router.post("/{recommendation_id}/dismiss")
def dismiss_recommendation(
    recommendation_id: int,
    client_id: int = Query(..., description="Client ID"),
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Dismiss a pending recommendation locally."""
    ensure_demo_write_allowed(
        db,
        client_id,
        allow_demo_write=allow_demo_write,
        operation="Odrzucanie rekomendacji",
    )

    rec = (
        db.query(RecommendationModel)
        .filter(
            RecommendationModel.id == recommendation_id,
            RecommendationModel.client_id == client_id,
            RecommendationModel.status == "pending",
        )
        .first()
    )

    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")

    rec.status = "dismissed"
    db.commit()
    invalidate_client(client_id)
    return {"status": "success", "message": f"Recommendation {recommendation_id} dismissed"}


# ---------------------------------------------------------------------------
# Bulk-apply "quick scripts" endpoint
# ---------------------------------------------------------------------------

class BulkApplyRequest(BaseModel):
    client_id: int
    category: str  # "clean_waste", "pause_burning", "boost_winners", "emergency_brake", "add_negatives"
    dry_run: bool = True  # Default to preview mode
    item_ids: list[int] | None = None  # Optional filter — only apply these recommendation ids


_CATEGORY_FILTERS: dict[str, dict] = {
    "clean_waste": {
        "rule_ids": ["ADD_NEGATIVE"],
        "priority": None,
    },
    "pause_burning": {
        "rule_ids": ["PAUSE_KEYWORD"],
        "priority": None,
    },
    "boost_winners": {
        "rule_ids": ["INCREASE_BUDGET", "REALLOCATE_BUDGET"],
        "priority": "HIGH",
    },
    "emergency_brake": {
        "rule_ids": ["DECREASE_BID", "PAUSE_KEYWORD"],
        "priority": "HIGH",
    },
    "add_negatives": {
        "rule_ids": ["ADD_NEGATIVE", "NGRAM_NEGATIVE"],
        "priority": None,
    },
}


def _build_item_summary(rec: RecommendationModel) -> str:
    """Build a human-readable summary string from a recommendation row."""
    action_payload = _normalize_action_payload(rec)
    evidence, metadata, _ctx, _expl = _normalize_evidence(rec)

    keyword_text = (
        action_payload.get("keyword_text")
        or action_payload.get("keyword")
        or metadata.get("keyword_text")
        or ""
    )
    campaign_name = (
        metadata.get("campaign_name")
        or action_payload.get("campaign_name")
        or rec.entity_name
        or ""
    )

    rule = rec.rule_id or ""
    parts = [rule.replace("_", " ").title()]
    if keyword_text:
        parts.append(f"'{keyword_text}'")
    if campaign_name:
        parts.append(f"in campaign '{campaign_name}'")

    return ": ".join(parts[:1]) + (" " + " ".join(parts[1:]) if len(parts) > 1 else "")


def _estimated_savings_usd(rec: RecommendationModel) -> float:
    """Return estimated savings in USD (from micros)."""
    if rec.impact_micros and rec.impact_micros > 0:
        return round(rec.impact_micros / 1_000_000, 2)
    evidence = rec.evidence_json if isinstance(rec.evidence_json, dict) else {}
    impact = evidence.get("estimated_impact") if isinstance(evidence.get("estimated_impact"), dict) else {}
    if isinstance(impact, dict):
        for key in ("savings_usd", "estimated_savings_usd", "value"):
            val = impact.get(key)
            if val is not None:
                try:
                    return round(float(val), 2)
                except (ValueError, TypeError):
                    pass
    return 0.0


@router.post("/bulk-apply")
def bulk_apply_recommendations(
    body: BulkApplyRequest,
    allow_demo_write: bool = Query(False, description="Override DEMO write lock"),
    db: Session = Depends(get_db),
):
    """Apply a batch of recommendations by quick-script category.

    When dry_run is True (default) returns a preview of matching recommendations.
    When dry_run is False, applies each via ActionExecutor and reports results.
    """
    if body.category not in _CATEGORY_FILTERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category '{body.category}'. Valid: {', '.join(_CATEGORY_FILTERS)}",
        )

    if not body.dry_run:
        ensure_demo_write_allowed(
            db,
            body.client_id,
            allow_demo_write=allow_demo_write,
            operation=f"Bulk apply: {body.category}",
        )

    cfg = _CATEGORY_FILTERS[body.category]
    rule_ids: list[str] = cfg["rule_ids"]
    priority_filter: str | None = cfg["priority"]

    query = (
        db.query(RecommendationModel)
        .filter(
            RecommendationModel.client_id == body.client_id,
            RecommendationModel.status == "pending",
            RecommendationModel.rule_id.in_(rule_ids),
        )
    )
    if priority_filter:
        query = query.filter(RecommendationModel.priority == priority_filter)

    # When NOT a dry run, optionally narrow to user-selected item ids (from preview UI).
    # Dry run always returns the full matching set so the UI can build the selection list.
    if not body.dry_run and body.item_ids:
        query = query.filter(RecommendationModel.id.in_(body.item_ids))

    all_recs: list[RecommendationModel] = query.all()

    # Separate executable from non-executable
    executable_recs: list[RecommendationModel] = []
    skipped_recs: list[RecommendationModel] = []
    for rec in all_recs:
        ap = rec.action_payload or {}
        # Check executable flag in action_payload or suggested_action
        is_exe = ap.get("executable", True) if ap.get("action_type") else True
        if is_exe:
            executable_recs.append(rec)
        else:
            skipped_recs.append(rec)

    # Build items list — only executable recommendations
    items: List[dict] = []
    for rec in executable_recs:
        _, metadata, _ctx, _expl = _normalize_evidence(rec)
        action_payload = _normalize_action_payload(rec)
        # Metric snapshot for the "why" panel
        metrics_snapshot = {
            "clicks": metadata.get("clicks"),
            "impressions": metadata.get("impressions"),
            "cost_usd": metadata.get("cost"),
            "conversions": metadata.get("conversions"),
            "ctr": metadata.get("ctr"),
            "cpa": metadata.get("cpa"),
            "roas": metadata.get("roas"),
            "quality_score": metadata.get("quality_score"),
        }
        # strip Nones for clean payload
        metrics_snapshot = {k: v for k, v in metrics_snapshot.items() if v is not None}

        items.append({
            "id": rec.id,
            "action_type": rec.rule_id,
            "priority": rec.priority,
            "summary": _build_item_summary(rec),
            "estimated_savings_usd": _estimated_savings_usd(rec),
            "status": "pending",
            # Rich context for UI "why?" panel
            "entity_name": rec.entity_name,
            "campaign_name": metadata.get("campaign_name"),
            "reason": rec.reason,
            "suggested_action": rec.suggested_action,
            "metrics": metrics_snapshot,
            "match_type": action_payload.get("params", {}).get("match_type") if isinstance(action_payload.get("params"), dict) else None,
            "negative_level": action_payload.get("params", {}).get("negative_level") if isinstance(action_payload.get("params"), dict) else None,
        })

    applied = 0
    failed = 0
    errors: List[str] = []
    # Track per-item results by rec id
    item_status: dict[int, str] = {}

    if not body.dry_run:
        executor = ActionExecutor(db)

        # Use batch path for ADD_NEGATIVE — single API call per campaign
        batch_eligible = [r for r in executable_recs if r.rule_id == "ADD_NEGATIVE"]
        individual = [r for r in executable_recs if r.rule_id != "ADD_NEGATIVE"]

        if batch_eligible:
            batch_result = executor.apply_add_negative_batch(
                batch_eligible, body.client_id, allow_demo_write=allow_demo_write,
            )
            applied += batch_result["applied"]
            failed += batch_result["failed"]
            errors.extend(batch_result["errors"])
            # Mark items from batch
            for rec in batch_eligible:
                # After batch, rec.status was updated to "applied" if successful
                item_status[rec.id] = "success" if rec.status == "applied" else "failed"

        for rec in individual:
            try:
                result = executor.apply_recommendation(
                    rec.id,
                    body.client_id,
                    dry_run=False,
                    allow_demo_write=allow_demo_write,
                )
                if result.get("status") in ("success", "applied", "dry_run"):
                    applied += 1
                    item_status[rec.id] = "success"
                else:
                    failed += 1
                    item_status[rec.id] = "failed"
                    errors.append(
                        f"Rec #{rec.id}: {result.get('message') or result.get('reason', 'unknown error')}"
                    )
            except Exception as exc:
                failed += 1
                item_status[rec.id] = "failed"
                errors.append(f"Rec #{rec.id}: {exc}")

        # Update item statuses in response
        for item in items:
            item["status"] = item_status.get(item["id"], "pending")

        if applied > 0:
            invalidate_client(body.client_id)

    skipped_count = len(skipped_recs)

    return {
        "category": body.category,
        "dry_run": body.dry_run,
        "total_matching": len(executable_recs),
        "total_skipped": skipped_count,
        "items": items,
        "applied": applied,
        "failed": failed,
        "errors": errors,
    }
