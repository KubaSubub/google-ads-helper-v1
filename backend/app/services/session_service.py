"""In-memory session token management for API authorization."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Optional

SESSION_TTL_MINUTES = 60
SESSION_COOKIE_NAME = "gah_session"


class SessionService:
    """Short-lived in-memory session store keyed by token hash."""

    _sessions: dict[str, datetime] = {}

    @classmethod
    def _now(cls) -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _hash(cls, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, ttl_minutes: int = SESSION_TTL_MINUTES) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = cls._hash(token)
        cls._sessions[token_hash] = cls._now() + timedelta(minutes=ttl_minutes)
        cls._purge_expired()
        return token

    @classmethod
    def is_valid(cls, token: Optional[str]) -> bool:
        if not token:
            return False
        token_hash = cls._hash(token)
        expires_at = cls._sessions.get(token_hash)
        if not expires_at:
            return False
        if expires_at <= cls._now():
            cls._sessions.pop(token_hash, None)
            return False
        return True

    @classmethod
    def revoke(cls, token: Optional[str]) -> None:
        if not token:
            return
        cls._sessions.pop(cls._hash(token), None)

    @classmethod
    def clear_all(cls) -> None:
        cls._sessions.clear()

    @classmethod
    def _purge_expired(cls) -> None:
        now = cls._now()
        for key, expires_at in list(cls._sessions.items()):
            if expires_at <= now:
                cls._sessions.pop(key, None)
