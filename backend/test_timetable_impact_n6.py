import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.course_meeting import CourseMeeting
from app.models.student_availability import StudentAvailability
from app.models.time_block import BlockStatus, BlockType, TimeBlock

client = TestClient(app)


def create_test_user(prefix: str) -> tuple[int, str]:
    """Helper to register a unique test user and return (user_id, token)."""
    email = f"{prefix}_{int(time.time() * 1000)}@univ-test.edu"
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "timezone": "America/New_York",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return data["user_id"], data["token"]


def create_test_institution(admin_token: str, name_prefix: str = "Test University") -> tuple[int, str]:
    """Helper to create an institution where the user becomes admin."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"INST_{int(time.time() * 1000)}"[:16]
    resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={
            "name": f"{name_prefix} {code}",
            "code": code,
            "timezone": "America/New_York",
            "country": "US",
        },
    )
    assert resp.status_code == 201, resp.text
    inst_id = resp.json()["data"]["id"]
    return inst_id, code


def create_test_term(admin_token: str, inst_id: int, name: str = "Fall 2026", status: str = "active") -> int:
    """Helper to create an academic term."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": name,
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "status": status,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def create_test_room(
    admin_token: str,
    inst_id: int,
    room_number: str = "101",
    capacity: int = 50,
    building: str = "Main Hall",
    room_type: str = "classroom",
) -> int:
    """Helper to create a room."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=headers,
        json={
            "room_number": room_number,
            "building": building,
            "capacity": capacity,
            "room_type": room_type,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def add_member(admin_token: str, inst_id: int, user_id: int, role: str = "student") -> dict:
    """Helper for admin to add a member to the institution."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def setup_university_env():
    """Sets up a complete university baseline environment for N6 testing."""
    admin_id, admin_token = create_test_user("admin_n6")
    inst_id, _ = create_test_institution(admin_token, "N6 Impact University")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Dept
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": "CS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    # Term
    term_id = create_test_term(admin_token, inst_id, "Fall 2026", status="active")

    # Course
    crs_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={
            "department_id": dept_id,
            "code": "CS301",
            "name": "Database Systems",
            "credits": 3,
        },
    )
    crs_id = crs_resp.json()["data"]["id"]

    # Section A (Capacity 40)
    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": crs_id,
            "academic_term_id": term_id,
            "section_code": "A",
            "capacity": 40,
        },
    )
    sec_id = sec_resp.json()["data"]["id"]

    # Room (Capacity 50)
    room_id = create_test_room(admin_token, inst_id, room_number="B204", capacity=50, building="Turing Hall")

    # Timetable
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={
            "academic_term_id": term_id,
            "name": "Fall 2026 Master Timetable",
            "status": "active",
        },
    )
    tt_id = tt_resp.json()["data"]["id"]

    # Meeting: Monday 10:00–11:00 in Room B204
    mtg_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id,
            "day_of_week": 1,  # Monday
            "start_time": "10:00",
            "end_time": "11:00",
            "room_id": room_id,
            "meeting_type": "lecture",
        },
    )
    assert mtg_resp.status_code == 201, mtg_resp.text
    meeting_data = mtg_resp.json()["data"]

    return {
        "admin_id": admin_id,
        "admin_token": admin_token,
        "admin_headers": admin_headers,
        "inst_id": inst_id,
        "dept_id": dept_id,
        "term_id": term_id,
        "crs_id": crs_id,
        "sec_id": sec_id,
        "room_id": room_id,
        "tt_id": tt_id,
        "meeting": meeting_data,
    }


