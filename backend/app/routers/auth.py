"""
OAuth2 flow for Google Ads API.

Endpoints:
  GET  /auth/status        - check if user is authenticated
  GET  /auth/setup-status  - check if API credentials are configured
  POST /auth/setup         - save API credentials (first-time setup)
  GET  /auth/login         - generate OAuth consent URL
  GET  /auth/callback      - Google redirects here with code
  POST /auth/logout        - clear all credentials
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.credentials_service import CredentialsService
from app.services.session_service import SessionService


if settings.is_development or settings.oauth_allow_insecure_transport:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
else:
    os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)


class SetupRequest(BaseModel):
    developer_token: str
    client_id: str
    client_secret: str
    login_customer_id: str = ""


router = APIRouter(prefix="/auth", tags=["Authentication"])

SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"


def _allow_env_fallback() -> bool:
    return settings.is_development


def _build_flow() -> Flow:
    """Create OAuth2 Flow. Priority: keyring -> .env (dev only)."""
    if _allow_env_fallback():
        client_id = (
            CredentialsService.get(CredentialsService.CLIENT_ID)
            or settings.google_ads_client_id
        )
        client_secret = (
            CredentialsService.get(CredentialsService.CLIENT_SECRET)
            or settings.google_ads_client_secret
        )
    else:
        client_id = CredentialsService.get(CredentialsService.CLIENT_ID)
        client_secret = CredentialsService.get(CredentialsService.CLIENT_SECRET)

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth client credentials are not configured")

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
    """Check if user has completed OAuth and return active API session if available."""
    has_credentials = bool(
        (CredentialsService.get(CredentialsService.CLIENT_ID) or (_allow_env_fallback() and settings.google_ads_client_id))
        and (CredentialsService.get(CredentialsService.DEVELOPER_TOKEN) or (_allow_env_fallback() and settings.google_ads_developer_token))
    )

    authenticated = CredentialsService.exists()
    response = {
        "authenticated": authenticated,
        "configured": has_credentials,
    }

    if authenticated:
        response["session"] = SessionService.ensure_session()

    return response


@router.get("/setup-status")
async def setup_status():
    """Check if API credentials are configured."""
    if _allow_env_fallback():
        developer_token = CredentialsService.get(CredentialsService.DEVELOPER_TOKEN) or settings.google_ads_developer_token
        client_id = CredentialsService.get(CredentialsService.CLIENT_ID) or settings.google_ads_client_id
        client_secret = CredentialsService.get(CredentialsService.CLIENT_SECRET) or settings.google_ads_client_secret
        login_customer_id = CredentialsService.get("login_customer_id") or settings.google_ads_login_customer_id
    else:
        developer_token = CredentialsService.get(CredentialsService.DEVELOPER_TOKEN)
        client_id = CredentialsService.get(CredentialsService.CLIENT_ID)
        client_secret = CredentialsService.get(CredentialsService.CLIENT_SECRET)
        login_customer_id = CredentialsService.get("login_customer_id")

    return {
        "configured": bool(developer_token and client_id and client_secret),
        "has_developer_token": bool(developer_token),
        "has_client_id": bool(client_id),
        "has_client_secret": bool(client_secret),
        "has_login_customer_id": bool(login_customer_id),
    }


@router.post("/setup")
async def setup(data: SetupRequest):
    """Save API credentials to Credential Manager (first-time setup)."""
    if not data.developer_token or not data.client_id or not data.client_secret:
        raise HTTPException(status_code=400, detail="All required fields must be provided")

    CredentialsService.set(CredentialsService.DEVELOPER_TOKEN, data.developer_token.strip())
    CredentialsService.set(CredentialsService.CLIENT_ID, data.client_id.strip())
    CredentialsService.set(CredentialsService.CLIENT_SECRET, data.client_secret.strip())

    if data.login_customer_id:
        CredentialsService.set("login_customer_id", data.login_customer_id.strip())

    logger.info("API credentials saved to Credential Manager via /auth/setup")
    return {"success": True, "message": "Credentials saved. You can log in now."}


@router.get("/login")
async def login():
    """Generate Google OAuth consent URL for the user to open in browser."""
    flow = _build_flow()
    state = SessionService.issue_oauth_state()

    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=state,
    )
    logger.info("OAuth login URL generated")
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str = None, state: str = None, error: str = None):
    """Google redirects here after user grants/denies consent."""
    if error:
        logger.warning(f"OAuth denied: {error}")
        return HTMLResponse(_html_page(
            "Logowanie anulowane",
            "Odmowiono dostepu. Mozesz zamknac to okno i sprobowac ponownie.",
            success=False,
        ))

    if not code:
        raise HTTPException(status_code=400, detail="Missing parameter: code")

    if not SessionService.verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    try:
        flow = _build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        if not creds.refresh_token:
            logger.error("No refresh_token returned by Google")
            return HTMLResponse(_html_page(
                "Brak refresh token",
                "Google nie zwrocil refresh token. Usun dostep aplikacji i sproboj ponownie.",
                success=False,
            ))

        CredentialsService.set(CredentialsService.REFRESH_TOKEN, creds.refresh_token)
        CredentialsService.set(CredentialsService.CLIENT_ID, creds.client_id)
        CredentialsService.set(CredentialsService.CLIENT_SECRET, creds.client_secret)

        dev_token = CredentialsService.get(CredentialsService.DEVELOPER_TOKEN)
        if not dev_token and _allow_env_fallback():
            dev_token = settings.google_ads_developer_token
        if dev_token:
            CredentialsService.set(CredentialsService.DEVELOPER_TOKEN, dev_token)

        SessionService.issue_session()

        logger.info("OAuth success - tokens saved to Credential Manager")
        return HTMLResponse(_html_page(
            "Logowanie udane!",
            "Wroc do aplikacji Google Ads Helper. Mozesz zamknac to okno.",
            success=True,
        ))

    except HTTPException:
        raise
    except Exception:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/logout")
async def logout():
    """Clear all credentials from Credential Manager."""
    CredentialsService.clear_all()
    SessionService.clear_session()
    SessionService.clear_oauth_state()
    logger.info("User logged out - credentials cleared")
    return {"status": "logged_out"}


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
