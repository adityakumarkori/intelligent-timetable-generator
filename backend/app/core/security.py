"""Password hashing (Argon2id) and JWT handling.

Pure functions only — no HTTP, no database access. Route handlers must use
the service layer (`app.services.auth_service`) and dependencies
(`app.core.dependencies`), never this module's internals directly.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

from app.core.config import settings

# Argon2id is argon2-cffi's default (OWASP-recommended memory-hard KDF).
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password. Each call uses a fresh random salt."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time verification. Never raises on mismatch — returns False."""
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False


def _require_secret() -> str:
    if not settings.JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured. Set it in backend/.env "
            "(see backend/.env.example)."
        )
    return settings.JWT_SECRET_KEY


def create_access_token(
    *, subject: UUID | str, role: str, expires_minutes: int | None = None
) -> str:
    """Mint a signed access token carrying the user id (sub) and role."""
    now = datetime.now(timezone.utc)
    lifetime = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=lifetime),
    }
    return jwt.encode(payload, _require_secret(), algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify signature + expiry. Raises jwt.ExpiredSignatureError /
    jwt.InvalidTokenError — mapped to 401 by the auth dependencies."""
    return jwt.decode(token, _require_secret(), algorithms=[settings.JWT_ALGORITHM])
