"""Faculty availability service.

Domain rule: a missing row means AVAILABLE, so reads return only explicit
rows and writes only touch exceptions. Only ADMIN/SUPER_ADMIN may modify;
FACULTY sees their own rows; STUDENT sees none.
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Faculty, FacultyAvailability, Period, User
from app.models.enums import AvailabilityStatus, UserRole
from app.schemas.availability import AvailabilityBulkUpdate
from app.services.common import commit_or_409, get_or_404, not_found

UNIQUE_MESSAGES = {
    "uq_availability_faculty_period": "Availability for this period is already set",
}

_FORBIDDEN = "Insufficient permissions"


async def _scope_faculty(db: AsyncSession, actor: User, faculty_id: UUID) -> Faculty:
    """Return the Faculty row the actor may manage/view, else 403/404."""
    if actor.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        return await get_or_404(db, Faculty, faculty_id, "Faculty")
    if actor.role == UserRole.FACULTY:
        profile = await db.scalar(select(Faculty).where(Faculty.user_id == actor.id))
        if profile is None or profile.id != faculty_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
        return profile
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)


async def list_availability(db: AsyncSession, actor: User, faculty_id: UUID) -> list:
    await _scope_faculty(db, actor, faculty_id)
    rows = (
        await db.scalars(
            select(FacultyAvailability)
            .options(joinedload(FacultyAvailability.period))
            .where(FacultyAvailability.faculty_id == faculty_id)
            .order_by(Period.day_of_week, Period.period_order)
            .join(Period, FacultyAvailability.period_id == Period.id)
        )
    ).all()
    return list(rows)


async def replace_availability(
    db: AsyncSession, actor: User, faculty_id: UUID, data: AvailabilityBulkUpdate
) -> list:
    if actor.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    await get_or_404(db, Faculty, faculty_id, "Faculty")

    wanted = {item.period_id for item in data.items}
    if wanted:
        found = set(
            (
                await db.scalars(select(Period.id).where(Period.id.in_(wanted)))
            ).all()
        )
        missing = wanted - found
        if missing:
            raise not_found("Period", sorted(str(m) for m in missing)[:3])
    if len(wanted) != len(data.items):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Duplicate periods in request",
        )

    await db.execute(delete(FacultyAvailability).where(FacultyAvailability.faculty_id == faculty_id))
    for item in data.items:
        db.add(
            FacultyAvailability(
                faculty_id=faculty_id, period_id=item.period_id, status=item.status
            )
        )
    await commit_or_409(db, UNIQUE_MESSAGES)
    return await list_availability(db, actor, faculty_id)


async def set_one_availability(
    db: AsyncSession,
    actor: User,
    faculty_id: UUID,
    period_id: UUID,
    status_value: AvailabilityStatus,
):
    if actor.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    await get_or_404(db, Faculty, faculty_id, "Faculty")
    await get_or_404(db, Period, period_id, "Period")

    row = await db.scalar(
        select(FacultyAvailability).where(
            FacultyAvailability.faculty_id == faculty_id,
            FacultyAvailability.period_id == period_id,
        )
    )
    if row is None:
        row = FacultyAvailability(
            faculty_id=faculty_id, period_id=period_id, status=status_value
        )
        db.add(row)
    else:
        row.status = status_value
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(row)
    row = await db.scalar(
        select(FacultyAvailability)
        .options(joinedload(FacultyAvailability.period))
        .where(FacultyAvailability.id == row.id)
    )
    return row
