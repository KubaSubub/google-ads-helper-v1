"""Shared test fixtures - in-memory SQLite DB for fast tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.security import require_session
from app.services.google_ads import GoogleAdsService, google_ads_service


@pytest.fixture
def db():
    """Yield a fresh in-memory SQLite session per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def disable_live_google_ads(monkeypatch):
    """Tests should not auto-connect to a real Google Ads account."""
    monkeypatch.setattr(GoogleAdsService, "_try_init", lambda self: None)
    google_ads_service.client = None
    yield
    google_ads_service.client = None


@pytest.fixture(autouse=True)
def bypass_auth_for_non_auth_tests(request):
    """Keep legacy endpoint tests working unless they explicitly verify auth."""
    filename = request.node.fspath.basename
    if filename in {"test_auth_session.py", "test_security_hardening.py"}:
        yield
        return

    app.dependency_overrides[require_session] = lambda: True
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_session, None)
