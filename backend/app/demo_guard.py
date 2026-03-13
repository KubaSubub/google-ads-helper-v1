"""Protection helpers for the DEMO client write-lock."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.client import Client


def _normalize_customer_id(value: str | None) -> str:
    return (value or "").replace("-", "").strip()


def _is_demo_record(client: Client | None) -> bool:
    if client is None:
        return False

    if settings.demo_client_id is not None and client.id == settings.demo_client_id:
        return True

    demo_cid = _normalize_customer_id(settings.demo_google_customer_id)
    if demo_cid and _normalize_customer_id(client.google_customer_id) == demo_cid:
        return True

    return False


def is_demo_protected_client(db: Session, client_id: int | None) -> bool:
    if not settings.demo_protection_enabled or client_id is None:
        return False

    client = db.get(Client, client_id)
    return _is_demo_record(client)


def demo_write_lock_reason(operation: str = "Ta operacja") -> str:
    return (
        f"{operation} jest zablokowana dla klienta DEMO. "
        "Klient DEMO jest chroniony przed zmianami. "
        "Uzyj allow_demo_write=true tylko przy swiadomym, jednorazowym odblokowaniu."
    )


def ensure_demo_write_allowed(
    db: Session,
    client_id: int | None,
    allow_demo_write: bool = False,
    operation: str = "Ta operacja",
) -> None:
    if allow_demo_write:
        return
    if is_demo_protected_client(db, client_id):
        raise HTTPException(status_code=423, detail=demo_write_lock_reason(operation))
