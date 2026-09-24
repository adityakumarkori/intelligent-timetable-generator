"""Domain-level infeasibility diagnosis.

 CP-SAT's INFEASIBLE verdict says *that* no schedule exists, never *why*.
 This module answers why using only real configuration data:
 rejection tallies from candidate building, plus load analysis when every
 session has candidates but they still cannot coexist. It never claims a
 proven minimal conflict set — only the dominant, evidenced blockers.
"""

from collections import Counter
from uuid import UUID

from app.timetable_engine.candidate_builder import CandidateBuild
from app.timetable_engine.models import (
    Conflict,
    ConflictSeverity,
    ConflictType,
    ScopeData,
    SessionSlot,
)


def _base(
    type_: ConflictType,
    subject: str | None = None,
    division: str | None = None,
    **details,
) -> Conflict:
    return Conflict(
        type=type_,
        severity=ConflictSeverity.ERROR,
        message="",
        subject=subject,
        division=division,
        details=details,
    )


def detect_pre_solve_conflicts(
    scope: ScopeData, sessions: list[SessionSlot], build: CandidateBuild
) -> list[Conflict]:
    """Conflicts provable without solving (missing pieces, zero candidates)."""
    conflicts: list[Conflict] = []

    if not scope.teaching_period_ids:
        conflicts.append(
            _base(
                ConflictType.INVALID_CONFIGURATION,
                message="",
                reason="no active, non-break periods exist",
            )
        )
        return conflicts

    # INSUFFICIENT_PERIOD_CAPACITY per division (H2 pigeonhole, exact).
    sessions_by_division: dict[UUID, int] = Counter(s.division_id for s in sessions)
    for division_id, count in sessions_by_division.items():
        slots = len(scope.teaching_period_ids)
        if count > slots:
            division = scope.divisions[division_id]
            conflicts.append(
                _base(
                    ConflictType.INSUFFICIENT_PERIOD_CAPACITY,
                    division=division.code,
                    sessions_required=count,
                    teaching_periods_available=slots,
                    deficit=count - slots,
                )
            )

    covered = {c.session_index for c in build.candidates}
    for session in sessions:
        if session.index in covered:
            continue
        conflicts.append(_diagnose_empty_session(scope, session, build))

    return conflicts


def _diagnose_empty_session(
    scope: ScopeData, session: SessionSlot, build: CandidateBuild
) -> Conflict:
    division = scope.divisions[session.division_id]
    tally = build.rejections.get(session.index, Counter())
    subject_code = session.subject_code

    if tally.get("NO_FACULTY"):
        rows = [
            a for a in scope.assignments
            if a.division_id == session.division_id and a.subject_id == session.subject_id
        ]
        active_rows = sum(
            1 for a in rows
            if a.is_active and scope.faculty.get(a.faculty_id) is not None
            and scope.faculty[a.faculty_id].is_active
        )
        return _base(
            ConflictType.NO_ELIGIBLE_FACULTY,
            subject=subject_code,
            division=division.code,
            sessions_required=session.sessions_total,
            assignment_rows_total=len(rows),
            assignment_rows_active=active_rows,
            reason=(
                "no faculty assignment exists at all"
                if not rows
                else "assignments exist but none is active / faculty inactive"
            ),
        )

    if tally.get("ROOM_CAPACITY", 0) >= tally.get("ROOM_TYPE", 0) and tally.get("ROOM_CAPACITY", 0) > 0:
        type_counts = Counter(
            r.room_type.value for r in scope.rooms.values() if r.is_active
        )
        fitting_type = [
            r.capacity for r in scope.rooms.values()
            if r.is_active
            and (not session.requires_lab or r.room_type.value == "LAB")
            and (session.required_room_type is None or r.room_type == session.required_room_type)
        ]
        return _base(
            ConflictType.ROOM_CAPACITY_CONFLICT,
            subject=subject_code,
            division=division.code,
            required_capacity=session.required_capacity,
            division_size=division.student_count,
            largest_type_matching_room=max(fitting_type) if fitting_type else 0,
            active_rooms_by_type=dict(type_counts),
        )

    if tally.get("ROOM_TYPE", 0) > 0:
        type_counts = Counter(
            r.room_type.value for r in scope.rooms.values() if r.is_active
        )
        return _base(
            ConflictType.NO_ELIGIBLE_ROOM,
            subject=subject_code,
            division=division.code,
            required_room_type=(
                session.required_room_type.value if session.required_room_type else None
            ),
            requires_lab=session.requires_lab,
            active_rooms_by_type=dict(type_counts),
        )

    if tally.get("UNAVAILABLE", 0) > 0:
        faculty_names = sorted(
            scope.faculty[fid].name
            for fid in session.eligible_faculty_ids
            if fid in scope.faculty
        )
        return _base(
            ConflictType.FACULTY_AVAILABILITY_CONFLICT,
            subject=subject_code,
            division=division.code,
            eligible_faculty=faculty_names,
            teaching_periods=len(scope.teaching_period_ids),
            periods_blocked_by_availability=int(tally.get("UNAVAILABLE", 0)),
        )

    return _base(
        ConflictType.NO_AVAILABLE_PERIOD,
        subject=subject_code,
        division=division.code,
        teaching_periods=len(scope.teaching_period_ids),
    )


