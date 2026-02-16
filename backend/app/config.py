"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Central configuration — reads from .env file or environment variables."""

    # App
    app_env: str = "development"
    app_secret_key: str = "change-this-to-a-random-string"

    # Database
    database_url: str = "sqlite:///./data/google_ads_app.db"

    # Google Ads API
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_login_customer_id: str = ""

    # Data sync interval in hours
    data_sync_interval_hours: int = 6

    # Cache TTL in seconds (default 1 hour)
    cache_ttl: int = 3600

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def data_dir(self) -> Path:
        """Directory for persistent data (SQLite DB, logs, etc.)."""
        path = Path("./data")
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
