"""Application configuration loaded from environment variables."""

import sys
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


_BACKEND_DIR = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_APP_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else _SOURCE_ROOT
)
_ENV_FILE = _BACKEND_DIR / ".env" if (_BACKEND_DIR / ".env").exists() else _APP_ROOT / ".env"


def _default_sqlite_url() -> str:
    db_path = (_APP_ROOT / "data" / "google_ads_app.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


def _normalize_sqlite_url(value: str | None) -> str:
    if not value:
        return _default_sqlite_url()

    if not value.startswith("sqlite:///"):
        return value

    path_part = value.removeprefix("sqlite:///")
    if path_part in {"", ":memory:"}:
        return value

    db_path = Path(path_part)
    if not db_path.is_absolute():
        db_path = _APP_ROOT / db_path

    return f"sqlite:///{db_path.resolve().as_posix()}"


class Settings(BaseSettings):
    """Central configuration - reads from .env file or environment variables."""

    # App
    app_env: str = "development"
    session_ttl_minutes: int = 60
    oauth_allow_insecure_transport: bool = False

    # Database
    database_url: str = _default_sqlite_url()

    # Google Ads API
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_login_customer_id: str = ""

    # Data sync interval in hours
    data_sync_interval_hours: int = 6

    # Cache TTL in seconds (default 1 hour)
    cache_ttl: int = 3600

    # AI Agent (Claude Code headless)
    agent_timeout: int = 120

    # Specialist emails (comma-separated) — used to distinguish external changes
    specialist_emails: str = ""

    # Demo protection
    demo_protection_enabled: bool = True
    # Optional hard pin by runtime client id (leave None to avoid accidental lock on non-demo clients).
    demo_client_id: int | None = None
    # Canonical demo customer id used for write-lock matching.
    demo_google_customer_id: str = "123-456-7890"

    # extra="ignore" — silently drops unknown env vars (e.g. legacy APP_SECRET_KEY in .env files).
    # The app uses OAuth2 + in-memory sessions; no custom secret key is needed.
    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def _resolve_database_url(cls, value: str | None) -> str:
        return _normalize_sqlite_url(value)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production_like(self) -> bool:
        return not self.is_development

    @property
    def data_dir(self) -> Path:
        """Directory for persistent data (SQLite DB, logs, etc.)."""
        return self.app_root / "data"

    @property
    def app_root(self) -> Path:
        """Canonical runtime root for source and frozen builds."""
        return _APP_ROOT

    @property
    def backend_dir(self) -> Path:
        """Backend directory used for config discovery and legacy migrations."""
        return _BACKEND_DIR


settings = Settings()
