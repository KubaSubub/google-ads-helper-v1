"""Session token management for API authorization."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.services.credentials_service import CredentialsService


class SessionService:
    """Stores API session token in keyring with expiry metadata."""

    SESSION_TOKEN = "session_token"
    SESSION_EXPIRES_AT = "session_expires_at"
    OAUTH_STATE = "oauth_state"
    OAUTH_STATE_EXPIRES_AT = "oauth_state_expires_at"

    @classmethod
    def issue_session(cls) -> dict:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)

        CredentialsService.set(cls.SESSION_TOKEN, token)
        CredentialsService.set(cls.SESSION_EXPIRES_AT, expires_at.isoformat())

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    @classmethod
    def get_session(cls) -> Optional[dict]:
        token = CredentialsService.get(cls.SESSION_TOKEN)
        expires_raw = CredentialsService.get(cls.SESSION_EXPIRES_AT)
        if not token or not expires_raw:
            return None

        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            cls.clear_session()
            return None

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= datetime.now(timezone.utc):
            cls.clear_session()
            return None

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    @classmethod
    def ensure_session(cls) -> dict:
        existing = cls.get_session()
        if existing:
            return existing
        return cls.issue_session()

    @classmethod
    def is_valid(cls, token: str) -> bool:
        if not token:
            return False

        session = cls.get_session()
        if not session:
            return False

        return secrets.compare_digest(token, session["token"])

    @classmethod
    def clear_session(cls):
        CredentialsService.delete(cls.SESSION_TOKEN)
        CredentialsService.delete(cls.SESSION_EXPIRES_AT)

    @classmethod
    def issue_oauth_state(cls) -> str:
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        CredentialsService.set(cls.OAUTH_STATE, state)
        CredentialsService.set(cls.OAUTH_STATE_EXPIRES_AT, expires_at.isoformat())
        return state

    @classmethod
    def verify_oauth_state(cls, state: Optional[str]) -> bool:
        saved_state = CredentialsService.get(cls.OAUTH_STATE)
        expires_raw = CredentialsService.get(cls.OAUTH_STATE_EXPIRES_AT)

        if not state or not saved_state or not expires_raw:
            return False

        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            cls.clear_oauth_state()
            return False

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= datetime.now(timezone.utc):
            cls.clear_oauth_state()
            return False

        is_valid = secrets.compare_digest(state, saved_state)
        cls.clear_oauth_state()
        return is_valid

    @classmethod
    def clear_oauth_state(cls):
        CredentialsService.delete(cls.OAUTH_STATE)
        CredentialsService.delete(cls.OAUTH_STATE_EXPIRES_AT)
