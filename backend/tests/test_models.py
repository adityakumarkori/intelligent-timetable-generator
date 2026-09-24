"""Model tests — creation, relationships, and every load-bearing DB constraint."""

import uuid
from datetime import date, time

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import (
    AcademicSession,
    Department,
    Division,
    DivisionSubjectRequirement,
    Faculty,
    FacultyAssignment,
    FacultyAvailability,
    Period,
    Room,
    Subject,
    Timetable,
    TimetableEntry,
    User,
)
from app.models.enums import (
    AvailabilityStatus,
    DayOfWeek,
    RoomType,
    SubjectType,
    TimetableStatus,
    UserRole,
)


def _tag() -> str:
    return uuid.uuid4().hex[:6]


async def make_core(db, tag: str) -> dict:
    """Minimal valid graph: dept/division/session/subject/faculty/room/period/timetable."""
    dept = Department(name=f"CS {tag}", code=f"CS{tag}")
    db.add(dept)
    await db.flush()
    division = Division(department_id=dept.id, name=f"CSE-A {tag}", code="CSE-A", student_count=60)
    session_obj = AcademicSession(
        name=f"2026-27-{tag}", start_date=date(2026, 7, 1), end_date=date(2027, 5, 31)
    )
    subject = Subject(
        code=f"MATH{tag}", name="Mathematics", subject_type=SubjectType.LECTURE,
        required_periods_per_week=5, required_room_type=RoomType.CLASSROOM,
    )
    faculty = Faculty(employee_code=f"EMP{tag}", department_id=dept.id, name="Alice")
    room = Room(name=f"R-{tag}", room_type=RoomType.CLASSROOM, capacity=80)
    period = Period(
        day_of_week=DayOfWeek.MONDAY, start_time=time(9, 0), end_time=time(10, 0), period_order=1
    )
    db.add_all([division, session_obj, subject, faculty, room, period])
    await db.flush()
    timetable = Timetable(academic_session_id=session_obj.id, division_id=division.id)
    db.add(timetable)
    await db.flush()
    await db.commit()
    return {
        "dept": dept, "division": division, "session": session_obj, "subject": subject,
        "faculty": faculty, "room": room, "period": period, "timetable": timetable,
    }


async def test_create_and_navigate_relationships(db):
    core = await make_core(db, _tag())
    db.add(
        TimetableEntry(
            timetable_id=core["timetable"].id, subject_id=core["subject"].id,
            faculty_id=core["faculty"].id, room_id=core["room"].id, period_id=core["period"].id,
        )
    )
    await db.commit()

    division = await db.scalar(
        select(Division)
        .options(selectinload(Division.department).selectinload(Department.divisions))
        .where(Division.id == core["division"].id)
    )
    assert division.department.code == core["dept"].code
    assert division.department.divisions[0].id == division.id
    assert core["faculty"].department_id == core["dept"].id

    timetable = await db.scalar(
        select(Timetable)
        .options(
            selectinload(Timetable.entries).selectinload(TimetableEntry.subject),
            selectinload(Timetable.entries).selectinload(TimetableEntry.period),
            selectinload(Timetable.division),
        )
        .where(Timetable.id == core["timetable"].id)
    )
    assert timetable.status == TimetableStatus.DRAFT
    assert timetable.version == 1
    entry = timetable.entries[0]
    assert entry.subject.code == core["subject"].code
    assert entry.period.day_of_week == DayOfWeek.MONDAY
    assert entry.timetable.division.id == division.id  # division derived, not duplicated
    assert core["timetable"].created_at is not None
    assert core["timetable"].updated_at is not None


async def test_duplicate_department_code_rejected(db):
    tag = _tag()
    db.add_all([Department(name="A", code=f"DUP{tag}"), Department(name="B", code=f"DUP{tag}")])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_division_code_unique_within_department_only(db):
    tag = _tag()
    dept_a = Department(name="A", code=f"A{tag}")
    dept_b = Department(name="B", code=f"B{tag}")
    db.add_all([dept_a, dept_b])
    await db.flush()
    db.add(Division(department_id=dept_a.id, name="X", code="CSE-A"))
    db.add(Division(department_id=dept_b.id, name="Y", code="CSE-A"))  # OK: other dept
    await db.commit()

    db.add(Division(department_id=dept_a.id, name="Z", code="CSE-A"))  # same dept -> reject
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_subject_code_rejected(db):
    tag = _tag()
    kwargs = dict(name="Math", subject_type=SubjectType.LECTURE, required_periods_per_week=3)
    db.add_all([Subject(code=f"SUB{tag}", **kwargs), Subject(code=f"SUB{tag}", **kwargs)])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_employee_code_rejected(db):
    tag = _tag()
    dept = Department(name="D", code=f"D{tag}")
    db.add(dept)
    await db.flush()
    db.add_all([
        Faculty(employee_code=f"E{tag}", department_id=dept.id, name="A"),
        Faculty(employee_code=f"E{tag}", department_id=dept.id, name="B"),
    ])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_user_email_rejected(db):
    tag = _tag()
    db.add_all([
        User(name="A", email=f"u{tag}@x.edu", password_hash="h", role=UserRole.ADMIN),
        User(name="B", email=f"u{tag}@x.edu", password_hash="h", role=UserRole.ADMIN),
    ])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_faculty_user_link_is_unique(db):
    tag = _tag()
    user = User(name="F", email=f"f{tag}@x.edu", password_hash="h", role=UserRole.FACULTY)
    dept = Department(name="D", code=f"D{tag}")
    db.add_all([user, dept])
    await db.flush()
    db.add_all([
        Faculty(employee_code=f"E1{tag}", department_id=dept.id, name="A", user_id=user.id),
        Faculty(employee_code=f"E2{tag}", department_id=dept.id, name="B", user_id=user.id),
    ])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.parametrize("capacity", [0, -10])
