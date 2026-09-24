"""Period service.

Break rows are ordinary config here; the Phase 5 generator/validator (not the
DB) is what keeps them out of timetable entries.
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Period
from app.models.enums import DayOfWeek
from app.schemas.common import PageParams
from app.schemas.period import PeriodCreate, PeriodUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, paginate

UNIQUE_MESSAGES = {
    "uq_periods_day_order": "A period with this order already exists on this day",
}


async def list_periods(
    db: AsyncSession,
    params: PageParams,
    *,
    day_of_week: DayOfWeek | None = None,
    is_break: bool | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(Period).order_by(Period.day_of_week, Period.period_order)
    if day_of_week is not None:
        stmt = stmt.where(Period.day_of_week == day_of_week)
    if is_break is not None:
        stmt = stmt.where(Period.is_break == is_break)
    if is_active is not None:
        stmt = stmt.where(Period.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_period(db: AsyncSession, period_id: UUID) -> Period:
    return await get_or_404(db, Period, period_id, "Period")


async def create_period(db: AsyncSession, data: PeriodCreate) -> Period:
    obj = Period(
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        period_order=data.period_order,
        is_break=data.is_break,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_period(db: AsyncSession, period_id: UUID, data: PeriodUpdate) -> Period:
    obj = await get_period(db, period_id)
    patch = data.model_dump(exclude_unset=True)
    start = patch.get("start_time", obj.start_time)
    end = patch.get("end_time", obj.end_time)
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_time must be after start_time",
        )
    for field, value in patch.items():
        setattr(obj, field, value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_period(db: AsyncSession, period_id: UUID) -> None:
    await delete_safe(db, await get_period(db, period_id), "period")
