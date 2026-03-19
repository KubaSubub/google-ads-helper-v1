"""Reports router — generate, list, and retrieve monthly reports."""

import asyncio
import json
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report
from app.services.agent_service import AgentService, MONTHLY_PROMPT, REPORT_DATA_MAP, check_claude_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

_reports_lock = asyncio.Lock()


class ReportGenerateRequest(BaseModel):
    report_type: str = "monthly"
    year: int | None = None
    month: int | None = None


class ReportListItem(BaseModel):
    id: int
    report_type: str
    period_label: str | None
    status: str
    created_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ReportDetail(BaseModel):
    id: int
    client_id: int
    report_type: str
    period_label: str | None
    date_from: date | None
    date_to: date | None
    status: str
    report_data: dict | None
    ai_narrative: str | None
    error_message: str | None
    created_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


def _sse_event(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    escaped = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {escaped}\n\n"


@router.post("/generate")
async def generate_report(
    req: ReportGenerateRequest,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Generate a monthly report. Returns SSE stream and saves to DB."""
    today = date.today()
    year = req.year or today.year
    month = req.month or today.month

    import calendar as cal
    period_start = date(year, month, 1)
    last_day = cal.monthrange(year, month)[1]
    period_end = date(year, month, last_day)
    period_label = f"{year}-{month:02d}"

    async def event_stream():
        if _reports_lock.locked():
            yield _sse_event("error", "Generowanie raportu jest juz w toku — poczekaj na zakonczenie.")
            yield _sse_event("done", "")
            return

        async with _reports_lock:
            # Create report row
            report = Report(
                client_id=client_id,
                report_type=req.report_type,
                period_label=period_label,
                date_from=period_start,
                date_to=period_end,
                status="generating",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            report_id = report.id

            try:
                service = AgentService(db, client_id)

                # Phase 1: Gather data section-by-section with progress
                import calendar as cal2
                service._period_start = period_start
                service._period_end = period_end

                sections = REPORT_DATA_MAP.get(req.report_type, REPORT_DATA_MAP["monthly"])
                section_labels = {
                    "month_comparison": "Porownanie m/m",
                    "campaigns_detail": "Kampanie",
                    "change_history": "Historia zmian",
                    "change_impact": "Analiza wplywu zmian",
                    "budget_pacing": "Realizacja budzetow",
                    "wasted_spend": "Zmarnowane wydatki",
                    "alerts": "Alerty",
                    "health": "Health score",
                }
                total_sections = len(sections)
                data = {}

                for i, section in enumerate(sections):
                    pct = int((i / (total_sections + 2)) * 65)  # 0–65% for data
                    label = section_labels.get(section, section)
                    yield _sse_event("progress", json.dumps({
                        "pct": pct, "label": label,
                    }))
                    try:
                        data[section] = service._gather_section(section)
                    except Exception as exc:
                        logger.warning("Section %s failed: %s", section, exc)
                        data[section] = {"error": str(exc)}

                report.report_data = json.dumps(data, ensure_ascii=False, default=str)
                db.commit()

                yield _sse_event("progress", json.dumps({"pct": 65, "label": "Dane gotowe"}))
                yield _sse_event("data_ready", json.dumps({
                    "report_id": report_id,
                    "report_data": data,
                }, ensure_ascii=False, default=str))

                # Phase 2: Generate AI narrative via Claude CLI
                claude_status = await check_claude_available()
                if not claude_status.get("available"):
                    report.status = "completed"
                    report.ai_narrative = "(Claude CLI niedostepny — raport zawiera tylko dane strukturalne)"
                    report.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    yield _sse_event("delta", report.ai_narrative)
                    yield _sse_event("progress", json.dumps({"pct": 100, "label": "Gotowe"}))
                    yield _sse_event("report_id", str(report_id))
                    yield _sse_event("done", "")
                    return

                yield _sse_event("progress", json.dumps({
                    "pct": 70, "label": "Claude generuje narracje...",
                }))

                ai_narrative = ""
                chunk_count = 0
                async for chunk in service.generate_report(MONTHLY_PROMPT, "monthly", pre_gathered_data=data):
                    try:
                        parsed = json.loads(chunk)
                        event_type = parsed.get("type", "delta")
                        content = parsed.get("content", "")
                        if event_type == "delta":
                            ai_narrative += content
                            yield _sse_event("delta", content)
                            chunk_count += 1
                            # Progress 70→95% during AI generation
                            ai_pct = min(70 + int(chunk_count * 0.5), 95)
                            if chunk_count % 5 == 0:
                                yield _sse_event("progress", json.dumps({
                                    "pct": ai_pct, "label": "Claude generuje narracje...",
                                }))
                        elif event_type == "error":
                            yield _sse_event("error", content)
                        elif event_type == "model":
                            report.model_name = content
                            yield _sse_event("model", content)
                        elif event_type == "usage":
                            usage_data = content if isinstance(content, dict) else {}
                            report.input_tokens = usage_data.get("input_tokens")
                            report.output_tokens = usage_data.get("output_tokens")
                            report.cache_read_tokens = usage_data.get("cache_read_tokens")
                            report.total_cost_usd = usage_data.get("total_cost_usd")
                            report.duration_ms = usage_data.get("duration_ms")
                            yield _sse_event("usage", json.dumps(usage_data, default=str))
                    except json.JSONDecodeError:
                        ai_narrative += chunk
                        yield _sse_event("delta", chunk)

                report.ai_narrative = ai_narrative
                report.status = "completed"
                report.completed_at = datetime.now(timezone.utc)
                db.commit()

                yield _sse_event("progress", json.dumps({"pct": 100, "label": "Gotowe"}))
                yield _sse_event("report_id", str(report_id))

            except Exception as exc:
                logger.exception("Report generation failed")
                report.status = "failed"
                report.error_message = str(exc)
                report.completed_at = datetime.now(timezone.utc)
                db.commit()
                yield _sse_event("error", f"Blad generowania raportu: {exc}")

            yield _sse_event("done", "")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/")
def list_reports(
    client_id: int = Query(..., description="Client ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List saved reports for a client."""
    query = db.query(Report).filter(
        Report.client_id == client_id,
    ).order_by(Report.created_at.desc())

    total = query.count()
    reports = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "period_label": r.period_label,
                "status": r.status,
                "created_at": str(r.created_at) if r.created_at else None,
                "completed_at": str(r.completed_at) if r.completed_at else None,
            }
            for r in reports
        ],
    }


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific report with full data."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Raport nie znaleziony")

    return {
        "id": report.id,
        "client_id": report.client_id,
        "report_type": report.report_type,
        "period_label": report.period_label,
        "date_from": str(report.date_from) if report.date_from else None,
        "date_to": str(report.date_to) if report.date_to else None,
        "status": report.status,
        "report_data": json.loads(report.report_data) if report.report_data else None,
        "ai_narrative": report.ai_narrative,
        "error_message": report.error_message,
        "input_tokens": report.input_tokens,
        "output_tokens": report.output_tokens,
        "cache_read_tokens": report.cache_read_tokens,
        "total_cost_usd": report.total_cost_usd,
        "model_name": report.model_name,
        "duration_ms": report.duration_ms,
        "created_at": str(report.created_at) if report.created_at else None,
        "completed_at": str(report.completed_at) if report.completed_at else None,
    }
