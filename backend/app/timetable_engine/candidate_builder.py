"""Builds the legal (session, period, faculty, room) candidate combinations.

 Pre-filtered here (structurally excluded from the CP-SAT model):
 H5 availability, H6 capacity, H7 room type/lab, H8 assignment eligibility,
 H9 break periods, H10 inactive entities. H1–H4 become solver constraints;
 H11 follows from session expansion + H1. The independent validator
 re-checks every one of these against the final timetable.
"""

from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from app.models.enums import RoomType
from app.timetable_engine.models import Candidate, ScopeData, SessionSlot


@dataclass
class CandidateBuild:
    candidates: list[Candidate]
    # session index -> {reason: eliminated-combination count}, for conflict analysis.
    rejections: dict[int, Counter] = field(default_factory=dict)
    # session index -> number of teaching periods with at least one available faculty.
    periods_with_faculty: dict[int, int] = field(default_factory=dict)


def _room_ok(room_type: RoomType, capacity: int, session: SessionSlot) -> bool:
    if capacity < session.required_capacity:
        return False
    if session.requires_lab:
        return room_type == RoomType.LAB
    if session.required_room_type is not None:
        return room_type == session.required_room_type
    return True


def build_candidates(
    scope: ScopeData, sessions: list[SessionSlot]
) -> CandidateBuild:
    """Enumerate every legal combination, in deterministic order."""
    build = CandidateBuild(candidates=[])
    active_rooms = sorted(
        (r for r in scope.rooms.values() if r.is_active),
        key=lambda r: (r.name, str(r.id)),
    )

    for session in sessions:
        tally: Counter = Counter()
        faculty = sorted(
            (
                scope.faculty[fid]
                for fid in session.eligible_faculty_ids
                if fid in scope.faculty and scope.faculty[fid].is_active
            ),
            key=lambda f: (f.name, str(f.id)),
        )
        if not faculty:
            tally["NO_FACULTY"] += 1
            build.rejections[session.index] = tally
            build.periods_with_faculty[session.index] = 0
            continue

        rooms = [r for r in active_rooms if _room_ok(r.room_type, r.capacity, session)]
        if not rooms:
            # Record WHY rooms were eliminated, for precise conflict messages.
            for room in active_rooms:
                if room.capacity < session.required_capacity:
                    tally["ROOM_CAPACITY"] += 1
                else:
                    tally["ROOM_TYPE"] += 1
            build.rejections[session.index] = tally
            build.periods_with_faculty[session.index] = 0
            continue

        periods_with_faculty = 0
        session_candidates: list[Candidate] = []
        for period_id in scope.teaching_period_ids:
            available = [f for f in faculty if period_id not in f.unavailable_period_ids]
            if not available:
                tally["UNAVAILABLE"] += 1
                continue
            periods_with_faculty += 1
            for fac in available:
                for room in rooms:
                    session_candidates.append(
                        Candidate(
                            session_index=session.index,
                            period_id=period_id,
                            faculty_id=fac.id,
                            room_id=room.id,
                        )
                    )
        if session_candidates:
            build.candidates.extend(session_candidates)
        else:
            # Faculty and rooms each exist, but never together in one period.
            build.rejections[session.index] = tally
        build.periods_with_faculty[session.index] = periods_with_faculty

    # Deterministic global order regardless of construction path.
    build.candidates.sort(
        key=lambda c: (c.session_index, str(c.period_id), str(c.faculty_id), str(c.room_id))
    )
    return build


def eligible_room_ids(scope: ScopeData, session: SessionSlot) -> list[UUID]:
    """Rooms passing H6/H7/H10 for one session (used by diagnostics/tests)."""
    return [
        r.id
        for r in scope.rooms.values()
        if r.is_active and _room_ok(r.room_type, r.capacity, session)
    ]
