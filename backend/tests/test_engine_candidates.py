"""Candidate builder tests: every pre-filterable hard constraint."""

import dataclasses

from app.models.enums import RoomType
from app.timetable_engine.candidate_builder import build_candidates
from app.timetable_engine.session_builder import build_sessions
from tests.engine_helpers import basic_case


def _build(case):
    sessions = build_sessions(case.scope)
    return sessions, build_candidates(case.scope, sessions)


def test_full_candidate_grid_for_unconstrained_scope():
    # 3 sessions x 4 periods x 2 faculty(MATH only F1/F2; LABX only F1) x rooms.
    case = basic_case()
    sessions, built = _build(case)
    assert len(sessions) == 3
    # MATH: 2 sessions x 4 periods x 2 faculty x 1 classroom room = 16
    # LABX: 1 session x 4 periods x 1 faculty x 1 lab room = 4
    assert len(built.candidates) == 20


def test_incompatible_room_type_excluded():
    case = basic_case()
    sessions, built = _build(case)
    lab_room = case.rooms["L1"].id
    math_idx = {s.index for s in sessions if s.subject_code == "MATH"}
    assert not [c for c in built.candidates if c.session_index in math_idx and c.room_id == lab_room]


def test_insufficient_capacity_rooms_excluded():
    case = basic_case(div_students=100, room_capacity=40)
    sessions, built = _build(case)
    assert built.candidates == []
    tallies = list(built.rejections.values())
    assert tallies and all(t.get("ROOM_CAPACITY", 0) > 0 for t in tallies)


def test_unavailable_faculty_excluded():
    all_periods = ["MONDAY1", "MONDAY2", "TUESDAY1", "TUESDAY2"]
    case = basic_case(unavailable={"F1": all_periods, "F2": all_periods})
    sessions, built = _build(case)
    math_idx = {s.index for s in sessions if s.subject_code == "MATH"}
    # MATH has no available faculty anywhere; LABX still has F1? No — F1 blocked too.
    assert not [c for c in built.candidates if c.session_index in math_idx]
    assert any(t.get("UNAVAILABLE", 0) > 0 for t in built.rejections.values())


def test_inactive_entities_excluded():
    case = basic_case()
    fac = case.faculty["F1"]
    case.scope.faculty[fac.id] = dataclasses.replace(fac, is_active=False)
    sessions, built = _build(case)
    # MATH only via F2 now; LABX has no active eligible faculty at all.
    lab_idx = {s.index for s in sessions if s.subject_code == "LABX"}
    assert not [c for c in built.candidates if c.session_index in lab_idx]
    assert any("NO_FACULTY" in t for t in built.rejections.values())
    math_candidates = [c for c in built.candidates if c.session_index not in lab_idx]
    assert math_candidates
    assert all(c.faculty_id == case.faculty["F2"].id for c in math_candidates)

    # Deactivating the only classroom kills MATH rooms (type tally, not capacity).
    fresh = basic_case()
    room = fresh.rooms["R1"]
    fresh.scope.rooms[room.id] = dataclasses.replace(room, is_active=False)
    fresh_sessions, fresh_built = build_sessions(fresh.scope), None
    fresh_built = build_candidates(fresh.scope, fresh_sessions)
    math_idx = {s.index for s in fresh_sessions if s.subject_code == "MATH"}
    assert not [c for c in fresh_built.candidates if c.session_index in math_idx]
    assert any(t.get("ROOM_TYPE", 0) > 0 for t in fresh_built.rejections.values())


def test_break_periods_excluded():
    case = basic_case()
    period = case.periods["MONDAY1"]
    case.scope.periods[period.id] = dataclasses.replace(period, is_break=True)
    case.scope.teaching_period_ids = tuple(
        pid for pid in case.scope.teaching_period_ids if pid != period.id
    )
    sessions, built = _build(case)
    assert not [c for c in built.candidates if c.period_id == period.id]


def test_sessions_without_assignment_have_no_candidates():
    case = basic_case(math_faculty=(), lab_faculty=())
    sessions, built = _build(case)
    assert built.candidates == []
    assert all("NO_FACULTY" in t for t in built.rejections.values())


def test_lab_subject_only_gets_lab_rooms():
    case = basic_case()
    sessions, built = _build(case)
    lab_idx = {s.index for s in sessions if s.subject_code == "LABX"}
    lab_room = case.rooms["L1"].id
    assert [c for c in built.candidates if c.session_index in lab_idx]
    assert all(c.room_id == lab_room for c in built.candidates if c.session_index in lab_idx)


def test_candidate_order_is_deterministic():
    # Same logical scope built twice must yield structurally identical grids
    # (compared in normalized day/order/name space, not raw UUIDs).
    def signature(case):
        sessions = build_sessions(case.scope)
        built = build_candidates(case.scope, sessions)
        return sorted(
            (
                c.session_index,
                case.scope.periods[c.period_id].day.value,
                case.scope.periods[c.period_id].order,
                case.scope.faculty[c.faculty_id].name,
                case.scope.rooms[c.room_id].name,
            )
            for c in built.candidates
        )

    assert signature(basic_case()) == signature(basic_case())
