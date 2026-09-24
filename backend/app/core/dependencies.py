"""Authentication/authorization dependencies for protected routes.

- get_current_user: valid Bearer token + existing user, else 401.
- get_current_active_user: additionally rejects deactivated accounts, 403.
- require_roles(...): role gate factory, 403 on mismatch.
- can_manage_role: account-management rule for future user-admin endpoints.
"""

from uuid import UUID

import jwt
from fastapi import Depends, status
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)

_NOT_AUTHENTICATED = "Not authenticated"
_INVALID_TOKEN = "Invalid token"
_TOKEN_EXPIRED = "Token expired"
_INACTIVE_USER = "Inactive user account"
_FORBIDDEN = "Insufficient permissions"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_NOT_AUTHENTICATED)
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_TOKEN_EXPIRED) from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN) from None

    try:
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN) from None

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_INACTIVE_USER)
    return user


def require_roles(*allowed: UserRole):
    """Dependency factory: only users with one of `allowed` roles pass."""

    async def checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
        return user

    return checker


def can_manage_role(actor: UserRole, target: UserRole) -> bool:
    """Who may manage whose account (enforced by future user-admin endpoints).

    - SUPER_ADMIN manages everyone, including other SUPER_ADMINs.
    - ADMIN manages everyone except SUPER_ADMINs.
    - FACULTY/STUDENT manage no accounts.
    """
    if actor == UserRole.SUPER_ADMIN:
        return True
    if actor == UserRole.ADMIN:
        return target != UserRole.SUPER_ADMIN
    return False


async def get_current_faculty_profile(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve the Faculty row linked to the caller's login.

    403 unless the caller is a FACULTY user with a linked faculty profile.
    Used for every "own" scoping rule (availability, assignments, timetables).
    """
    from sqlalchemy import select

    from app.models import Faculty

    if user.role != UserRole.FACULTY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    profile = await db.scalar(select(Faculty).where(Faculty.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    return profile
