"""Independent timetable validator — the mandatory second opinion.

 Verifies a generated (or persisted) timetable against the domain rules using
 only the entry list plus scope data. It never consults the CP-SAT model, so
 solver, mapping, or persistence bugs cannot slip an invalid timetable
 through. One timetable at a time: cross-version contention is out of scope
 (each version is an alternative future, not a simultaneous commitment).
"""

from collections import Counter

from app.models.enums import RoomType
from app.timetable_engine.models import (
    ConflictType,
    GeneratedEntry,
    ScopeData,
    ValidationResult,
    Violation,
)


def _v(
    type_: ConflictType, message: str, **details,
) -> Violation:
    return Violation(type=type_, message=message, details=details)


def validate_entries(
    entries: list[GeneratedEntry], scope: ScopeData
) -> ValidationResult:
    """Check H1–H11 against scope data. Pure function, no I/O."""
    violations: list[Violation] = []

    req_by_div_subj = {(r.division_id, r.subject.id): r for r in scope.requirements}

    for entry in entries:
        period = scope.periods.get(entry.period_id)
        subject = scope.subjects.get(entry.subject_id)
        faculty = scope.faculty.get(entry.faculty_id)
        room = scope.rooms.get(entry.room_id)
        division = scope.divisions.get(entry.division_id)

        label = (
            f"{subject.code if subject else entry.subject_id} / "
            f"{division.code if division else entry.division_id} / "
            f"{period.day.value if period else entry.period_id}"
        )

        # H9 — no break periods.
        if period is None or period.is_break:
            violations.append(
                _v(ConflictType.BREAK_PERIOD_USED,
                   f"Entry {label} uses a break period",
                   period_id=str(entry.period_id)))
            continue  # further period-based checks are meaningless
        # H10 — active entities.
        if not period.is_active:
            violations.append(_v(ConflictType.INACTIVE_ENTITY,
                                 f"Entry {label} uses inactive period {period.day.value} #{period.order}",
                                 period_id=str(entry.period_id)))
        for entity, name, kind in (
            (subject, getattr(subject, "code", "?"), "subject"),
            (faculty, getattr(faculty, "name", "?"), "faculty"),
            (room, getattr(room, "name", "?"), "room"),
            (division, getattr(division, "code", "?"), "division"),
        ):
            if entity is None or not entity.is_active:
                violations.append(
                    _v(ConflictType.INACTIVE_ENTITY,
                       f"Entry {label} references missing/inactive {kind} '{name}'",
                       kind=kind))

        if faculty is not None and entry.period_id in faculty.unavailable_period_ids:
            violations.append(
                _v(ConflictType.FACULTY_UNAVAILABLE,
                   f"Faculty '{faculty.name}' is unavailable during {label}",
                   faculty_id=str(entry.faculty_id), period_id=str(entry.period_id)))

        if room is not None and division is not None:
            if room.capacity < division.student_count:
                violations.append(
                    _v(ConflictType.ROOM_CAPACITY,
                       f"Room '{room.name}' (capacity {room.capacity}) is too small "
                       f"for division '{division.code}' ({division.student_count} students)",
                       room_id=str(entry.room_id), division_id=str(entry.division_id)))

        if room is not None and subject is not None:
            req = req_by_div_subj.get((entry.division_id, entry.subject_id))
            effective_type = (
                req.preferred_room_type
                if req is not None and req.preferred_room_type is not None
                else subject.required_room_type
            )
            effective_lab = (req.requires_lab if req is not None else False) or subject.requires_lab
            type_ok = (
                room.room_type == RoomType.LAB
                if effective_lab
                else (effective_type is None or room.room_type == effective_type)
            )
            if not type_ok:
                violations.append(
                    _v(ConflictType.ROOM_TYPE,
                       f"Room '{room.name}' ({room.room_type.value}) does not satisfy "
                       f"the room requirement for '{subject.code}'"
                       + (" (lab required)" if effective_lab else ""),
                       room_id=str(entry.room_id), subject_id=str(entry.subject_id)))

        if faculty is not None and subject is not None and division is not None:
            ok = any(
                a.faculty_id == entry.faculty_id
                and a.subject_id == entry.subject_id
                and a.division_id == entry.division_id
                and a.session_id == scope.session_id
                and a.is_active
                for a in scope.assignments
            )
            if not ok:
                violations.append(
                    _v(ConflictType.INVALID_ASSIGNMENT,
                       f"Faculty '{faculty.name}' has no active assignment for "
                       f"'{subject.code}' / '{division.code}'",
                       faculty_id=str(entry.faculty_id), subject_id=str(entry.subject_id)))

    # H2/H3/H4 — per-period uniqueness within this timetable.
    for key, count in Counter((e.division_id, e.period_id) for e in entries).items():
        if count > 1:
            violations.append(
                _v(ConflictType.DIVISION_CONFLICT,
                   f"Division has {count} classes in one period (division {key[0]}, period {key[1]})",
                   division_id=str(key[0]), period_id=str(key[1])))
    for key, count in Counter((e.faculty_id, e.period_id) for e in entries).items():
        if count > 1:
            violations.append(
                _v(ConflictType.FACULTY_CONFLICT,
                   f"Faculty teaches {count} classes in one period "
                   f"(faculty {key[0]}, period {key[1]})",
                   faculty_id=str(key[0]), period_id=str(key[1])))
    for key, count in Counter((e.room_id, e.period_id) for e in entries).items():
        if count > 1:
            violations.append(
                _v(ConflictType.ROOM_CONFLICT,
                   f"Room hosts {count} classes in one period (room {key[0]}, period {key[1]})",
                   room_id=str(key[0]), period_id=str(key[1])))

    # H1/H11 — every required session scheduled exactly once.
    actual = Counter((e.division_id, e.subject_id) for e in entries)
    for req in scope.requirements:
        got = actual.get((req.division_id, req.subject.id), 0)
        if got != req.periods_per_week:
            division = scope.divisions[req.division_id]
            violations.append(
                _v(ConflictType.WEEKLY_LOAD_MISMATCH,
                   f"'{req.subject.code}' for '{division.code}': "
                   f"scheduled {got}, required {req.periods_per_week}",
                   division_id=str(req.division_id), subject_id=str(req.subject.id),
                   scheduled=got, required=req.periods_per_week))

    return ValidationResult(valid=not violations, violations=violations)
