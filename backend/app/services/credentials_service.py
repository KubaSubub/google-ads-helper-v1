"""Credentials Service - single place for credential storage."""

import os
from typing import Optional

import keyring


SERVICE_NAME = "GoogleAdsHelper"


class CredentialsService:
    """Wrapper for Windows Credential Manager (keyring)."""

    REFRESH_TOKEN = "refresh_token"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"
    DEVELOPER_TOKEN = "developer_token"
    LOGIN_CUSTOMER_ID = "login_customer_id"

    @staticmethod
    def get(key: str) -> Optional[str]:
        if os.getenv("DEV_MODE") == "1":
            return os.getenv(f"GOOGLE_ADS_{key.upper()}")

        try:
            return keyring.get_password(SERVICE_NAME, key)
        except Exception:
            return None

    @staticmethod
    def set(key: str, value: str) -> bool:
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except Exception:
            return False

    @staticmethod
    def delete(key: str) -> bool:
        try:
            keyring.delete_password(SERVICE_NAME, key)
            return True
        except keyring.errors.PasswordDeleteError:
            return False
        except Exception:
            return False

    @classmethod
    def exists(cls) -> bool:
        return cls.get(cls.REFRESH_TOKEN) is not None

    @classmethod
    def get_google_ads_credentials(cls) -> dict:
        return {
            "developer_token": cls.get(cls.DEVELOPER_TOKEN),
            "client_id": cls.get(cls.CLIENT_ID),
            "client_secret": cls.get(cls.CLIENT_SECRET),
            "refresh_token": cls.get(cls.REFRESH_TOKEN),
            "login_customer_id": cls.get(cls.LOGIN_CUSTOMER_ID),
        }

    @classmethod
    def clear_all(cls):
        for key in [
            cls.REFRESH_TOKEN,
            cls.CLIENT_ID,
            cls.CLIENT_SECRET,
            cls.DEVELOPER_TOKEN,
            cls.LOGIN_CUSTOMER_ID,
        ]:
            cls.delete(key)
