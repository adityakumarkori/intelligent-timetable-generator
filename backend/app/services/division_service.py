"""Division service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Division
from app.schemas.common import PageParams
from app.schemas.division import DivisionCreate, DivisionUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, not_found, paginate

UNIQUE_MESSAGES = {
    "uq_divisions_department_code": "Division code already exists in this department",
}


async def _require_department(db: AsyncSession, department_id: UUID) -> Department:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise not_found("Department", department_id)
    return dept


async def list_divisions(
    db: AsyncSession,
    params: PageParams,
    *,
    department_id: UUID | None = None,
    q: str | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(Division).order_by(Division.code)
    if department_id is not None:
        stmt = stmt.where(Division.department_id == department_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Division.code.ilike(like)) | (Division.name.ilike(like)))
    if is_active is not None:
        stmt = stmt.where(Division.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_division(db: AsyncSession, division_id: UUID) -> Division:
    return await get_or_404(db, Division, division_id, "Division")


async def create_division(db: AsyncSession, data: DivisionCreate) -> Division:
    await _require_department(db, data.department_id)
    obj = Division(
        department_id=data.department_id,
        name=data.name.strip(),
        code=data.code.strip(),
        student_count=data.student_count,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_division(db: AsyncSession, division_id: UUID, data: DivisionUpdate) -> Division:
    obj = await get_division(db, division_id)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("department_id") is not None:
        await _require_department(db, patch["department_id"])
    for field in ("name", "code"):
        if isinstance(patch.get(field), str):
            patch[field] = patch[field].strip()
    for field, value in patch.items():
        setattr(obj, field, value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_division(db: AsyncSession, division_id: UUID) -> None:
    await delete_safe(db, await get_division(db, division_id), "division")
