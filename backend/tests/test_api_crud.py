"""CRUD + RBAC tests for the seven master-data resources."""

import uuid

import pytest

from tests.conftest import TEST_PASSWORD, login_headers

SESSIONS = "/api/v1/academic-sessions"
DEPARTMENTS = "/api/v1/departments"
DIVISIONS = "/api/v1/divisions"
SUBJECTS = "/api/v1/subjects"
FACULTY = "/api/v1/faculty"
ROOMS = "/api/v1/rooms"
PERIODS = "/api/v1/periods"


def admin_h(client, accounts):
    return login_headers(client, accounts["admin"].email)


def faculty_h(client, accounts):
    return login_headers(client, accounts["faculty"].email)


def student_h(client, accounts):
    return login_headers(client, accounts["student"].email)


def crud_cycle(client, headers, base, create_payload, patch_payload):
    """create 201 -> get 200 -> listed -> patch 200 -> delete 204 -> get 404."""
    created = client.post(base, json=create_payload, headers=headers)
    assert created.status_code == 201, created.text
    obj_id = created.json()["id"]

    got = client.get(f"{base}/{obj_id}", headers=headers)
    assert got.status_code == 200

    listed = client.get(base, headers=headers).json()
    assert listed["total"] >= 1
    assert any(i["id"] == obj_id for i in listed["items"])
    assert set(listed) == {"items", "page", "page_size", "total"}

    patched = client.patch(f"{base}/{obj_id}", json=patch_payload, headers=headers)
    assert patched.status_code == 200, patched.text

    assert client.delete(f"{base}/{obj_id}", headers=headers).status_code == 204
    assert client.get(f"{base}/{obj_id}", headers=headers).status_code == 404
    return obj_id


async def test_department_crud(client, accounts):
    h = admin_h(client, accounts)
    crud_cycle(
        client, h, DEPARTMENTS,
        {"name": "Science", "code": "SCI"},
        {"name": "Science & Tech"},
    )


async def test_department_duplicate_code_409(client, accounts):
    h = admin_h(client, accounts)
    assert client.post(DEPARTMENTS, json={"name": "A", "code": "DUP"}).status_code == 401
    assert client.post(DEPARTMENTS, json={"name": "A", "code": "DUP"}, headers=h).status_code == 201
    dup = client.post(DEPARTMENTS, json={"name": "B", "code": "DUP"}, headers=h)
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]


async def test_department_validation_422(client, accounts):
    h = admin_h(client, accounts)
    assert client.post(DEPARTMENTS, json={"code": "X"}, headers=h).status_code == 422


async def test_department_safe_delete_409(client, accounts, engine):
    h = admin_h(client, accounts)
    dept_id = client.post(DEPARTMENTS, json={"name": "D", "code": "D1"}, headers=h).json()["id"]
    div = client.post(
        DIVISIONS,
        json={"department_id": dept_id, "name": "D-A", "code": "D-A"},
        headers=h,
    )
    assert div.status_code == 201
    blocked = client.delete(f"{DEPARTMENTS}/{dept_id}", headers=h)
    assert blocked.status_code == 409
    assert "referenced" in blocked.json()["detail"]
    assert client.delete(f"{DIVISIONS}/{div.json()['id']}", headers=h).status_code == 204
    assert client.delete(f"{DEPARTMENTS}/{dept_id}", headers=h).status_code == 204


