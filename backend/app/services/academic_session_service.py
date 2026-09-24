"""Academic session service.

Single-active-session business rule: activating one session deactivates the
rest (explicit, auditable behavior — no silent multi-active states).
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcademicSession
from app.schemas.academic_session import AcademicSessionCreate, AcademicSessionUpdate
from app.schemas.common import PageParams
from app.services.common import commit_or_409, delete_safe, get_or_404, paginate

UNIQUE_MESSAGES = {
    "academic_sessions_name_key": "Academic session name already exists",
    "ix_academic_sessions_name": "Academic session name already exists",
}


async def list_sessions(
    db: AsyncSession, params: PageParams, *, is_active: bool | None = None
) -> dict:
    stmt = select(AcademicSession).order_by(AcademicSession.start_date.desc())
    if is_active is not None:
        stmt = stmt.where(AcademicSession.is_active == is_active)
    return await paginate(db, stmt, params)


async def get_session(db: AsyncSession, session_id: UUID) -> AcademicSession:
    return await get_or_404(db, AcademicSession, session_id, "Academic session")


async def _deactivate_others(db: AsyncSession, keep_id: UUID) -> None:
    await db.execute(
        update(AcademicSession)
        .where(AcademicSession.id != keep_id, AcademicSession.is_active == True)  # noqa: E712
        .values(is_active=False)
    )


async def create_session(db: AsyncSession, data: AcademicSessionCreate) -> AcademicSession:
    obj = AcademicSession(
        name=data.name.strip(),
        start_date=data.start_date,
        end_date=data.end_date,
        is_active=data.is_active,
    )
    db.add(obj)
    await db.flush()
    if obj.is_active:
        await _deactivate_others(db, obj.id)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def update_session(
    db: AsyncSession, session_id: UUID, data: AcademicSessionUpdate
) -> AcademicSession:
    obj = await get_session(db, session_id)
    patch = data.model_dump(exclude_unset=True)
    if "name" in patch and isinstance(patch["name"], str):
        patch["name"] = patch["name"].strip()
    start = patch.get("start_date", obj.start_date)
    end = patch.get("end_date", obj.end_date)
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date must be after start_date",
        )
    for field, value in patch.items():
        setattr(obj, field, value)
    await db.flush()
    if patch.get("is_active") is True:
        await _deactivate_others(db, obj.id)
    await commit_or_409(db, UNIQUE_MESSAGES)
    await db.refresh(obj)
    return obj


async def delete_session(db: AsyncSession, session_id: UUID) -> None:
    await delete_safe(db, await get_session(db, session_id), "academic session")
