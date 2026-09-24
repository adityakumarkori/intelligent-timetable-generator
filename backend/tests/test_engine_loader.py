"""Data loader tests: scope assembly, inactive filtering, configuration errors."""

import uuid
from datetime import date, time

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    AcademicSession,
    Department,
    Division,
    DivisionSubjectRequirement,
    Faculty,
    FacultyAssignment,
    Period,
    Room,
    Subject,
    User,
)
from app.models.enums import DayOfWeek, RoomType, UserRole
from app.timetable_engine.data_loader import load_scope_data
from app.timetable_engine.exceptions import ConfigurationError


async def _seed_minimal(
    db, *, session_active=True, division_active=True,
    day=DayOfWeek.MONDAY, order=1,
):
    tag = uuid.uuid4().hex[:6]
    db.add(User(
        name="A", email=f"a-{tag}@x.edu",
        password_hash=hash_password("pw"), role=UserRole.ADMIN,
    ))
    dept = Department(name="D", code=f"D{tag}")
    db.add(dept)
    await db.flush()
    academic = AcademicSession(
        name=f"S{tag}", start_date=date(2026, 7, 1),
        end_date=date(2027, 5, 31), is_active=session_active,
    )
    division = Division(
        department_id=dept.id, name=f"DIV{tag}", code=f"DIV{tag}",
        student_count=20, is_active=division_active,
    )
    subject = Subject(code=f"SUB{tag}", name="Sub", required_periods_per_week=2)
    faculty = Faculty(employee_code=f"E{tag}", department_id=dept.id, name="Fac")
    room = Room(name=f"R{tag}", room_type=RoomType.CLASSROOM, capacity=30)
    period = Period(day_of_week=day, start_time=time(9, 0),
                    end_time=time(10, 0), period_order=order)
    db.add_all([academic, division, subject, faculty, room, period])
    await db.flush()
    db.add_all([
        DivisionSubjectRequirement(
            division_id=division.id, subject_id=subject.id,
            academic_session_id=academic.id, required_periods_per_week=2,
        ),
        FacultyAssignment(
            faculty_id=faculty.id, subject_id=subject.id, division_id=division.id,
            academic_session_id=academic.id,
        ),
    ])
    await db.commit()
    return academic, division


async def test_loader_builds_complete_scope(db):
    academic, division = await _seed_minimal(db)
    scope = await load_scope_data(db, academic.id, [division.id])
    assert scope.session_name == academic.name
    assert len(scope.requirements) == 1
    assert scope.requirements[0].periods_per_week == 2
    assert len(scope.requirements[0].eligible_faculty_ids) == 1
    assert len(scope.teaching_period_ids) == 1
    assert scope.divisions[division.id].student_count == 20


async def test_loader_missing_session_or_division(db):
    academic, division = await _seed_minimal(db)
    with pytest.raises(ConfigurationError):
        await load_scope_data(db, uuid.uuid4(), [division.id])
    with pytest.raises(ConfigurationError):
        await load_scope_data(db, academic.id, [uuid.uuid4()])
    with pytest.raises(ConfigurationError):
        await load_scope_data(db, academic.id, [])


async def test_loader_rejects_inactive_scope(db):
    academic, division = await _seed_minimal(db, session_active=False)
    with pytest.raises(ConfigurationError, match="inactive"):
        await load_scope_data(db, academic.id, [division.id])

    academic2, division2 = await _seed_minimal(
        db, division_active=False, day=DayOfWeek.TUESDAY
    )
    with pytest.raises(ConfigurationError, match="inactive"):
        await load_scope_data(db, academic2.id, [division2.id])


async def test_loader_excludes_inactive_subject_requirement(db):
    academic, division = await _seed_minimal(db)
    subject = (await db.scalars(select(Subject))).first()
    subject.is_active = False
    await db.commit()
    with pytest.raises(ConfigurationError, match="No active subject requirements"):
        await load_scope_data(db, academic.id, [division.id])


async def test_loader_drops_inactive_faculty_from_eligibility(db):
    academic, division = await _seed_minimal(db)
    faculty = (await db.scalars(select(Faculty))).first()
    faculty.is_active = False
    await db.commit()
    scope = await load_scope_data(db, academic.id, [division.id])
    assert scope.requirements[0].eligible_faculty_ids == ()
