"""Academic session endpoints (ADMIN/SUPER_ADMIN only)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.academic_session import (
    AcademicSessionCreate,
    AcademicSessionResponse,
    AcademicSessionUpdate,
)
from app.schemas.common import Page, PageParams
from app.services import academic_session_service

router = APIRouter(tags=["academic-sessions"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.get("", response_model=Page[AcademicSessionResponse], summary="List academic sessions")
async def list_sessions(
    params: PageParams = Depends(),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await academic_session_service.list_sessions(db, params, is_active=is_active)


@router.get("/{session_id}", response_model=AcademicSessionResponse, summary="Get a session")
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await academic_session_service.get_session(db, session_id)


@router.post(
    "",
    response_model=AcademicSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a session (activating it deactivates the rest)",
)
async def create_session(
    data: AcademicSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await academic_session_service.create_session(db, data)


@router.patch("/{session_id}", response_model=AcademicSessionResponse, summary="Update a session")
async def update_session(
    session_id: UUID,
    data: AcademicSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await academic_session_service.update_session(db, session_id, data)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session (blocked while in use)",
)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await academic_session_service.delete_session(db, session_id)
