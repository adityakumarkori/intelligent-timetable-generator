"""Turns structured conflicts into human-readable explanations.

 Every message cites real configuration data (names, counts, capacities);
 suggestions are deterministic per conflict type (§20 of the spec) and never
 modify academic data — they only advise the administrator.
"""

from app.timetable_engine.models import Conflict, ConflictType


def explain_conflicts(conflicts: list[Conflict]) -> list[Conflict]:
    """Fill message + suggestions on each conflict, in place, and return them."""
    for conflict in conflicts:
        message, suggestions = _explain(conflict)
        conflict.message = message
        conflict.suggestions = suggestions
    return conflicts


def suggest_for(violation_type: ConflictType) -> list[str]:
    """Deterministic resolution suggestions for a validator violation type.

    Unlike explain_conflicts, this never touches messages — validator
    messages already cite the concrete entities involved.
    """
    return list(_VIOLATION_SUGGESTIONS.get(violation_type, _GENERIC_SUGGESTIONS))


_GENERIC_SUGGESTIONS = ["Review the scheduling configuration and try again"]

_VIOLATION_SUGGESTIONS = {
    ConflictType.DIVISION_CONFLICT: [
        "Move the entry to a period where the division is free.",
        "Remove the other entry occupying that period.",
    ],
    ConflictType.FACULTY_CONFLICT: [
        "Assign another eligible faculty member.",
        "Choose another available period.",
    ],
    ConflictType.ROOM_CONFLICT: [
        "Choose another compatible room.",
        "Choose another available period.",
    ],
    ConflictType.FACULTY_UNAVAILABLE: [
        "Change faculty availability for the blocked period.",
        "Assign another eligible faculty member with wider availability.",
    ],
    ConflictType.ROOM_CAPACITY_CONFLICT: [
        "Use a larger compatible room.",
        "Split the division if academically appropriate.",
    ],
    ConflictType.ROOM_CAPACITY: [
        "Use a larger compatible room.",
        "Split the division if academically appropriate.",
    ],
    ConflictType.ROOM_TYPE_CONFLICT: [
        "Choose a room of the required type.",
        "Change the room requirement if academically valid.",
    ],
    ConflictType.ROOM_TYPE: [
        "Choose a room of the required type.",
        "Change the room requirement if academically valid.",
    ],
    ConflictType.INVALID_ASSIGNMENT: [
        "Assign an eligible faculty member via Faculty Assignments.",
        "Reactivate the assignment or faculty account if disabled.",
    ],
    ConflictType.BREAK_PERIOD_USED: [
        "Choose a non-break teaching period.",
    ],
    ConflictType.INACTIVE_ENTITY: [
        "Reactivate the referenced record or choose an active one.",
    ],
    ConflictType.WEEKLY_LOAD_MISMATCH: [
        "Add the missing session(s) to complete the weekly load.",
        "Adjust the subject requirement if the configuration is incorrect.",
    ],
    ConflictType.NO_AVAILABLE_PERIOD: [
        "Increase available scheduling periods.",
        "Change faculty availability.",
    ],
    ConflictType.INVALID_CONFIGURATION: [
        "Configure the missing scheduling data and try again.",
    ],
}


def _explain(conflict: Conflict) -> tuple[str, list[str]]:
    d = conflict.details
    t = conflict.type

    if t == ConflictType.NO_ELIGIBLE_FACULTY:
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            f"{d.get('reason', 'no eligible faculty')}. "
            f"Required: {d.get('sessions_required', '?')} session(s)/week.",
            [
                "Assign an eligible faculty member via Faculty Assignments",
                "Reactivate the existing assignment or faculty account if it was disabled",
                "Reduce the weekly requirement if the configuration is incorrect",
            ],
        )

    if t == ConflictType.ROOM_CAPACITY_CONFLICT:
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            f"division has {d.get('division_size')} students but the largest compatible "
            f"room fits {d.get('largest_type_matching_room', 0)}. "
            f"Required capacity: {d.get('required_capacity')}.",
            [
                f"Provide a compatible room with capacity >= {d.get('required_capacity')}",
                "Split the division if academically appropriate",
                "Correct the room capacity data if it is wrong",
            ],
        )

    if t == ConflictType.NO_ELIGIBLE_ROOM:
        need = "a laboratory" if d.get("requires_lab") else (
            f"a {d.get('required_room_type')} room" if d.get("required_room_type") else "a room"
        )
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            f"no active {need} is available. "
            f"Active rooms by type: {d.get('active_rooms_by_type', {})}.",
            [
                "Add another suitable room of the required type",
                "Reactivate a suitable room if one was disabled",
                "Change the room requirement if academically valid",
            ],
        )

    if t == ConflictType.ROOM_TYPE_CONFLICT:
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            "room type requirements cannot be satisfied.",
            [
                "Add a room of the required type",
                "Change the room requirement if academically valid",
            ],
        )

    if t == ConflictType.FACULTY_AVAILABILITY_CONFLICT:
        faculty = ", ".join(d.get("eligible_faculty", []) or ["(none)"])
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            f"eligible faculty ({faculty}) are unavailable during "
            f"{d.get('periods_blocked_by_availability')} of {d.get('teaching_periods')} "
            "teaching periods.",
            [
                "Change faculty availability for the blocked periods",
                "Assign another eligible faculty member with wider availability",
                "Increase available scheduling periods",
            ],
        )

    if t == ConflictType.NO_AVAILABLE_PERIOD:
        return (
            f"'{conflict.subject}' cannot be scheduled for '{conflict.division}': "
            f"no teachable period fits (checked {d.get('teaching_periods', 0)} periods).",
            [
                "Increase available scheduling periods",
                "Change faculty availability",
                "Reduce the weekly requirement if the configuration is incorrect",
            ],
        )

    if t == ConflictType.INSUFFICIENT_PERIOD_CAPACITY:
        return (
            f"Division '{conflict.division}' needs {d.get('sessions_required')} sessions/week "
            f"but has only {d.get('teaching_periods_available')} teachable periods "
            f"(deficit {d.get('deficit')}).",
            [
                "Add more teaching periods to the week",
                "Reduce weekly requirements if the configuration is incorrect",
                "Move a break period back to a teaching slot if appropriate",
            ],
        )

    if t == ConflictType.RESOURCE_CONTENTION:
        tightest = "; ".join(
            f"{f['faculty']} ({f['sessions_needing']} sessions / {f['periods_available']} periods)"
            for f in d.get("tightest_faculty", [])
        )
        return (
            f"Division(s) '{conflict.division}' cannot all be scheduled together: "
            f"{d.get('sessions_total')} sessions compete for {d.get('teaching_periods')} periods "
            f"({d.get('candidates_total')} legal combinations, "
            f"fewest options for one session: {d.get('min_candidates_per_session')}). "
            f"Tightest faculty: {tightest or '(none)'}.",
            [
                "Add another compatible room to relieve contention",
                "Widen faculty availability on the busiest periods",
                "Assign additional eligible faculty to spread the load",
                "Reduce weekly requirements if the configuration is incorrect",
            ],
        )

    if t == ConflictType.INVALID_CONFIGURATION:
        return (
            f"Cannot generate a timetable: {d.get('reason', 'invalid configuration')}.",
            [
                "Configure active teaching periods",
                "Configure active subject requirements for the scope",
            ],
        )

    return (
        f"Scheduling failed ({t.value}).",
        ["Review the scheduling configuration and try again"],
    )
