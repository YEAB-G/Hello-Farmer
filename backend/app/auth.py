"""Authentication and access control dependencies for Hello Farmer."""
import os
import secrets
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings

# HTTP Bearer scheme for token authorization
security_bearer = HTTPBearer(auto_error=False)

DEFAULT_DEV_KEY = "dev_admin_key_hello_farmer_2026"


def get_expected_admin_key() -> str:
    """Retrieve the configured admin API key from settings or environment."""
    key = getattr(settings, "ADMIN_API_KEY", None) or os.getenv("ADMIN_API_KEY")
    if not key:
        return DEFAULT_DEV_KEY
    return key


async def require_admin_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> str:
    """Enforce authentication on protected admin and data-access endpoints.
    
    Accepts:
    - Authorization: Bearer <token>
    - X-Admin-Key: <token>
    """
    expected_key = get_expected_admin_key()
    
    # Check Bearer token
    provided_key = None
    if credentials and credentials.credentials:
        provided_key = credentials.credentials
    elif x_admin_key:
        provided_key = x_admin_key
        
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide 'Authorization: Bearer <token>' or 'X-Admin-Key' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return provided_key
