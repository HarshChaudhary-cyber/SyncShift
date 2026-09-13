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
            "timezone": "Europe/London",
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


def add_student_member(admin_token: str, inst_id: int, user_id: int) -> dict:
    """Helper for admin to add user as a student member of institution."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_student_profile_lifecycle():
    """Verify StudentProfile retrieval, update, student number uniqueness, and authorization."""
    # 1. Setup institution
    _, admin_token = create_test_user("admin_std_prof")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Engineering", "code": "ENG"},
    )
    assert dept_resp.status_code == 201
    dept_id = dept_resp.json()["data"]["id"]

    # 2. Non-member student access should fail
    std_id_1, std_token_1 = create_test_user("student_one")
    std_headers_1 = {"Authorization": f"Bearer {std_token_1}"}

    resp = client.get("/api/v1/students/me", headers=std_headers_1)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_institution_member"

    # Unauthenticated should fail
    resp_unauth = client.get("/api/v1/students/me")
    assert resp_unauth.status_code == 401

    # 3. Add student 1 to institution
    add_student_member(admin_token, inst_id, std_id_1)

    # 4. Fetch profile -> should auto-initialize
    resp = client.get("/api/v1/students/me", headers=std_headers_1)
    assert resp.status_code == 200
    pdata = resp.json()["data"]
    assert pdata["institution_id"] == inst_id
    assert pdata["status"] == "active"

    # 5. Update profile
    patch_resp = client.patch(
        "/api/v1/students/me",
        headers=std_headers_1,
        json={
            "department_id": dept_id,
            "program": "Computer Science B.S.",
            "year_of_study": 3,
            "student_number": "STU-1001",
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()["data"]
    assert updated["department_id"] == dept_id
    assert updated["program"] == "Computer Science B.S."
    assert updated["year_of_study"] == 3
    assert updated["student_number"] == "STU-1001"
    assert updated["department_name"] == "Engineering"

    # 6. Add student 2 and verify duplicate student_number in same institution is rejected
    std_id_2, std_token_2 = create_test_user("student_two")
    std_headers_2 = {"Authorization": f"Bearer {std_token_2}"}
    add_student_member(admin_token, inst_id, std_id_2)

    dup_resp = client.patch(
        "/api/v1/students/me",
        headers=std_headers_2,
        json={"student_number": "STU-1001"},
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "student_number_exists"


def test_section_enrollment_and_capacity():
    """Verify student enrollment, duplicate rejection, capacity limit enforcement, and drop."""
    _, admin_token = create_test_user("admin_enr")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Department, Course, Term, Section
    dept_id = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Science", "code": "SCI"},
    ).json()["data"]["id"]

    course_id = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "PHYS101", "name": "Physics I", "credits": 4},
    ).json()["data"]["id"]

    term_id = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=90)),
            "status": "active",
        },
    ).json()["data"]["id"]

    # Section with capacity = 2
    section_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "SEC-A",
            "capacity": 2,
            "status": "active",
        },
    )
    assert section_resp.status_code == 201
    section_id = section_resp.json()["data"]["id"]

    # Register 3 students in this institution
    s1_id, s1_token = create_test_user("enr_std1")
    s2_id, s2_token = create_test_user("enr_std2")
    s3_id, s3_token = create_test_user("enr_std3")

    for sid in (s1_id, s2_id, s3_id):
        add_student_member(admin_token, inst_id, sid)

    h1 = {"Authorization": f"Bearer {s1_token}"}
    h2 = {"Authorization": f"Bearer {s2_token}"}
    h3 = {"Authorization": f"Bearer {s3_token}"}

    # 1. Student 1 enrolls
    r1 = client.post("/api/v1/students/me/enrollments", headers=h1, json={"section_id": section_id})
    assert r1.status_code == 201
    e1_data = r1.json()["data"]
    assert e1_data["section_id"] == section_id
    assert e1_data["course_code"] == "PHYS101"
    assert e1_data["status"] == "active"
    e1_id = e1_data["id"]

    # 2. Student 1 attempts to re-enroll -> 409
    r1_dup = client.post("/api/v1/students/me/enrollments", headers=h1, json={"section_id": section_id})
    assert r1_dup.status_code == 409
    assert r1_dup.json()["error"]["code"] == "already_enrolled"

    # Check available sections endpoint from student perspective
    avail_resp = client.get(f"/api/v1/institutions/{inst_id}/sections/available", headers=h1)
    assert avail_resp.status_code == 200
    secs = avail_resp.json()["data"]
    sec_meta = next(s for s in secs if s["section_id"] == section_id)
    assert sec_meta["capacity"] == 2
    assert sec_meta["enrolled_count"] == 1
    assert sec_meta["remaining_seats"] == 1
    assert sec_meta["is_enrolled_by_me"] is True

    # 3. Student 2 enrolls -> capacity full
    r2 = client.post("/api/v1/students/me/enrollments", headers=h2, json={"section_id": section_id})
    assert r2.status_code == 201

    # 4. Student 3 attempts to enroll -> section_capacity_reached
    r3 = client.post("/api/v1/students/me/enrollments", headers=h3, json={"section_id": section_id})
    assert r3.status_code == 400
    assert r3.json()["error"]["code"] == "section_capacity_reached"

    # 5. Student 1 drops enrollment
    drop_resp = client.delete(f"/api/v1/students/me/enrollments/{e1_id}", headers=h1)
    assert drop_resp.status_code == 200
    assert drop_resp.json()["data"]["dropped"] is True

    # Verify Student 1 enrollments list shows it's dropped / omitted by default
    enrs = client.get("/api/v1/students/me/enrollments", headers=h1).json()["data"]
    assert len(enrs) == 0  # Active filter default

    # 6. Student 3 can now enroll in the freed seat
    r3_retry = client.post("/api/v1/students/me/enrollments", headers=h3, json={"section_id": section_id})
    assert r3_retry.status_code == 201
    assert r3_retry.json()["data"]["status"] == "active"


def test_enrollment_validation_rules():
    """Verify invalid section status, archived term, and nonexistent section rejection."""
    _, admin_token = create_test_user("admin_val")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    dept_id = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Math", "code": "MTH"},
    ).json()["data"]["id"]

    course_id = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "MTH101", "name": "Calculus I"},
    ).json()["data"]["id"]

    archived_term_id = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Past Term",
            "academic_year": "2024-2025",
            "start_date": "2024-09-01",
            "end_date": "2024-12-15",
            "status": "completed",
        },
    ).json()["data"]["id"]

    sec_in_archived = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": archived_term_id,
            "section_code": "OLD-1",
            "status": "active",
        },
    ).json()["data"]["id"]

    std_id, std_token = create_test_user("val_student")
    add_student_member(admin_token, inst_id, std_id)
    std_headers = {"Authorization": f"Bearer {std_token}"}

    # Attempt to enroll in completed term section -> 400
    r_archived = client.post("/api/v1/students/me/enrollments", headers=std_headers, json={"section_id": sec_in_archived})
    assert r_archived.status_code == 400
    assert r_archived.json()["error"]["code"] == "term_not_active"

    # Nonexistent section -> 404
    r_none = client.post("/api/v1/students/me/enrollments", headers=std_headers, json={"section_id": 999999})
    assert r_none.status_code == 404
    assert r_none.json()["error"]["code"] == "section_not_found"


def test_student_availability():
    """Verify weekly recurring availability schedule creation, validation, and retrieval."""
    std_id, std_token = create_test_user("avail_student")
    headers = {"Authorization": f"Bearer {std_token}"}

    # 1. Invalid time range (start >= end)
    inv_resp = client.put(
        "/api/v1/students/me/availability",
        headers=headers,
        json={
            "slots": [
                {"day_of_week": 1, "start_time": "17:00:00", "end_time": "09:00:00", "is_available": True}
            ]
        },
    )
    assert inv_resp.status_code == 400
    assert inv_resp.json()["error"]["code"] == "invalid_time_range"

    # 2. Overlapping slots on same day
    overlap_resp = client.put(
        "/api/v1/students/me/availability",
        headers=headers,
        json={
            "slots": [
                {"day_of_week": 1, "start_time": "09:00:00", "end_time": "13:00:00", "is_available": True},
                {"day_of_week": 1, "start_time": "12:00:00", "end_time": "15:00:00", "is_available": True},
            ]
        },
    )
    assert overlap_resp.status_code == 400
    assert overlap_resp.json()["error"]["code"] == "overlapping_availability"

    # 3. Valid weekly schedule
    valid_resp = client.put(
        "/api/v1/students/me/availability",
        headers=headers,
        json={
            "slots": [
                {"day_of_week": 1, "start_time": "08:00:00", "end_time": "12:00:00", "is_available": True, "title": "Morning"},
                {"day_of_week": 1, "start_time": "13:00:00", "end_time": "17:00:00", "is_available": True, "title": "Afternoon"},
                {"day_of_week": 3, "start_time": "10:00:00", "end_time": "16:00:00", "is_available": False, "title": "Work Blackout"},
            ]
        },
    )
    assert valid_resp.status_code == 200
    saved = valid_resp.json()["data"]
    assert len(saved) == 3

    # 4. Retrieve
    get_resp = client.get("/api/v1/students/me/availability", headers=headers)
    assert get_resp.status_code == 200
    retrieved = get_resp.json()["data"]
    assert len(retrieved) == 3
    assert retrieved[2]["day_of_week"] == 3
    assert retrieved[2]["is_available"] is False


def test_student_constraints_and_preferences():
    """Verify creation, update, and deletion of hard constraints and soft optimizer preferences."""
    std_id, std_token = create_test_user("constraints_student")
    headers = {"Authorization": f"Bearer {std_token}"}

    # 1. Create hard constraint
    c1_resp = client.post(
        "/api/v1/students/me/constraints",
        headers=headers,
        json={
            "constraint_type": "latest_end",
            "is_hard": True,
            "time_value": "18:00:00",
            "description": "Cannot attend classes after 18:00",
        },
    )
    assert c1_resp.status_code == 201
    c1 = c1_resp.json()["data"]
    assert c1["is_hard"] is True
    assert c1["constraint_type"] == "latest_end"
    c1_id = c1["id"]

    # 2. Create soft preference constraint
    c2_resp = client.post(
        "/api/v1/students/me/constraints",
        headers=headers,
        json={
            "constraint_type": "max_hours_per_day",
            "is_hard": False,
            "int_value": 6,
            "description": "Prefer no more than 6 hours of classes per day",
        },
    )
    assert c2_resp.status_code == 201

    # 3. List constraints with filter
    hard_list = client.get("/api/v1/students/me/constraints?is_hard=true", headers=headers).json()["data"]
    assert len(hard_list) == 1
    assert hard_list[0]["id"] == c1_id

    # 4. Update constraint
    patch_resp = client.patch(
        f"/api/v1/students/me/constraints/{c1_id}",
        headers=headers,
        json={"time_value": "17:30:00"},
    )
    assert patch_resp.status_code == 200
    assert "17:30" in patch_resp.json()["data"]["time_value"]

    # 5. Delete constraint
    del_resp = client.delete(f"/api/v1/students/me/constraints/{c1_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 6. Soft preferences
    pref_get = client.get("/api/v1/students/me/preferences", headers=headers)
    assert pref_get.status_code == 200
    default_pref = pref_get.json()["data"]
    assert default_pref["preferred_time_of_day"] == "any"

    pref_update = client.put(
        "/api/v1/students/me/preferences",
        headers=headers,
        json={
            "preferred_time_of_day": "morning",
            "schedule_density": "compact",
            "preferred_break_duration_minutes": 45,
            "max_campus_days_per_week": 4,
            "work_study_balance_weight": 5,
        },
    )
    assert pref_update.status_code == 200
    updated_pref = pref_update.json()["data"]
    assert updated_pref["preferred_time_of_day"] == "morning"
    assert updated_pref["schedule_density"] == "compact"
    assert updated_pref["preferred_break_duration_minutes"] == 45
    assert updated_pref["work_study_balance_weight"] == 5


def test_tenant_isolation_student_academics():
    """Verify Student from Institution A cannot access or enroll in Institution B resources."""
    # Institution A
    _, admin_a = create_test_user("admin_a")
    inst_a, _ = create_test_institution(admin_a, "University A")
    ha = {"Authorization": f"Bearer {admin_a}"}

    # Institution B
    _, admin_b = create_test_user("admin_b")
    inst_b, _ = create_test_institution(admin_b, "University B")
    hb = {"Authorization": f"Bearer {admin_b}"}

    # Create section in B
    dept_b = client.post(f"/api/v1/institutions/{inst_b}/departments", headers=hb, json={"name": "Dept B", "code": "DB"}).json()["data"]["id"]
    course_b = client.post(f"/api/v1/institutions/{inst_b}/courses", headers=hb, json={"department_id": dept_b, "code": "B101", "name": "Course B"}).json()["data"]["id"]
    term_b = client.post(f"/api/v1/institutions/{inst_b}/terms", headers=hb, json={"name": "Term B", "academic_year": "2026-2027", "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=60)), "status": "active"}).json()["data"]["id"]
    sec_b = client.post(f"/api/v1/institutions/{inst_b}/sections", headers=hb, json={"course_id": course_b, "academic_term_id": term_b, "section_code": "SEC-B", "capacity": 30}).json()["data"]["id"]

    # Student A in Institution A
    std_a, token_a = create_test_user("std_tenant_a")
    add_student_member(admin_a, inst_a, std_a)
    h_std_a = {"Authorization": f"Bearer {token_a}"}

    # Student A attempts to enroll in Section B -> 404 (section_not_found)
    cross_enr = client.post("/api/v1/students/me/enrollments", headers=h_std_a, json={"section_id": sec_b})
    assert cross_enr.status_code == 404
    assert cross_enr.json()["error"]["code"] == "section_not_found"

    # Student A attempts to view available sections for Institution B -> 403 Forbidden
    cross_avail = client.get(f"/api/v1/institutions/{inst_b}/sections/available", headers=h_std_a)
    assert cross_avail.status_code == 403


def test_dashboard_academic_summary():
    """Verify that student dashboard returns academic summary when enrolled."""
    _, admin_token = create_test_user("admin_dash")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    dept_id = client.post(f"/api/v1/institutions/{inst_id}/departments", headers=admin_headers, json={"name": "Biology", "code": "BIO"}).json()["data"]["id"]
    course_id = client.post(f"/api/v1/institutions/{inst_id}/courses", headers=admin_headers, json={"department_id": dept_id, "code": "BIO101", "name": "General Biology", "credits": 4}).json()["data"]["id"]
    term_id = client.post(f"/api/v1/institutions/{inst_id}/terms", headers=admin_headers, json={"name": "Spring 2026", "academic_year": "2025-2026", "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=90)), "status": "active"}).json()["data"]["id"]
    section_id = client.post(f"/api/v1/institutions/{inst_id}/sections", headers=admin_headers, json={"course_id": course_id, "academic_term_id": term_id, "section_code": "001", "capacity": 25}).json()["data"]["id"]

    std_id, std_token = create_test_user("dash_std")
    add_student_member(admin_token, inst_id, std_id)
    std_headers = {"Authorization": f"Bearer {std_token}"}

    # Enroll in section
    client.post("/api/v1/students/me/enrollments", headers=std_headers, json={"section_id": section_id})

    # Call /api/v1/dashboard
    dash_resp = client.get("/api/v1/dashboard", headers=std_headers)
    assert dash_resp.status_code == 200
    data = dash_resp.json()["data"]

    assert data["academics"] is not None
    academics = data["academics"]
    assert academics["institution_id"] == inst_id
    assert academics["enrolled_sections_count"] == 1
    assert academics["total_credits"] == 4
    assert academics["enrolled_sections"][0]["course_code"] == "BIO101"
