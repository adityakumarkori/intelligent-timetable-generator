"""In-memory scheduling fixtures for engine unit tests (no database)."""

import uuid
from dataclasses import dataclass
from datetime import time

from app.models.enums import DayOfWeek, RoomType
from app.timetable_engine.generator import generate_from_scope
from app.timetable_engine.models import (
    AssignmentInfo,
    DivisionInfo,
    FacultyInfo,
    PeriodSlot,
    RequirementInfo,
    RoomInfo,
    ScopeData,
    SubjectInfo,
)
from app.timetable_engine.solver import SolverOptions


@dataclass
class Case:
    scope: ScopeData
    divisions: dict[str, DivisionInfo]
    subjects: dict[str, SubjectInfo]
    faculty: dict[str, FacultyInfo]
    rooms: dict[str, RoomInfo]
    periods: dict[str, PeriodSlot]  # key f"{DAY}{order}", e.g. "MONDAY1"
    requirements: dict[str, RequirementInfo]


def basic_case(
    *,
    div_students: int = 30,
    math_per_week: int = 2,
    lab_per_week: int = 1,
    unavailable: dict[str, list[str]] | None = None,
    room_capacity: int = 40,
    days: tuple[str, ...] = ("MONDAY", "TUESDAY"),
    slots_per_day: int = 2,
    math_faculty: tuple[str, ...] = ("F1", "F2"),
    lab_faculty: tuple[str, ...] = ("F1",),
) -> Case:
    """Two subjects (MATH lectures + LABX lab), two faculty, two rooms.

    MATH needs a CLASSROOM, LABX needs a LAB room. Totals: math+lab sessions
    across days*slots teaching periods.
    """
    unavailable = unavailable or {}
    div = DivisionInfo(id=uuid.uuid4(), code="D1", student_count=div_students, is_active=True)

    subjects = {
        "MATH": SubjectInfo(
            id=uuid.uuid4(), code="MATH", name="Mathematics",
            required_room_type=RoomType.CLASSROOM, requires_lab=False, is_active=True,
        ),
        "LABX": SubjectInfo(
            id=uuid.uuid4(), code="LABX", name="Lab Work",
            required_room_type=RoomType.LAB, requires_lab=True, is_active=True,
        ),
    }
    faculty = {
        name: FacultyInfo(id=uuid.uuid4(), name=name, is_active=True, unavailable_period_ids=frozenset())
        for name in ("F1", "F2")
    }
    rooms = {
        "R1": RoomInfo(id=uuid.uuid4(), name="R1", room_type=RoomType.CLASSROOM,
                       capacity=room_capacity, is_active=True),
        "L1": RoomInfo(id=uuid.uuid4(), name="L1", room_type=RoomType.LAB,
                       capacity=room_capacity, is_active=True),
    }
    periods: dict[str, PeriodSlot] = {}
    order = 0
    for day in days:
        for slot in range(1, slots_per_day + 1):
            order += 1
            key = f"{day}{slot}"
            periods[key] = PeriodSlot(
                id=uuid.uuid4(), day=DayOfWeek[day], order=slot,
                start=time(8 + slot, 0), end=time(9 + slot, 0),
                is_break=False, is_active=True,
            )
    # Wire unavailability now that period ids exist.
    for name, keys in unavailable.items():
        fac = faculty[name]
        faculty[name] = FacultyInfo(
            id=fac.id, name=fac.name, is_active=fac.is_active,
            unavailable_period_ids=frozenset(periods[k].id for k in keys),
        )

    session_id = uuid.uuid4()
    requirements = {}
    for code, per_week, eligible in (
        ("MATH", math_per_week, math_faculty),
        ("LABX", lab_per_week, lab_faculty),
    ):
        if per_week < 1:
            continue
        subject = subjects[code]
        requirements[code] = RequirementInfo(
            id=uuid.uuid4(),
            division_id=div.id,
            subject=subject,
            periods_per_week=per_week,
            preferred_room_type=None,
            requires_lab=False,
            eligible_faculty_ids=tuple(sorted(faculty[n].id for n in eligible)),
        )
    assignments = [
        AssignmentInfo(
            faculty_id=faculty[n].id, subject_id=subjects[code].id,
            division_id=div.id, session_id=session_id, is_active=True,
        )
        for code, names in (("MATH", math_faculty), ("LABX", lab_faculty))
        for n in names
        if code in requirements
    ]
    scope = ScopeData(
        session_id=session_id,
        session_name="TEST",
        divisions={div.id: div},
        periods={p.id: p for p in periods.values()},
        teaching_period_ids=tuple(p.id for p in periods.values()),
        rooms={r.id: r for r in rooms.values()},
        faculty={f.id: f for f in faculty.values()},
        subjects={s.id: s for s in subjects.values()},
        requirements=list(requirements.values()),
        assignments=assignments,
    )
    return Case(
        scope=scope, divisions={"D1": div}, subjects=subjects,
        faculty=faculty, rooms=rooms, periods=periods, requirements=requirements,
    )


def solve_case(case: Case, **kwargs) -> object:
    """Deterministic solve (single worker, fixed seed) for unit tests."""
    options = SolverOptions(
        time_limit_seconds=kwargs.pop("time_limit_seconds", 10.0),
        num_workers=kwargs.pop("num_workers", 1),
        random_seed=kwargs.pop("random_seed", 42),
    )
    return generate_from_scope(case.scope, options, **kwargs)


def spread_score(entries, scope) -> int:
    """Distinct (subject, day) pairs covered — mirrors S1 for assertions."""
    days = {e.subject_id: set() for e in entries}
    for e in entries:
        days[e.subject_id].add(scope.periods[e.period_id].day.value)
    return sum(len(d) for d in days.values())