def test_proposed_change_preview_valid():
    """
    Verify previewing a proposed meeting move:
    - Calculates real enrolled students count (not section capacity).
    - Detects student work shift overlaps.
    - Detects student availability blackout overlaps.
    - Accurately classifies severity.
    - Confirms database is NOT mutated (strictly read-only).
    """
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    sec_id = env["sec_id"]
    meeting = env["meeting"]
    admin_headers = env["admin_headers"]

    # 1. Create 3 test students
    stu1_id, stu1_tok = create_test_user("student_work")
    stu2_id, stu2_tok = create_test_user("student_blackout")
    stu3_id, stu3_tok = create_test_user("student_clear")

    add_member(env["admin_token"], inst_id, stu1_id, "student")
    add_member(env["admin_token"], inst_id, stu2_id, "student")
    add_member(env["admin_token"], inst_id, stu3_id, "student")

    # Student 1: has a work shift on Tuesday 14:00–16:00
    with SessionLocal() as db:
        shift = TimeBlock(
            user_id=stu1_id,
            type=BlockType.SHIFT,
            status=BlockStatus.ENROLLED,
            title="Cafe Barista",
            day_of_week=2,  # Tuesday
            start_time=dt_time(14, 0),
            end_time=dt_time(16, 0),
            duration_minutes=120,
            is_recurring=True,
            deleted=False,
        )
        db.add(shift)

        # Student 2: has an unavailable blackout on Tuesday 14:30–15:30
        avail = StudentAvailability(
            user_id=stu2_id,
            institution_id=inst_id,
            day_of_week=2,  # Tuesday
            start_time=dt_time(14, 30),
            end_time=dt_time(15, 30),
            is_available=False,
            title="Doctor appointment",
        )
        db.add(avail)
        db.commit()

    # Enroll all 3 students in section A
    for tok in [stu1_tok, stu2_tok, stu3_tok]:
        enr_resp = client.post(
            f"/api/v1/students/me/enrollments",
            headers={"Authorization": f"Bearer {tok}"},
            json={"section_id": sec_id},
        )
        assert enr_resp.status_code == 201, enr_resp.text

    # 2. Admin calls PREVIEW: propose moving class to Tuesday 14:00–15:15
    preview_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/preview",
        headers=admin_headers,
        json={
            "meeting_id": meeting["id"],
            "day_of_week": 2,  # Tuesday
            "start_time": "14:00",
            "end_time": "15:15",
            "room_id": env["room_id"],
        },
    )
    assert preview_resp.status_code == 200, preview_resp.text
    data = preview_resp.json()["data"]

    # 3. Assertions on impact
    assert data["is_blocked"] is False
    summary = data["summary"]
    assert summary["students_affected"] == 3  # Actual enrolled students
    assert summary["new_conflicts"] == 2  # Stu 1 work shift + Stu 2 blackout
    assert summary["work_conflicts"] == 1
    assert summary["availability_conflicts"] == 1
    assert summary["severity"] in ["HIGH", "MEDIUM"]

    # Before / After snapshots
    assert data["before"]["day_of_week"] == 1
    assert data["before"]["start_time"] == "10:00"
    assert data["after"]["day_of_week"] == 2
    assert data["after"]["start_time"] == "14:00"
    assert data["after"]["end_time"] == "15:15"

    # Verify student impacts list contains the 3 students
    student_impacts = data["student_impacts"]
    assert len(student_impacts) == 3
    conflict_types = {s["conflict_type"] for s in student_impacts}
    assert "work_shift" in conflict_types
    assert "unavailable" in conflict_types
    assert "none" in conflict_types

    # Privacy verification: no wage or private notes in description
    for s in student_impacts:
        assert "$" not in s["conflict_description"]
        assert "Doctor" not in s["conflict_description"]  # Blackout private title masked

    # 4. Verify database is NOT mutated (strictly read-only)
    with SessionLocal() as db:
        m_fresh = db.query(CourseMeeting).filter(CourseMeeting.id == meeting["id"]).first()
        assert m_fresh.day_of_week == 1  # Still Monday!
        assert str(m_fresh.start_time).startswith("10:00")  # Still 10:00!


