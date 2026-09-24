"""Manual timetable-entry endpoints (Phase 6).

 ADMIN/SUPER_ADMIN only. Every write is validated — including cross-timetable
 clashes with PUBLISHED timetables of the same session — and rolled back on
 any violation. PUBLISHED/ARCHIVED timetables are immutable (clone to edit).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.entry import EntryCreate, EntryUpdate, TimetableEntryDetailResponse
from app.services import timetable_write_service

router = APIRouter(tags=["timetable-entries"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.post(
    "/{timetable_id}/entries",
    response_model=TimetableEntryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an entry (validated, incl. cross-timetable clashes)",
)
async def create_entry(
    timetable_id: UUID,
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
    if_unmodified_since: str | None = Header(default=None),
):
    return await timetable_write_service.create_entry(
        db, timetable_id, data, if_unmodified_since
    )


@router.patch(
    "/{timetable_id}/entries/{entry_id}",
    response_model=TimetableEntryDetailResponse,
    summary="Move/edit an entry (whole timetable revalidated)",
)
async def update_entry(
    timetable_id: UUID,
    entry_id: UUID,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
    if_unmodified_since: str | None = Header(default=None),
):
    return await timetable_write_service.update_entry(
        db, timetable_id, entry_id, data, if_unmodified_since
    )


@router.delete(
    "/{timetable_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entry (timetable reclassified if incomplete)",
)
async def delete_entry(
    timetable_id: UUID,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await timetable_write_service.delete_entry(db, timetable_id, entry_id)
