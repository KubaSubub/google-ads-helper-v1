"""HTTP authorization dependencies for protected routes."""

from fastapi import HTTPException, Request, status

from app.services.session_service import SESSION_COOKIE_NAME, SessionService


def require_session(request: Request) -> bool:
    """Validate session cookie and block access when missing/invalid."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    if not SessionService.is_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )
    return True
