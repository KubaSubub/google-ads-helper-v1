"""Tests for demo_guard — DEMO client write-lock protection."""

import pytest
from fastapi import HTTPException

from app.config import settings
from app.demo_guard import (
    _is_demo_record,
    _normalize_customer_id,
    demo_write_lock_reason,
    ensure_demo_write_allowed,
    is_demo_protected_client,
)
from app.models.client import Client


# ---------------------------------------------------------------------------
# _normalize_customer_id
# ---------------------------------------------------------------------------

class TestNormalizeCustomerId:
    def test_strips_dashes(self):
        assert _normalize_customer_id("123-456-7890") == "1234567890"

    def test_strips_whitespace(self):
        assert _normalize_customer_id("  1234567890  ") == "1234567890"

    def test_strips_dashes_and_whitespace(self):
        assert _normalize_customer_id(" 123-456-7890 ") == "1234567890"

    def test_none_returns_empty(self):
        assert _normalize_customer_id(None) == ""

    def test_empty_string(self):
        assert _normalize_customer_id("") == ""


# ---------------------------------------------------------------------------
# _is_demo_record
# ---------------------------------------------------------------------------

class TestIsDemoRecord:
    def test_none_client_returns_false(self):
        assert _is_demo_record(None) is False

    def test_matches_by_customer_id_with_dashes(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(id=99, name="Test", google_customer_id="1234567890")
        assert _is_demo_record(client) is True

    def test_matches_by_customer_id_reverse_dashes(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "1234567890")

        client = Client(id=99, name="Test", google_customer_id="123-456-7890")
        assert _is_demo_record(client) is True

    def test_matches_by_demo_client_id(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_client_id", 42)
        monkeypatch.setattr(settings, "demo_google_customer_id", "")

        client = Client(id=42, name="Test", google_customer_id="9999999999")
        assert _is_demo_record(client) is True

    def test_no_match_different_ids(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(id=99, name="Test", google_customer_id="9999999999")
        assert _is_demo_record(client) is False

    def test_empty_demo_customer_id_does_not_match(self, monkeypatch):
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "")

        client = Client(id=99, name="Test", google_customer_id="1234567890")
        assert _is_demo_record(client) is False


# ---------------------------------------------------------------------------
# is_demo_protected_client
# ---------------------------------------------------------------------------

class TestIsDemoProtectedClient:
    def test_returns_false_when_protection_disabled(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", False)
        client = Client(name="Demo", google_customer_id="123-456-7890")
        db.add(client)
        db.commit()
        db.refresh(client)

        assert is_demo_protected_client(db, client.id) is False

    def test_returns_false_when_client_id_is_none(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        assert is_demo_protected_client(db, None) is False

    def test_returns_false_for_nonexistent_client(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        assert is_demo_protected_client(db, 99999) is False

    def test_returns_true_for_demo_client(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Demo", google_customer_id="1234567890")
        db.add(client)
        db.commit()
        db.refresh(client)

        assert is_demo_protected_client(db, client.id) is True

    def test_returns_false_for_non_demo_client(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Regular", google_customer_id="9999999999")
        db.add(client)
        db.commit()
        db.refresh(client)

        assert is_demo_protected_client(db, client.id) is False


# ---------------------------------------------------------------------------
# ensure_demo_write_allowed
# ---------------------------------------------------------------------------

class TestEnsureDemoWriteAllowed:
    def test_blocks_demo_client_without_override(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Demo", google_customer_id="1234567890")
        db.add(client)
        db.commit()
        db.refresh(client)

        with pytest.raises(HTTPException) as exc_info:
            ensure_demo_write_allowed(db, client.id)

        assert exc_info.value.status_code == 423
        assert "DEMO" in exc_info.value.detail

    def test_allows_demo_client_with_override(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Demo", google_customer_id="1234567890")
        db.add(client)
        db.commit()
        db.refresh(client)

        # Should not raise
        ensure_demo_write_allowed(db, client.id, allow_demo_write=True)

    def test_allows_non_demo_client(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Regular", google_customer_id="9999999999")
        db.add(client)
        db.commit()
        db.refresh(client)

        # Should not raise
        ensure_demo_write_allowed(db, client.id)

    def test_custom_operation_in_error_message(self, db, monkeypatch):
        monkeypatch.setattr(settings, "demo_protection_enabled", True)
        monkeypatch.setattr(settings, "demo_client_id", None)
        monkeypatch.setattr(settings, "demo_google_customer_id", "123-456-7890")

        client = Client(name="Demo", google_customer_id="1234567890")
        db.add(client)
        db.commit()
        db.refresh(client)

        with pytest.raises(HTTPException) as exc_info:
            ensure_demo_write_allowed(db, client.id, operation="Synchronizacja")

        assert "Synchronizacja" in exc_info.value.detail


# ---------------------------------------------------------------------------
# demo_write_lock_reason
# ---------------------------------------------------------------------------

class TestDemoWriteLockReason:
    def test_default_operation(self):
        msg = demo_write_lock_reason()
        assert "Ta operacja" in msg
        assert "DEMO" in msg

    def test_custom_operation(self):
        msg = demo_write_lock_reason("Eksport danych")
        assert "Eksport danych" in msg
