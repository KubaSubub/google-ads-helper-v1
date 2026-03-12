"""OAuth2 flow and session lifecycle for Google Ads API."""

import os

# Allow HTTP redirect for localhost (desktop app)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.credentials_service import CredentialPersistenceError, CredentialsService
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


def _build_flow() -> Flow:
    """Create OAuth2 Flow using credentials from Windows Credential Manager."""
    client_id = CredentialsService.get(CredentialsService.CLIENT_ID)
    client_secret = CredentialsService.get(CredentialsService.CLIENT_SECRET)

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brak zapisanych OAuth credentials. Uzupelnij konfiguracje API przed logowaniem.",
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


def _setup_status_payload() -> dict:
    credentials = CredentialsService.get_google_ads_credentials()
    missing_setup = [
        key for key in CredentialsService.SETUP_KEYS if not credentials.get(key)
    ]
    return {
        "configured": not missing_setup,
        "has_developer_token": bool(credentials["developer_token"]),
        "has_client_id": bool(credentials["client_id"]),
        "has_client_secret": bool(credentials["client_secret"]),
        "has_login_customer_id": bool(credentials["login_customer_id"]),
        "missing": missing_setup,
        "missing_credentials": missing_setup,
    }


def _setup_values_payload() -> dict:
    credentials = CredentialsService.get_google_ads_credentials()
    return {
        "developer_token": credentials["developer_token"] or "",
        "client_id": credentials["client_id"] or "",
        "client_secret": credentials["client_secret"] or "",
        "login_customer_id": credentials["login_customer_id"] or "",
    }


@router.get("/status")
async def auth_status(request: Request, response: Response, bootstrap: int = 0):
    """Return OAuth readiness and local session state for frontend gating."""
    diagnostics = google_ads_service.get_connection_diagnostics()
    oauth_authenticated = bool(CredentialsService.get(CredentialsService.REFRESH_TOKEN))

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    session_authenticated = SessionService.is_valid(session_token)

    if bootstrap == 1 and not session_authenticated and diagnostics.get("configured") and oauth_authenticated:
        session_token = SessionService.issue()
        _set_session_cookie(response, session_token)
        session_authenticated = True

    reason = diagnostics.get("reason", "")
    if diagnostics.get("configured") and oauth_authenticated and not session_authenticated:
        reason = "Sesja wygasla. Zaloguj sie ponownie przez Google."

    missing = diagnostics.get("missing_credentials", [])
    return {
        "authenticated": session_authenticated,
        "session_authenticated": session_authenticated,
        "oauth_authenticated": oauth_authenticated,
        "configured": diagnostics.get("configured", False),
        "ready": bool(session_authenticated and diagnostics.get("ready", False)),
        "connected": diagnostics.get("connected", False),
        "reason": reason,
        "missing": missing,
        "missing_credentials": missing,
        "has_login_customer_id": diagnostics.get("has_login_customer_id", False),
    }


@router.get("/setup-status")
async def setup_status():
    """Check if API credentials are configured in the secure store."""
    return _setup_status_payload()


@router.get("/setup-values")
async def setup_values():
    """Return stored setup values from the secure store, excluding OAuth tokens."""
    return _setup_values_payload()