async def test_session_crud_and_dates(client, accounts):
    h = admin_h(client, accounts)
    crud_cycle(
        client, h, SESSIONS,
        {"name": "2027-28", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        {"is_active": False},
    )
    bad = client.post(
        SESSIONS,
        json={"name": "BAD", "start_date": "2028-01-01", "end_date": "2027-01-01"},
        headers=h,
    )
    assert bad.status_code == 422


async def test_session_activation_deactivates_others(client, accounts):
    h = admin_h(client, accounts)
    a = client.post(
        SESSIONS,
        json={"name": "S-A", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        headers=h,
    ).json()
    b = client.post(
        SESSIONS,
        json={"name": "S-B", "start_date": "2028-07-01", "end_date": "2029-05-31"},
        headers=h,
    ).json()
    assert client.get(f"{SESSIONS}/{a['id']}", headers=h).json()["is_active"] is False
    assert client.get(f"{SESSIONS}/{b['id']}", headers=h).json()["is_active"] is True


async def test_division_crud_filters_and_validation(client, accounts):
    h = admin_h(client, accounts)
    dept_id = str(accounts["department"].id)
    crud_cycle(
        client, h, DIVISIONS,
        {"department_id": dept_id, "name": "CSE-X", "code": "CSE-X", "student_count": 40},
        {"student_count": 45},
    )
    missing_dept = client.post(
        DIVISIONS,
        json={"department_id": str(uuid.uuid4()), "name": "N", "code": "N"},
        headers=h,
    )
    assert missing_dept.status_code == 404
    client.post(
        DIVISIONS, json={"department_id": dept_id, "name": "A", "code": "SAME"}, headers=h
    )
    dup = client.post(
        DIVISIONS, json={"department_id": dept_id, "name": "B", "code": "SAME"}, headers=h
    )
    assert dup.status_code == 409
    neg = client.post(
        DIVISIONS,
        json={"department_id": dept_id, "name": "C", "code": "C", "student_count": -1},
        headers=h,
    )
    assert neg.status_code == 422
    filtered = client.get(f"{DIVISIONS}?department_id={dept_id}", headers=h).json()
    assert filtered["total"] >= 1


async def test_subject_crud(client, accounts):
    h = admin_h(client, accounts)
    crud_cycle(
        client, h, SUBJECTS,
        {"code": "M101", "name": "Math", "required_periods_per_week": 5},
        {"required_periods_per_week": 4, "requires_lab": True},
    )
    client.post(SUBJECTS, json={"code": "DUP", "name": "A", "required_periods_per_week": 2}, headers=h)
    dup = client.post(
        SUBJECTS, json={"code": "DUP", "name": "B", "required_periods_per_week": 2}, headers=h
    )
    assert dup.status_code == 409
    zero = client.post(
        SUBJECTS, json={"code": "Z", "name": "Z", "required_periods_per_week": 0}, headers=h
    )
    assert zero.status_code == 422


async def test_faculty_crud_and_user_link(client, accounts, engine):
    h = admin_h(client, accounts)
    dept_id = str(accounts["department"].id)
    crud_cycle(
        client, h, FACULTY,
        {"employee_code": "E100", "department_id": dept_id, "name": "Prof X"},
        {"name": "Prof Y", "is_active": False},
    )
    # Link to an existing user, then prove double-linking is rejected.
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.security import hash_password
    from app.models import User
    from app.models.enums import UserRole

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        user = User(
            name="Link", email="link@x.edu", password_hash=hash_password(TEST_PASSWORD),
            role=UserRole.FACULTY,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = str(user.id)
    first = client.post(
        FACULTY,
        json={"employee_code": "E101", "department_id": dept_id, "name": "Linked", "user_id": user_id},
        headers=h,
    )
    assert first.status_code == 201, first.text
    assert first.json()["user_id"] == user_id
    assert "password_hash" not in first.json()
    second = client.post(
        FACULTY,
        json={"employee_code": "E102", "department_id": dept_id, "name": "Linked2", "user_id": user_id},
        headers=h,
    )
    assert second.status_code == 409
    ghost = client.post(
        FACULTY,
        json={"employee_code": "E103", "department_id": dept_id, "name": "Ghost",
              "user_id": str(uuid.uuid4())},
        headers=h,
    )
    assert ghost.status_code == 404


async def test_room_crud(client, accounts):
    h = admin_h(client, accounts)
    crud_cycle(
        client, h, ROOMS,
        {"name": "R-1", "room_type": "CLASSROOM", "capacity": 60},
        {"capacity": 70},
    )
    client.post(ROOMS, json={"name": "RD", "room_type": "LAB", "capacity": 30}, headers=h)
    dup = client.post(ROOMS, json={"name": "RD", "room_type": "LAB", "capacity": 30}, headers=h)
    assert dup.status_code == 409
    bad = client.post(ROOMS, json={"name": "RZ", "room_type": "LAB", "capacity": 0}, headers=h)
    assert bad.status_code == 422
    labs = client.get(f"{ROOMS}?room_type=LAB&min_capacity=20", headers=h).json()
    assert labs["total"] >= 1


async def test_period_crud(client, accounts):
    h = admin_h(client, accounts)
    crud_cycle(
        client, h, PERIODS,
        {"day_of_week": "MONDAY", "start_time": "09:00", "end_time": "10:00", "period_order": 1},
        {"is_break": True},
    )
    client.post(
        PERIODS,
        json={"day_of_week": "TUESDAY", "start_time": "09:00", "end_time": "10:00", "period_order": 3},
        headers=h,
    )
    dup = client.post(
        PERIODS,
        json={"day_of_week": "TUESDAY", "start_time": "10:00", "end_time": "11:00", "period_order": 3},
        headers=h,
    )
    assert dup.status_code == 409
    bad = client.post(
        PERIODS,
        json={"day_of_week": "WEDNESDAY", "start_time": "11:00", "end_time": "10:00", "period_order": 1},
        headers=h,
    )
    assert bad.status_code == 422
    day = client.get(f"{PERIODS}?day_of_week=TUESDAY", headers=h).json()
    assert day["total"] >= 1


@pytest.mark.parametrize("base,student_read,faculty_read", [
    (SESSIONS, 403, 403),
    (DEPARTMENTS, 403, 200),
    (DIVISIONS, 200, 200),
    (SUBJECTS, 200, 200),
    (FACULTY, 200, 200),
    (ROOMS, 200, 200),
    (PERIODS, 200, 200),
])
async def test_read_matrix(client, accounts, base, student_read, faculty_read):
    assert client.get(base).status_code == 401
    assert client.get(base, headers=student_h(client, accounts)).status_code == student_read
    assert client.get(base, headers=faculty_h(client, accounts)).status_code == faculty_read


@pytest.mark.parametrize("base,payload", [
    (SESSIONS, {"name": "W", "start_date": "2030-07-01", "end_date": "2031-05-31"}),
    (DEPARTMENTS, {"name": "W", "code": "W"}),
    (SUBJECTS, {"code": "W", "name": "W", "required_periods_per_week": 1}),
    (ROOMS, {"name": "W", "room_type": "CLASSROOM", "capacity": 10}),
    (PERIODS, {"day_of_week": "FRIDAY", "start_time": "09:00", "end_time": "10:00", "period_order": 9}),
])
async def test_writes_forbidden_for_non_admins(client, accounts, base, payload):
    obj_id = client.post(base, json=payload, headers=admin_h(client, accounts)).json()["id"]
    for headers in (faculty_h(client, accounts), student_h(client, accounts)):
        assert client.post(base, json=payload, headers=headers).status_code == 403
        assert client.patch(f"{base}/{obj_id}", json=payload, headers=headers).status_code == 403
        assert client.delete(f"{base}/{obj_id}", headers=headers).status_code == 403


async def test_missing_resource_404(client, accounts):
    h = admin_h(client, accounts)
    ghost = str(uuid.uuid4())
    for base in (SESSIONS, DEPARTMENTS, DIVISIONS, SUBJECTS, FACULTY, ROOMS, PERIODS):
        assert client.get(f"{base}/{ghost}", headers=h).status_code == 404
        assert client.delete(f"{base}/{ghost}", headers=h).status_code == 404


async def test_pagination_envelope(client, accounts):
    h = admin_h(client, accounts)
    for i in range(3):
        client.post(DEPARTMENTS, json={"name": f"P{i}", "code": f"P{i}"}, headers=h)
    page1 = client.get(f"{DEPARTMENTS}?page=1&page_size=2", headers=h).json()
    assert page1["page"] == 1 and page1["page_size"] == 2
    assert len(page1["items"]) == 2 and page1["total"] >= 3
    assert client.get(f"{DEPARTMENTS}?page_size=1000", headers=h).status_code == 422
