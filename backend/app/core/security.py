import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (cost=12)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: str, role: str, extra_claims: dict | None = None) -> str:
    """Create a signed JWT access token.
    Expiry is configurable via ACCESS_TOKEN_EXPIRE_MINUTES (default 15 min)."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises JWTError if invalid."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_refresh_token() -> str:
    """Generate a cryptographically secure random token (256-bit)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token with SHA-256 for safe database storage."""
    return hashlib.sha256(token.encode()).hexdigest()
