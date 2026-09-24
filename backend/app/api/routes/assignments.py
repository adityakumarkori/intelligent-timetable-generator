"""Faculty assignment endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.assignment import FacultyAssignmentCreate, FacultyAssignmentResponse
from app.schemas.common import Page, PageParams
from app.services import assignment_service

router = APIRouter(tags=["faculty-assignments"])

manage = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
view = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.FACULTY)


@router.get("", response_model=Page[FacultyAssignmentResponse], summary="List assignments")
async def list_assignments(
    params: PageParams = Depends(),
    faculty_id: UUID | None = None,
    subject_id: UUID | None = None,
    division_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(view),
):
    return await assignment_service.list_assignments(
        db,
        user,
        params,
        faculty_id=faculty_id,
        subject_id=subject_id,
        division_id=division_id,
        academic_session_id=academic_session_id,
        is_active=is_active,
    )


@router.get("/{assignment_id}", response_model=FacultyAssignmentResponse, summary="Get an assignment")
async def get_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(view),
):
    return await assignment_service.get_assignment(db, user, assignment_id)


@router.post(
    "",
    response_model=FacultyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an assignment (entities must exist and be active)",
)
async def create_assignment(
    data: FacultyAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    return await assignment_service.create_assignment(db, data)


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an assignment",
)
async def delete_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(manage),
):
    await assignment_service.delete_assignment(db, assignment_id)