@router.post("/setup")
async def setup(data: SetupRequest):
    """Save API credentials to Windows Credential Manager."""
    if not data.developer_token or not data.client_id or not data.client_secret:
        raise HTTPException(status_code=400, detail="Wszystkie pola sa wymagane.")

    try:
        CredentialsService.save_and_verify(
            {
                CredentialsService.DEVELOPER_TOKEN: data.developer_token,
                CredentialsService.CLIENT_ID: data.client_id,
                CredentialsService.CLIENT_SECRET: data.client_secret,
                CredentialsService.LOGIN_CUSTOMER_ID: data.login_customer_id,
            },
            clear_keys=(CredentialsService.LOGIN_CUSTOMER_ID,) if not data.login_customer_id.strip() else (),
        )
        google_ads_service.reinitialize()
    except CredentialPersistenceError as exc:
        logger.error(f"Credential setup failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    setup_payload = _setup_status_payload()
    logger.info("API credentials saved to Windows Credential Manager via /auth/setup")
    return {
        "success": setup_payload["configured"],
        "configured": setup_payload["configured"],
        "missing": setup_payload["missing"],
        "missing_credentials": setup_payload["missing_credentials"],
        "message": "Credentials zapisane. Mozesz teraz przejsc do logowania Google.",
    }


@router.get("/login")
async def login():
    """Generate Google OAuth consent URL for the user to open in browser."""
    setup_status_data = _setup_status_payload()
    if not setup_status_data["configured"]:
        missing = ", ".join(setup_status_data["missing_credentials"])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brak zapisanych credentials Google Ads: {missing}.",
        )

    flow = _build_flow()
    oauth_state = SessionService.issue_oauth_state()
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=oauth_state,
    )
    logger.info("OAuth login URL generated")
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str = None, error: str = None, state: str = None):
    """Google redirects here after user grants or denies consent."""
    if error:
        logger.warning(f"OAuth denied: {error}")
        return HTMLResponse(
            _html_page(
                "Logowanie anulowane",
                "Odmowiono dostepu. Mozesz zamknac to okno i sprobowac ponownie.",
                success=False,
            )
        )

    if not state or not SessionService.verify_oauth_state(state):
        logger.warning("OAuth callback rejected because of invalid state")
        return HTMLResponse(
            _html_page(
                "Nieprawidlowy stan logowania",
                "Sesja logowania wygasla lub jest nieprawidlowa. Sprobuj ponownie z aplikacji.",
                success=False,
            )
        )

    if not code:
        raise HTTPException(status_code=400, detail="Brak parametru 'code'")

    try:
        flow = _build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        if not creds.refresh_token:
            logger.error("No refresh_token returned by Google")
            return HTMLResponse(
                _html_page(
                    "Brak refresh token",
                    "Google nie zwrocil refresh token. Usun dostep aplikacji w Google Account i sproboj ponownie.",
                    success=False,
                )
            )

        developer_token = CredentialsService.get(CredentialsService.DEVELOPER_TOKEN)
        if not developer_token:
            logger.error("OAuth callback missing developer_token in secure store")
            return HTMLResponse(
                _html_page(
                    "Brak developer token",
                    "Developer token nie jest zapisany. Wroc do konfiguracji API i zapisz credentials ponownie.",
                    success=False,
                )
            )

        CredentialsService.save_and_verify(
            {
                CredentialsService.REFRESH_TOKEN: creds.refresh_token,
                CredentialsService.CLIENT_ID: creds.client_id,
                CredentialsService.CLIENT_SECRET: creds.client_secret,
                CredentialsService.DEVELOPER_TOKEN: developer_token,
                CredentialsService.LOGIN_CUSTOMER_ID: CredentialsService.get(
                    CredentialsService.LOGIN_CUSTOMER_ID
                ),
            }
        )

        google_ads_service.reinitialize()
        diagnostics = google_ads_service.get_connection_diagnostics()
        session_token = SessionService.issue()

        if diagnostics["ready"]:
            logger.info("OAuth success - tokens saved and Google Ads API is ready")
            html = _html_page(
                "Logowanie udane!",
                "Wroc do aplikacji Google Ads Helper. Mozesz zamknac to okno.",
                success=True,
            )
        else:
            logger.error(f"OAuth callback completed but API is not ready: {diagnostics['reason']}")
            html = _html_page(
                "Logowanie zakonczone, ale API nie jest gotowe",
                diagnostics["reason"],
                success=False,
            )

        response = HTMLResponse(html)
        _set_session_cookie(response, session_token)
        return response

    except CredentialPersistenceError as exc:
        logger.error(f"OAuth credential persistence failed: {exc}")
        return HTMLResponse(
            _html_page(
                "Nie udalo sie zapisac credentials",
                str(exc),
                success=False,
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"OAuth callback failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Blad autentykacji: {exc}") from exc


@router.post("/logout")
async def logout(request: Request):
    """Clear session cookie and all stored credentials."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    SessionService.revoke(session_token)
    SessionService.clear_oauth_state()
    CredentialsService.clear_all()
    google_ads_service.reinitialize()
    logger.info("User logged out - credentials and session cleared")

    response = Response(content='{"status":"logged_out"}', media_type="application/json")
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
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
