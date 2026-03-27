"""
FastAPI dependency functions for authentication
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from config.settings import settings

security = HTTPBearer()


def _decode_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_current_organizer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Require a valid organizer JWT. Returns the decoded payload."""
    payload = _decode_token(credentials)
    if payload.get("role") != "organizer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer access required",
        )
    return payload


def get_current_participant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Require a valid participant JWT. Returns the decoded payload."""
    payload = _decode_token(credentials)
    if payload.get("role") != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant access required",
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Require any valid JWT (organizer or participant). Returns the decoded payload."""
    return _decode_token(credentials)
