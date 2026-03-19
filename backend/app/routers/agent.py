"""AI Agent router — report generation via Claude Code headless mode."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.agent_service import AgentService, check_claude_available

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["AI Agent"])

# In-memory lock — one report at a time (single-user app)
_generating = asyncio.Lock()

VALID_REPORT_TYPES = {"weekly", "campaigns", "keywords", "search_terms", "budget", "alerts", "freeform"}


class ChatRequest(BaseModel):
    message: str
    report_type: str = "freeform"


@router.get("/status")
async def agent_status():
    """Check if Claude CLI is available."""
    return await check_claude_available()


@router.post("/chat")
async def agent_chat(
    req: ChatRequest,
    client_id: int = Query(..., description="Client ID"),
    db: Session = Depends(get_db),
):
    """Generate a report via Claude Code headless mode. Returns SSE stream."""
    report_type = req.report_type if req.report_type in VALID_REPORT_TYPES else "freeform"

    async def event_stream():
        # Atomic lock check — both check and acquire in same async context
        if _generating.locked():
            yield _sse_event("error", "Agent jest zajety — poczekaj na zakonczenie poprzedniego raportu.")
            yield _sse_event("done", "")
            return

        async with _generating:
            yield _sse_event("status", "Generuje raport z Claude...")
            service = AgentService(db, client_id)

            try:
                async for chunk in service.generate_report(req.message, report_type):
                    try:
                        parsed = json.loads(chunk)
                        event_type = parsed.get("type", "delta")
                        content = parsed.get("content", "")
                        if event_type == "usage":
                            yield _sse_event("usage", json.dumps(content, default=str))
                        else:
                            yield _sse_event(event_type, content)
                    except json.JSONDecodeError:
                        yield _sse_event("delta", chunk)
            except Exception as exc:
                logger.exception("Report generation failed")
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


def _sse_event(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    escaped = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {escaped}\n\n"


async def _error_stream(message: str):
    """Yield a single error event."""
    yield _sse_event("error", message)
    yield _sse_event("done", "")
