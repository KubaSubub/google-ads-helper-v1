"""Credentials Service - JEDYNE miejsce na odczyt/zapis tokenów.

ADR-004: Windows Credential Manager via keyring.
CLAUDE.md Reguła 5: NEVER store tokens in .env, SQLite, or logs.

This is the ONLY module allowed to access credentials.
"""

import keyring
from typing import Optional
import os


SERVICE_NAME = "GoogleAdsHelper"


class CredentialsService:
    """Wrapper for Windows Credential Manager (keyring).

    All credential operations MUST go through this service.
    """

    # Keys stored in Credential Manager
    REFRESH_TOKEN = "refresh_token"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"
    DEVELOPER_TOKEN = "developer_token"

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Retrieve credential from Windows Credential Manager.

        Args:
            key: Credential key (e.g., "refresh_token")

        Returns:
            Credential value or None if not found
        """
        # DEV MODE fallback (for Linux/Mac development)
        if os.getenv("DEV_MODE") == "1":
            return os.getenv(f"GOOGLE_ADS_{key.upper()}")

        try:
            value = keyring.get_password(SERVICE_NAME, key)
            return value
        except Exception as e:
            # Don't log the error message as it might contain sensitive info
            return None

    @staticmethod
    def set(key: str, value: str) -> bool:
        """Save credential to Windows Credential Manager.

        Args:
            key: Credential key
            value: Credential value (will be encrypted by Windows)

        Returns:
            True if successful, False otherwise
        """
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except Exception as e:
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Remove credential from Windows Credential Manager.

        Args:
            key: Credential key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            keyring.delete_password(SERVICE_NAME, key)
            return True
        except keyring.errors.PasswordDeleteError:
            # Already doesn't exist
            return False
        except Exception as e:
            return False

    @classmethod
    def exists(cls) -> bool:
        """Check if user is authenticated (refresh_token exists).

        Returns:
            True if refresh_token is stored, False otherwise
        """
        return cls.get(cls.REFRESH_TOKEN) is not None

    @classmethod
    def get_google_ads_credentials(cls) -> dict:
        """Get all Google Ads API credentials as a dict.

        Returns:
            Dict with developer_token, client_id, client_secret, refresh_token
        """
        return {
            "developer_token": cls.get(cls.DEVELOPER_TOKEN),
            "client_id": cls.get(cls.CLIENT_ID),
            "client_secret": cls.get(cls.CLIENT_SECRET),
            "refresh_token": cls.get(cls.REFRESH_TOKEN),
        }

    @classmethod
    def clear_all(cls):
        """Remove all credentials (logout).

        Deletes all stored credentials from Windows Credential Manager.
        """
        for key in [cls.REFRESH_TOKEN, cls.CLIENT_ID, cls.CLIENT_SECRET, cls.DEVELOPER_TOKEN]:
            cls.delete(key)
