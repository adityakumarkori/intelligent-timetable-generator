"""Development seed — explicit command only, never runs on startup.

Usage (from backend/):
    python -m app.seed

Seeds 1 department, 2 divisions, 7 subjects, 4 faculty (+ users), 4 rooms,
Mon–Fri x 7 periods, sample availability, requirements, and assignments —
enough to exercise timetable generation in Phase 5. Idempotent: exits early
if the CS department already exists.
"""

import asyncio
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
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
    User,
)
from app.models.enums import (
    AvailabilityStatus,
    DayOfWeek,
    RoomType,
    SubjectType,
    UserRole,
)

# Dev-only login password for every seeded user (Argon2id-hashed at insert).
DEV_PASSWORD = "college123"

PERIOD_TEMPLATE = [
    # (order, start, end, is_break)
    (1, time(9, 0), time(10, 0), False),
    (2, time(10, 0), time(11, 0), False),
    (3, time(11, 15), time(12, 15), False),
    (4, time(12, 15), time(13, 15), True),
    (5, time(13, 15), time(14, 15), False),
    (6, time(14, 15), time(15, 15), False),
    (7, time(15, 15), time(16, 15), False),
]

SUBJECTS = [
    # (code, name, type, periods/week, room type, requires_lab)
    ("MATH201", "Mathematics", SubjectType.LECTURE, 5, RoomType.CLASSROOM, False),
    ("CS201", "Database Management Systems", SubjectType.LECTURE, 4, RoomType.CLASSROOM, False),
    ("CS202", "Operating Systems", SubjectType.LECTURE, 4, RoomType.CLASSROOM, False),
    ("PH101", "Physics", SubjectType.LECTURE, 3, RoomType.CLASSROOM, False),
    ("PH102L", "Physics Lab", SubjectType.LAB, 2, RoomType.LAB, True),
    ("CS203L", "Programming Lab", SubjectType.PRACTICAL, 2, RoomType.LAB, True),
    ("EN101", "English", SubjectType.LECTURE, 3, RoomType.CLASSROOM, False),
]


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await _backfill_password_hashes(session)
        existing = await session.scalar(select(Department).where(Department.code == "CS"))
        if existing is not None:
            print("Seed already applied (department CS exists) — nothing to do.")
            return

        dev_hash = hash_password(DEV_PASSWORD)
        admin = User(name="Admin", email="admin@college.edu", password_hash=dev_hash, role=UserRole.ADMIN)
        session.add(admin)
        faculty_users = [
            User(name=n, email=e, password_hash=dev_hash, role=UserRole.FACULTY)
            for n, e in [
                ("Alice Sharma", "alice@college.edu"),
                ("Bob Patil", "bob@college.edu"),
                ("Carol D'Souza", "carol@college.edu"),
                ("Dave Kumar", "dave@college.edu"),
            ]
        ]
        session.add_all(faculty_users)

        dept = Department(name="Computer Science", code="CS")
        session.add(dept)
        await session.flush()

        div_a = Division(department_id=dept.id, name="CSE-A", code="CSE-A", student_count=68)
        div_b = Division(department_id=dept.id, name="CSE-B", code="CSE-B", student_count=71)
        session.add_all([div_a, div_b])

        academic_session = AcademicSession(
            name="2026-27", start_date=date(2026, 7, 1), end_date=date(2027, 5, 31)
        )
        session.add(academic_session)

        subjects = [
            Subject(
                code=code, name=name, subject_type=stype,
                required_periods_per_week=ppw, required_room_type=rtype, requires_lab=lab,
            )
            for code, name, stype, ppw, rtype, lab in SUBJECTS
        ]
        session.add_all(subjects)

        faculty = [
            Faculty(user_id=faculty_users[0].id, employee_code="EMP001", department_id=dept.id, name="Alice Sharma"),
            Faculty(user_id=faculty_users[1].id, employee_code="EMP002", department_id=dept.id, name="Bob Patil"),
            Faculty(user_id=faculty_users[2].id, employee_code="EMP003", department_id=dept.id, name="Carol D'Souza"),
            Faculty(user_id=faculty_users[3].id, employee_code="EMP004", department_id=dept.id, name="Dave Kumar"),
        ]
        session.add_all(faculty)

        rooms = [
            Room(name="R-101", room_type=RoomType.CLASSROOM, capacity=80, building="Main Block"),
            Room(name="R-102", room_type=RoomType.CLASSROOM, capacity=75, building="Main Block"),
            # LAB-1 must fit both divisions (68/71 students) or lab sessions can
            # never satisfy the room-capacity hard constraint (Phase 5).
            Room(name="LAB-1", room_type=RoomType.LAB, capacity=75, building="Lab Block"),
            Room(name="S-201", room_type=RoomType.SEMINAR_ROOM, capacity=150, building="Main Block"),
        ]
        session.add_all(rooms)

        periods: list[Period] = []
        for day in (DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY):
            for order, start, end, is_break in PERIOD_TEMPLATE:
                periods.append(
                    Period(day_of_week=day, start_time=start, end_time=end, period_order=order, is_break=is_break)
                )
        session.add_all(periods)
        await session.flush()

        by_code = {s.code: s for s in subjects}
        for division in (div_a, div_b):
            for code, _name, _stype, ppw, rtype, lab in SUBJECTS:
                session.add(
                    DivisionSubjectRequirement(
                        division_id=division.id,
                        subject_id=by_code[code].id,
                        academic_session_id=academic_session.id,
                        required_periods_per_week=ppw,
                        preferred_room_type=rtype,
                        requires_lab=lab,
                    )
                )

        # (faculty_index, subject_code, division) — every requirement has coverage.
        assignment_plan = [
            (0, "MATH201", div_a), (0, "MATH201", div_b),
            (1, "CS201", div_a), (1, "CS201", div_b),
            (1, "CS202", div_a), (2, "CS202", div_b),
            (3, "PH101", div_a), (3, "PH101", div_b),
            (2, "PH102L", div_a), (2, "PH102L", div_b),
            (3, "CS203L", div_a), (3, "CS203L", div_b),
            (3, "EN101", div_a), (3, "EN101", div_b),
        ]
        for fac_idx, code, division in assignment_plan:
            session.add(
                FacultyAssignment(
                    faculty_id=faculty[fac_idx].id,
                    subject_id=by_code[code].id,
                    division_id=division.id,
                    academic_session_id=academic_session.id,
                )
            )

        monday_p1 = next(p for p in periods if p.day_of_week == DayOfWeek.MONDAY and p.period_order == 1)
        friday_p6 = next(p for p in periods if p.day_of_week == DayOfWeek.FRIDAY and p.period_order == 6)
        session.add_all(
            [
                FacultyAvailability(faculty_id=faculty[0].id, period_id=monday_p1.id, status=AvailabilityStatus.UNAVAILABLE),
                FacultyAvailability(faculty_id=faculty[1].id, period_id=friday_p6.id, status=AvailabilityStatus.UNAVAILABLE),
            ]
        )

        await session.commit()
        print("Seeded: 1 department, 2 divisions, 7 subjects, 4 faculty, 4 rooms, "
              f"{len(periods)} periods, requirements, assignments, availability.")
        print(f"Dev login password for all seeded users: {DEV_PASSWORD}")


async def _backfill_password_hashes(session) -> None:
    """One-time repair for databases seeded before Phase 3: any user whose
    stored value is not an Argon2 hash gets the dev password hash."""
    users = (await session.scalars(select(User))).all()
    fixed = 0
    for user in users:
        if not user.password_hash.startswith("$argon2"):
            user.password_hash = hash_password(DEV_PASSWORD)
            fixed += 1
    if fixed:
        await session.commit()
        print(f"Re-hashed passwords for {fixed} pre-Phase-3 user(s).")


if __name__ == "__main__":
    asyncio.run(main())
