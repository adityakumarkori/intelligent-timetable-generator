"""Department endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import Page, PageParams
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.services import department_service

router = APIRouter(tags=["departments"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
read = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY)


@router.get("", response_model=Page[DepartmentResponse], summary="List departments")
async def list_departments(
    params: PageParams = Depends(),
    q: str | None = Query(default=None, description="Search code or name"),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await department_service.list_departments(db, params, q=q, is_active=is_active)


@router.get("/{department_id}", response_model=DepartmentResponse, summary="Get a department")
async def get_department(
    department_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(read),
):
    return await department_service.get_department(db, department_id)


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await department_service.create_department(db, data)


@router.patch("/{department_id}", response_model=DepartmentResponse, summary="Update a department")
async def update_department(
    department_id: UUID,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await department_service.update_department(db, department_id, data)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department (blocked while in use)",
)
async def delete_department(
    department_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await department_service.delete_department(db, department_id)