def test_proposed_change_preview_blocked_room_conflict():
    """Verify that a proposed move causing a room collision returns severity BLOCKED and cannot be applied."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    room_id = env["room_id"]
    admin_headers = env["admin_headers"]

    # Create Section B in same course
    sec_resp_b = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": env["crs_id"],
            "academic_term_id": env["term_id"],
            "section_code": "B",
            "capacity": 30,
        },
    )
    sec_id_b = sec_resp_b.json()["data"]["id"]

    # Schedule Section B in Room B204 on Tuesday 14:00–15:00
    m2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id_b,
            "day_of_week": 2,
            "start_time": "14:00",
            "end_time": "15:00",
            "room_id": room_id,
        },
    )
    assert m2_resp.status_code == 201

    # Propose moving Section A meeting into the same room at overlapping time (Tuesday 14:30–15:30)
    preview_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/preview",
        headers=admin_headers,
        json={
            "meeting_id": env["meeting"]["id"],
            "day_of_week": 2,
            "start_time": "14:30",
            "end_time": "15:30",
            "room_id": room_id,
        },
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()["data"]

    assert data["is_blocked"] is True
    assert data["summary"]["severity"] == "BLOCKED"
    assert len(data["summary"]["blocked_reasons"]) >= 1
    assert "already occupied" in data["summary"]["blocked_reasons"][0]

    # Try to APPLY this blocked change -> Must fail with 409
    apply_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/apply",
        headers=admin_headers,
        json={
            "meeting_id": env["meeting"]["id"],
            "day_of_week": 2,
            "start_time": "14:30",
            "end_time": "15:30",
            "room_id": room_id,
        },
    )
    assert apply_resp.status_code == 409
    assert apply_resp.json()["error"]["code"] == "change_blocked"


def test_proposed_change_preview_blocked_faculty_conflict():
    """Verify that a proposed move causing a faculty overlap returns severity BLOCKED."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    admin_headers = env["admin_headers"]

    # Create Faculty member
    fac_user_id, _ = create_test_user("prof_overlap")
    add_member(env["admin_token"], inst_id, fac_user_id, "professor")

    fac_resp = client.post(
        f"/api/v1/institutions/{inst_id}/faculty",
        headers=admin_headers,
        json={"user_id": fac_user_id, "title": "Dr.", "department_id": env["dept_id"]},
    )
    assert fac_resp.status_code == 201
    faculty_id = fac_resp.json()["data"]["id"]

    # Create Room 2
    room_2 = create_test_room(env["admin_token"], inst_id, room_number="C101", capacity=50)

    # Assign faculty to Meeting 1 (currently Mon 10:00)
    client.patch(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings/{env['meeting']['id']}",
        headers=admin_headers,
        json={"faculty_id": faculty_id},
    )

    # Create Section B and schedule on Wednesday 11:00–12:00 in Room C101 with same faculty
    sec_resp_b = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": env["crs_id"],
            "academic_term_id": env["term_id"],
            "section_code": "B",
            "capacity": 30,
        },
    )
    sec_id_b = sec_resp_b.json()["data"]["id"]

    client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id_b,
            "day_of_week": 3,  # Wednesday
            "start_time": "11:00",
            "end_time": "12:00",
            "room_id": room_2,
            "faculty_id": faculty_id,
        },
    )

    # Propose moving Meeting 1 to Wednesday 11:30–12:30 with same faculty (in Room B204)
    preview_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/preview",
        headers=admin_headers,
        json={
            "meeting_id": env["meeting"]["id"],
            "day_of_week": 3,
            "start_time": "11:30",
            "end_time": "12:30",
            "room_id": env["room_id"],
            "faculty_id": faculty_id,
        },
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()["data"]

    assert data["is_blocked"] is True
    assert data["summary"]["severity"] == "BLOCKED"
    assert any("has another meeting scheduled" in r for r in data["summary"]["blocked_reasons"])


def test_proposed_change_preview_blocked_capacity():
    """Verify that assigning a section to an undersized room is BLOCKED."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    admin_headers = env["admin_headers"]

    # Section A capacity is 40. Create small room with capacity 20.
    small_room_id = create_test_room(
        env["admin_token"], inst_id, room_number="Mini-10", capacity=20, building="Small Hall"
    )

    preview_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/preview",
        headers=admin_headers,
        json={
            "meeting_id": env["meeting"]["id"],
            "day_of_week": 1,
            "start_time": "13:00",
            "end_time": "14:00",
            "room_id": small_room_id,
        },
    )
    assert preview_resp.status_code == 200
    data = preview_resp.json()["data"]

    assert data["is_blocked"] is True
    assert data["summary"]["severity"] == "BLOCKED"
    assert any("capacity" in r.lower() for r in data["summary"]["blocked_reasons"])


def test_apply_change_atomic_and_audit():
    """Verify applying a valid change atomically modifies CourseMeeting and writes an audit log."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    meeting = env["meeting"]
    admin_headers = env["admin_headers"]

    # Call Apply
    apply_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/apply",
        headers=admin_headers,
        json={
            "meeting_id": meeting["id"],
            "day_of_week": 4,  # Thursday
            "start_time": "15:00",
            "end_time": "16:15",
            "room_id": env["room_id"],
            "expected_updated_at": meeting["updated_at"],
        },
    )
    assert apply_resp.status_code == 200, apply_resp.text
    apply_data = apply_resp.json()["data"]
    assert apply_data["success"] is True
    assert apply_data["meeting"]["day_of_week"] == 4
    assert apply_data["meeting"]["start_time"] == "15:00"
    assert apply_data["meeting"]["end_time"] == "16:15"

    # Verify CourseMeeting in DB
    with SessionLocal() as db:
        m = db.query(CourseMeeting).filter(CourseMeeting.id == meeting["id"]).first()
        assert m.day_of_week == 4
        assert str(m.start_time).startswith("15:00")
        assert str(m.end_time).startswith("16:15")

        # Verify Audit Log entry created
        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == env["admin_id"],
                AuditLog.action == "timetable_meeting_change",
                AuditLog.entity_id == meeting["id"],
            )
            .first()
        )
        assert audit is not None
        assert "Modified class meeting" in audit.description
        assert "CS301" in audit.description
        assert audit.metadata_json is not None
        assert "impact" in audit.metadata_json


