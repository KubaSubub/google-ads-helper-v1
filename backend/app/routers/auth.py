"""
OAuth2 flow for Google Ads API.

Endpoints:
  GET  /auth/status        - check session + credentials status
  GET  /auth/setup-status  - check if API credentials are configured
  POST /auth/setup         - save API credentials in Windows Credential Manager
  GET  /auth/login         - generate OAuth consent URL
  GET  /auth/callback      - Google redirects here with code
  POST /auth/logout        - clear session and credentials
"""

import os

# Allow HTTP redirect for localhost (desktop app)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.credentials_service import CredentialsService
from app.services.google_ads import google_ads_service
from app.services.session_service import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_MINUTES,
    SessionService,
)


class SetupRequest(BaseModel):
    developer_token: str
    client_id: str
    client_secret: str
    login_customer_id: str = ""


router = APIRouter(prefix="/auth", tags=["Authentication"])

SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = "http://localhost:8000/api/v1/auth/callback"
REQUIRED_SETUP_KEYS = [
    CredentialsService.DEVELOPER_TOKEN,
    CredentialsService.CLIENT_ID,
    CredentialsService.CLIENT_SECRET,
]
REQUIRED_RUNTIME_KEYS = REQUIRED_SETUP_KEYS + [CredentialsService.REFRESH_TOKEN]


def _missing_credentials(required_keys: list[str]) -> list[str]:
    missing = []
    for key in required_keys:
        value = CredentialsService.get(key)
        if not value:
            missing.append(key)
    return missing


def _build_flow() -> Flow:
    """Create OAuth2 Flow from secure storage values only."""
    missing = _missing_credentials(REQUIRED_SETUP_KEYS)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Missing setup credentials: {', '.join(missing)}",
        )

    client_config = {
        "web": {
            "client_id": CredentialsService.get(CredentialsService.CLIENT_ID),
            "client_secret": CredentialsService.get(CredentialsService.CLIENT_SECRET),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )


@router.get("/status")
async def auth_status(request: Request, response: Response, bootstrap: int = 0):
    """Return session and configuration state for frontend gate."""
    missing = _missing_credentials(REQUIRED_RUNTIME_KEYS)
    configured = len(missing) == 0

    token = request.cookies.get(SESSION_COOKIE_NAME)
    authenticated = configured and SessionService.is_valid(token)
    if configured and not authenticated and bootstrap == 1:
        token = SessionService.issue()
        _set_session_cookie(response, token)
        authenticated = True

    return {
        "authenticated": authenticated,
        "configured": configured,
        "missing": missing,
    }


@router.get("/setup-status")
async def setup_status():
    """Check if API setup credentials are configured."""
    missing = _missing_credentials(REQUIRED_SETUP_KEYS)
    return {
        "configured": len(missing) == 0,
        "missing": missing,
        "has_developer_token": CredentialsService.get(CredentialsService.DEVELOPER_TOKEN) is not None,
        "has_client_id": CredentialsService.get(CredentialsService.CLIENT_ID) is not None,
        "has_client_secret": CredentialsService.get(CredentialsService.CLIENT_SECRET) is not None,
        "has_login_customer_id": CredentialsService.get("login_customer_id") is not None,
    }


@router.post("/setup")
async def setup(data: SetupRequest):
    """Save API credentials to Windows Credential Manager."""
    if not data.developer_token or not data.client_id or not data.client_secret:
        raise HTTPException(status_code=400, detail="Wszystkie pola sa wymagane.")

    ok = all([
        CredentialsService.set(CredentialsService.DEVELOPER_TOKEN, data.developer_token.strip()),
        CredentialsService.set(CredentialsService.CLIENT_ID, data.client_id.strip()),
        CredentialsService.set(CredentialsService.CLIENT_SECRET, data.client_secret.strip()),
    ])
    if not ok:
        raise HTTPException(status_code=500, detail="Nie udalo sie zapisac credentials.")

    if data.login_customer_id.strip():
        CredentialsService.set("login_customer_id", data.login_customer_id.strip())

    missing = _missing_credentials(REQUIRED_SETUP_KEYS)
    logger.info("API credentials saved to Windows Credential Manager via /auth/setup")
    return {
        "success": len(missing) == 0,
        "configured": len(missing) == 0,
        "missing": missing,
        "message": "Credentials zapisane. Mozesz przejsc do logowania OAuth.",
    }


@router.get("/login")
async def login():
    """Generate Google OAuth consent URL for user to open in browser."""
    missing = _missing_credentials(REQUIRED_SETUP_KEYS)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brak konfiguracji API: {', '.join(missing)}",
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
            "Odmowiono dostepu. Mozesz zamknac to okno i sprobowac ponownie.",
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
                "Google nie zwrocil refresh token. Usun dostep aplikacji i sproboj ponownie.",
                success=False,
            ))

        saved = all([
            CredentialsService.set(CredentialsService.REFRESH_TOKEN, creds.refresh_token),
            CredentialsService.set(CredentialsService.CLIENT_ID, creds.client_id),
            CredentialsService.set(CredentialsService.CLIENT_SECRET, creds.client_secret),
        ])
        if not saved:
            raise HTTPException(status_code=500, detail="Nie udalo sie zapisac tokenow OAuth.")

        google_ads_service.reinitialize()

        session_token = SessionService.issue()
        response = HTMLResponse(_html_page(
            "Logowanie udane!",
            "Wroc do aplikacji Google Ads Helper. Mozesz zamknac to okno.",
            success=True,
        ))
        _set_session_cookie(response, session_token)

        logger.info("OAuth success - credentials saved and session cookie issued")
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"OAuth callback failed: {exc}")
        raise HTTPException(status_code=500, detail="Blad autentykacji OAuth")


@router.post("/logout")
async def logout(request: Request):
    """Clear API session and all credentials from secure storage."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    SessionService.revoke(token)
    SessionService.clear_all()
    CredentialsService.clear_all()

    response = Response(content='{"status":"logged_out"}', media_type="application/json")
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")

    logger.info("User logged out - session and credentials cleared")
    return response


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
