"""
Google Ads Helper - FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --port 8000
"""

import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger


class PLJsonEncoder(json.JSONEncoder):
    """JSON encoder that appends 'Z' to naive datetimes (assumed UTC)."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            # Naive datetimes from DB are UTC — mark them so browsers convert to local TZ
            if obj.tzinfo is None:
                return obj.isoformat() + "Z"
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class UTCJsonResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            cls=PLJsonEncoder,
            ensure_ascii=False,
        ).encode("utf-8")

from app.config import settings
from app.database import init_db
from app.routers import (
    actions,
    agent,
    analytics,
    auth,
    campaigns,
    clients,
    daily_audit,
    export,
    history,
    keywords_ads,
    recommendations,
    reports,
    search_terms,
    semantic,
    sync,
)
from app.security import require_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup, cleanup on shutdown."""
    logger.info("Starting Google Ads Helper API...")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(f"Database ready: {settings.database_url}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Google Ads Helper API",
    description="Local-first API for managing and optimizing Google Ads campaigns.",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=UTCJsonResponse,
)

# CORS - allow frontend dev server (Vite default port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
protected = [Depends(require_session)]

app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])
app.include_router(clients.router, prefix=API_PREFIX, tags=["clients"], dependencies=protected)
app.include_router(campaigns.router, prefix=API_PREFIX, tags=["campaigns"], dependencies=protected)
app.include_router(search_terms.router, prefix=API_PREFIX, tags=["search-terms"], dependencies=protected)
app.include_router(keywords_ads.router, prefix=API_PREFIX, tags=["keywords", "ads"], dependencies=protected)
app.include_router(analytics.router, prefix=API_PREFIX, tags=["analytics"], dependencies=protected)
app.include_router(sync.router, prefix=API_PREFIX, tags=["sync"], dependencies=protected)
app.include_router(export.router, prefix=API_PREFIX, tags=["export"], dependencies=protected)
app.include_router(semantic.router, prefix=API_PREFIX, tags=["semantic"], dependencies=protected)
app.include_router(recommendations.router, prefix=API_PREFIX, tags=["recommendations"], dependencies=protected)
app.include_router(actions.router, prefix=API_PREFIX, tags=["actions"], dependencies=protected)
app.include_router(history.router, prefix=API_PREFIX, tags=["history"], dependencies=protected)
app.include_router(agent.router, prefix=API_PREFIX, tags=["agent"], dependencies=protected)
app.include_router(reports.router, prefix=API_PREFIX, tags=["reports"], dependencies=protected)
app.include_router(daily_audit.router, prefix=API_PREFIX, tags=["daily-audit"], dependencies=protected)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "version": app.version,
        "env": settings.app_env,
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Google Ads Helper API",
        "docs": "/docs",
        "health": "/health",
    }
