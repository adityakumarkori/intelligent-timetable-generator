"""Department service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department
from app.schemas.common import PageParams
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, paginate

UNIQUE_MESSAGES = {
    "departments_code_key": "Department code already exists",
    "ix_departments_code": "Department code already exists",
}


async def list_departments(
    db: AsyncSession, params: PageParams, *, q: str | None = None, is_active: bool | None = None
) -> dict:
    stmt = select(Department).order_by(Department.code)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Department.code.ilike(like)) | (Department.name.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_department(db: AsyncSession, department_id: UUID) -> Department:
    return await get_or_404(db, Department, department_id, "Department")


async def create_department(db: AsyncSession, data: DepartmentCreate) -> Department:
    obj = Department(name=data.name.strip(), code=data.code.strip(), is_active=data.is_active)
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_department(
    db: AsyncSession, department_id: UUID, data: DepartmentUpdate
) -> Department:
    obj = await get_department(db, department_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value.strip() if isinstance(value, str) else value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_department(db: AsyncSession, department_id: UUID) -> None:
    await delete_safe(db, await get_department(db, department_id), "department")
