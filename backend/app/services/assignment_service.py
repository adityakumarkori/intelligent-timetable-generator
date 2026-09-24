"""Faculty assignment service (faculty x subject x division x session).

Only valid, active-entity assignments can exist — the Phase 5 generator will
rely on this table as its allow-list.
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import AcademicSession, Division, Faculty, FacultyAssignment, Subject, User
from app.models.enums import UserRole
from app.schemas.assignment import FacultyAssignmentCreate
from app.schemas.common import PageParams
from app.services.common import (
    commit_or_409,
    delete_safe,
    ensure_active,
    get_or_404,
    not_found,
    paginate,
)

UNIQUE_MESSAGES = {
    "uq_assignments_faculty_subject_division_session": "This faculty assignment already exists",
}

_FORBIDDEN = "Insufficient permissions"


async def _require_active(db: AsyncSession, model, obj_id: UUID, label: str):
    obj = await db.get(model, obj_id)
    if obj is None:
        raise not_found(label, obj_id)
    ensure_active(obj, label, obj_id)
    return obj


async def _own_faculty_id(db: AsyncSession, actor: User) -> UUID | None:
    if actor.role != UserRole.FACULTY:
        return None
    profile = await db.scalar(select(Faculty).where(Faculty.user_id == actor.id))
    return profile.id if profile else None


def _to_dict(a: FacultyAssignment) -> dict:
    return {
        "id": a.id,
        "faculty_id": a.faculty_id,
        "subject_id": a.subject_id,
        "division_id": a.division_id,
        "academic_session_id": a.academic_session_id,
        "is_active": a.is_active,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "faculty_name": a.faculty.name,
        "subject_code": a.subject.code,
        "division_code": a.division.code,
    }


def _options():
    return (
        joinedload(FacultyAssignment.faculty),
        joinedload(FacultyAssignment.subject),
        joinedload(FacultyAssignment.division),
    )


async def list_assignments(
    db: AsyncSession,
    actor: User,
    params: PageParams,
    *,
    faculty_id: UUID | None = None,
    subject_id: UUID | None = None,
    division_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    is_active: bool | None = None,
) -> dict:
    if actor.role == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    if actor.role == UserRole.FACULTY:
        own = await _own_faculty_id(db, actor)
        if own is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
        faculty_id = own  # faculty sees only their own assignments

    stmt = select(FacultyAssignment).options(*_options()).order_by(FacultyAssignment.created_at)
    if faculty_id is not None:
        stmt = stmt.where(FacultyAssignment.faculty_id == faculty_id)
    if subject_id is not None:
        stmt = stmt.where(FacultyAssignment.subject_id == subject_id)
    if division_id is not None:
        stmt = stmt.where(FacultyAssignment.division_id == division_id)
    if academic_session_id is not None:
        stmt = stmt.where(FacultyAssignment.academic_session_id == academic_session_id)
    if is_active is not None:
        stmt = stmt.where(FacultyAssignment.is_active == is_active)
    page = await paginate(db, stmt, params)
    page["items"] = [_to_dict(a) for a in page["items"]]
    return page


async def get_assignment(db: AsyncSession, actor: User, assignment_id: UUID) -> dict:
    stmt = (
        select(FacultyAssignment)
        .options(*_options())
        .where(FacultyAssignment.id == assignment_id)
    )
    obj = await db.scalar(stmt)
    if obj is None:
        raise not_found("Faculty assignment", assignment_id)
    if actor.role == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    if actor.role == UserRole.FACULTY:
        own = await _own_faculty_id(db, actor)
        if own is None or obj.faculty_id != own:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    return _to_dict(obj)


async def create_assignment(db: AsyncSession, data: FacultyAssignmentCreate) -> dict:
    await _require_active(db, Faculty, data.faculty_id, "Faculty")
    await _require_active(db, Subject, data.subject_id, "Subject")
    await _require_active(db, Division, data.division_id, "Division")
    await _require_active(db, AcademicSession, data.academic_session_id, "Academic session")

    duplicate = await db.scalar(
        select(FacultyAssignment).where(
            FacultyAssignment.faculty_id == data.faculty_id,
            FacultyAssignment.subject_id == data.subject_id,
            FacultyAssignment.division_id == data.division_id,
            FacultyAssignment.academic_session_id == data.academic_session_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This faculty assignment already exists",
        )
    obj = FacultyAssignment(
        faculty_id=data.faculty_id,
        subject_id=data.subject_id,
        division_id=data.division_id,
        academic_session_id=data.academic_session_id,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    return await get_assignment_admin(db, obj.id)


async def get_assignment_admin(db: AsyncSession, assignment_id: UUID) -> dict:
    stmt = (
        select(FacultyAssignment)
        .options(*_options())
        .where(FacultyAssignment.id == assignment_id)
    )
    obj = await db.scalar(stmt)
    if obj is None:
        raise not_found("Faculty assignment", assignment_id)
    return _to_dict(obj)


async def delete_assignment(db: AsyncSession, assignment_id: UUID) -> None:
    await delete_safe(
        db, await get_or_404(db, FacultyAssignment, assignment_id, "Faculty assignment"), "faculty assignment"
    )
