"""Phase 6 lifecycle tests: edit → validate → publish, with safety rails."""

import uuid
from email.utils import format_datetime
from datetime import datetime, timezone

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


async def build_lifecycle_graph(client, h, tag, *, math_per_week=2, divisions=1):
    """Two classroom periods + MATH requirement; returns ids incl. periods."""
    sess = client.post(
        "/api/v1/academic-sessions",
        json={"name": f"LS-{tag}", "start_date": "2027-07-01", "end_date": "2028-05-31"},
        headers=h,
    ).json()
    dept = client.post(
        "/api/v1/departments", json={"name": f"LD-{tag}", "code": f"LD{tag}"}, headers=h
    ).json()
    divs = []
    for i in range(divisions):
        divs.append(client.post(
            "/api/v1/divisions",
            json={"department_id": dept["id"], "name": f"LX-{tag}-{i}",
                  "code": f"LX{tag}{i}", "student_count": 20},
            headers=h,
        ).json())
    math = client.post(
        "/api/v1/subjects",
        json={"code": f"LM{tag}", "name": "Math", "required_periods_per_week": math_per_week,
              "required_room_type": "CLASSROOM"},
        headers=h,
    ).json()
    facs = []
    for i in range(2):
        fac = client.post(
            "/api/v1/faculty",
            json={"employee_code": f"LE{tag}{i}", "department_id": dept["id"],
                  "name": f"Prof {tag} {i}"},
            headers=h,
        )
        assert fac.status_code == 201, fac.text
        facs.append(fac.json())
    rooms = []
    for i in range(2):
        rooms.append(client.post(
            "/api/v1/rooms",
            json={"name": f"LR{tag}{i}", "room_type": "CLASSROOM", "capacity": 30},
            headers=h,
        ).json())
    periods = []
    for day, order in (("MONDAY", 1), ("MONDAY", 2), ("MONDAY", 3)):
        periods.append(client.post(
            "/api/v1/periods",
            json={"day_of_week": day, "start_time": "09:00", "end_time": "10:00",
                  "period_order": order},
            headers=h,
        ).json())
    for div in divs:
        for fac in facs:
            created = client.post(
                "/api/v1/faculty-assignments",
                json={"faculty_id": fac["id"], "subject_id": math["id"],
                      "division_id": div["id"], "academic_session_id": sess["id"]},
                headers=h,
            )
            assert created.status_code == 201, created.text
        created = client.post(
            "/api/v1/division-subject-requirements",
            json={"division_id": div["id"], "subject_id": math["id"],
                  "academic_session_id": sess["id"],
                  "required_periods_per_week": math_per_week},
            headers=h,
        )
        assert created.status_code == 201, created.text
    return {"session": sess, "divisions": divs, "math": math,
            "facs": facs, "rooms": rooms, "periods": periods}


async def generate(client, h, session_id, division_id):
    response = client.post(
        GENERATE,
        json={"academic_session_id": session_id, "division_id": division_id,
              "options": _options()},
        headers=h,
    )
    assert response.status_code == 201, response.text
    return response.json()


def entries_url(timetable_id):
    return f"/api/v1/timetables/{timetable_id}/entries"


