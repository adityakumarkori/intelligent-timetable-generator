"""Timetable read service (Phase 4: retrieval only, no generation).

Visibility rules:
- ADMIN/SUPER_ADMIN: everything.
- FACULTY: published timetables, plus any timetable containing their entries.
- STUDENT: published timetables only. Drafts are invisible (404, not 403, so
  their existence never leaks).
"""

from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Division,
    Faculty,
    Timetable,
    TimetableEntry,
    User,
)
from app.models.enums import TimetableStatus, UserRole
from app.schemas.common import PageParams
from app.services.common import get_or_404, not_found, paginate

_FORBIDDEN = "Insufficient permissions"


def _is_admin(actor: User) -> bool:
    return actor.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)


async def _own_faculty_id(db: AsyncSession, actor: User) -> UUID | None:
    if actor.role != UserRole.FACULTY:
        return None
    profile = await db.scalar(select(Faculty).where(Faculty.user_id == actor.id))
    return profile.id if profile else None


async def _own_timetable_ids(db: AsyncSession, faculty_id: UUID) -> set[UUID]:
    rows = await db.scalars(
        select(TimetableEntry.timetable_id)
        .where(TimetableEntry.faculty_id == faculty_id)
        .distinct()
    )
    return set(rows.all())


def _entry_to_dict(e: TimetableEntry) -> dict:
    return {
        "id": e.id,
        "timetable_id": e.timetable_id,
        "division_code": e.timetable.division.code,
        "subject_id": e.subject_id,
        "subject_code": e.subject.code,
        "subject_name": e.subject.name,
        "faculty_id": e.faculty_id,
        "faculty_name": e.faculty.name,
        "room_id": e.room_id,
        "room_name": e.room.name,
        "period": e.period,
    }


