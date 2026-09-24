"""Subject endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import RoomType, SubjectType, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services import subject_service

router = APIRouter(tags=["subjects"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[SubjectResponse], summary="List subjects")
async def list_subjects(
    params: PageParams = Depends(),
    q: str | None = Query(default=None, description="Search code or name"),
    subject_type: SubjectType | None = None,
    required_room_type: RoomType | None = None,
    requires_lab: bool | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await subject_service.list_subjects(
        db,
        params,
        q=q,
        subject_type=subject_type,
        required_room_type=required_room_type,
        requires_lab=requires_lab,
        is_active=is_active,
    )


@router.get("/{subject_id}", response_model=SubjectResponse, summary="Get a subject")
async def get_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await subject_service.get_subject(db, subject_id)


@router.post(
    "",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subject",
)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await subject_service.create_subject(db, data)


@router.patch("/{subject_id}", response_model=SubjectResponse, summary="Update a subject")
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await subject_service.update_subject(db, subject_id, data)


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subject (blocked while in use)",
)
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await subject_service.delete_subject(db, subject_id)
