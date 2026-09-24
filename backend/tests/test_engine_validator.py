"""Validator tests: a valid timetable passes; each corruption is classified."""

import dataclasses

from app.timetable_engine.models import ConflictType, GeneratedEntry
from app.timetable_engine.validator import validate_entries
from tests.engine_helpers import basic_case, solve_case


def _valid(case):
    result = solve_case(case)
    assert result.status.value == "SUCCESS"
    return list(result.entries)


def _types(report):
    return {v.type for v in report.violations}


def test_valid_timetable_passes():
    case = basic_case()
    assert validate_entries(_valid(case), case.scope).valid


def test_duplicate_faculty_period_flagged():
    case = basic_case()
    entries = _valid(case)
    entries.append(dataclasses.replace(entries[0]))  # same faculty+period twice
    report = validate_entries(entries, case.scope)
    assert not report.valid
    assert ConflictType.FACULTY_CONFLICT in _types(report)
    assert ConflictType.DIVISION_CONFLICT in _types(report)  # same division+period too


def test_duplicate_room_period_flagged():
    case = basic_case(math_per_week=2, lab_per_week=0)
    entries = _valid(case)
    first, second = entries[0], entries[1]
    # Force the second entry into the first entry's room (same period too).
    moved = dataclasses.replace(second, room_id=first.room_id, period_id=first.period_id)
    report = validate_entries([first, moved], case.scope)
    assert ConflictType.ROOM_CONFLICT in _types(report)


def test_wrong_room_type_flagged():
    case = basic_case()
    entries = _valid(case)
    math = next(e for e in entries if case.scope.subjects[e.subject_id].code == "MATH")
    lab_room = case.rooms["L1"].id
    moved = dataclasses.replace(math, room_id=lab_room)
    report = validate_entries(
        [moved if e == math else e for e in entries], case.scope
    )
    assert ConflictType.ROOM_TYPE in _types(report)


def test_lab_in_non_lab_room_flagged():
    case = basic_case()
    entries = _valid(case)
    lab = next(e for e in entries if case.scope.subjects[e.subject_id].code == "LABX")
    classroom = case.rooms["R1"].id
    moved = dataclasses.replace(lab, room_id=classroom)
    report = validate_entries(
        [moved if e == lab else e for e in entries], case.scope
    )
    assert ConflictType.ROOM_TYPE in _types(report)


def test_unavailable_faculty_flagged():
    case = basic_case()
    entries = _valid(case)
    first = entries[0]
    fac = case.scope.faculty[first.faculty_id]
    blocked = fac.unavailable_period_ids or {first.period_id}
    case.scope.faculty[first.faculty_id] = dataclasses.replace(
        fac, unavailable_period_ids=frozenset(blocked)
    )
    moved = dataclasses.replace(first, period_id=next(iter(blocked)))
    report = validate_entries(
        [moved if e == first else e for e in entries], case.scope
    )
    assert ConflictType.FACULTY_UNAVAILABLE in _types(report)


def test_break_period_flagged():
    case = basic_case()
    entries = _valid(case)
    first = entries[0]
    period = case.scope.periods[first.period_id]
    case.scope.periods[first.period_id] = dataclasses.replace(period, is_break=True)
    report = validate_entries(entries, case.scope)
    assert ConflictType.BREAK_PERIOD_USED in _types(report)


def test_missing_weekly_session_flagged():
    case = basic_case()
    entries = _valid(case)[:-1]  # drop one required session
    report = validate_entries(entries, case.scope)
    assert ConflictType.WEEKLY_LOAD_MISMATCH in _types(report)


def test_inactive_room_flagged():
    case = basic_case()
    entries = _valid(case)
    first = entries[0]
    room = case.scope.rooms[first.room_id]
    case.scope.rooms[first.room_id] = dataclasses.replace(room, is_active=False)
    report = validate_entries(entries, case.scope)
    assert ConflictType.INACTIVE_ENTITY in _types(report)


def test_small_room_flagged():
    case = basic_case()
    entries = _valid(case)
    first = entries[0]
    room = case.scope.rooms[first.room_id]
    case.scope.rooms[first.room_id] = dataclasses.replace(room, capacity=1)
    report = validate_entries(entries, case.scope)
    assert ConflictType.ROOM_CAPACITY in _types(report)


def test_unassigned_faculty_flagged():
    case = basic_case()
    entries = _valid(case)
    first = entries[0]
    # Deactivate every assignment matching this entry.
    case.scope.assignments[:] = [
        dataclasses.replace(a, is_active=False)
        if (a.faculty_id, a.subject_id, a.division_id)
        == (first.faculty_id, first.subject_id, first.division_id)
        else a
        for a in case.scope.assignments
    ]
    report = validate_entries(entries, case.scope)
    assert ConflictType.INVALID_ASSIGNMENT in _types(report)


def test_empty_timetable_reports_every_missing_session():
    case = basic_case()
    report = validate_entries([], case.scope)
    assert not report.valid
    mismatches = [v for v in report.violations if v.type == ConflictType.WEEKLY_LOAD_MISMATCH]
    assert len(mismatches) == 2  # MATH + LABX requirements
