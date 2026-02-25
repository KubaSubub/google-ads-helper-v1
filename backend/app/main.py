"""
Google Ads Helper — FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import init_db
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


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown logic
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables on startup, cleanup on shutdown."""
    logger.info("Starting Google Ads Helper API...")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(f"Database ready: {settings.database_url}")
    yield
    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Google Ads Helper API",
    description="Local-first API for managing and optimizing Google Ads campaigns.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server (Vite default port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])
app.include_router(clients.router, prefix=API_PREFIX, tags=["clients"])
app.include_router(campaigns.router, prefix=API_PREFIX, tags=["campaigns"])
app.include_router(search_terms.router, prefix=API_PREFIX, tags=["search-terms"])
app.include_router(keywords_ads.router, prefix=API_PREFIX, tags=["keywords", "ads"])
app.include_router(analytics.router, prefix=API_PREFIX, tags=["analytics"])
app.include_router(sync.router, prefix=API_PREFIX, tags=["sync"])
app.include_router(export.router, prefix=API_PREFIX, tags=["export"])
app.include_router(semantic.router, prefix=API_PREFIX, tags=["semantic"])
app.include_router(recommendations.router, prefix=API_PREFIX, tags=["recommendations"])
app.include_router(actions.router, prefix=API_PREFIX, tags=["actions"])
app.include_router(history.router, prefix=API_PREFIX, tags=["history"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

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
