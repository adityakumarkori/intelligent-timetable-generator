"""Period endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import DayOfWeek, UserRole
from app.schemas.common import Page, PageParams
from app.schemas.period import PeriodCreate, PeriodResponse, PeriodUpdate
from app.services import period_service

router = APIRouter(tags=["periods"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[PeriodResponse], summary="List periods")
async def list_periods(
    params: PageParams = Depends(),
    day_of_week: DayOfWeek | None = None,
    is_break: bool | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await period_service.list_periods(
        db, params, day_of_week=day_of_week, is_break=is_break, is_active=is_active
    )


@router.get("/{period_id}", response_model=PeriodResponse, summary="Get a period")
async def get_period(
    period_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await period_service.get_period(db, period_id)


@router.post(
    "",
    response_model=PeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a period",
)
async def create_period(
    data: PeriodCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await period_service.create_period(db, data)


@router.patch("/{period_id}", response_model=PeriodResponse, summary="Update a period")
async def update_period(
    period_id: UUID,
    data: PeriodUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await period_service.update_period(db, period_id, data)


@router.delete(
    "/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a period (blocked while in use)",
)
async def delete_period(
    period_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await period_service.delete_period(db, period_id)
