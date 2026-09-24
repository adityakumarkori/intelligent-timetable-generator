"""Subject service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subject
from app.models.enums import RoomType, SubjectType
from app.schemas.common import PageParams
from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.services.common import commit_or_409, delete_safe, get_or_404, paginate

UNIQUE_MESSAGES = {
    "subjects_code_key": "Subject code already exists",
    "ix_subjects_code": "Subject code already exists",
}


async def list_subjects(
    db: AsyncSession,
    params: PageParams,
    *,
    q: str | None = None,
    subject_type: SubjectType | None = None,
    required_room_type: RoomType | None = None,
    requires_lab: bool | None = None,
    is_active: bool | None = None,
) -> dict:
    stmt = select(Subject).order_by(Subject.code)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Subject.code.ilike(like)) | (Subject.name.ilike(like)))
    if subject_type is not None:
        stmt = stmt.where(Subject.subject_type == subject_type)
    if required_room_type is not None:
        stmt = stmt.where(Subject.required_room_type == required_room_type)
    if requires_lab is not None:
        stmt = stmt.where(Subject.requires_lab == requires_lab)
    if is_active is not None:
        stmt = stmt.where(Subject.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_subject(db: AsyncSession, subject_id: UUID) -> Subject:
    return await get_or_404(db, Subject, subject_id, "Subject")


async def create_subject(db: AsyncSession, data: SubjectCreate) -> Subject:
    obj = Subject(
        code=data.code.strip(),
        name=data.name.strip(),
        subject_type=data.subject_type,
        required_periods_per_week=data.required_periods_per_week,
        required_room_type=data.required_room_type,
        requires_lab=data.requires_lab,
        is_active=data.is_active,
    )
    db.add(obj)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_subject(db: AsyncSession, subject_id: UUID, data: SubjectUpdate) -> Subject:
    obj = await get_subject(db, subject_id)
    patch = data.model_dump(exclude_unset=True)
    for field in ("code", "name"):
        if isinstance(patch.get(field), str):
            patch[field] = patch[field].strip()
    for field, value in patch.items():
        setattr(obj, field, value)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_subject(db: AsyncSession, subject_id: UUID) -> None:
    await delete_safe(db, await get_subject(db, subject_id), "subject")
