import time
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

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
    """Helper to create an academic term with valid required fields."""
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
    """Helper to create a room with all required fields."""
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
    """Helper for admin to add a user to the institution."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_timetable_crud_lifecycle():
    """Verify Timetable create, read, update, list with filters, and archive/delete."""
    # 1. Setup institution and admin
    admin_id, admin_token = create_test_user("admin_tt_crud")
    inst_id, _ = create_test_institution(admin_token, "Timetable University")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create academic term
    term_id = create_test_term(admin_token, inst_id, "Fall 2026", status="active")

    # 2. Create baseline timetable
    create_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={
            "academic_term_id": term_id,
            "name": "Fall 2026 Authoritative Baseline",
            "description": "Main campus official timetable",
            "status": "draft",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    tt_data = create_resp.json()["data"]
    tt_id = tt_data["id"]
    assert tt_data["institution_id"] == inst_id
    assert tt_data["academic_term_id"] == term_id
    assert tt_data["name"] == "Fall 2026 Authoritative Baseline"
    assert tt_data["status"] == "draft"

    # 3. Retrieve timetable by ID
    get_resp = client.get(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}",
        headers=admin_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == tt_id

    # 4. List timetables with filters
    list_resp = client.get(
        f"/api/v1/institutions/{inst_id}/timetables?term_id={term_id}&status=draft",
        headers=admin_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert len(items) >= 1
    assert any(item["id"] == tt_id for item in items)

    # 5. Update timetable (set to active)
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}",
        headers=admin_headers,
        json={
            "name": "Fall 2026 Official Baseline",
            "status": "active",
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()["data"]
    assert updated["name"] == "Fall 2026 Official Baseline"
    assert updated["status"] == "active"

    # 6. Archive timetable
    del_resp = client.delete(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 7. Verified archived timetable is not returned by active fetch
    get_deleted = client.get(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}",
        headers=admin_headers,
    )
    assert get_deleted.status_code == 404


def test_course_meeting_crud_and_consecutive_scheduling():
    """Verify CourseMeeting create, read, update, delete, and back-to-back non-overlapping scheduling."""
    admin_id, admin_token = create_test_user("admin_mtg_crud")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": "CS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    # Term
    term_id = create_test_term(admin_token, inst_id, "Spring 2026", status="active")

    # Course
    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={
            "department_id": dept_id,
            "code": "CS301",
            "name": "Database Systems",
            "credits": 3,
        },
    )
    course_id = course_resp.json()["data"]["id"]

    # Section A (Capacity 40)
    sec_resp_a = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "A",
            "capacity": 40,
        },
    )
    sec_id_a = sec_resp_a.json()["data"]["id"]

    # Section B (Capacity 40)
    sec_resp_b = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "B",
            "capacity": 40,
        },
    )
    sec_id_b = sec_resp_b.json()["data"]["id"]

    # Room (Capacity 60)
    room_id = create_test_room(
        admin_token, inst_id, room_number="B204", capacity=60, building="Turing Hall", room_type="lecture_hall"
    )

    # Timetable
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={
            "academic_term_id": term_id,
            "name": "Spring 2026 Baseline",
            "status": "active",
        },
    )
    tt_id = tt_resp.json()["data"]["id"]

    # Create Meeting 1: Section A on Monday (day 1), 09:00 - 10:00 in Room B204
    mtg1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id_a,
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "10:00",
            "room_id": room_id,
            "meeting_type": "lecture",
        },
    )
    assert mtg1_resp.status_code == 201, mtg1_resp.text
    mtg1 = mtg1_resp.json()["data"]
    assert mtg1["section_id"] == sec_id_a
    assert mtg1["room_id"] == room_id
    assert mtg1["day_of_week"] == 1
    assert mtg1["start_time"].startswith("09:00")
    assert mtg1["end_time"].startswith("10:00")

    # Create Meeting 2: Section B on Monday (day 1), consecutive back-to-back: 10:00 - 11:00 in same Room B204
    # This must NOT conflict because A.end (10:00) == B.start (10:00) (not A.start < B.end AND B.start < A.end)
    mtg2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id_b,
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "11:00",
            "room_id": room_id,
            "meeting_type": "lecture",
        },
    )
    assert mtg2_resp.status_code == 201, mtg2_resp.text
    mtg2 = mtg2_resp.json()["data"]
    assert mtg2["id"] != mtg1["id"]

    # Retrieve Meeting
    get_mtg_resp = client.get(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings/{mtg1['id']}",
        headers=admin_headers,
    )
    assert get_mtg_resp.status_code == 200
    assert get_mtg_resp.json()["data"]["id"] == mtg1["id"]

    # Update Meeting
    patch_mtg_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings/{mtg1['id']}",
        headers=admin_headers,
        json={"meeting_type": "tutorial"},
    )
    assert patch_mtg_resp.status_code == 200
    assert patch_mtg_resp.json()["data"]["meeting_type"] == "tutorial"

    # Delete Meeting
    del_mtg_resp = client.delete(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings/{mtg2['id']}",
        headers=admin_headers,
    )
    assert del_mtg_resp.status_code == 200
    assert del_mtg_resp.json()["data"]["deleted"] is True


def test_validation_and_conflict_engine():
    """Verify input validation, room capacity enforcement, and overlap conflicts (room, section, faculty)."""
    admin_id, admin_token = create_test_user("admin_validator")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Department, Term, Course
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Mathematics", "code": "MATH"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    term_id = create_test_term(admin_token, inst_id, "Fall 2026", status="active")

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "MATH201", "name": "Linear Algebra"},
    )
    course_id = course_resp.json()["data"]["id"]

    # Faculty Profile
    fac_user_id, _ = create_test_user("prof_euler")
    add_member(admin_token, inst_id, fac_user_id, role="professor")
    fac_resp = client.post(
        f"/api/v1/institutions/{inst_id}/faculty",
        headers=admin_headers,
        json={
            "user_id": fac_user_id,
            "department_id": dept_id,
            "title": "Dr.",
        },
    )
    fac_id = fac_resp.json()["data"]["id"]

    # Section 1 (Capacity 50) assigned to Dr. Euler
    sec1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "01",
            "capacity": 50,
        },
    )
    sec1_id = sec1_resp.json()["data"]["id"]

    client.post(
        f"/api/v1/institutions/{inst_id}/sections/{sec1_id}/faculty",
        headers=admin_headers,
        json={"faculty_id": fac_id, "role": "primary_instructor", "is_primary": True},
    )

    # Section 2 (Capacity 30)
    sec2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "02",
            "capacity": 30,
        },
    )
    sec2_id = sec2_resp.json()["data"]["id"]

    # Small Room (Capacity 40)
    small_room_id = create_test_room(
        admin_token, inst_id, room_number="101", capacity=40, building="Euler Hall", room_type="classroom"
    )

    # Large Room (Capacity 100)
    large_room_id = create_test_room(
        admin_token, inst_id, room_number="Auditorium", capacity=100, building="Main Campus", room_type="auditorium"
    )

    # Timetable
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={"academic_term_id": term_id, "name": "MATH Schedule", "status": "active"},
    )
    tt_id = tt_resp.json()["data"]["id"]

    # 1. Validation: start_time >= end_time rejected
    bad_time_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec1_id,
            "day_of_week": 2,
            "start_time": "14:00",
            "end_time": "13:00",
            "room_id": large_room_id,
        },
    )
    assert bad_time_resp.status_code == 422
    assert bad_time_resp.json()["error"]["code"] == "invalid_time_range"

    # 2. Validation: Room capacity too small (room cap 40 < section cap 50)
    small_room_fail_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec1_id,
            "day_of_week": 2,
            "start_time": "10:00",
            "end_time": "11:00",
            "room_id": small_room_id,
        },
    )
    assert small_room_fail_resp.status_code == 422
    assert small_room_fail_resp.json()["error"]["code"] == "insufficient_room_capacity"

    # 3. Create initial valid meeting for Section 1 in large_room on Tuesday 10:00 - 11:30
    ok_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec1_id,
            "day_of_week": 2,
            "start_time": "10:00",
            "end_time": "11:30",
            "room_id": large_room_id,
        },
    )
    assert ok_resp.status_code == 201

    # 4. Conflict: Overlapping room meeting (Section 2 attempts large_room on Tuesday 10:30 - 12:00)
    room_conflict_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec2_id,
            "day_of_week": 2,
            "start_time": "10:30",
            "end_time": "12:00",
            "room_id": large_room_id,
        },
    )
    assert room_conflict_resp.status_code == 409
    assert room_conflict_resp.json()["error"]["code"] == "room_conflict"

    # 5. Conflict: Overlapping section meeting (Section 1 attempts another meeting on Tuesday 11:00 - 12:00 in small_room)
    section_conflict_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec1_id,
            "day_of_week": 2,
            "start_time": "11:00",
            "end_time": "12:00",
            "room_id": None,
        },
    )
    assert section_conflict_resp.status_code == 409
    assert section_conflict_resp.json()["error"]["code"] == "section_conflict"

    # 6. Conflict: Overlapping faculty meeting
    # Section 2 explicitly assigns Dr. Euler to a meeting on Tuesday 10:45 - 11:45
    faculty_conflict_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec2_id,
            "day_of_week": 2,
            "start_time": "10:45",
            "end_time": "11:45",
            "room_id": small_room_id,
            "faculty_id": fac_id,
        },
    )
    assert faculty_conflict_resp.status_code == 409
    assert faculty_conflict_resp.json()["error"]["code"] == "faculty_conflict"


def test_student_schedule_and_calendar_integration():
    """Verify enrolled student automatically sees active baseline meetings in their schedule and calendar."""
    # 1. Setup university, course, section, room, timetable, meetings
    admin_id, admin_token = create_test_user("admin_std_integ")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    term_id = create_test_term(admin_token, inst_id, "Fall 2026", status="active")

    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Physics", "code": "PHYS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "PHYS101", "name": "Mechanics", "credits": 4},
    )
    course_id = course_resp.json()["data"]["id"]

    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "01",
            "capacity": 50,
        },
    )
    sec_id = sec_resp.json()["data"]["id"]

    room_id = create_test_room(
        admin_token, inst_id, room_number="Lab-1", capacity=60, building="Newton Lab", room_type="lab"
    )

    # Create active baseline timetable
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={"academic_term_id": term_id, "name": "Fall 2026 Master", "status": "active"},
    )
    tt_id = tt_resp.json()["data"]["id"]

    # Add Meeting: Wednesday (day 3), 14:00 - 16:00
    mtg_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id,
            "day_of_week": 3,
            "start_time": "14:00",
            "end_time": "16:00",
            "room_id": room_id,
            "meeting_type": "laboratory",
        },
    )
    assert mtg_resp.status_code == 201
    mtg_id = mtg_resp.json()["data"]["id"]

    # 2. Setup Student
    std_id, std_token = create_test_user("student_integ")
    add_member(admin_token, inst_id, std_id, role="student")
    std_headers = {"Authorization": f"Bearer {std_token}"}

    # Initially, student is NOT enrolled: schedule must be empty
    sched_resp_empty = client.get("/api/v1/students/me/schedule", headers=std_headers)
    assert sched_resp_empty.status_code == 200
    assert sched_resp_empty.json()["data"]["enrolled_sections_count"] == 0
    assert len(sched_resp_empty.json()["data"]["meetings"]) == 0

    # 3. Student enrolls in section
    enroll_resp = client.post(
        "/api/v1/students/me/enrollments",
        headers=std_headers,
        json={"section_id": sec_id},
    )
    assert enroll_resp.status_code == 201
    enrollment_id = enroll_resp.json()["data"]["id"]

    # 4. Now student's academic schedule MUST include the course meeting
    sched_resp = client.get("/api/v1/students/me/schedule", headers=std_headers)
    assert sched_resp.status_code == 200
    sched_data = sched_resp.json()["data"]
    assert sched_data["enrolled_sections_count"] == 1
    assert len(sched_data["meetings"]) == 1
    meeting_entry = sched_data["meetings"][0]
    assert meeting_entry["id"] == mtg_id
    assert meeting_entry["course_code"] == "PHYS101"
    assert meeting_entry["room_number"] == "Lab-1"
    assert meeting_entry["day_of_week"] == 3

    # 5. Check student's calendar week view (/api/v1/week)
    # The week covering 2026-09-02 (which is Wednesday, day 3, starting on Monday 2026-08-31)
    week_resp = client.get("/api/v1/week?start=2026-08-31", headers=std_headers)
    assert week_resp.status_code == 200
    week_data = week_resp.json()["data"]

    # The course meeting must appear as a class block in the week view
    found_class_block = any(
        b["type"] == "class" and "PHYS101" in b.get("title", "")
        for b in week_data.get("blocks", [])
    )
    assert found_class_block, f"Expected PHYS101 class block in week occurrences, got {week_data.get('blocks')}"

    # 6. If student schedules an overlapping work shift on Wednesday 15:00 - 18:00,
    # the conflict engine must detect a class_vs_shift conflict!
    shift_resp = client.post(
        "/api/v1/blocks",
        headers=std_headers,
        json={
            "title": "Campus Bookstore Shift",
            "type": "shift",
            "day_of_week": 3,
            "start_time": "15:00:00",
            "end_time": "18:00:00",
            "date": "2026-09-02",
        },
    )
    assert shift_resp.status_code in (200, 201)

    week_conflict_resp = client.get("/api/v1/week?start=2026-08-31", headers=std_headers)
    assert week_conflict_resp.status_code == 200
    conflicts = week_conflict_resp.json()["data"].get("conflicts", [])
    assert len(conflicts) > 0, "Expected conflict between class meeting and overlapping work shift"

    # 7. Student drops the section -> meetings are cleanly removed from academic schedule
    drop_resp = client.delete(
        f"/api/v1/students/me/enrollments/{enrollment_id}",
        headers=std_headers,
    )
    assert drop_resp.status_code == 200

    sched_after_drop = client.get("/api/v1/students/me/schedule", headers=std_headers)
    assert sched_after_drop.status_code == 200
    assert sched_after_drop.json()["data"]["enrolled_sections_count"] == 0
    assert len(sched_after_drop.json()["data"]["meetings"]) == 0


def test_tenant_isolation():
    """Verify strict multi-tenant isolation between Institution A and Institution B."""
    # Institution A
    admin_a_id, admin_a_token = create_test_user("admin_tenant_a")
    inst_a_id, _ = create_test_institution(admin_a_token, "Institution Alpha")
    headers_a = {"Authorization": f"Bearer {admin_a_token}"}

    # Institution B
    admin_b_id, admin_b_token = create_test_user("admin_tenant_b")
    inst_b_id, _ = create_test_institution(admin_b_token, "Institution Beta")
    headers_b = {"Authorization": f"Bearer {admin_b_token}"}

    # Terms
    term_a = create_test_term(admin_a_token, inst_a_id, "Term A", status="active")
    term_b = create_test_term(admin_b_token, inst_b_id, "Term B", status="active")

    # Timetables
    tt_a = client.post(
        f"/api/v1/institutions/{inst_a_id}/timetables",
        headers=headers_a,
        json={"academic_term_id": term_a, "name": "Timetable A"},
    ).json()["data"]["id"]

    tt_b = client.post(
        f"/api/v1/institutions/{inst_b_id}/timetables",
        headers=headers_b,
        json={"academic_term_id": term_b, "name": "Timetable B"},
    ).json()["data"]["id"]

    # 1. Admin A cannot read Timetable B
    resp_cross_read = client.get(
        f"/api/v1/institutions/{inst_b_id}/timetables/{tt_b}",
        headers=headers_a,
    )
    assert resp_cross_read.status_code in (403, 404)

    # 2. Admin A cannot modify Timetable B through ID spoofing in Institution A's endpoint
    resp_spoof = client.patch(
        f"/api/v1/institutions/{inst_a_id}/timetables/{tt_b}",
        headers=headers_a,
        json={"name": "Hacked Name"},
    )
    assert resp_spoof.status_code == 404

    # 3. Room of Institution B cannot be used in Institution A's meeting
    room_b = create_test_room(
        admin_b_token, inst_b_id, room_number="Beta-101", capacity=50, building="Beta Quad", room_type="classroom"
    )

    dept_a = client.post(
        f"/api/v1/institutions/{inst_a_id}/departments",
        headers=headers_a,
        json={"name": "Dept A", "code": "DA"},
    ).json()["data"]["id"]

    course_a = client.post(
        f"/api/v1/institutions/{inst_a_id}/courses",
        headers=headers_a,
        json={"department_id": dept_a, "code": "DA101", "name": "Alpha Course"},
    ).json()["data"]["id"]

    sec_a = client.post(
        f"/api/v1/institutions/{inst_a_id}/sections",
        headers=headers_a,
        json={"course_id": course_a, "academic_term_id": term_a, "section_code": "01", "capacity": 30},
    ).json()["data"]["id"]

    cross_room_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/timetables/{tt_a}/meetings",
        headers=headers_a,
        json={
            "section_id": sec_a,
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "10:00",
            "room_id": room_b,
        },
    )
    assert cross_room_resp.status_code in (400, 404)
    assert cross_room_resp.json()["error"]["code"] in ("tenant_mismatch", "room_not_found")
