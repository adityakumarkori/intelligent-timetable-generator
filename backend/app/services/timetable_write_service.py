"""Manual entry editing + timetable lifecycle (publish/archive/clone).

 Every mutation follows one pattern: load → editable? → concurrency? →
 apply → cross-check against PUBLISHED timetables of other divisions in the
 same session → full independent revalidation → recompute status → commit,
 else rollback. Nothing invalid is ever stored as valid, and published
 history is immutable.

 Cross-timetable rule (§6): faculty/room clashes are checked against
 PUBLISHED timetables only — never against drafts/versions, which are
 alternative futures. No global UNIQUE constraint is used, so versioned
 history keeps working; conflicts are enforced at the service layer.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import UUID

from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    DivisionSubjectRequirement,
    Faculty,
    FacultyAssignment,
    Period,
    Room,
    Subject,
    Timetable,
    TimetableEntry,
    User,
)
from app.models.enums import TimetableStatus
from app.schemas.entry import EntryCreate, EntryUpdate
from app.services import timetable_service
from app.services.common import get_or_404, not_found, translate_integrity
from app.timetable_engine import GeneratedEntry, load_scope_data
from app.timetable_engine.conflict_explainer import suggest_for
from app.timetable_engine.exceptions import ConfigurationError
from app.timetable_engine.models import ConflictSeverity, ConflictType
from app.timetable_engine.quality import evaluate_quality
from app.timetable_engine.validator import validate_entries
from app.timetable_engine.validator import validate_entries

EDITABLE_STATUSES = {
    TimetableStatus.DRAFT,
    TimetableStatus.GENERATED,
    TimetableStatus.VALID,
}

_CONFLICT = "TIMETABLE_CONFLICT"


def _conflict(
    type_: ConflictType,
    message: str,
    suggestions: list[str] | None = None,
    **details,
) -> dict:
    return {
        "type": type_.value,
        "severity": ConflictSeverity.ERROR.value,
        "message": message,
        "subject": None,
        "division": None,
        "details": details,
        "suggestions": suggestions if suggestions is not None else suggest_for(type_),
    }


def _conflict_error(conflicts: list[dict]) -> HTTPException:
    seen: list[str] = []
    for conflict in conflicts:
        for suggestion in conflict.get("suggestions", []):
            if suggestion not in seen:
                seen.append(suggestion)
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": _CONFLICT, "conflicts": conflicts, "suggestions": seen},
    )


def _require_editable(timetable: Timetable) -> None:
    if timetable.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Timetable is {timetable.status.value} and immutable; "
                "clone it to create an editable version."
            ),
        )


def _check_concurrency(timetable: Timetable, if_unmodified_since: str | None) -> None:
    """Optimistic concurrency via If-Unmodified-Since (HTTP-date, 1s resolution)."""
    if if_unmodified_since is None:
        return
    try:
        stamp = parsedate_to_datetime(if_unmodified_since)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid If-Unmodified-Since header; expected an HTTP date.",
        ) from None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    current = timetable.updated_at
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if int(stamp.timestamp()) != int(current.timestamp()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "STALE_TIMETABLE",
                "message": "Timetable was modified by another administrator. "
                "Reload and retry.",
            },
        )


def _touch(timetable: Timetable) -> None:
    timetable.updated_at = datetime.now(timezone.utc)


def _entry_options():
    return (
        joinedload(TimetableEntry.subject),
        joinedload(TimetableEntry.faculty),
        joinedload(TimetableEntry.room),
        joinedload(TimetableEntry.period),
    )


async def _fetch_entry(db: AsyncSession, entry_id: UUID) -> TimetableEntry:
    row = await db.scalar(
        select(TimetableEntry).options(*_entry_options()).where(TimetableEntry.id == entry_id)
    )
    if row is None:
        raise not_found("Timetable entry", entry_id)
    return row


async def _scope_or_409(db: AsyncSession, timetable: Timetable):
    try:
        return await load_scope_data(db, timetable.academic_session_id, [timetable.division_id])
    except ConfigurationError as exc:
        raise _conflict_error(
            [_conflict(ConflictType.INVALID_CONFIGURATION, str(exc))]
        ) from None


def _to_generated(timetable: Timetable, rows: list[TimetableEntry]) -> list[GeneratedEntry]:
    return [
        GeneratedEntry(
            session_index=index,
            division_id=timetable.division_id,
            subject_id=row.subject_id,
            period_id=row.period_id,
            faculty_id=row.faculty_id,
            room_id=row.room_id,
        )
        for index, row in enumerate(rows)
    ]


async def _rows(db: AsyncSession, timetable_id: UUID) -> list[TimetableEntry]:
    return list(
        (
            await db.scalars(
                select(TimetableEntry).where(TimetableEntry.timetable_id == timetable_id)
            )
        ).all()
    )


def _period_label(period: Period) -> str:
    return f"{period.day_of_week.value.capitalize()} Period {period.period_order}"


async def _cross_conflicts(
    db: AsyncSession,
    timetable: Timetable,
    faculty_id: UUID,
    room_id: UUID,
    period_id: UUID,
) -> list[dict]:
    """Faculty/room clashes vs PUBLISHED timetables of OTHER divisions.

    Same-division published versions are excluded: publishing a new version
    archives them in the same transaction, so they are replaced rather than
    rival. Drafts/versions are never checked — only committed reality.
    """
    rows = list(
        (
            await db.scalars(
                select(TimetableEntry)
                .join(Timetable, TimetableEntry.timetable_id == Timetable.id)
                .options(
                    joinedload(TimetableEntry.faculty),
                    joinedload(TimetableEntry.room),
                    joinedload(TimetableEntry.period),
                    joinedload(TimetableEntry.timetable).joinedload(Timetable.division),
                )
                .where(
                    Timetable.academic_session_id == timetable.academic_session_id,
                    Timetable.id != timetable.id,
                    Timetable.division_id != timetable.division_id,
                    Timetable.status == TimetableStatus.PUBLISHED,
                    TimetableEntry.period_id == period_id,
                    or_(
                        TimetableEntry.faculty_id == faculty_id,
                        TimetableEntry.room_id == room_id,
                    ),
                )
            )
        ).all()
    )
    conflicts: list[dict] = []
    for row in rows:
        label = _period_label(row.period)
        if row.faculty_id == faculty_id:
            conflicts.append(
                _conflict(
                    ConflictType.FACULTY_CONFLICT,
                    f"Faculty '{row.faculty.name}' already teaches "
                    f"'{row.timetable.division.code}' during {label}.",
                    faculty_id=str(faculty_id),
                    period_id=str(period_id),
                    other_timetable_id=str(row.timetable_id),
                )
            )
        if row.room_id == room_id:
            conflicts.append(
                _conflict(
                    ConflictType.ROOM_CONFLICT,
                    f"Room '{row.room.name}' is already occupied by "
                    f"'{row.timetable.division.code}' during {label}.",
                    room_id=str(room_id),
                    period_id=str(period_id),
                    other_timetable_id=str(row.timetable_id),
                )
            )
    return conflicts


def _violation_conflicts(violations) -> list[dict]:
    return [
        _conflict(v.type, v.message, suggest_for(v.type), **v.details)
        for v in violations
    ]


async def _revalidate(db: AsyncSession, timetable: Timetable):
    """Full independent validation + quality of the current (flushed) state."""
    scope = await _scope_or_409(db, timetable)
    report = validate_entries(_to_generated(timetable, await _rows(db, timetable.id)), scope)
    quality = evaluate_quality(
        _to_generated(timetable, await _rows(db, timetable.id)), scope
    )
    return report, quality


async def _commit_or_rollback(db: AsyncSession, timetable: Timetable, report) -> None:
    """Recompute status from validation, then commit — or roll everything back."""
    if report.valid:
        timetable.status = TimetableStatus.VALID
    else:
        timetable.status = TimetableStatus.DRAFT
    _touch(timetable)
    await db.commit()


async def _requirement_or_409(
    db: AsyncSession, timetable: Timetable, subject: Subject
) -> None:
    requirement = await db.scalar(
        select(DivisionSubjectRequirement).where(
            DivisionSubjectRequirement.division_id == timetable.division_id,
            DivisionSubjectRequirement.subject_id == subject.id,
            DivisionSubjectRequirement.academic_session_id == timetable.academic_session_id,
            DivisionSubjectRequirement.is_active == True,  # noqa: E712
        )
    )
    if requirement is None:
        raise _conflict_error(
            [
                _conflict(
                    ConflictType.INVALID_CONFIGURATION,
                    f"Subject '{subject.code}' is not part of this division's "
                    "requirements for the session.",
                    subject_id=str(subject.id),
                )
            ]
        )


async def _assignment_or_409(
    db: AsyncSession, timetable: Timetable, faculty: Faculty, subject: Subject
) -> None:
    assignment = await db.scalar(
        select(FacultyAssignment).where(
            FacultyAssignment.faculty_id == faculty.id,
            FacultyAssignment.subject_id == subject.id,
            FacultyAssignment.division_id == timetable.division_id,
            FacultyAssignment.academic_session_id == timetable.academic_session_id,
            FacultyAssignment.is_active == True,  # noqa: E712
        )
    )
    if assignment is None or not faculty.is_active:
        raise _conflict_error(
            [
                _conflict(
                    ConflictType.INVALID_ASSIGNMENT,
                    f"Faculty '{faculty.name}' has no active assignment for "
                    f"'{subject.code}' in this division/session.",
                    faculty_id=str(faculty.id),
                    subject_id=str(subject.id),
                )
            ]
        )


async def create_entry(
    db: AsyncSession,
    timetable_id: UUID,
    data: EntryCreate,
    if_unmodified_since: str | None = None,
) -> TimetableEntry:
    """Validate a proposed entry precisely, then revalidate the whole timetable."""
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    _require_editable(timetable)
    _check_concurrency(timetable, if_unmodified_since)

    subject = await get_or_404(db, Subject, data.subject_id, "Subject")
    faculty = await get_or_404(db, Faculty, data.faculty_id, "Faculty")
    room = await get_or_404(db, Room, data.room_id, "Room")
    period = await get_or_404(db, Period, data.period_id, "Period")

    for entity, kind, name in (
        (subject, "Subject", subject.code),
        (faculty, "Faculty", faculty.name),
        (room, "Room", room.name),
    ):
        if not entity.is_active:
            raise _conflict_error(
                [_conflict(ConflictType.INACTIVE_ENTITY, f"{kind} '{name}' is inactive.")]
            )
    if not period.is_active or period.is_break:
        raise _conflict_error(
            [_conflict(ConflictType.BREAK_PERIOD_USED,
                       f"{_period_label(period)} is not a teachable period.")]
        )
    await _requirement_or_409(db, timetable, subject)
    await _assignment_or_409(db, timetable, faculty, subject)

    occupied = await db.scalar(
        select(TimetableEntry).where(
            TimetableEntry.timetable_id == timetable_id,
            TimetableEntry.period_id == period.id,
        )
    )
    if occupied is not None:
        raise _conflict_error(
            [
                _conflict(
                    ConflictType.DIVISION_CONFLICT,
                    f"This timetable already has a class during {_period_label(period)}.",
                    period_id=str(period.id),
                )
            ]
        )

    entry = TimetableEntry(
        timetable_id=timetable_id,
        subject_id=subject.id,
        faculty_id=faculty.id,
        room_id=room.id,
        period_id=period.id,
    )
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity(exc, {}) from None

    cross = await _cross_conflicts(db, timetable, faculty.id, room.id, period.id)
    if cross:
        await db.rollback()
        raise _conflict_error(cross)

    report, _quality = await _revalidate(db, timetable)
    if not report.valid:
        await db.rollback()
        raise _conflict_error(_violation_conflicts(report.violations))

    await _commit_or_rollback(db, timetable, report)
    return await _fetch_entry(db, entry.id)


async def update_entry(
    db: AsyncSession,
    timetable_id: UUID,
    entry_id: UUID,
    data: EntryUpdate,
    if_unmodified_since: str | None = None,
) -> TimetableEntry:
    """Apply a patch, then validate the complete resulting timetable state."""
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    _require_editable(timetable)
    _check_concurrency(timetable, if_unmodified_since)
    entry = await get_or_404(db, TimetableEntry, entry_id, "Timetable entry")
    if entry.timetable_id != timetable.id:
        raise not_found("Timetable entry", entry_id)

    patch = data.model_dump(exclude_unset=True)
    if not patch:
        return await _fetch_entry(db, entry.id)
    for field, model, label in (
        ("subject_id", Subject, "Subject"),
        ("faculty_id", Faculty, "Faculty"),
        ("room_id", Room, "Room"),
        ("period_id", Period, "Period"),
    ):
        if field in patch:
            obj = await db.get(model, patch[field])
            if obj is None:
                raise not_found(label, patch[field])
            setattr(entry, field, obj.id)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        code = getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)
        if code == "23505":
            raise _conflict_error(
                [
                    _conflict(
                        ConflictType.DIVISION_CONFLICT,
                        "This timetable already has a class during that period.",
                    )
                ]
            ) from None
        raise translate_integrity(exc, {}) from None
    subject = await db.get(Subject, entry.subject_id)
    faculty = await db.get(Faculty, entry.faculty_id)
    room = await db.get(Room, entry.room_id)
    period = await db.get(Period, entry.period_id)
    for entity, kind, name in (
        (subject, "Subject", subject.code),
        (faculty, "Faculty", faculty.name),
        (room, "Room", room.name),
    ):
        if not entity.is_active:
            await db.rollback()
            raise _conflict_error(
                [_conflict(ConflictType.INACTIVE_ENTITY, f"{kind} '{name}' is inactive.")]
            )
    if not period.is_active or period.is_break:
        await db.rollback()
        raise _conflict_error(
            [_conflict(ConflictType.BREAK_PERIOD_USED,
                       f"{_period_label(period)} is not a teachable period.")]
        )
    await _requirement_or_409(db, timetable, subject)
    await _assignment_or_409(db, timetable, faculty, subject)

    cross = await _cross_conflicts(db, timetable, faculty.id, room.id, period.id)
    if cross:
        await db.rollback()
        raise _conflict_error(cross)

    report, _quality = await _revalidate(db, timetable)
    if not report.valid:
        await db.rollback()
        raise _conflict_error(_violation_conflicts(report.violations))

    await _commit_or_rollback(db, timetable, report)
    return await _fetch_entry(db, entry.id)


async def delete_entry(db: AsyncSession, timetable_id: UUID, entry_id: UUID) -> None:
    """Delete, then reclassify: a timetable that is no longer complete or
    valid must not stay VALID (and PUBLISHED timetables cannot be touched)."""
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    _require_editable(timetable)
    entry = await get_or_404(db, TimetableEntry, entry_id, "Timetable entry")
    if entry.timetable_id != timetable.id:
        raise not_found("Timetable entry", entry_id)
    await db.delete(entry)
    await db.flush()
    report, _quality = await _revalidate(db, timetable)
    await _commit_or_rollback(db, timetable, report)


async def publish_timetable(
    db: AsyncSession,
    actor: User,
    timetable_id: UUID,
    if_unmodified_since: str | None = None,
) -> dict:
    """VALID (+GENERATED/DRAFT that validate inline) → PUBLISHED, atomically.

    Archives same-division published versions in the same transaction, and
    rejects clashes with other divisions' published timetables. There is
    never a moment where an invalid timetable is the published one.
    """
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    _check_concurrency(timetable, if_unmodified_since)
    if timetable.status == TimetableStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Timetable is already published.",
        )
    if timetable.status == TimetableStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Archived timetables cannot be published; clone to edit.",
        )

    scope = await _scope_or_409(db, timetable)
    report = validate_entries(_to_generated(timetable, await _rows(db, timetable.id)), scope)
    if not report.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "TIMETABLE_INVALID",
                "conflicts": [
                    {
                        "type": v.type.value,
                        "severity": ConflictSeverity.ERROR.value,
                        "message": v.message,
                        "subject": None,
                        "division": None,
                        "details": v.details,
                        "suggestions": suggest_for(v.type),
                    }
                    for v in report.violations
                ],
            },
        )

    rows = await _rows(db, timetable.id)
    cross: list[dict] = []
    for row in rows:
        cross.extend(
            await _cross_conflicts(db, timetable, row.faculty_id, row.room_id, row.period_id)
        )
    if cross:
        await db.rollback()
        raise _conflict_error(cross)

    superseded = list(
        (
            await db.scalars(
                select(Timetable).where(
                    Timetable.academic_session_id == timetable.academic_session_id,
                    Timetable.division_id == timetable.division_id,
                    Timetable.status == TimetableStatus.PUBLISHED,
                    Timetable.id != timetable.id,
                )
            )
        ).all()
    )
    for old in superseded:
        old.status = TimetableStatus.ARCHIVED
        _touch(old)
    timetable.status = TimetableStatus.PUBLISHED
    timetable.published_at = datetime.now(timezone.utc)
    timetable.published_by = actor.id
    _touch(timetable)
    await db.commit()
    return await timetable_service.get_timetable_detail(db, actor, timetable.id)


async def archive_timetable(db: AsyncSession, actor: User, timetable_id: UUID) -> dict:
    timetable = await get_or_404(db, Timetable, timetable_id, "Timetable")
    if timetable.status == TimetableStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Timetable is already archived.",
        )
    if timetable.status == TimetableStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Draft timetables cannot be archived.",
        )
    timetable.status = TimetableStatus.ARCHIVED
    _touch(timetable)
    await db.commit()
    return await timetable_service.get_timetable_detail(db, actor, timetable.id)


async def clone_timetable(db: AsyncSession, actor: User, timetable_id: UUID) -> dict:
    """Copy a timetable into a new editable DRAFT version (new IDs throughout)."""
    source = await get_or_404(db, Timetable, timetable_id, "Timetable")
    source_rows = await _rows(db, source.id)
    max_version = await db.scalar(
        select(func.max(Timetable.version)).where(
            Timetable.academic_session_id == source.academic_session_id,
            Timetable.division_id == source.division_id,
        )
    )
    clone = Timetable(
        academic_session_id=source.academic_session_id,
        division_id=source.division_id,
        status=TimetableStatus.DRAFT,
        version=(max_version or 0) + 1,
        generated_at=None,
        published_at=None,
        published_by=None,
        created_by=actor.id,
    )
    db.add(clone)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity(
            exc, {"uq_timetables_session_division_version": "Version already exists; retry."}
        ) from None
    for row in source_rows:
        db.add(
            TimetableEntry(
                timetable_id=clone.id,
                subject_id=row.subject_id,
                faculty_id=row.faculty_id,
                room_id=row.room_id,
                period_id=row.period_id,
            )
        )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity(exc, {}) from None

    scope = await _scope_or_409(db, clone)
    report = validate_entries(_to_generated(clone, await _rows(db, clone.id)), scope)
    quality = evaluate_quality(_to_generated(clone, await _rows(db, clone.id)), scope)
    return {
        "id": clone.id,
        "academic_session_id": clone.academic_session_id,
        "division_id": clone.division_id,
        "status": clone.status,
        "version": clone.version,
        "entry_count": len(source_rows),
        "valid": report.valid,
        "violations": [
            {"type": v.type.value, "message": v.message, "details": v.details}
            for v in report.violations
        ],
        "warnings": quality.warnings,
    }
