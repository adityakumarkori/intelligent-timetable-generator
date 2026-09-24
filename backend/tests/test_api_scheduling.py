"""Scheduling-config API tests: availability, assignments, requirements."""

import uuid

from tests.conftest import login_headers

SESSIONS = "/api/v1/academic-sessions"
DEPARTMENTS = "/api/v1/departments"
DIVISIONS = "/api/v1/divisions"
SUBJECTS = "/api/v1/subjects"
FACULTY = "/api/v1/faculty"
ROOMS = "/api/v1/rooms"
PERIODS = "/api/v1/periods"
ASSIGNMENTS = "/api/v1/faculty-assignments"
REQUIREMENTS = "/api/v1/division-subject-requirements"


def admin_h(client, accounts):
    return login_headers(client, accounts["admin"].email)


def faculty_h(client, accounts):
    return login_headers(client, accounts["faculty"].email)


def student_h(client, accounts):
    return login_headers(client, accounts["student"].email)


def make_graph(client, h, tag):
    """Minimal valid scheduling graph via the API. Returns id dict."""
    sess = client.post(
        SESSIONS,
        json={"name": f"S-{tag}", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        headers=h,
    ).json()
    dept = client.post(DEPARTMENTS, json={"name": f"D-{tag}", "code": f"D{tag}"}, headers=h).json()
    div = client.post(
        DIVISIONS,
        json={"department_id": dept["id"], "name": f"DIV-{tag}", "code": f"V{tag}"},
        headers=h,
    ).json()
    subj = client.post(
        SUBJECTS,
        json={"code": f"SUB{tag}", "name": f"Sub {tag}", "required_periods_per_week": 3},
        headers=h,
    ).json()
    fac = client.post(
        FACULTY,
        json={"employee_code": f"E{tag}", "department_id": dept["id"], "name": f"Prof {tag}"},
        headers=h,
    ).json()
    room = client.post(
        ROOMS, json={"name": f"R{tag}", "room_type": "CLASSROOM", "capacity": 50}, headers=h
    ).json()
    period = client.post(
        PERIODS,
        json={"day_of_week": "MONDAY", "start_time": "09:00", "end_time": "10:00", "period_order": 1},
        headers=h,
    ).json()
    return {"session": sess, "dept": dept, "div": div, "subj": subj, "fac": fac,
            "room": room, "period": period}


def availability_url(faculty_id):
    return f"{FACULTY}/{faculty_id}/availability"


async def test_availability_put_patch_get(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    url = availability_url(g["fac"]["id"])

    put = client.put(
        url,
        json={"items": [
            {"period_id": g["period"]["id"], "status": "AVAILABLE"},
        ]},
        headers=h,
    )
    assert put.status_code == 200, put.text
    assert len(put.json()) == 1
    assert put.json()[0]["period"]["day_of_week"] == "MONDAY"

    patched = client.patch(
        f"{url}/{g['period']['id']}", json={"status": "UNAVAILABLE"}, headers=h
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "UNAVAILABLE"

    got = client.get(url, headers=h).json()
    assert len(got) == 1 and got[0]["status"] == "UNAVAILABLE"


async def test_availability_scoping(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    own_id = str(accounts["profile"].id)
    other_url = availability_url(g["fac"]["id"])
    own_url = availability_url(own_id)

    fh = faculty_h(client, accounts)
    assert client.get(own_url, headers=fh).status_code == 200
    assert client.get(other_url, headers=fh).status_code == 403
    assert client.put(other_url, json={"items": []}, headers=fh).status_code == 403

    sh = student_h(client, accounts)
    assert client.get(other_url, headers=sh).status_code == 403
    assert client.get(other_url).status_code == 401


async def test_availability_validation(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    url = availability_url(g["fac"]["id"])
    ghost = str(uuid.uuid4())

    bad_period = client.put(
        url, json={"items": [{"period_id": ghost, "status": "AVAILABLE"}]}, headers=h
    )
    assert bad_period.status_code == 404
    dup = client.put(
        url,
        json={"items": [
            {"period_id": g["period"]["id"], "status": "AVAILABLE"},
            {"period_id": g["period"]["id"], "status": "UNAVAILABLE"},
        ]},
        headers=h,
    )
    assert dup.status_code == 422
    missing = client.patch(f"{url}/{ghost}", json={"status": "AVAILABLE"}, headers=h)
    assert missing.status_code == 404


async def test_assignment_crud(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    payload = {
        "faculty_id": g["fac"]["id"],
        "subject_id": g["subj"]["id"],
        "division_id": g["div"]["id"],
        "academic_session_id": g["session"]["id"],
    }
    created = client.post(ASSIGNMENTS, json=payload, headers=h)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["faculty_name"] and body["subject_code"] and body["division_code"]
    assignment_id = body["id"]

    assert client.get(f"{ASSIGNMENTS}/{assignment_id}", headers=h).status_code == 200
    dup = client.post(ASSIGNMENTS, json=payload, headers=h)
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]
    assert client.delete(f"{ASSIGNMENTS}/{assignment_id}", headers=h).status_code == 204
    assert client.get(f"{ASSIGNMENTS}/{assignment_id}", headers=h).status_code == 404


async def test_assignment_rejects_inactive_or_missing(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    ghost = str(uuid.uuid4())

    base = {
        "faculty_id": g["fac"]["id"],
        "subject_id": g["subj"]["id"],
        "division_id": g["div"]["id"],
        "academic_session_id": g["session"]["id"],
    }
    missing = client.post(ASSIGNMENTS, json={**base, "subject_id": ghost}, headers=h)
    assert missing.status_code == 404

    for key, url in (("subject_id", SUBJECTS), ("division_id", DIVISIONS), ("faculty_id", FACULTY)):
        target = g[("subj" if key == "subject_id" else "div" if key == "division_id" else "fac")]
        assert client.patch(f"{url}/{target['id']}", json={"is_active": False}, headers=h).status_code == 200
        rejected = client.post(ASSIGNMENTS, json=base, headers=h)
        assert rejected.status_code == 422, (key, rejected.text)
        assert "inactive" in rejected.json()["detail"]
        assert client.patch(f"{url}/{target['id']}", json={"is_active": True}, headers=h).status_code == 200


async def test_assignment_faculty_sees_own_only(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    # Assignment for the caller's own profile.
    own = client.post(
        ASSIGNMENTS,
        json={
            "faculty_id": str(accounts["profile"].id),
            "subject_id": g["subj"]["id"],
            "division_id": g["div"]["id"],
            "academic_session_id": g["session"]["id"],
        },
        headers=h,
    )
    assert own.status_code == 201
    other = client.post(
        ASSIGNMENTS,
        json={
            "faculty_id": g["fac"]["id"],
            "subject_id": g["subj"]["id"],
            "division_id": g["div"]["id"],
            "academic_session_id": g["session"]["id"],
        },
        headers=h,
    )
    assert other.status_code == 201

    fh = faculty_h(client, accounts)
    mine = client.get(ASSIGNMENTS, headers=fh).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == own.json()["id"]
    assert client.get(f"{ASSIGNMENTS}/{other.json()['id']}", headers=fh).status_code == 403

    sh = student_h(client, accounts)
    assert client.get(ASSIGNMENTS, headers=sh).status_code == 403
    assert client.get(ASSIGNMENTS).status_code == 401


async def test_requirement_crud_and_room_compat(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    payload = {
        "division_id": g["div"]["id"],
        "subject_id": g["subj"]["id"],
        "academic_session_id": g["session"]["id"],
        "required_periods_per_week": 3,
    }
    created = client.post(REQUIREMENTS, json=payload, headers=h)
    assert created.status_code == 201, created.text
    assert created.json()["subject_code"] and created.json()["division_code"]
    req_id = created.json()["id"]

    dup = client.post(REQUIREMENTS, json=payload, headers=h)
    assert dup.status_code == 409

    patched = client.patch(f"{REQUIREMENTS}/{req_id}",
                           json={"required_periods_per_week": 4}, headers=h)
    assert patched.status_code == 200 and patched.json()["required_periods_per_week"] == 4

    zero = client.patch(f"{REQUIREMENTS}/{req_id}", json={"required_periods_per_week": 0}, headers=h)
    assert zero.status_code == 422

    # Pin the subject to CLASSROOM: a LAB override is then incompatible,
    # while a matching CLASSROOM override is accepted.
    pinned = client.patch(
        f"{SUBJECTS}/{g['subj']['id']}", json={"required_room_type": "CLASSROOM"}, headers=h
    )
    assert pinned.status_code == 200
    assert client.delete(f"{REQUIREMENTS}/{req_id}", headers=h).status_code == 204
    clash = client.post(
        REQUIREMENTS,
        json={**payload, "preferred_room_type": "LAB"},
        headers=h,
    )
    assert clash.status_code == 422
    assert "conflicts" in clash.json()["detail"]
    match = client.post(
        REQUIREMENTS,
        json={**payload, "preferred_room_type": "CLASSROOM"},
        headers=h,
    )
    assert match.status_code == 201, match.text

    # Lab subject + classroom override -> incompatible; + LAB override -> fine.
    lab_subj = client.post(
        SUBJECTS,
        json={"code": f"LAB{uuid.uuid4().hex[:5]}", "name": "Lab",
              "subject_type": "LAB", "required_periods_per_week": 2,
              "required_room_type": "LAB", "requires_lab": True},
        headers=h,
    ).json()
    bad_lab = client.post(
        REQUIREMENTS,
        json={"division_id": g["div"]["id"], "subject_id": lab_subj["id"],
              "academic_session_id": g["session"]["id"],
              "required_periods_per_week": 2, "preferred_room_type": "CLASSROOM",
              "requires_lab": True},
        headers=h,
    )
    assert bad_lab.status_code == 422
    good_lab = client.post(
        REQUIREMENTS,
        json={"division_id": g["div"]["id"], "subject_id": lab_subj["id"],
              "academic_session_id": g["session"]["id"],
              "required_periods_per_week": 2, "preferred_room_type": "LAB",
              "requires_lab": True},
        headers=h,
    )
    assert good_lab.status_code == 201, good_lab.text


async def test_requirement_read_open_but_writes_admin(client, accounts):
    h = admin_h(client, accounts)
    g = make_graph(client, h, uuid.uuid4().hex[:6])
    req = client.post(
        REQUIREMENTS,
        json={"division_id": g["div"]["id"], "subject_id": g["subj"]["id"],
              "academic_session_id": g["session"]["id"], "required_periods_per_week": 2},
        headers=h,
    ).json()

    fh, sh = faculty_h(client, accounts), student_h(client, accounts)
    assert client.get(REQUIREMENTS, headers=fh).status_code == 200
    assert client.get(f"{REQUIREMENTS}/{req['id']}", headers=sh).status_code == 200
    assert client.get(REQUIREMENTS).status_code == 401
    assert client.post(REQUIREMENTS, json={}, headers=sh).status_code == 403
    assert client.delete(f"{REQUIREMENTS}/{req['id']}", headers=fh).status_code == 403
