"""HTTP authorization dependencies for protected routes."""

from fastapi import HTTPException, Request, status

from app.services.session_service import SESSION_COOKIE_NAME, SessionService


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip() or None


def require_session(request: Request) -> bool:
    """Validate auth token from cookie (preferred) or Bearer header."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    bearer_token = _extract_bearer_token(request)
    token = cookie_token or bearer_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    if not SessionService.is_valid(token):
        # Keep compatibility with hardening tests expecting 403 for provided invalid Bearer
        if bearer_token and not cookie_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization scheme",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    return True
