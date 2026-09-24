"""Timetable retrieval endpoints (Phase 4: no generation yet)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import TimetableStatus, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.timetable import TimetableDetailResponse, TimetableEntryResponse, TimetableResponse
from app.services import timetable_service

router = APIRouter(tags=["timetables"])

read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[TimetableResponse], summary="List timetables (visibility-scoped)")
async def list_timetables(
    params: PageParams = Depends(),
    division_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    status: TimetableStatus | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await timetable_service.list_timetables(
        db,
        user,
        params,
        division_id=division_id,
        academic_session_id=academic_session_id,
        status_value=status,
    )


@router.get("/{timetable_id}", response_model=TimetableDetailResponse, summary="Get a timetable with entries")
async def get_timetable(
    timetable_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await timetable_service.get_timetable_detail(db, user, timetable_id)


@router.get(
    "/{timetable_id}/entries",
    response_model=Page[TimetableEntryResponse],
    summary="List a timetable's entries in weekly order",
)
async def list_entries(
    timetable_id: UUID,
    params: PageParams = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await timetable_service.list_timetable_entries(db, user, timetable_id, params)