def detect_contention_conflicts(
    scope: ScopeData, sessions: list[SessionSlot], build: CandidateBuild
) -> list[Conflict]:
    """Fallback when the solver proves infeasibility but every session has options.

    Reports evidenced load hotspots — the faculty, rooms, and periods under
    the most pressure — without claiming a minimal conflict set.
    """
    # Per-session candidate counts (tightness).
    per_session: Counter = Counter(c.session_index for c in build.candidates)
    counts = [per_session.get(s.index, 0) for s in sessions]

    # Period demand: sessions placeable in each period.
    period_sessions: dict[str, set[int]] = {}
    for c in build.candidates:
        period_sessions.setdefault(str(c.period_id), set()).add(c.session_index)
    period_labels = {
        str(pid): f"{scope.periods[pid].day.value} #{scope.periods[pid].order}"
        for pid in scope.teaching_period_ids
    }
    top_periods = sorted(
        (
            {"period": period_labels.get(pid, pid), "sessions_needing": len(s)}
            for pid, s in period_sessions.items()
        ),
        key=lambda d: d["sessions_needing"],
        reverse=True,
    )[:3]

    # Faculty pressure: sessions needing them vs periods they can teach.
    faculty_load = []
    for fid, fac in sorted(scope.faculty.items(), key=lambda kv: kv[1].name):
        if not fac.is_active:
            continue
        needing = sum(1 for s in sessions if fid in s.eligible_faculty_ids)
        if not needing:
            continue
        available = sum(
            1 for pid in scope.teaching_period_ids if pid not in fac.unavailable_period_ids
        )
        faculty_load.append(
            {
                "faculty": fac.name,
                "sessions_needing": needing,
                "periods_available": available,
            }
        )
    faculty_load.sort(
        key=lambda d: (d["sessions_needing"] / max(d["periods_available"], 1)),
        reverse=True,
    )

    # Room pressure: sessions that fit vs usable periods.
    room_load = []
    for rid, room in sorted(scope.rooms.items(), key=lambda kv: kv[1].name):
        if not room.is_active:
            continue
        fitting = sum(
            1
            for s in sessions
            if room.capacity >= s.required_capacity
            and (not s.requires_lab or room.room_type.value == "LAB")
            and (s.required_room_type is None or room.room_type == s.required_room_type)
        )
        if fitting:
            room_load.append(
                {
                    "room": room.name,
                    "sessions_fitting": fitting,
                    "periods_usable": len(scope.teaching_period_ids),
                }
            )
    room_load.sort(key=lambda d: d["sessions_fitting"], reverse=True)

    return [
        _base(
            ConflictType.RESOURCE_CONTENTION,
            division=", ".join(sorted(d.code for d in scope.divisions.values())),
            sessions_total=len(sessions),
            teaching_periods=len(scope.teaching_period_ids),
            candidates_total=len(build.candidates),
            min_candidates_per_session=min(counts) if counts else 0,
            avg_candidates_per_session=(
                round(sum(counts) / len(counts), 1) if counts else 0
            ),
            top_periods=top_periods,
            tightest_faculty=faculty_load[:3],
            tightest_rooms=room_load[:3],
        )
    ]


def tight_session_warnings(
    sessions: list[SessionSlot], build: CandidateBuild, limit: int = 2
) -> list[str]:
    """Human warnings for sessions with very few options (non-blocking)."""
    per_session: Counter = Counter(c.session_index for c in build.candidates)
    warnings = []
    for session in sessions:
        count = per_session.get(session.index, 0)
        if 0 < count <= limit:
            warnings.append(
                f"'{session.subject_code}' session #{session.session_number} "
                f"has only {count} candidate assignment(s)"
            )
    return warnings