async def test_room_capacity_must_be_positive(db, capacity):
    db.add(Room(name=f"R{_tag()}", room_type=RoomType.CLASSROOM, capacity=capacity))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_subject_periods_must_be_positive(db):
    db.add(Subject(code=f"S{_tag()}", name="X", required_periods_per_week=0))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_division_student_count_cannot_be_negative(db):
    tag = _tag()
    dept = Department(name="D", code=f"D{tag}")
    db.add(dept)
    await db.flush()
    db.add(Division(department_id=dept.id, name="X", code="X", student_count=-1))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_period_end_must_follow_start(db):
    db.add(Period(day_of_week=DayOfWeek.TUESDAY, start_time=time(11, 0), end_time=time(10, 0), period_order=9))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_session_end_must_follow_start(db):
    db.add(AcademicSession(name=f"S{_tag()}", start_date=date(2027, 1, 1), end_date=date(2026, 1, 1)))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_assignment_rejected(db):
    core = await make_core(db, _tag())
    kwargs = dict(
        faculty_id=core["faculty"].id, subject_id=core["subject"].id,
        division_id=core["division"].id, academic_session_id=core["session"].id,
    )
    db.add_all([FacultyAssignment(**kwargs), FacultyAssignment(**kwargs)])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_requirement_rejected(db):
    core = await make_core(db, _tag())
    kwargs = dict(
        division_id=core["division"].id, subject_id=core["subject"].id,
        academic_session_id=core["session"].id, required_periods_per_week=4,
    )
    db.add_all([DivisionSubjectRequirement(**kwargs), DivisionSubjectRequirement(**kwargs)])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_duplicate_availability_rejected(db):
    core = await make_core(db, _tag())
    db.add_all([
        FacultyAvailability(faculty_id=core["faculty"].id, period_id=core["period"].id, status=AvailabilityStatus.AVAILABLE),
        FacultyAvailability(faculty_id=core["faculty"].id, period_id=core["period"].id, status=AvailabilityStatus.UNAVAILABLE),
    ])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_timetable_version_unique_per_session_division(db):
    core = await make_core(db, _tag())
    # Stash plain ids: rollback() expires all ORM state, so capture before IO.
    session_id, division_id = core["session"].id, core["division"].id
    db.add(Timetable(academic_session_id=session_id, division_id=division_id, version=1))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    db.add(Timetable(academic_session_id=session_id, division_id=division_id, version=2))
    await db.commit()  # new version is fine


async def test_entry_unique_per_timetable_period(db):
    """DB-level division-conflict guard: one entry per division (timetable) per period."""
    core = await make_core(db, _tag())
    entry_kwargs = dict(
        timetable_id=core["timetable"].id, subject_id=core["subject"].id,
        faculty_id=core["faculty"].id, room_id=core["room"].id, period_id=core["period"].id,
    )
    db.add(TimetableEntry(**entry_kwargs))
    await db.commit()

    db.add(TimetableEntry(**entry_kwargs))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_same_period_allowed_across_timetables(db):
    """Uniqueness is scoped to one timetable so drafts/history stay valid;
    cross-timetable faculty/room clashes are the Phase 5 validator's job."""
    tag = _tag()
    core = await make_core(db, tag)
    other_division = Division(department_id=core["dept"].id, name="CSE-B", code="CSE-B", student_count=10)
    db.add(other_division)
    await db.flush()
    other_table = Timetable(
        academic_session_id=core["session"].id, division_id=other_division.id, version=1
    )
    db.add(other_table)
    await db.flush()

    for table_id in (core["timetable"].id, other_table.id):
        db.add(
            TimetableEntry(
                timetable_id=table_id, subject_id=core["subject"].id,
                faculty_id=core["faculty"].id, room_id=core["room"].id, period_id=core["period"].id,
            )
        )
    await db.commit()  # must succeed


async def test_restrict_blocks_deleting_department_with_divisions(db):
    core = await make_core(db, _tag())
    await db.delete(core["dept"])
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


async def test_cascade_deletes_entries_with_timetable(db):
    core = await make_core(db, _tag())
    entry = TimetableEntry(
        timetable_id=core["timetable"].id, subject_id=core["subject"].id,
        faculty_id=core["faculty"].id, room_id=core["room"].id, period_id=core["period"].id,
    )
    db.add(entry)
    await db.commit()

    await db.delete(core["timetable"])
    await db.commit()
    remaining = await db.scalars(select(TimetableEntry))
    assert remaining.all() == []
