"""Division subject requirement endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import Page, PageParams
from app.schemas.requirement import (
    DivisionSubjectRequirementCreate,
    DivisionSubjectRequirementResponse,
    DivisionSubjectRequirementUpdate,
)
from app.services import requirement_service

router = APIRouter(tags=["subject-requirements"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[DivisionSubjectRequirementResponse], summary="List requirements")
async def list_requirements(
    params: PageParams = Depends(),
    division_id: UUID | None = None,
    subject_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await requirement_service.list_requirements(
        db,
        params,
        division_id=division_id,
        subject_id=subject_id,
        academic_session_id=academic_session_id,
        is_active=is_active,
    )


@router.get(
    "/{requirement_id}",
    response_model=DivisionSubjectRequirementResponse,
    summary="Get a requirement",
)
async def get_requirement(
    requirement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await requirement_service.get_requirement(db, requirement_id)


@router.post(
    "",
    response_model=DivisionSubjectRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a requirement (room overrides must be compatible)",
)
async def create_requirement(
    data: DivisionSubjectRequirementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await requirement_service.create_requirement(db, data)


@router.patch(
    "/{requirement_id}",
    response_model=DivisionSubjectRequirementResponse,
    summary="Update a requirement",
)
async def update_requirement(
    requirement_id: UUID,
    data: DivisionSubjectRequirementUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await requirement_service.update_requirement(db, requirement_id, data)


@router.delete(
    "/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a requirement",
)
async def delete_requirement(
    requirement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await requirement_service.delete_requirement(db, requirement_id)