def _timetable_to_dict(t: Timetable) -> dict:
    return {
        "id": t.id,
        "academic_session_id": t.academic_session_id,
        "session_name": t.academic_session.name,
        "division_id": t.division_id,
        "division_code": t.division.code,
        "status": t.status,
        "version": t.version,
        "generated_at": t.generated_at,
        "published_at": t.published_at,
        "entry_count": len(t.entries),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _detail_options():
    return (
        joinedload(Timetable.academic_session),
        joinedload(Timetable.division),
        selectinload(Timetable.entries)
        .joinedload(TimetableEntry.subject),
        selectinload(Timetable.entries).joinedload(TimetableEntry.faculty),
        selectinload(Timetable.entries).joinedload(TimetableEntry.room),
        selectinload(Timetable.entries).joinedload(TimetableEntry.period),
        selectinload(Timetable.entries).joinedload(TimetableEntry.timetable).joinedload(
            Timetable.division
        ),
    )


def _entry_options():
    return (
        joinedload(TimetableEntry.subject),
        joinedload(TimetableEntry.faculty),
        joinedload(TimetableEntry.room),
        joinedload(TimetableEntry.period),
        joinedload(TimetableEntry.timetable).joinedload(Timetable.division),
    )


async def _visible_stmt(db: AsyncSession, actor: User):
    """Base timetable query already scoped to what the actor may see."""
    stmt = select(Timetable).options(
        joinedload(Timetable.academic_session),
        joinedload(Timetable.division),
        selectinload(Timetable.entries),
    )
    if _is_admin(actor):
        return stmt
    if actor.role == UserRole.FACULTY:
        own_id = await _own_faculty_id(db, actor)
        own_tables = await _own_timetable_ids(db, own_id) if own_id else set()
        if own_tables:
            return stmt.where(
                or_(
                    Timetable.status == TimetableStatus.PUBLISHED,
                    Timetable.id.in_(own_tables),
                )
            )
        return stmt.where(Timetable.status == TimetableStatus.PUBLISHED)
    # STUDENT and anything else: published only.
    return stmt.where(Timetable.status == TimetableStatus.PUBLISHED)


async def list_timetables(
    db: AsyncSession,
    actor: User,
    params: PageParams,
    *,
    division_id: UUID | None = None,
    academic_session_id: UUID | None = None,
    status_value: TimetableStatus | None = None,
) -> dict:
    stmt = await _visible_stmt(db, actor)
    if division_id is not None:
        stmt = stmt.where(Timetable.division_id == division_id)
    if academic_session_id is not None:
        stmt = stmt.where(Timetable.academic_session_id == academic_session_id)
    if status_value is not None and _is_admin(actor):
        stmt = stmt.where(Timetable.status == status_value)
    stmt = stmt.order_by(Timetable.updated_at.desc())
    page = await paginate(db, stmt, params)
    page["items"] = [_timetable_to_dict(t) for t in page["items"]]
    return page


async def get_timetable_detail(db: AsyncSession, actor: User, timetable_id: UUID) -> dict:
    stmt = (
        select(Timetable).options(*_detail_options()).where(Timetable.id == timetable_id)
    )
    obj = await db.scalar(stmt)
    if obj is None:
        raise not_found("Timetable", timetable_id)
    if not await _may_see(db, actor, obj):
        raise not_found("Timetable", timetable_id)
    detail = _timetable_to_dict(obj)
    detail["entries"] = [_entry_to_dict(e) for e in _sort_entries(obj.entries)]
    return detail


async def _may_see(db: AsyncSession, actor: User, obj: Timetable) -> bool:
    if _is_admin(actor):
        return True
    if obj.status == TimetableStatus.PUBLISHED:
        return True
    if actor.role == UserRole.FACULTY:
        own_id = await _own_faculty_id(db, actor)
        if own_id is None:
            return False
        return await db.scalar(
            select(func.count())
            .select_from(TimetableEntry)
            .where(
                TimetableEntry.timetable_id == obj.id,
                TimetableEntry.faculty_id == own_id,
            )
        ) > 0
    return False


def _sort_entries(entries) -> list:
    return sorted(entries, key=lambda e: (e.period.day_of_week.value, e.period.period_order))


async def list_timetable_entries(
    db: AsyncSession, actor: User, timetable_id: UUID, params: PageParams
) -> dict:
    obj = await get_or_404(db, Timetable, timetable_id, "Timetable")
    if not await _may_see(db, actor, obj):
        raise not_found("Timetable", timetable_id)
    from app.models import Period

    stmt = (
        select(TimetableEntry)
        .options(*_entry_options())
        .join(Period, TimetableEntry.period_id == Period.id)
        .where(TimetableEntry.timetable_id == timetable_id)
        .order_by(Period.day_of_week, Period.period_order)
    )
    page = await paginate(db, stmt, params)
    page["items"] = [_entry_to_dict(e) for e in page["items"]]
    return page


async def division_timetable(db: AsyncSession, actor: User, division_id: UUID) -> dict:
    if await db.get(Division, division_id) is None:
        raise not_found("Division", division_id)
    stmt = await _visible_stmt(db, actor)
    stmt = (
        stmt.where(Timetable.division_id == division_id)
        .order_by(Timetable.version.desc())
        .limit(1)
    )
    obj = await db.scalar(stmt)
    if obj is None:
        raise not_found("Timetable", f"division {division_id}")
    return await get_timetable_detail(db, actor, obj.id)


async def faculty_timetable_entries(
    db: AsyncSession, actor: User, faculty_id: UUID, params: PageParams
) -> dict:
    """Entries taught by one faculty member. Students are never allowed here —
    they use the division timetable view."""
    if actor.role == UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    if actor.role == UserRole.FACULTY:
        own_id = await _own_faculty_id(db, actor)
        if own_id is None or own_id != faculty_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    elif await db.get(Faculty, faculty_id) is None:
        raise not_found("Faculty", faculty_id)

    from app.models import Period

    stmt = (
        select(TimetableEntry)
        .options(*_entry_options())
        .join(Period, TimetableEntry.period_id == Period.id)
        .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
        .where(TimetableEntry.faculty_id == faculty_id)
    )
    if not _is_admin(actor):
        # Faculty viewing their own entries: only through visible timetables.
        visible_ids = select(Timetable.id)
        own_tables = await _own_timetable_ids(db, faculty_id)
        if actor.role == UserRole.FACULTY:
            clauses = [Timetable.status == TimetableStatus.PUBLISHED]
            if own_tables:
                clauses.append(Timetable.id.in_(own_tables))
            visible_ids = visible_ids.where(or_(*clauses))
        else:
            visible_ids = visible_ids.where(Timetable.status == TimetableStatus.PUBLISHED)
        stmt = stmt.where(TimetableEntry.timetable_id.in_(visible_ids))
    stmt = stmt.order_by(Period.day_of_week, Period.period_order)
    page = await paginate(db, stmt, params)
    page["items"] = [_entry_to_dict(e) for e in page["items"]]
    return page