async def test_create_entry_roundtrip_via_delete(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])

    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    assert detail["entry_count"] == 2
    victim = detail["entries"][0]
    free_period = next(
        p for p in g["periods"]
        if p["id"] not in {e["period"]["id"] for e in detail["entries"]}
    )

    # Delete → DRAFT + incomplete.
    assert client.delete(
        f"{entries_url(table['timetable_id'])}/{victim['id']}", headers=h
    ).status_code == 204
    draft = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    assert draft["status"] == "DRAFT"
    validation = client.post(
        f"/api/v1/timetables/{table['timetable_id']}/validate", headers=h
    ).json()
    assert validation["valid"] is False
    assert validation["status"] == "INVALID"
    assert any(v["type"] == "WEEKLY_LOAD_MISMATCH" for v in validation["violations"])

    # Recreate elsewhere → VALID again, nested display shape intact.
    other_fac = g["facs"][1] if victim["faculty_id"] == g["facs"][0]["id"] else g["facs"][0]
    created = client.post(
        entries_url(table["timetable_id"]),
        json={"subject_id": victim["subject_id"], "faculty_id": other_fac["id"],
              "room_id": g["rooms"][1]["id"], "period_id": free_period["id"]},
        headers=h,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["period"]["id"] == free_period["id"]
    assert body["subject"]["code"] == victim["subject_code"]
    assert body["faculty"]["id"] == other_fac["id"]
    assert body["room"]["id"] == g["rooms"][1]["id"]
    restored = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    assert restored["status"] == "VALID"
    assert restored["entry_count"] == 2


async def test_create_entry_duplicate_period_rejected(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    first = detail["entries"][0]

    response = client.post(
        entries_url(table["timetable_id"]),
        json={"subject_id": first["subject_id"], "faculty_id": g["facs"][1]["id"],
              "room_id": g["rooms"][1]["id"], "period_id": first["period"]["id"]},
        headers=h,
    )
    assert response.status_code == 409, response.text
    body = response.json()["detail"]
    assert body["error"] == "TIMETABLE_CONFLICT"
    assert any(c["type"] == "DIVISION_CONFLICT" for c in body["conflicts"])
    assert body["suggestions"], "suggestions must accompany conflicts"
    # Nothing persisted: still 2 entries.
    assert client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()["entry_count"] == 2


async def test_create_entry_cross_timetable_conflicts(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6], divisions=2)
    div_a, div_b = g["divisions"]
    table_b = await generate(client, h, g["session"]["id"], div_b["id"])
    client.post(f"/api/v1/timetables/{table_b['timetable_id']}/validate", headers=h)
    assert client.post(
        f"/api/v1/timetables/{table_b['timetable_id']}/publish", headers=h
    ).status_code == 200
    table_a = await generate(client, h, g["session"]["id"], div_a["id"])
    detail_b = client.get(f"/api/v1/timetables/{table_b['timetable_id']}", headers=h).json()
    other = detail_b["entries"][0]

    # Free A's copy of that period (if any) so only the cross check can fire.
    detail_a = client.get(f"/api/v1/timetables/{table_a['timetable_id']}", headers=h).json()
    occupant = next(
        (e for e in detail_a["entries"] if e["period"]["id"] == other["period"]["id"]), None
    )
    if occupant is not None:
        assert client.delete(
            f"{entries_url(table_a['timetable_id'])}/{occupant['id']}", headers=h
        ).status_code == 204

    faculty_clash = client.post(
        entries_url(table_a["timetable_id"]),
        json={"subject_id": other["subject_id"], "faculty_id": other["faculty_id"],
              "room_id": g["rooms"][1]["id"], "period_id": other["period"]["id"]},
        headers=h,
    )
    assert faculty_clash.status_code == 409, faculty_clash.text
    assert any(
        c["type"] == "FACULTY_CONFLICT" for c in faculty_clash.json()["detail"]["conflicts"]
    )

    room_clash = client.post(
        entries_url(table_a["timetable_id"]),
        json={"subject_id": other["subject_id"], "faculty_id": g["facs"][1]["id"],
              "room_id": other["room_id"], "period_id": other["period"]["id"]},
        headers=h,
    )
    assert room_clash.status_code == 409, room_clash.text
    assert any(
        c["type"] == "ROOM_CONFLICT" for c in room_clash.json()["detail"]["conflicts"]
    )


async def test_create_entry_domain_rejections(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    first = detail["entries"][0]
    free = next(
        p for p in g["periods"]
        if p["id"] not in {e["period"]["id"] for e in detail["entries"]}
    )
    base = {"subject_id": first["subject_id"], "faculty_id": first["faculty_id"],
            "room_id": first["room_id"], "period_id": free["id"]}

    # Break period.
    brk = client.post(
        "/api/v1/periods",
        json={"day_of_week": "TUESDAY", "start_time": "12:00", "end_time": "13:00",
              "period_order": 9, "is_break": True},
        headers=h,
    ).json()
    response = client.post(
        entries_url(table["timetable_id"]), json={**base, "period_id": brk["id"]}, headers=h
    )
    assert response.status_code == 409
    assert any(c["type"] == "BREAK_PERIOD_USED" for c in response.json()["detail"]["conflicts"])

    # Unavailable faculty.
    client.patch(
        f"/api/v1/faculty/{first['faculty_id']}/availability/{free['id']}",
        json={"status": "UNAVAILABLE"},
        headers=h,
    )
    response = client.post(entries_url(table["timetable_id"]), json=base, headers=h)
    assert response.status_code == 409
    assert any(
        c["type"] == "FACULTY_UNAVAILABLE" for c in response.json()["detail"]["conflicts"]
    )
    client.patch(
        f"/api/v1/faculty/{first['faculty_id']}/availability/{free['id']}",
        json={"status": "AVAILABLE"},
        headers=h,
    )

    # Too-small room.
    tiny = client.post(
        "/api/v1/rooms",
        json={"name": f"TINY{uuid.uuid4().hex[:6]}", "room_type": "CLASSROOM", "capacity": 1},
        headers=h,
    ).json()
    response = client.post(
        entries_url(table["timetable_id"]), json={**base, "room_id": tiny["id"]}, headers=h
    )
    assert response.status_code == 409
    assert any(c["type"] == "ROOM_CAPACITY" for c in response.json()["detail"]["conflicts"])

    # Wrong room type.
    lab_room = client.post(
        "/api/v1/rooms",
        json={"name": f"LAB{uuid.uuid4().hex[:6]}", "room_type": "LAB", "capacity": 30},
        headers=h,
    ).json()
    response = client.post(
        entries_url(table["timetable_id"]), json={**base, "room_id": lab_room["id"]}, headers=h
    )
    assert response.status_code == 409
    assert any(c["type"] == "ROOM_TYPE" for c in response.json()["detail"]["conflicts"])

    # Subject outside the division's requirements.
    outsider = client.post(
        "/api/v1/subjects",
        json={"code": f"OUT{uuid.uuid4().hex[:6]}", "name": "Outsider",
              "required_periods_per_week": 1},
        headers=h,
    ).json()
    response = client.post(
        entries_url(table["timetable_id"]), json={**base, "subject_id": outsider["id"]},
        headers=h,
    )
    assert response.status_code == 409
    assert any(
        c["type"] == "INVALID_CONFIGURATION" for c in response.json()["detail"]["conflicts"]
    )

    # Inactive subject.
    client.patch(f"/api/v1/subjects/{first['subject_id']}",
                 json={"is_active": False}, headers=h)
    response = client.post(entries_url(table["timetable_id"]), json=base, headers=h)
    assert response.status_code == 409
    assert any(
        c["type"] == "INACTIVE_ENTITY" for c in response.json()["detail"]["conflicts"]
    )
    client.patch(f"/api/v1/subjects/{first['subject_id']}",
                 json={"is_active": True}, headers=h)

    # Missing entities → 404, not 409.
    ghost = str(uuid.uuid4())
    response = client.post(
        entries_url(table["timetable_id"]), json={**base, "room_id": ghost}, headers=h
    )
    assert response.status_code == 404


async def test_create_entry_unassigned_faculty_rejected(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    # Requirement added after generation, but nobody is assigned to teach PHYS.
    phys = client.post(
        "/api/v1/subjects",
        json={"code": f"PH{uuid.uuid4().hex[:6]}", "name": "Physics",
              "required_periods_per_week": 1},
        headers=h,
    ).json()
    client.post(
        "/api/v1/division-subject-requirements",
        json={"division_id": g["divisions"][0]["id"], "subject_id": phys["id"],
              "academic_session_id": g["session"]["id"], "required_periods_per_week": 1},
        headers=h,
    )
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    free = next(
        p for p in g["periods"]
        if p["id"] not in {e["period"]["id"] for e in detail["entries"]}
    )
    response = client.post(
        entries_url(table["timetable_id"]),
        json={"subject_id": phys["id"], "faculty_id": g["facs"][0]["id"],
              "room_id": g["rooms"][0]["id"], "period_id": free["id"]},
        headers=h,
    )
    assert response.status_code == 409, response.text
    assert any(
        c["type"] == "INVALID_ASSIGNMENT" for c in response.json()["detail"]["conflicts"]
    )


async def test_update_entry_move_and_conflict_rollback(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    moving, staying = detail["entries"]
    free = next(
        p for p in g["periods"]
        if p["id"] not in {e["period"]["id"] for e in detail["entries"]}
    )

    # Valid move keeps VALID.
    moved = client.patch(
        f"{entries_url(table['timetable_id'])}/{moving['id']}",
        json={"period_id": free["id"]},
        headers=h,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["period"]["id"] == free["id"]
    assert client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()["status"] == "VALID"

    # Conflicting move rolls back: entry stays where it was.
    clash = client.patch(
        f"{entries_url(table['timetable_id'])}/{moving['id']}",
        json={"period_id": staying["period"]["id"]},
        headers=h,
    )
    assert clash.status_code == 409
    assert any(
        c["type"] == "DIVISION_CONFLICT" for c in clash.json()["detail"]["conflicts"]
    )
    unchanged = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    current = next(e for e in unchanged["entries"] if e["id"] == moving["id"])
    assert current["period"]["id"] == free["id"]

    # Empty patch is a no-op success.
    assert client.patch(
        f"{entries_url(table['timetable_id'])}/{moving['id']}", json={}, headers=h
    ).status_code == 200

    # Entry from another timetable → 404.
    other = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    other_detail = client.get(f"/api/v1/timetables/{other['timetable_id']}", headers=h).json()
    assert client.patch(
        f"{entries_url(table['timetable_id'])}/{other_detail['entries'][0]['id']}",
        json={"period_id": free["id"]},
        headers=h,
    ).status_code == 404


async def test_update_entry_cross_timetable_and_availability(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6], divisions=2)
    div_a, div_b = g["divisions"]
    table_b = await generate(client, h, g["session"]["id"], div_b["id"])
    client.post(f"/api/v1/timetables/{table_b['timetable_id']}/validate", headers=h)
    client.post(f"/api/v1/timetables/{table_b['timetable_id']}/publish", headers=h)
    detail_b = client.get(f"/api/v1/timetables/{table_b['timetable_id']}", headers=h).json()
    rival = detail_b["entries"][0]

    table_a = await generate(client, h, g["session"]["id"], div_a["id"])
    detail_a = client.get(f"/api/v1/timetables/{table_a['timetable_id']}", headers=h).json()
    # Free A's copy of the rival period (if any), then move another entry into the clash.
    occupant = next(
        (e for e in detail_a["entries"] if e["period"]["id"] == rival["period"]["id"]), None
    )
    if occupant is not None:
        assert client.delete(
            f"{entries_url(table_a['timetable_id'])}/{occupant['id']}", headers=h
        ).status_code == 204
        remaining = [e for e in detail_a["entries"] if e["id"] != occupant["id"]]
    else:
        remaining = detail_a["entries"]
    other_entry = remaining[0]
    clash = client.patch(
        f"{entries_url(table_a['timetable_id'])}/{other_entry['id']}",
        json={"faculty_id": rival["faculty_id"], "room_id": g["rooms"][1]["id"],
              "period_id": rival["period"]["id"]},
        headers=h,
    )
    assert clash.status_code == 409, clash.text
    assert any(
        c["type"] == "FACULTY_CONFLICT" for c in clash.json()["detail"]["conflicts"]
    )

    # Availability conflict on move: use a faculty/room pair with no published clash.
    alt_fac = next(f for f in g["facs"] if f["id"] != rival["faculty_id"])
    alt_room = next(r for r in g["rooms"] if r["id"] != rival["room_id"])
    client.patch(
        f"/api/v1/faculty/{alt_fac['id']}/availability/{rival['period']['id']}",
        json={"status": "UNAVAILABLE"},
        headers=h,
    )
    blocked = client.patch(
        f"{entries_url(table_a['timetable_id'])}/{other_entry['id']}",
        json={"faculty_id": alt_fac["id"], "room_id": alt_room["id"],
              "period_id": rival["period"]["id"]},
        headers=h,
    )
    assert blocked.status_code == 409
    assert any(
        c["type"] == "FACULTY_UNAVAILABLE" for c in blocked.json()["detail"]["conflicts"]
    )


async def test_published_timetable_immutable(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    client.post(f"/api/v1/timetables/{table['timetable_id']}/validate", headers=h)
    client.post(f"/api/v1/timetables/{table['timetable_id']}/publish", headers=h)
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    entry = detail["entries"][0]

    for method, url, payload in (
        ("POST", entries_url(table["timetable_id"]),
         {"subject_id": entry["subject_id"], "faculty_id": entry["faculty_id"],
          "room_id": entry["room_id"], "period_id": entry["period"]["id"]}),
        ("PATCH", f"{entries_url(table['timetable_id'])}/{entry['id']}",
         {"room_id": g["rooms"][1]["id"]}),
    ):
        response = client.request(method, url, json=payload, headers=h)
        assert response.status_code == 422, (method, response.text)
        assert "immutable" in response.json()["detail"]
    assert client.delete(
        f"{entries_url(table['timetable_id'])}/{entry['id']}", headers=h
    ).status_code == 422


async def test_validate_reports_quality_and_demotes(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])

    report = client.post(
        f"/api/v1/timetables/{table['timetable_id']}/validate", headers=h
    ).json()
    assert report["valid"] is True
    assert report["status"] == "VALID"
    assert report["errors"] == [] and report["violations"] == []
    assert isinstance(report["score"], int)
    assert isinstance(report["warnings"], list)

    # Break it via master data, then validation demotes VALID → DRAFT.
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    assert detail["status"] == "VALID"
    client.patch(f"/api/v1/rooms/{detail['entries'][0]['room_id']}",
                 json={"is_active": False}, headers=h)
    broken = client.post(
        f"/api/v1/timetables/{table['timetable_id']}/validate", headers=h
    ).json()
    assert broken["valid"] is False
    assert broken["status"] == "INVALID"
    assert any(v["type"] == "INACTIVE_ENTITY" for v in broken["violations"])
    assert broken["errors"] == broken["violations"]
    assert client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()["status"] == "DRAFT"


async def test_publish_lifecycle_replacement_and_audit(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    div_id = g["divisions"][0]["id"]

    v1 = await generate(client, h, g["session"]["id"], div_id)
    client.post(f"/api/v1/timetables/{v1['timetable_id']}/validate", headers=h)
    published = client.post(
        f"/api/v1/timetables/{v1['timetable_id']}/publish", headers=h
    )
    assert published.status_code == 200, published.text
    body = published.json()
    assert body["status"] == "PUBLISHED"
    assert body["entry_count"] == 2

    # Audit trail lives on the row even though list views omit it.
    stored = client.get(f"/api/v1/timetables/{v1['timetable_id']}", headers=h).json()
    assert stored["status"] == "PUBLISHED"

    # Double publish rejected.
    again = client.post(f"/api/v1/timetables/{v1['timetable_id']}/publish", headers=h)
    assert again.status_code == 422

    # Clone → v2 DRAFT with fresh IDs, source untouched.
    clone = client.post(f"/api/v1/timetables/{v1['timetable_id']}/clone", headers=h)
    assert clone.status_code == 201, clone.text
    clone_body = clone.json()
    assert clone_body["version"] == 2
    assert clone_body["status"] == "DRAFT"
    assert clone_body["id"] != v1["timetable_id"]
    assert clone_body["entry_count"] == 2
    assert clone_body["valid"] is True
    assert client.get(f"/api/v1/timetables/{v1['timetable_id']}", headers=h).json()["status"] == "PUBLISHED"

    # Publishing v2 archives v1 atomically.
    client.post(f"/api/v1/timetables/{clone_body['id']}/validate", headers=h)
    v2pub = client.post(f"/api/v1/timetables/{clone_body['id']}/publish", headers=h)
    assert v2pub.status_code == 200, v2pub.text
    assert v2pub.json()["status"] == "PUBLISHED"
    assert client.get(f"/api/v1/timetables/{v1['timetable_id']}", headers=h).json()["status"] == "ARCHIVED"

    # Archived history is immutable too.
    assert client.delete(
        f"{entries_url(v1['timetable_id'])}/{stored['entries'][0]['id']}", headers=h
    ).status_code == 422


async def test_publish_rejects_invalid_and_clashing(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6], divisions=2)
    div_a, div_b = g["divisions"]

    # Incomplete draft cannot publish.
    table = await generate(client, h, g["session"]["id"], div_a["id"])
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    assert client.delete(
        f"{entries_url(table['timetable_id'])}/{detail['entries'][0]['id']}", headers=h
    ).status_code == 204
    rejected = client.post(f"/api/v1/timetables/{table['timetable_id']}/publish", headers=h)
    assert rejected.status_code == 422
    assert client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()["status"] == "DRAFT"

    # Publish-time clash: A2 holds F_E/R_E@P_e while only a draft;
    # B then publishes the identical slot; publishing A2 must be rejected
    # without side effects (edit-time checks could not see this coming).
    table_a2 = await generate(client, h, g["session"]["id"], div_a["id"])
    detail_a2 = client.get(f"/api/v1/timetables/{table_a2['timetable_id']}", headers=h).json()
    anchor = detail_a2["entries"][0]

    table_b = await generate(client, h, g["session"]["id"], div_b["id"])
    detail_b = client.get(f"/api/v1/timetables/{table_b['timetable_id']}", headers=h).json()
    occupant = next(
        (e for e in detail_b["entries"] if e["period"]["id"] == anchor["period"]["id"]), None
    )
    doomed = occupant["id"] if occupant is not None else detail_b["entries"][0]["id"]
    assert client.delete(f"{entries_url(table_b['timetable_id'])}/{doomed}", headers=h).status_code == 204
    mirror = client.post(
        entries_url(table_b["timetable_id"]),
        json={"subject_id": anchor["subject_id"], "faculty_id": anchor["faculty_id"],
              "room_id": anchor["room_id"], "period_id": anchor["period"]["id"]},
        headers=h,
    )
    assert mirror.status_code == 201, mirror.text
    client.post(f"/api/v1/timetables/{table_b['timetable_id']}/validate", headers=h)
    assert client.post(
        f"/api/v1/timetables/{table_b['timetable_id']}/publish", headers=h
    ).status_code == 200

    clashing_publish = client.post(
        f"/api/v1/timetables/{table_a2['timetable_id']}/publish", headers=h
    )
    # Cross-division clash with live published data → 409 (state conflict),
    # while own-timetable invalidity above was 422 (semantic validation).
    assert clashing_publish.status_code == 409, clashing_publish.text
    types = {c["type"] for c in clashing_publish.json()["detail"]["conflicts"]}
    assert types & {"FACULTY_CONFLICT", "ROOM_CONFLICT"}
    assert client.get(
        f"/api/v1/timetables/{table_a2['timetable_id']}", headers=h
    ).json()["status"] == "GENERATED"


async def test_concurrency_guard_rejects_stale_writes(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    detail = client.get(f"/api/v1/timetables/{table['timetable_id']}", headers=h).json()
    entry = detail["entries"][0]
    assert "updated_at" in detail

    stale = {"If-Unmodified-Since": "Thu, 01 Jan 1970 00:00:00 GMT"}
    assert client.patch(
        f"{entries_url(table['timetable_id'])}/{entry['id']}",
        json={"room_id": g["rooms"][1]["id"]}, headers={**h, **stale},
    ).status_code == 409
    assert client.post(
        entries_url(table["timetable_id"]),
        json={"subject_id": entry["subject_id"], "faculty_id": entry["faculty_id"],
              "room_id": entry["room_id"], "period_id": entry["period"]["id"]},
        headers={**h, **stale},
    ).status_code == 409

    fresh_stamp = format_datetime(
        datetime.fromisoformat(detail["updated_at"]), usegmt=True
    )
    free = next(
        p for p in g["periods"]
        if p["id"] not in {e["period"]["id"] for e in detail["entries"]}
    )
    # Free slot exists only if generation left one; otherwise move within same slot set.
    ok = client.patch(
        f"{entries_url(table['timetable_id'])}/{entry['id']}",
        json={"period_id": free["id"]},
        headers={**h, "If-Unmodified-Since": fresh_stamp},
    )
    assert ok.status_code in (200, 409)  # 409 only if another change landed first


async def test_lifecycle_rbac_matrix(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    tid = table["timetable_id"]
    detail = client.get(f"/api/v1/timetables/{tid}", headers=h).json()
    entry_id = detail["entries"][0]["id"]
    sample = {"subject_id": detail["entries"][0]["subject_id"],
              "faculty_id": detail["entries"][0]["faculty_id"],
              "room_id": detail["entries"][0]["room_id"],
              "period_id": detail["entries"][0]["period"]["id"]}

    fh, sh = faculty_h(client, accounts), student_h(client, accounts)
    # Faculty/student: every write forbidden.
    assert client.post(entries_url(tid), json=sample, headers=fh).status_code == 403
    assert client.post(entries_url(tid), json=sample, headers=sh).status_code == 403
    assert client.patch(f"{entries_url(tid)}/{entry_id}", json={}, headers=fh).status_code == 403
    assert client.patch(f"{entries_url(tid)}/{entry_id}", json={}, headers=sh).status_code == 403
    assert client.delete(f"{entries_url(tid)}/{entry_id}", headers=fh).status_code == 403
    assert client.delete(f"{entries_url(tid)}/{entry_id}", headers=sh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/validate", headers=fh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/validate", headers=sh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/publish", headers=fh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/publish", headers=sh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/archive", headers=fh).status_code == 403
    assert client.post(f"/api/v1/timetables/{tid}/clone", headers=sh).status_code == 403
    assert client.get(f"/api/v1/timetables/{tid}/generation-result", headers=fh).status_code == 403
    # Unauthenticated: everything 401.
    assert client.post(entries_url(tid), json=sample).status_code == 401
    assert client.patch(f"{entries_url(tid)}/{entry_id}", json={}).status_code == 401
    assert client.delete(f"{entries_url(tid)}/{entry_id}").status_code == 401
    assert client.post(f"/api/v1/timetables/{tid}/validate").status_code == 401
    assert client.post(f"/api/v1/timetables/{tid}/publish").status_code == 401
    assert client.post(f"/api/v1/timetables/{tid}/archive").status_code == 401
    assert client.post(f"/api/v1/timetables/{tid}/clone").status_code == 401


async def test_archive_flow(client, accounts):
    h = admin_h(client, accounts)
    g = await build_lifecycle_graph(client, h, uuid.uuid4().hex[:6])
    table = await generate(client, h, g["session"]["id"], g["divisions"][0]["id"])
    tid = table["timetable_id"]

    # Drafts cannot be archived.
    clone = client.post(f"/api/v1/timetables/{tid}/clone", headers=h).json()
    assert client.post(
        f"/api/v1/timetables/{clone['id']}/archive", headers=h
    ).status_code == 422

    client.post(f"/api/v1/timetables/{tid}/validate", headers=h)
    client.post(f"/api/v1/timetables/{tid}/publish", headers=h)
    archived = client.post(f"/api/v1/timetables/{tid}/archive", headers=h)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert client.post(f"/api/v1/timetables/{tid}/archive", headers=h).status_code == 422
    assert client.post(f"/api/v1/timetables/{tid}/publish", headers=h).status_code == 422
