"""Maps raw solver decisions back to timetable entries."""

from app.timetable_engine.constraints import VarKey
from app.timetable_engine.exceptions import MappingError
from app.timetable_engine.models import Candidate, GeneratedEntry, SessionSlot


def map_solution(
    sessions: list[SessionSlot],
    candidates: list[Candidate],
    values: dict[VarKey, bool],
) -> list[GeneratedEntry]:
    """Translate selected x(s,p,f,r) variables into entries.

    Raises MappingError if any session is not assigned exactly once — a
    solver/model bug must never become a silently partial timetable.
    """
    by_session: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        key = (
            str(candidate.session_index),
            str(candidate.period_id),
            str(candidate.faculty_id),
            str(candidate.room_id),
        )
        if values.get(key):
            by_session.setdefault(candidate.session_index, []).append(candidate)

    session_of = {s.index: s for s in sessions}
    entries: list[GeneratedEntry] = []
    for session in sessions:
        chosen = by_session.get(session.index, [])
        if len(chosen) != 1:
            raise MappingError(
                f"Session {session.subject_code} #{session.session_number} mapped to "
                f"{len(chosen)} assignments (expected exactly 1)"
            )
        candidate = chosen[0]
        entries.append(
            GeneratedEntry(
                session_index=session.index,
                division_id=session.division_id,
                subject_id=session.subject_id,
                period_id=candidate.period_id,
                faculty_id=candidate.faculty_id,
                room_id=candidate.room_id,
            )
        )
    entries.sort(key=lambda e: e.session_index)
    return entries
