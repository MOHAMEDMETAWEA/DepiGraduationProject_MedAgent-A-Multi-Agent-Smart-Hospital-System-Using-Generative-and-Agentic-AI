from typing import Annotated

import structlog
from fastapi import Depends, Header
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.security import decode_access_token

# --- AUTH ---


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Extract and validate the current user from the JWT Bearer token.

    Returns a dict with at least {"sub": user_id, "role": role}.
    Raises HTTPException(401) if the token is missing, malformed, or expired.
    """
    from fastapi import HTTPException, status

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None

    # C6: enrich the log context for the rest of this request.
    # `merge_contextvars` will pick these up on every log line.
    user_id = payload.get("sub")
    role = payload.get("role")
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=str(user_id), user_role=role)

    return payload


def require_role(*roles: str):
    """Return a FastAPI dependency that enforces the given role(s)."""

    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        from fastapi import HTTPException, status

        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


_default_limits = [] if settings.DISABLE_RATE_LIMIT else ["60/minute"]

_limiter_kwargs: dict = {
    "key_func": get_remote_address,
    "default_limits": _default_limits,
    # `enabled=False` is required to also disable per-route `@limiter.limit(...)`
    # decorators — clearing `default_limits` alone is not enough.
    "enabled": not settings.DISABLE_RATE_LIMIT,
}

# Redis-backed if REDIS_URL is set
try:
    import redis as _redis  # noqa: F401

    if settings.REDIS_URL:
        _limiter_kwargs["storage_uri"] = settings.REDIS_URL
        _limiter_kwargs["strategy"] = "fixed-window"
except Exception:
    pass

limiter = Limiter(**_limiter_kwargs)
