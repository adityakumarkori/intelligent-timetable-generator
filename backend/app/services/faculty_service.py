"""Faculty service — responses never carry user credentials or hashes."""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Faculty, User
from app.schemas.common import PageParams
from app.schemas.faculty import FacultyCreate, FacultyUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, not_found, paginate

UNIQUE_MESSAGES = {
    "faculty_employee_code_key": "Employee code already exists",
    "ix_faculty_employee_code": "Employee code already exists",
    "faculty_user_id_key": "User is already linked to another faculty profile",
}


async def _require_department(db: AsyncSession, department_id: UUID) -> None:
    if await db.get(Department, department_id) is None:
        raise not_found("Department", department_id)


async def _require_linkable_user(db: AsyncSession, user_id: UUID, current_faculty_id: UUID | None = None) -> None:
    if await db.get(User, user_id) is None:
        raise not_found("User", user_id)
    existing = await db.scalar(select(Faculty).where(Faculty.user_id == user_id))
    if existing is not None and existing.id != current_faculty_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already linked to another faculty profile",
        )


async def list_faculty(
    db: AsyncSession,
    params: PageParams,
    *,
    department_id: UUID | None = None,
    q: str | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(Faculty).order_by(Faculty.employee_code)
    if department_id is not None:
        stmt = stmt.where(Faculty.department_id == department_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Faculty.employee_code.ilike(like)) | (Faculty.name.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(Faculty.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_faculty(db: AsyncSession, faculty_id: UUID) -> Faculty:
    return await get_or_404(db, Faculty, faculty_id, "Faculty")


async def create_faculty(db: AsyncSession, data: FacultyCreate) -> Faculty:
    await _require_department(db, data.department_id)
    if data.user_id is not None:
        await _require_linkable_user(db, data.user_id)
    obj = Faculty(
        user_id=data.user_id,
        employee_code=data.employee_code.strip(),
        department_id=data.department_id,
        name=data.name.strip(),
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_faculty(db: AsyncSession, faculty_id: UUID, data: FacultyUpdate) -> Faculty:
    obj = await get_faculty(db, faculty_id)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("department_id") is not None:
        await _require_department(db, patch["department_id"])
    if "user_id" in patch and patch["user_id"] is not None:
        await _require_linkable_user(db, patch["user_id"], faculty_id)
    for field in ("employee_code", "name"):
        if isinstance(patch.get(field), str):
            patch[field] = patch[field].strip()
    for field, value in patch.items():
        setattr(obj, field, value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_faculty(db: AsyncSession, faculty_id: UUID) -> None:
    await delete_safe(db, await get_faculty(db, faculty_id), "faculty member")
