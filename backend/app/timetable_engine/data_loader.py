"""Loads the generation scope from PostgreSQL into plain engine structures.

 Runs once per generation, before solving. Inactive master rows are loaded
 with their flags (the validator needs them); only active rows participate
 in candidate generation (H10).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AcademicSession,
    Division,
    DivisionSubjectRequirement,
    Faculty,
    FacultyAssignment,
    FacultyAvailability,
    Period,
    Room,
    Subject,
)
from app.models.enums import AvailabilityStatus
from app.timetable_engine.exceptions import ConfigurationError
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

_DAY_ORDER = {
    day: index
    for index, day in enumerate(
        ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    )
}


async def load_scope_data(
    db: AsyncSession, session_id: UUID, division_ids: list[UUID]
) -> ScopeData:
    """Load one academic session plus the requested divisions and all related config."""
    session = await db.get(AcademicSession, session_id)
    if session is None:
        raise ConfigurationError(f"Academic session '{session_id}' does not exist")
    if not session.is_active:
        raise ConfigurationError(
            f"Academic session '{session.name}' is inactive; "
            "activate it before generating timetables"
        )

    divisions: dict[UUID, DivisionInfo] = {}
    for division_id in division_ids:
        division = await db.get(Division, division_id)
        if division is None:
            raise ConfigurationError(f"Division '{division_id}' does not exist")
        if not division.is_active:
            raise ConfigurationError(
                f"Division '{division.code}' is inactive; "
                "activate it before generating timetables"
            )
        divisions[division.id] = DivisionInfo(
            id=division.id,
            code=division.code,
            student_count=division.student_count,
            is_active=division.is_active,
        )
    if not divisions:
        raise ConfigurationError("Generation scope must include at least one division")

    subjects = {
        s.id: SubjectInfo(
            id=s.id,
            code=s.code,
            name=s.name,
            required_room_type=s.required_room_type,
            requires_lab=s.requires_lab,
            is_active=s.is_active,
        )
        for s in (await db.scalars(select(Subject))).all()
    }

    rooms = {
        r.id: RoomInfo(
            id=r.id, name=r.name, room_type=r.room_type,
            capacity=r.capacity, is_active=r.is_active,
        )
        for r in (await db.scalars(select(Room))).all()
    }

    faculty_rows = (await db.scalars(select(Faculty))).all()
    unavailable: dict[UUID, set[UUID]] = {f.id: set() for f in faculty_rows}
    for row in (
        await db.scalars(
            select(FacultyAvailability).where(
                FacultyAvailability.status == AvailabilityStatus.UNAVAILABLE
            )
        )
    ).all():
        unavailable.setdefault(row.faculty_id, set()).add(row.period_id)
    faculty = {
        f.id: FacultyInfo(
            id=f.id,
            name=f.name,
            is_active=f.is_active,
            unavailable_period_ids=frozenset(unavailable.get(f.id, ())),
        )
        for f in faculty_rows
    }

    periods = {
        p.id: PeriodSlot(
            id=p.id,
            day=p.day_of_week,
            order=p.period_order,
            start=p.start_time,
            end=p.end_time,
            is_break=p.is_break,
            is_active=p.is_active,
        )
        for p in (await db.scalars(select(Period))).all()
    }
    teaching_period_ids = tuple(
        sorted(
            (pid for pid, p in periods.items() if p.teachable),
            key=lambda pid: (_DAY_ORDER[periods[pid].day.value], periods[pid].order),
        )
    )

    assignment_rows = (
        await db.scalars(
            select(FacultyAssignment).where(
                FacultyAssignment.academic_session_id == session.id,
                FacultyAssignment.division_id.in_(list(divisions)),
            )
        )
    ).all()
    assignments = [
        AssignmentInfo(
            faculty_id=a.faculty_id,
            subject_id=a.subject_id,
            division_id=a.division_id,
            session_id=a.academic_session_id,
            is_active=a.is_active,
        )
        for a in assignment_rows
    ]
    eligible: dict[tuple[UUID, UUID], set[UUID]] = {}
    for a in assignment_rows:
        if not a.is_active:
            continue
        fac = faculty.get(a.faculty_id)
        if fac is None or not fac.is_active:
            continue
        eligible.setdefault((a.division_id, a.subject_id), set()).add(a.faculty_id)

    requirements: list[RequirementInfo] = []
    warnings: list[str] = []
    req_rows = (
        await db.scalars(
            select(DivisionSubjectRequirement).where(
                DivisionSubjectRequirement.academic_session_id == session.id,
                DivisionSubjectRequirement.division_id.in_(list(divisions)),
                DivisionSubjectRequirement.is_active == True,  # noqa: E712
            )
        )
    ).all()
    for req in req_rows:
        subject = subjects.get(req.subject_id)
        if subject is None:
            warnings.append(
                f"Requirement for unknown subject '{req.subject_id}' skipped"
            )
            continue
        if not subject.is_active:
            warnings.append(
                f"Requirement for inactive subject '{subject.code}' skipped"
            )
            continue
        requirements.append(
            RequirementInfo(
                id=req.id,
                division_id=req.division_id,
                subject=subject,
                periods_per_week=req.required_periods_per_week,
                preferred_room_type=req.preferred_room_type,
                requires_lab=req.requires_lab,
                eligible_faculty_ids=tuple(
                    sorted(eligible.get((req.division_id, req.subject_id), ()))
                ),
            )
        )

    if not requirements:
        raise ConfigurationError(
            "No active subject requirements found for this session/division scope; "
            "configure DivisionSubjectRequirements before generating"
        )

    return ScopeData(
        session_id=session.id,
        session_name=session.name,
        divisions=divisions,
        periods=periods,
        teaching_period_ids=teaching_period_ids,
        rooms=rooms,
        faculty=faculty,
        subjects=subjects,
        requirements=requirements,
        assignments=assignments,
        warnings=warnings,
    )
