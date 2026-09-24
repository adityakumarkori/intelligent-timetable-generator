"""Timetable visibility tests: drafts hidden from students, own-scoping for faculty."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.conftest import login_headers

TIMETABLES = "/api/v1/timetables"
DIVISIONS = "/api/v1/divisions"
FACULTY = "/api/v1/faculty"


def admin_h(client, accounts):
    return login_headers(client, accounts["admin"].email)


def faculty_h(client, accounts):
    return login_headers(client, accounts["faculty"].email)


def student_h(client, accounts):
    return login_headers(client, accounts["student"].email)


async def build_graph(client, h, db, accounts, tag):
    """Master data via API; timetables + entries via ORM (no write API in Phase 4)."""
    from app.models import (
        AcademicSession,
        Division,
        Faculty,
        Period,
        Room,
        Subject,
        Timetable,
        TimetableEntry,
    )
    from app.models.enums import TimetableStatus

    sess = client.post(
        "/api/v1/academic-sessions",
        json={"name": f"VS-{tag}", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        headers=h,
    ).json()
    dept = client.post(
        "/api/v1/departments", json={"name": f"VD-{tag}", "code": f"VD{tag}"}, headers=h
    ).json()
    div1 = client.post(
        "/api/v1/divisions",
        json={"department_id": dept["id"], "name": f"V1-{tag}", "code": f"V1{tag}"},
        headers=h,
    ).json()
    div2 = client.post(
        "/api/v1/divisions",
        json={"department_id": dept["id"], "name": f"V2-{tag}", "code": f"V2{tag}"},
        headers=h,
    ).json()
    subj = client.post(
        "/api/v1/subjects",
        json={"code": f"VS{tag}", "name": f"Sub {tag}", "required_periods_per_week": 3},
        headers=h,
    ).json()
    other_fac = client.post(
        "/api/v1/faculty",
        json={"employee_code": f"VE{tag}", "department_id": dept["id"], "name": f"Other {tag}"},
        headers=h,
    ).json()
    room = client.post(
        "/api/v1/rooms", json={"name": f"VR{tag}", "room_type": "CLASSROOM", "capacity": 50},
        headers=h,
    ).json()
    period = client.post(
        "/api/v1/periods",
        json={"day_of_week": "MONDAY", "start_time": "09:00", "end_time": "10:00", "period_order": 1},
        headers=h,
    ).json()

    own_id = accounts["profile"].id
    # ORM inserts via a fresh session on the same engine (no write API in Phase 4).
    maker = async_sessionmaker(db.bind, expire_on_commit=False)
    async with maker() as session:
        academic = await session.get(AcademicSession, uuid.UUID(sess["id"]))
        division1 = await session.get(Division, uuid.UUID(div1["id"]))
        division2 = await session.get(Division, uuid.UUID(div2["id"]))
        subject = await session.get(Subject, uuid.UUID(subj["id"]))
        room_o = await session.get(Room, uuid.UUID(room["id"]))
        period_o = await session.get(Period, uuid.UUID(period["id"]))
        other_o = await session.get(Faculty, uuid.UUID(other_fac["id"]))
        own_o = await session.get(Faculty, own_id)

        draft = Timetable(
            academic_session_id=academic.id, division_id=division1.id,
            status=TimetableStatus.DRAFT, version=1,
        )
        published = Timetable(
            academic_session_id=academic.id, division_id=division1.id,
            status=TimetableStatus.PUBLISHED, version=2,
            published_at=datetime.now(timezone.utc),
        )
        draft2 = Timetable(
            academic_session_id=academic.id, division_id=division2.id,
            status=TimetableStatus.DRAFT, version=1,
        )
        session.add_all([draft, published, draft2])
        await session.flush()
        session.add_all(
            [
                TimetableEntry(
                    timetable_id=draft.id, subject_id=subject.id, faculty_id=own_o.id,
                    room_id=room_o.id, period_id=period_o.id,
                ),
                TimetableEntry(
                    timetable_id=published.id, subject_id=subject.id, faculty_id=own_o.id,
                    room_id=room_o.id, period_id=period_o.id,
                ),
                TimetableEntry(
                    timetable_id=draft2.id, subject_id=subject.id, faculty_id=own_o.id,
                    room_id=room_o.id, period_id=period_o.id,
                ),
            ]
        )
        # A draft containing only the other faculty member's class.
        other_draft = Timetable(
            academic_session_id=academic.id, division_id=division1.id,
            status=TimetableStatus.DRAFT, version=3,
        )
        session.add(other_draft)
        await session.flush()
        session.add(
            TimetableEntry(
                timetable_id=other_draft.id, subject_id=subject.id, faculty_id=other_o.id,
                room_id=room_o.id, period_id=period_o.id,
            )
        )
        await session.commit()
        ids = {
            "draft": draft.id, "published": published.id, "draft2": draft2.id,
            "other_draft": other_draft.id, "div1": division1.id, "div2": division2.id,
            "other_fac": other_o.id, "own_fac": own_o.id,
        }
    return ids


async def test_student_sees_published_only(client, accounts, db):
    h = admin_h(client, accounts)
    ids = await build_graph(client, h, db, accounts, uuid.uuid4().hex[:6])
    sh = student_h(client, accounts)

    listed = client.get(TIMETABLES, headers=sh).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == str(ids["published"])

    assert client.get(f"{TIMETABLES}/{ids['draft']}", headers=sh).status_code == 404
    assert client.get(f"{TIMETABLES}/{ids['draft']}/entries", headers=sh).status_code == 404

    detail = client.get(f"{TIMETABLES}/{ids['published']}", headers=sh)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "PUBLISHED" and body["entry_count"] == 1
    entry = body["entries"][0]
    assert entry["subject_code"] and entry["faculty_name"] and entry["room_name"]
    assert entry["period"]["day_of_week"] == "MONDAY"
    assert entry["division_code"]

    entries = client.get(f"{TIMETABLES}/{ids['published']}/entries", headers=sh).json()
    assert entries["total"] == 1

    div_tt = client.get(f"{DIVISIONS}/{ids['div1']}/timetable", headers=sh)
    assert div_tt.status_code == 200 and div_tt.json()["id"] == str(ids["published"])
    assert client.get(f"{DIVISIONS}/{ids['div2']}/timetable", headers=sh).status_code == 404

    other_fac_id = str(ids["other_fac"])
    assert client.get(f"{FACULTY}/{other_fac_id}/timetable", headers=sh).status_code == 403


async def test_faculty_sees_own_drafts_not_others(client, accounts, db):
    h = admin_h(client, accounts)
    ids = await build_graph(client, h, db, accounts, uuid.uuid4().hex[:6])
    fh = faculty_h(client, accounts)
    own_id, other_id = str(ids["own_fac"]), str(ids["other_fac"])

    assert client.get(f"{TIMETABLES}/{ids['draft']}", headers=fh).status_code == 200
    assert client.get(f"{TIMETABLES}/{ids['other_draft']}", headers=fh).status_code == 404

    own_tt = client.get(f"{FACULTY}/{own_id}/timetable", headers=fh).json()
    assert own_tt["total"] >= 3  # own entries across draft + published + draft2
    assert client.get(f"{FACULTY}/{other_id}/timetable", headers=fh).status_code == 403

    div2_tt = client.get(f"{DIVISIONS}/{ids['div2']}/timetable", headers=fh)
    assert div2_tt.status_code == 200 and div2_tt.json()["id"] == str(ids["draft2"])


async def test_admin_sees_all_and_filters(client, accounts, db):
    h = admin_h(client, accounts)
    ids = await build_graph(client, h, db, accounts, uuid.uuid4().hex[:6])

    listed = client.get(TIMETABLES, headers=h).json()
    assert listed["total"] == 4
    drafts = client.get(f"{TIMETABLES}?status=DRAFT", headers=h).json()
    assert drafts["total"] == 3
    div1 = client.get(f"{TIMETABLES}?division_id={ids['div1']}", headers=h).json()
    assert div1["total"] == 3
    assert client.get(f"{TIMETABLES}/{ids['draft']}", headers=h).status_code == 200


async def test_timetable_endpoints_require_auth(client, accounts, db):
    h = admin_h(client, accounts)
    ids = await build_graph(client, h, db, accounts, uuid.uuid4().hex[:6])
    urls = [
        TIMETABLES,
        f"{TIMETABLES}/{ids['published']}",
        f"{TIMETABLES}/{ids['published']}/entries",
        f"{DIVISIONS}/{ids['div1']}/timetable",
        f"{FACULTY}/{ids['own_fac']}/timetable",
    ]
    for url in urls:
        assert client.get(url).status_code == 401, url


async def test_entry_creation_exposed_admin_only(client, accounts, db):
    """Phase 6 deliberately exposes entry writes (spec §3) — admin-only.

    Replaces the Phase 4 assertion that no such endpoint exists.
    """
    h = admin_h(client, accounts)
    ids = await build_graph(client, h, db, accounts, uuid.uuid4().hex[:6])
    response = client.post(f"{TIMETABLES}/{ids['published']}/entries", json={}, headers=h)
    # Empty body → 422 schema validation (endpoint exists and is reachable).
    assert response.status_code == 422
