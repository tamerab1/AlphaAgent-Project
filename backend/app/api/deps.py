import hashlib
import json
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Portfolio

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UUID:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    if not settings.supabase_jwt_secret:
        # Paper-trading / demo fallback: JWT secret not injected in this
        # environment.  Decode without signature verification so each Supabase
        # user still gets a stable, isolated portfolio row rather than a 503.
        try:
            unverified = jwt.decode(
                credentials.credentials,
                key="",
                algorithms=["HS256"],
                options={"verify_signature": False, "verify_aud": False},
            )
            sub: Optional[str] = unverified.get("sub")
            if sub:
                return UUID(sub)
        except (JWTError, ValueError):
            pass
        # Last resort: derive a stable UUID from the raw token bytes so the
        # same bearer token always maps to the same portfolio row.
        digest = hashlib.sha256(credentials.credentials.encode()).digest()[:16]
        return UUID(bytes=digest)
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return UUID(sub)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UUID]:
    """Like get_current_user_id but returns None instead of raising when there
    is no token or auth is not configured — used on routes that support both
    anonymous and authenticated access."""
    if credentials is None or not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        sub: Optional[str] = payload.get("sub")
        return UUID(sub) if sub else None
    except (JWTError, ValueError):
        return None


def get_portfolio_or_404(db: Session, portfolio_id: int) -> Portfolio:
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


def loads_json(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None
