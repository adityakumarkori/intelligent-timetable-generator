"""Session builder tests: expansion counts, ordering, effective rules."""

import pytest

from app.timetable_engine.exceptions import ConfigurationError
from app.timetable_engine.session_builder import build_sessions
from tests.engine_helpers import basic_case


def test_five_periods_become_five_sessions():
    case = basic_case(math_per_week=5, lab_per_week=0)
    sessions = build_sessions(case.scope)
    assert len(sessions) == 5
    assert [s.session_number for s in sessions] == [1, 2, 3, 4, 5]
    assert all(s.sessions_total == 5 for s in sessions)
    assert all(s.subject_code == "MATH" for s in sessions)


def test_two_periods_become_two_sessions():
    case = basic_case(math_per_week=2, lab_per_week=2)
    sessions = build_sessions(case.scope)
    assert len(sessions) == 4
    math = [s for s in sessions if s.subject_code == "MATH"]
    lab = [s for s in sessions if s.subject_code == "LABX"]
    assert len(math) == 2 and len(lab) == 2


def test_sessions_carry_scheduling_context():
    case = basic_case()
    sessions = build_sessions(case.scope)
    math = next(s for s in sessions if s.subject_code == "MATH")
    lab = next(s for s in sessions if s.subject_code == "LABX")
    assert math.required_capacity == 30
    assert math.required_room_type.value == "CLASSROOM"
    assert math.requires_lab is False
    assert lab.requires_lab is True
    assert lab.required_room_type.value == "LAB"
    assert len(math.eligible_faculty_ids) == 2
    assert len(lab.eligible_faculty_ids) == 1


def test_requirement_override_wins_over_subject():
    import dataclasses

    from app.models.enums import RoomType

    case = basic_case()
    req = case.requirements["MATH"]
    overridden = dataclasses.replace(req, preferred_room_type=RoomType.SEMINAR_ROOM)
    case.scope.requirements[:] = [
        overridden if r.subject.code == "MATH" else r for r in case.scope.requirements
    ]
    sessions = build_sessions(case.scope)
    math = next(s for s in sessions if s.subject_code == "MATH")
    assert math.required_room_type == RoomType.SEMINAR_ROOM


def test_global_session_order_is_deterministic():
    first = [s.index for s in build_sessions(basic_case().scope)]
    second = [s.index for s in build_sessions(basic_case().scope)]
    assert first == second == [0, 1, 2]


def test_invalid_weekly_load_rejected():
    import dataclasses

    case = basic_case()
    req = case.requirements["MATH"]
    broken = dataclasses.replace(req, periods_per_week=0)
    case.scope.requirements[:] = [
        broken if r.subject.code == "MATH" else r for r in case.scope.requirements
    ]
    with pytest.raises(ConfigurationError):
        build_sessions(case.scope)
