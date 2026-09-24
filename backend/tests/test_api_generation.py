"""Generation API integration tests: API -> engine (CP-SAT) -> validator -> DB."""

import uuid

from tests.conftest import login_headers

GENERATE = "/api/v1/timetables/generate"


def admin_h(client, accounts):
    return login_headers(client, accounts["admin"].email)


def faculty_h(client, accounts):
    return login_headers(client, accounts["faculty"].email)


def student_h(client, accounts):
    return login_headers(client, accounts["student"].email)


def _options(**overrides):
    opts = {"optimize": True, "time_limit_seconds": 10.0,
            "num_workers": 1, "random_seed": 7}
    opts.update(overrides)
    return opts


async def build_feasible_graph(client, h, tag):
    """Small feasible scope: 3 sessions over 4 teaching periods."""
    sess = client.post(
        "/api/v1/academic-sessions",
        json={"name": f"GS-{tag}", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        headers=h,
    ).json()
    dept = client.post(
        "/api/v1/departments", json={"name": f"GD-{tag}", "code": f"GD{tag}"}, headers=h
    ).json()
    div = client.post(
        "/api/v1/divisions",
        json={"department_id": dept["id"], "name": f"GX-{tag}", "code": f"GX{tag}",
              "student_count": 20},
        headers=h,
    ).json()
    math = client.post(
        "/api/v1/subjects",
        json={"code": f"GM{tag}", "name": "Math", "required_periods_per_week": 2,
              "required_room_type": "CLASSROOM"},
        headers=h,
    ).json()
    lab = client.post(
        "/api/v1/subjects",
        json={"code": f"GL{tag}", "name": "Lab", "subject_type": "LAB",
              "required_periods_per_week": 1, "required_room_type": "LAB",
              "requires_lab": True},
        headers=h,
    ).json()
    fac2 = client.post(
        "/api/v1/faculty",
        json={"employee_code": f"GE{tag}", "department_id": dept["id"], "name": "Two"},
        headers=h,
    )
    assert fac2.status_code == 201, fac2.text
    fac2 = fac2.json()
    room = client.post(
        "/api/v1/rooms",
        json={"name": f"GR{tag}", "room_type": "CLASSROOM", "capacity": 30},
        headers=h,
    ).json()
    lab_room = client.post(
        "/api/v1/rooms",
        json={"name": f"GB{tag}", "room_type": "LAB", "capacity": 30},
        headers=h,
    ).json()
    periods = []
    for day, order in (("MONDAY", 1), ("MONDAY", 2), ("TUESDAY", 1), ("TUESDAY", 2)):
        periods.append(client.post(
            "/api/v1/periods",
            json={"day_of_week": day, "start_time": "09:00", "end_time": "10:00",
                  "period_order": order},
            headers=h,
        ).json())
    for subject in (math, lab):
        for fac_id in (fac2["id"],):
            created = client.post(
                "/api/v1/faculty-assignments",
                json={"faculty_id": fac_id, "subject_id": subject["id"],
                      "division_id": div["id"], "academic_session_id": sess["id"]},
                headers=h,
            )
            assert created.status_code == 201, created.text
    for subject, ppw in ((math, 2), (lab, 1)):
        created = client.post(
            "/api/v1/division-subject-requirements",
            json={"division_id": div["id"], "subject_id": subject["id"],
                  "academic_session_id": sess["id"], "required_periods_per_week": ppw,
                  "preferred_room_type": subject["required_room_type"],
                  "requires_lab": subject["requires_lab"]},
            headers=h,
        )
        assert created.status_code == 201, created.text
    return {"session": sess, "division": div, "faculty": fac2}


async def test_generate_success_end_to_end(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    response = client.post(
        GENERATE,
        json={"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
              "options": _options()},
        headers=h,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert body["objective_score"] is not None
    assert body["generation_duration_ms"] >= 0

    # Persisted and independently valid.
    detail = client.get(f"/api/v1/timetables/{body['timetable_id']}", headers=h).json()
    assert detail["entry_count"] == 3
    assert detail["status"] == "GENERATED"
    validation = client.post(
        f"/api/v1/timetables/{body['timetable_id']}/validate", headers=h
    ).json()
    assert validation["valid"] is True
    assert validation["violations"] == []
    promoted = client.get(f"/api/v1/timetables/{body['timetable_id']}", headers=h).json()
    assert promoted["status"] == "VALID"


async def test_generate_versions_without_overwriting(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    payload = {"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
               "options": _options()}
    first = client.post(GENERATE, json=payload, headers=h).json()
    second = client.post(GENERATE, json=payload, headers=h).json()
    assert first["timetable_id"] != second["timetable_id"]
    listed = client.get(
        f"/api/v1/timetables?division_id={g['division']['id']}", headers=h
    ).json()
    versions = sorted(t["version"] for t in listed["items"])
    assert versions == [1, 2]


async def test_generate_infeasible_reports_conflicts(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    # A requirement with no faculty assignment can never be scheduled.
    orphan = client.post(
        "/api/v1/subjects",
        json={"code": f"GO{uuid.uuid4().hex[:6]}", "name": "Orphan",
              "required_periods_per_week": 1},
        headers=h,
    ).json()
    created = client.post(
        "/api/v1/division-subject-requirements",
        json={"division_id": g["division"]["id"], "subject_id": orphan["id"],
              "academic_session_id": g["session"]["id"], "required_periods_per_week": 1},
        headers=h,
    )
    assert created.status_code == 201

    before = client.get(
        f"/api/v1/timetables?division_id={g['division']['id']}", headers=h
    ).json()["total"]
    response = client.post(
        GENERATE,
        json={"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
              "options": _options()},
        headers=h,
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["status"] == "INFEASIBLE"
    assert body["conflicts"], "conflicts must explain the failure"
    types = {c["type"] for c in body["conflicts"]}
    assert "NO_ELIGIBLE_FACULTY" in types
    assert body["suggestions"], "suggestions must accompany conflicts"
    for conflict in body["conflicts"]:
        assert conflict["message"] and conflict["severity"] == "ERROR"
    after = client.get(
        f"/api/v1/timetables?division_id={g['division']['id']}", headers=h
    ).json()["total"]
    assert after == before, "infeasible runs must not persist anything"


async def test_generate_unknown_scope_404(client, accounts):
    h = admin_h(client, accounts)
    ghost = str(uuid.uuid4())
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    for payload in (
        {"academic_session_id": ghost, "division_id": g["division"]["id"]},
        {"academic_session_id": g["session"]["id"], "division_id": ghost},
    ):
        response = client.post(GENERATE, json=payload, headers=h)
        assert response.status_code == 404, response.text


async def test_generation_endpoints_require_admin(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    payload = {"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
               "options": _options()}
    timetable_id = client.post(GENERATE, json=payload, headers=h).json()["timetable_id"]

    fh, sh = faculty_h(client, accounts), student_h(client, accounts)
    assert client.post(GENERATE, json=payload, headers=fh).status_code == 403
    assert client.post(GENERATE, json=payload, headers=sh).status_code == 403
    assert client.post(GENERATE, json=payload).status_code == 401
    for headers, expected in ((fh, 403), (sh, 403), (None, 401)):
        kwargs = {"headers": headers} if headers else {}
        assert client.post(
            f"/api/v1/timetables/{timetable_id}/validate", **kwargs
        ).status_code == expected
        assert client.get(
            f"/api/v1/timetables/{timetable_id}/generation-result", **kwargs
        ).status_code == expected


async def test_generation_result_view(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    timetable_id = client.post(
        GENERATE,
        json={"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
              "options": _options()},
        headers=h,
    ).json()["timetable_id"]
    result = client.get(
        f"/api/v1/timetables/{timetable_id}/generation-result", headers=h
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["timetable_id"] == timetable_id
    assert body["status"] == "GENERATED"  # read-only view must not promote
    assert body["entry_count"] == 3
    assert body["valid"] is True
    assert body["violations"] == []


async def test_generate_feasibility_only_mode(client, accounts):
    h = admin_h(client, accounts)
    g = await build_feasible_graph(client, h, uuid.uuid4().hex[:6])
    response = client.post(
        GENERATE,
        json={"academic_session_id": g["session"]["id"], "division_id": g["division"]["id"],
              "options": _options(optimize=False)},
        headers=h,
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "SUCCESS"
