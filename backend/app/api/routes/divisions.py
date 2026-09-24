"""Division endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import Page, PageParams
from app.schemas.division import DivisionCreate, DivisionResponse, DivisionUpdate
from app.schemas.timetable import TimetableDetailResponse
from app.services import division_service, timetable_service

router = APIRouter(tags=["divisions"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY, UserRole.STUDENT)


@router.get("", response_model=Page[DivisionResponse], summary="List divisions")
async def list_divisions(
    params: PageParams = Depends(),
    department_id: UUID | None = Query(default=None, description="Filter by department"),
    q: str | None = Query(default=None, description="Search code or name"),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await division_service.list_divisions(
        db, params, department_id=department_id, q=q, is_active=is_active
    )


@router.get("/{division_id}", response_model=DivisionResponse, summary="Get a division")
async def get_division(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await division_service.get_division(db, division_id)


@router.post(
    "",
    response_model=DivisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a division",
)
async def create_division(
    data: DivisionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await division_service.create_division(db, data)


@router.patch("/{division_id}", response_model=DivisionResponse, summary="Update a division")
async def update_division(
    division_id: UUID,
    data: DivisionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await division_service.update_division(db, division_id, data)


@router.delete(
    "/{division_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a division (blocked while in use)",
)
async def delete_division(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await division_service.delete_division(db, division_id)


@router.get(
    "/{division_id}/timetable",
    response_model=TimetableDetailResponse,
    summary="Latest visible timetable for a division (students: published only)",
)
async def division_timetable(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await timetable_service.division_timetable(db, user, division_id)
