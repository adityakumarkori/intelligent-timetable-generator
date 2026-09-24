"""Faculty endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import Page, PageParams
from app.schemas.faculty import FacultyCreate, FacultyResponse, FacultyUpdate
from app.schemas.timetable import TimetableEntryResponse
from app.services import faculty_service, timetable_service

router = APIRouter(tags=["faculty"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[FacultyResponse], summary="List faculty")
async def list_faculty(
    params: PageParams = Depends(),
    department_id: UUID | None = Query(default=None, description="Filter by department"),
    q: str | None = Query(default=None, description="Search employee code or name"),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await faculty_service.list_faculty(
        db, params, department_id=department_id, q=q, is_active=is_active
    )


@router.get("/{faculty_id}", response_model=FacultyResponse, summary="Get a faculty member")
async def get_faculty(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await faculty_service.get_faculty(db, faculty_id)


@router.post(
    "",
    response_model=FacultyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a faculty member",
)
async def create_faculty(
    data: FacultyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await faculty_service.create_faculty(db, data)


@router.patch("/{faculty_id}", response_model=FacultyResponse, summary="Update a faculty member")
async def update_faculty(
    faculty_id: UUID,
    data: FacultyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await faculty_service.update_faculty(db, faculty_id, data)


@router.delete(
    "/{faculty_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a faculty member (blocked while in use)",
)
async def delete_faculty(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await faculty_service.delete_faculty(db, faculty_id)


staff = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY)


@router.get(
    "/{faculty_id}/timetable",
    response_model=Page[TimetableEntryResponse],
    summary="Entries taught by a faculty member (faculty: own only, students: never)",
)
async def faculty_timetable(
    faculty_id: UUID,
    params: PageParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(staff),
):
    return await timetable_service.faculty_timetable_entries(db, user, faculty_id, params)
