"""Scripts router — date-aware search term / keyword optimization actions.

Replaces the stale `/recommendations/bulk-apply` flow for new-generation scripts.
Each script is a self-contained class registered in `app.services.scripts`.
"""

import json
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.services.scripts import get_script, list_scripts
from app.services.scripts.base import CATEGORY_LABELS_PL

router = APIRouter(prefix="/scripts", tags=["scripts"])

# Hard cap on `params` payload size to keep malicious clients from pumping
# megabyte-sized dicts into the scripts pipeline.
_MAX_PARAMS_BYTES = 16_384


def _validate_params_size(value: dict) -> dict:
    try:
        size = len(json.dumps(value or {}, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"params must be JSON-serialisable: {exc}") from None
    if size > _MAX_PARAMS_BYTES:
        raise ValueError(
            f"params payload too large ({size}B > {_MAX_PARAMS_BYTES}B)"
        )
    return value


def _merge_params(script_id: str, client_id: int, request_params: dict, db: Session) -> dict:
    """Merge params: script defaults → client saved config → request overrides."""
    script = get_script(script_id)
    if not script:
        return request_params

    base = dict(script.default_params)

    client = db.get(Client, client_id)
    if client and client.script_configs and isinstance(client.script_configs, dict):
        saved = client.script_configs.get(script_id) or {}
        base.update(saved)

    base.update({k: v for k, v in (request_params or {}).items() if v is not None})
    return base


# ── Request models ──────────────────────────────────────────────────────────
class ScriptRunRequest(BaseModel):
    client_id: int
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    params: dict = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def _params_bounded(cls, v: dict) -> dict:
        return _validate_params_size(v)


class ScriptExecuteRequest(ScriptRunRequest):
    item_ids: Optional[list[Any]] = None
    item_overrides: Optional[dict[str, dict]] = None  # {item_id: {ad_group_id: X, ...}}


class SaveConfigRequest(BaseModel):
    client_id: int
    params: dict

    @field_validator("params")
    @classmethod
    def _params_bounded(cls, v: dict) -> dict:
        return _validate_params_size(v)


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.get("/catalog")
def scripts_catalog():
    """Return all registered scripts grouped by category (for UI rendering)."""
    scripts = [s.to_catalog_dict() for s in list_scripts()]

    # Group by category preserving a stable order
    category_order = list(CATEGORY_LABELS_PL.keys())
    grouped: dict[str, dict] = {}
    for s in scripts:
        cat = s["category"]
        if cat not in grouped:
            grouped[cat] = {
                "category": cat,
                "label": CATEGORY_LABELS_PL.get(cat, cat),
                "scripts": [],
            }
        grouped[cat]["scripts"].append(s)

    groups = [grouped[c] for c in category_order if c in grouped]
    # Append any unknown categories last
    for cat, data in grouped.items():
        if cat not in category_order:
            groups.append(data)

    return {"groups": groups, "total": len(scripts)}


@router.post("/{script_id}/dry-run")
def dry_run_script(
    script_id: str,
    body: ScriptRunRequest,
    db: Session = Depends(get_db),
):
    """Run the script in preview mode — returns matches without applying."""
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

    merged = _merge_params(script_id, body.client_id, body.params, db)
    result = script.dry_run(
        db=db,
        client_id=body.client_id,
        date_from=body.date_from,
        date_to=body.date_to,
        params=merged,
    )
    response = {
        "script_id": result.script_id,
        "total_matching": result.total_matching,
        "estimated_savings_pln": result.estimated_savings_pln,
        "params_used": merged,
        "warnings": list(getattr(result, "warnings", []) or []),
        "items": [
            {
                "id": item.id,
                "entity_name": item.entity_name,
                "campaign_id": item.campaign_id,
                "campaign_name": item.campaign_name,
                "reason": item.reason,
                "metrics": item.metrics,
                "estimated_savings_pln": item.estimated_savings_pln,
                "action_payload": item.action_payload,
            }
            for item in result.items
        ],
    }
    # Attach extra data from script (e.g. B1 sends available ad groups for UI dropdown)
    if hasattr(result, "_search_ad_groups"):
        response["search_ad_groups"] = result._search_ad_groups
    return response


@router.post("/{script_id}/execute")
def execute_script(
    script_id: str,
    body: ScriptExecuteRequest,
    db: Session = Depends(get_db),
):
    """Apply actions for the script. Honors `item_ids` filter if provided."""
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

    merged = _merge_params(script_id, body.client_id, body.params, db)
    result = script.execute(
        db=db,
        client_id=body.client_id,
        date_from=body.date_from,
        date_to=body.date_to,
        params=merged,
        item_ids=body.item_ids,
        **({"item_overrides": body.item_overrides} if body.item_overrides else {}),
    )
    return {
        "script_id": result.script_id,
        "applied": result.applied,
        "failed": result.failed,
        "errors": result.errors,
        "applied_items": result.applied_items,
        "circuit_breaker_limit": result.circuit_breaker_limit,
    }


@router.get("/{script_id}/history")
def get_script_history(
    script_id: str,
    client_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Return the most recent ActionLog rows produced by this script.

    Matches on ``context_json->>'script_id'`` which every script populates in
    its execute() path. Result is bucketed by day so the UI can show
    "Ostatnio: 3 dni temu · 12 zastosowanych".
    """
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")
    if limit <= 0 or limit > 200:
        limit = 20

    from sqlalchemy import func
    from app.models.action_log import ActionLog

    # Push the script_id predicate into the DB via JSON_EXTRACT (SQLite 3.38+
    # and PostgreSQL both support it through SQLAlchemy's func). Python-side
    # filter then only handles rows the DB could not confidently decide.
    script_json_path = func.json_extract(ActionLog.context_json, "$.script_id")
    try:
        rows = (
            db.query(ActionLog)
            .filter(
                ActionLog.client_id == client_id,
                ActionLog.context_json.isnot(None),
                script_json_path == script.id,
            )
            .order_by(ActionLog.executed_at.desc())
            .limit(max(limit, 50))
            .all()
        )
    except Exception:
        # Fallback for DBs without JSON_EXTRACT — load a small window and
        # filter in-memory. Kept for portability but should rarely run.
        rows = (
            db.query(ActionLog)
            .filter(
                ActionLog.client_id == client_id,
                ActionLog.context_json.isnot(None),
            )
            .order_by(ActionLog.executed_at.desc())
            .limit(500)
            .all()
        )
    matched = [
        r for r in rows
        if isinstance(r.context_json, dict) and r.context_json.get("script_id") == script.id
    ][:limit]

    # Bucket by day for a compact recent-activity summary.
    by_day: dict[str, dict] = {}
    for row in matched:
        day = (row.executed_at or _current_day()).date().isoformat()
        slot = by_day.setdefault(day, {"day": day, "applied": 0, "failed": 0})
        if row.status == "SUCCESS":
            slot["applied"] += 1
        elif row.status == "FAILED":
            slot["failed"] += 1

    last = matched[0] if matched else None
    return {
        "script_id": script.id,
        "total_runs": len(matched),
        "applied_total": sum(s["applied"] for s in by_day.values()),
        "failed_total": sum(s["failed"] for s in by_day.values()),
        "last_executed_at": last.executed_at.isoformat() if last and last.executed_at else None,
        "recent_days": sorted(by_day.values(), key=lambda s: s["day"], reverse=True),
    }


def _current_day():
    from datetime import datetime
    return datetime.now()


# ── Per-client config management ───────────────────────────────────────────
@router.get("/config/{client_id}")
def get_client_configs(client_id: int, db: Session = Depends(get_db)):
    """Return saved script configs for a client, merged with defaults."""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    saved = client.script_configs or {}
    result = {}
    for script in list_scripts():
        merged = dict(script.default_params)
        if script.id in saved and isinstance(saved[script.id], dict):
            merged.update(saved[script.id])
        result[script.id] = {
            "params": merged,
            "is_customized": script.id in saved,
        }
    return result


@router.put("/{script_id}/config")
def save_script_config(
    script_id: str,
    body: SaveConfigRequest,
    db: Session = Depends(get_db),
):
    """Save per-client param overrides for a script."""
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")

    client = db.get(Client, body.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    configs = dict(client.script_configs or {})
    # Use the canonical registry key so the URL path cannot poison the JSON
    # blob with an unrelated slug.
    configs[script.id] = body.params
    client.script_configs = configs
    db.commit()
    return {"status": "ok", "script_id": script.id, "saved_params": body.params}


@router.delete("/{script_id}/config/{client_id}")
def reset_script_config(
    script_id: str,
    client_id: int,
    db: Session = Depends(get_db),
):
    """Reset a script's config to defaults for this client."""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    configs = dict(client.script_configs or {})
    configs.pop(script_id, None)
    client.script_configs = configs
    db.commit()
    return {"status": "ok", "reset": script_id}
