"""Expands weekly DivisionSubjectRequirements into individual session instances.

 Mathematics → 5/week becomes Mathematics-1 … Mathematics-5. Sessions are
 immutable, unpersisted, and globally ordered deterministically so solver
 runs are reproducible.
"""

from app.timetable_engine.exceptions import ConfigurationError
from app.timetable_engine.models import ScopeData, SessionSlot


def build_sessions(scope: ScopeData) -> list[SessionSlot]:
    """Expand every requirement into its weekly session instances."""
    ordered = sorted(
        scope.requirements,
        key=lambda r: (
            scope.divisions[r.division_id].code,
            r.subject.code,
            str(r.id),
        ),
    )
    sessions: list[SessionSlot] = []
    for req in ordered:
        if req.periods_per_week < 1:
            raise ConfigurationError(
                f"Requirement for '{req.subject.code}' has invalid weekly load "
                f"({req.periods_per_week}); must be at least 1"
            )
        division = scope.divisions[req.division_id]
        for number in range(1, req.periods_per_week + 1):
            sessions.append(
                SessionSlot(
                    index=len(sessions),
                    requirement_id=req.id,
                    division_id=req.division_id,
                    subject_id=req.subject.id,
                    subject_code=req.subject.code,
                    session_number=number,
                    sessions_total=req.periods_per_week,
                    eligible_faculty_ids=req.eligible_faculty_ids,
                    required_capacity=division.student_count,
                    required_room_type=(
                        req.preferred_room_type
                        if req.preferred_room_type is not None
                        else req.subject.required_room_type
                    ),
                    requires_lab=req.requires_lab or req.subject.requires_lab,
                )
            )
    if not sessions:
        raise ConfigurationError("No schedulable sessions: requirement list is empty")
    return sessions
