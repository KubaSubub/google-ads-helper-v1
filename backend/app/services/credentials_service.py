"""Credentials Service - the only place allowed to read or write secrets."""

from typing import Mapping, Optional

import keyring


SERVICE_NAME = "GoogleAdsHelper"


class CredentialPersistenceError(RuntimeError):
    """Sanitized error raised when credentials cannot be safely persisted."""


class CredentialsService:
    """Wrapper for Windows Credential Manager (keyring)."""

    REFRESH_TOKEN = "refresh_token"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"
    DEVELOPER_TOKEN = "developer_token"
    LOGIN_CUSTOMER_ID = "login_customer_id"

    SETUP_KEYS = (DEVELOPER_TOKEN, CLIENT_ID, CLIENT_SECRET)
    ALL_KEYS = (
        REFRESH_TOKEN,
        CLIENT_ID,
        CLIENT_SECRET,
        DEVELOPER_TOKEN,
        LOGIN_CUSTOMER_ID,
    )

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Retrieve a credential from Windows Credential Manager."""
        try:
            return keyring.get_password(SERVICE_NAME, key)
        except Exception:
            return None

    @staticmethod
    def set(key: str, value: str) -> bool:
        """Save a credential to Windows Credential Manager."""
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except Exception:
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Remove a credential from Windows Credential Manager."""
        try:
            keyring.delete_password(SERVICE_NAME, key)
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception:
            return False

    @classmethod
    def _restore_snapshot(cls, snapshot: Mapping[str, Optional[str]]):
        """Best-effort rollback for partially completed credential writes."""
        for key, previous_value in snapshot.items():
            if previous_value is None:
                cls.delete(key)
                continue
            cls.set(key, previous_value)

    @classmethod
    def save_and_verify(
        cls,
        values: Mapping[str, Optional[str]],
        clear_keys: tuple[str, ...] = (),
    ) -> None:
        """Persist credentials atomically and verify each write."""
        normalized: dict[str, str] = {}
        keys_to_clear = set(clear_keys)

        for key, raw_value in values.items():
            if raw_value is None:
                continue
            value = raw_value.strip() if isinstance(raw_value, str) else str(raw_value).strip()
            if value:
                normalized[key] = value
            else:
                keys_to_clear.add(key)

        affected_keys = tuple(dict.fromkeys([*normalized.keys(), *keys_to_clear]))
        snapshot = {key: cls.get(key) for key in affected_keys}

        try:
            for key, value in normalized.items():
                if not cls.set(key, value):
                    raise CredentialPersistenceError(
                        "Nie udalo sie zapisac credentials w Windows Credential Manager."
                    )
                if cls.get(key) != value:
                    raise CredentialPersistenceError(
                        "Nie udalo sie zweryfikowac zapisu credentials w Windows Credential Manager."
                    )

            for key in keys_to_clear:
                cls.delete(key)
                if cls.get(key) is not None:
                    raise CredentialPersistenceError(
                        "Nie udalo sie wyczyscic poprzednich credentials w Windows Credential Manager."
                    )
        except CredentialPersistenceError:
            cls._restore_snapshot(snapshot)
            raise
        except Exception as exc:
            cls._restore_snapshot(snapshot)
            raise CredentialPersistenceError(
                "Nie udalo sie zapisac credentials w Windows Credential Manager."
            ) from exc

    @classmethod
    def exists(cls) -> bool:
        """Check if the OAuth refresh token is present."""
        return cls.get(cls.REFRESH_TOKEN) is not None

    @classmethod
    def get_missing_credentials(cls, keys: tuple[str, ...]) -> list[str]:
        """Return the credential keys that are currently missing."""
        return [key for key in keys if not cls.get(key)]

    @classmethod
    def has_complete_setup(cls) -> bool:
        """Check whether all non-OAuth setup credentials are present."""
        return not cls.get_missing_credentials(cls.SETUP_KEYS)

    @classmethod
    def get_google_ads_credentials(cls) -> dict[str, Optional[str]]:
        """Get all Google Ads credentials from the secure store."""
        return {
            "developer_token": cls.get(cls.DEVELOPER_TOKEN),
            "client_id": cls.get(cls.CLIENT_ID),
            "client_secret": cls.get(cls.CLIENT_SECRET),
            "refresh_token": cls.get(cls.REFRESH_TOKEN),
            "login_customer_id": cls.get(cls.LOGIN_CUSTOMER_ID),
        }

    @classmethod
    def clear_all(cls):
        """Remove all stored Google Ads credentials."""
        for key in cls.ALL_KEYS:
            cls.delete(key)
