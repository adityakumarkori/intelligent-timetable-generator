"""Faculty availability endpoints. Missing rows mean AVAILABLE."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.availability import (
    AvailabilityBulkUpdate,
    AvailabilityResponse,
    AvailabilityStatusUpdate,
)
from app.services import availability_service

router = APIRouter(tags=["availability"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
view = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY)


@router.get(
    "/faculty/{faculty_id}/availability",
    response_model=list[AvailabilityResponse],
    summary="List a faculty member's explicit availability (admins any, faculty own)",
)
async def list_availability(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(view),
):
    return await availability_service.list_availability(db, user, faculty_id)


@router.put(
    "/faculty/{faculty_id}/availability",
    response_model=list[AvailabilityResponse],
    summary="Replace a faculty member's availability (admin only)",
)
async def replace_availability(
    faculty_id: UUID,
    data: AvailabilityBulkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await availability_service.replace_availability(db, user, faculty_id, data)


@router.patch(
    "/faculty/{faculty_id}/availability/{period_id}",
    response_model=AvailabilityResponse,
    summary="Set availability for one period (admin only)",
)
async def set_one_availability(
    faculty_id: UUID,
    period_id: UUID,
    data: AvailabilityStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await availability_service.set_one_availability(
        db, user, faculty_id, period_id, data.status
    )
