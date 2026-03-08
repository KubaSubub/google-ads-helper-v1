"""
Google Ads Helper - FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db
from app.security import require_session
from app.routers import (
    auth,
    clients,
    campaigns,
    search_terms,
    analytics,
    keywords_ads,
    sync,
    export,
    semantic,
    recommendations,
    actions,
    history,
)


DEFAULT_SECRET = "change-this-to-a-random-string"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup, cleanup on shutdown."""
    logger.info("Starting Google Ads Helper API...")

    if settings.is_production_like and settings.app_secret_key == DEFAULT_SECRET:
        raise RuntimeError("APP_SECRET_KEY must be changed for production-like environments")

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
)

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

# Public auth endpoints
app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])

# Protected API surface
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
