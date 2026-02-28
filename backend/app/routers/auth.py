"""
OAuth2 flow for Google Ads API.

Endpoints:
  GET  /auth/status        — check if user is authenticated
  GET  /auth/setup-status  — check if API credentials are configured
  POST /auth/setup         — save API credentials (first-time setup)
  GET  /auth/login         — generate OAuth consent URL
  GET  /auth/callback      — Google redirects here with code
  POST /auth/logout        — clear all credentials
"""

import os

# Allow HTTP redirect for localhost (desktop app)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.credentials_service import CredentialsService


class SetupRequest(BaseModel):
    developer_token: str
    client_id: str
    client_secret: str
    login_customer_id: str = ""

router = APIRouter(prefix="/auth", tags=["Authentication"])

SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"


def _build_flow() -> Flow:
    """Create OAuth2 Flow. Priority: keyring → .env."""
    client_id = (
        CredentialsService.get(CredentialsService.CLIENT_ID)
        or settings.google_ads_client_id
    )
    client_secret = (
        CredentialsService.get(CredentialsService.CLIENT_SECRET)
        or settings.google_ads_client_secret
    )
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


@router.get("/status")
async def auth_status():
    """Check if user has completed OAuth (refresh_token in keyring)."""
    has_credentials = bool(
        (CredentialsService.get(CredentialsService.CLIENT_ID) or settings.google_ads_client_id)
        and (CredentialsService.get(CredentialsService.DEVELOPER_TOKEN) or settings.google_ads_developer_token)
    )
    return {
        "authenticated": CredentialsService.exists(),
        "configured": has_credentials,
    }


@router.get("/setup-status")
async def setup_status():
    """Check if API credentials (developer_token, client_id, client_secret) are configured."""
    developer_token = CredentialsService.get(CredentialsService.DEVELOPER_TOKEN) or settings.google_ads_developer_token
    client_id = CredentialsService.get(CredentialsService.CLIENT_ID) or settings.google_ads_client_id
    client_secret = CredentialsService.get(CredentialsService.CLIENT_SECRET) or settings.google_ads_client_secret
    login_customer_id = settings.google_ads_login_customer_id

    return {
        "configured": bool(developer_token and client_id and client_secret),
        "has_developer_token": bool(developer_token),
        "has_client_id": bool(client_id),
        "has_client_secret": bool(client_secret),
        "has_login_customer_id": bool(login_customer_id),
    }


@router.post("/setup")
async def setup(data: SetupRequest):
    """Save API credentials to Windows Credential Manager (first-time setup)."""
    if not data.developer_token or not data.client_id or not data.client_secret:
        raise HTTPException(status_code=400, detail="Wszystkie pola sa wymagane.")

    CredentialsService.set(CredentialsService.DEVELOPER_TOKEN, data.developer_token.strip())
    CredentialsService.set(CredentialsService.CLIENT_ID, data.client_id.strip())
    CredentialsService.set(CredentialsService.CLIENT_SECRET, data.client_secret.strip())

    if data.login_customer_id:
        # Store login_customer_id in settings override (keyring)
        CredentialsService.set("login_customer_id", data.login_customer_id.strip())

    logger.info("API credentials saved to Windows Credential Manager via /auth/setup")
    return {"success": True, "message": "Credentials zapisane. Mozesz teraz sie zalogowac."}


@router.get("/login")
async def login():
    """Generate Google OAuth consent URL for the user to open in browser."""
    client_id = (
        CredentialsService.get(CredentialsService.CLIENT_ID)
        or settings.google_ads_client_id
    )
    client_secret = (
        CredentialsService.get(CredentialsService.CLIENT_SECRET)
        or settings.google_ads_client_secret
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google Ads client_id lub client_secret nie skonfigurowane. Ustaw w .env lub uruchom pierwszą konfigurację.",
        )

    flow = _build_flow()
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    logger.info("OAuth login URL generated")
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str = None, error: str = None):
    """Google redirects here after user grants/denies consent."""
    if error:
        logger.warning(f"OAuth denied: {error}")
        return HTMLResponse(_html_page(
            "Logowanie anulowane",
            "Odmówiono dostępu. Możesz zamknąć to okno i spróbować ponownie.",
            success=False,
        ))

    if not code:
        raise HTTPException(status_code=400, detail="Brak parametru 'code'")

    try:
        flow = _build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        if not creds.refresh_token:
            logger.error("No refresh_token returned by Google")
            return HTMLResponse(_html_page(
                "Brak refresh token",
                "Google nie zwrócił refresh token. "
                "Usuń dostęp aplikacji na <a href='https://myaccount.google.com/permissions' "
                "style='color:#3B82F6'>myaccount.google.com/permissions</a> i spróbuj ponownie.",
                success=False,
            ))

        # Save to Windows Credential Manager
        CredentialsService.set(CredentialsService.REFRESH_TOKEN, creds.refresh_token)
        CredentialsService.set(CredentialsService.CLIENT_ID, creds.client_id)
        CredentialsService.set(CredentialsService.CLIENT_SECRET, creds.client_secret)
        # Persist developer_token (may come from setup or .env)
        dev_token = (
            CredentialsService.get(CredentialsService.DEVELOPER_TOKEN)
            or settings.google_ads_developer_token
        )
        if dev_token:
            CredentialsService.set(CredentialsService.DEVELOPER_TOKEN, dev_token)

        logger.info("OAuth success — tokens saved to Windows Credential Manager")
        return HTMLResponse(_html_page(
            "Logowanie udane!",
            "Wróć do aplikacji Google Ads Helper. Możesz zamknąć to okno.",
            success=True,
        ))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"Błąd autentykacji: {e}")


@router.post("/logout")
async def logout():
    """Clear all credentials from Windows Credential Manager."""
    CredentialsService.clear_all()
    logger.info("User logged out — credentials cleared")
    return {"status": "logged_out"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _html_page(title: str, message: str, success: bool = True) -> str:
    color = "#10B981" if success else "#EF4444"
    icon = "&#10003;" if success else "&#10007;"
    return f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="utf-8"><title>{title}</title></head>
<body style="
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; margin: 0;
    background: #0F172A; color: #F1F5F9;
">
<div style="text-align:center; max-width:420px; padding:40px;">
    <div style="
        width:64px; height:64px; border-radius:50%;
        background:{color}22; color:{color};
        display:flex; align-items:center; justify-content:center;
        font-size:32px; margin:0 auto 24px;
    ">{icon}</div>
    <h1 style="font-size:24px; margin:0 0 12px;">{title}</h1>
    <p style="color:#94A3B8; line-height:1.6;">{message}</p>
</div>
<script>setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 3000);</script>
</body>
</html>"""
