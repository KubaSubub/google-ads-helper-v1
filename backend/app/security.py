"""HTTP authorization dependencies for protected routes."""

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.session_service import SessionService


bearer_scheme = HTTPBearer(auto_error=False)


def require_session(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    if not SessionService.is_valid(credentials.credentials):
        raise HTTPException(status_code=403, detail="Invalid or expired session token")

    return {"authenticated": True}