def test_apply_change_stale_concurrency_rejection():
    """Verify that applying with a stale expected_updated_at is rejected with 409 Conflict."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    meeting = env["meeting"]
    admin_headers = env["admin_headers"]

    stale_timestamp = "2020-01-01T00:00:00Z"

    apply_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/apply",
        headers=admin_headers,
        json={
            "meeting_id": meeting["id"],
            "day_of_week": 5,
            "start_time": "09:00",
            "end_time": "10:15",
            "expected_updated_at": stale_timestamp,
        },
    )
    assert apply_resp.status_code == 409
    err = apply_resp.json()["error"]
    assert err["code"] == "stale_preview"
    assert "timetable changed since you reviewed it" in err["message"]


def test_tenant_isolation_impact_analysis():
    """Verify that Institution A admin cannot preview or apply changes to Institution B timetable."""
    env_a = setup_university_env()
    env_b = setup_university_env()

    # Admin A attempts to preview Institution B's meeting on Institution B's timetable
    resp_cross = client.post(
        f"/api/v1/institutions/{env_b['inst_id']}/timetables/{env_b['tt_id']}/changes/preview",
        headers=env_a["admin_headers"],
        json={
            "meeting_id": env_b["meeting"]["id"],
            "day_of_week": 1,
            "start_time": "11:00",
            "end_time": "12:00",
        },
    )
    assert resp_cross.status_code in [403, 404]

    # Admin A attempts to apply change on Institution B
    resp_apply_cross = client.post(
        f"/api/v1/institutions/{env_b['inst_id']}/timetables/{env_b['tt_id']}/changes/apply",
        headers=env_a["admin_headers"],
        json={
            "meeting_id": env_b["meeting"]["id"],
            "day_of_week": 1,
            "start_time": "11:00",
            "end_time": "12:00",
        },
    )
    assert resp_apply_cross.status_code in [403, 404]


def test_student_schedule_automatic_update():
    """Verify that when an admin applies a meeting change, the enrolled student's schedule updates automatically."""
    env = setup_university_env()
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    sec_id = env["sec_id"]
    meeting = env["meeting"]
    admin_headers = env["admin_headers"]

    # Student registers and enrolls
    stu_id, stu_tok = create_test_user("student_sched_sync")
    add_member(env["admin_token"], inst_id, stu_id, "student")
    stu_headers = {"Authorization": f"Bearer {stu_tok}"}

    client.post(
        f"/api/v1/students/me/enrollments",
        headers=stu_headers,
        json={"section_id": sec_id},
    )

    # 1. Student checks schedule BEFORE change -> Meeting is Monday 10:00
    sched_before = client.get("/api/v1/students/me/schedule", headers=stu_headers)
    assert sched_before.status_code == 200
    meetings_before = sched_before.json()["data"]["meetings"]
    assert len(meetings_before) == 1
    assert meetings_before[0]["day_of_week"] == 1
    assert meetings_before[0]["start_time"].startswith("10:00")

    # 2. Admin applies change to Thursday 16:00–17:15
    apply_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/changes/apply",
        headers=admin_headers,
        json={
            "meeting_id": meeting["id"],
            "day_of_week": 4,  # Thursday
            "start_time": "16:00",
            "end_time": "17:15",
            "room_id": env["room_id"],
            "expected_updated_at": meeting["updated_at"],
        },
    )
    assert apply_resp.status_code == 200

    # 3. Student checks schedule AFTER change -> Automatically reflects Thursday 16:00!
    sched_after = client.get("/api/v1/students/me/schedule", headers=stu_headers)
    assert sched_after.status_code == 200
    meetings_after = sched_after.json()["data"]["meetings"]
    assert len(meetings_after) == 1
    assert meetings_after[0]["day_of_week"] == 4
    assert meetings_after[0]["start_time"].startswith("16:00")
    assert meetings_after[0]["end_time"].startswith("17:15")
