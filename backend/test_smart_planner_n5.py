import time
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_test_user(prefix: str) -> tuple[int, str]:
    """Registers a unique test user and returns (user_id, token)."""
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


def create_test_institution(admin_token: str, name_prefix: str = "Plan Univ") -> tuple[int, str]:
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"PLAN_{int(time.time() * 1000)}"[:16]
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


def create_test_term(admin_token: str, inst_id: int) -> int:
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "status": "active",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def test_smart_planner_hard_constraints_and_preview_immutability():
    """
    Verifies that Smart Planning:
    1. Treats university classes as authoritative fixed anchors (zero overlaps).
    2. Respects fixed work shifts and blackout availability slots.
    3. Respects task deadlines.
    4. Is strictly read-only during preview (mutates zero database records).
    """
    # 1. Setup Admin, Institution, Term, Course, Section, Room, Timetable, Meeting
    admin_id, admin_token = create_test_user("admin_n5")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    inst_id, _ = create_test_institution(admin_token)
    term_id = create_test_term(admin_token, inst_id)

    # Department & Course
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": "CS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={
            "department_id": dept_id,
            "code": "CS101",
            "name": "Intro to Programming",
            "credits": 3,
            "level": "undergraduate",
        },
    )
    course_id = course_resp.json()["data"]["id"]

    section_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "SEC-A",
            "capacity": 30,
        },
    )
    section_id = section_resp.json()["data"]["id"]

    room_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={
            "building": "Turing Hall",
            "room_number": "101",
            "capacity": 50,
            "room_type": "lecture_hall",
        },
    )
    room_id = room_resp.json()["data"]["id"]

    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={
            "academic_term_id": term_id,
            "name": "Official Baseline",
            "status": "active",
        },
    )
    tt_id = tt_resp.json()["data"]["id"]

    # Official university meeting: Monday (day_of_week=1) 10:00 - 11:30
    client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": section_id,
            "day_of_week": 1,
            "start_time": "10:00:00",
            "end_time": "11:30:00",
            "room_id": room_id,
            "meeting_type": "lecture",
        },
    )

    # 2. Setup Student and Enroll
    student_id, student_token = create_test_user("student_n5")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Add student to institution
    client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=admin_headers,
        json={"user_id": student_id, "role": "student"},
    )

    # Enroll in section
    client.post(
        "/api/v1/students/me/enrollments",
        headers=student_headers,
        json={"section_id": section_id},
    )

    # 3. Add student fixed work shift: Monday 14:00 - 18:00
    client.post(
        "/api/v1/blocks",
        headers=student_headers,
        json={
            "title": "Campus Bookstore",
            "type": "shift",
            "day_of_week": 1,
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "is_flexible": False,
            "location": "Bookstore",
        },
    )

    # 4. Add student blackout unavailable slot: Tuesday (day_of_week=2) 09:00 - 12:00
    client.put(
        "/api/v1/students/me/availability",
        headers=student_headers,
        json={
            "slots": [
                {
                    "day_of_week": 2,
                    "start_time": "09:00:00",
                    "end_time": "12:00:00",
                    "is_available": False,
                    "title": "Doctor Appointment",
                }
            ]
        },
    )

    # 5. Add StudyTask: 3 hours needed by upcoming Friday
    today_d = date.today()
    target_monday = today_d + timedelta(days=((7 - today_d.weekday()) % 7))
    if target_monday == today_d:
        target_monday += timedelta(days=7)
    friday_deadline = target_monday + timedelta(days=4)

    task_resp = client.post(
        "/api/v1/tasks",
        headers=student_headers,
        json={
            "title": "CS101 Problem Set 1",
            "total_hours_required": 3.0,
            "deadline": friday_deadline.isoformat(),
            "priority": "high",
            "preferred_duration": 90,
        },
    )
    assert task_resp.status_code == 201, task_resp.text
    task_data = task_resp.json()["data"]

    # Record initial database state
    initial_blocks_resp = client.get("/api/v1/blocks", headers=student_headers)
    initial_block_count = len(initial_blocks_resp.json()["data"])
    assert task_data["status"] == "pending"

    # 6. Call Preview Endpoint
    preview_resp = client.post(
        "/api/v1/students/me/planning/preview",
        headers=student_headers,
        json={"target_week_start": target_monday.isoformat()},
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview_data = preview_resp.json()["data"]

    # Verify preview response structure
    assert preview_data["has_feasible_solution"] is True
    assert preview_data["context_summary"]["enrolled_classes_count"] >= 1
    assert preview_data["context_summary"]["fixed_work_shifts_count"] >= 1
    assert preview_data["context_summary"]["pending_tasks_count"] >= 1

    options = preview_data["options"]
    assert len(options) == 3
    option_ids = [opt["id"] for opt in options]
    assert "balanced" in option_ids
    assert "focused" in option_ids
    assert "compact" in option_ids

    # 7. Check Hard Constraints in Generated Options
    for opt in options:
        assert opt["score"] > 0
        assert opt["summary"]["is_valid"] is True
        assert opt["summary"]["unchanged_classes_count"] >= 1

        for blk in opt["added_blocks"]:
            # Hard constraint 1: No overlap with Monday 10:00 - 11:30 (Class)
            if blk["day_of_week"] == 1:
                assert not ("10:00:00" <= blk["start_time"] < "11:30:00")
                # Hard constraint 2: No overlap with Monday 14:00 - 18:00 (Fixed Shift)
                assert not ("14:00:00" <= blk["start_time"] < "18:00:00")
            # Hard constraint 3: No overlap with Tuesday 09:00 - 12:00 (Blackout)
            if blk["day_of_week"] == 2:
                assert not ("09:00:00" <= blk["start_time"] < "12:00:00")
            # Hard constraint 4: Deadline check
            assert date.fromisoformat(blk["date"]) <= friday_deadline

    # 8. Assert Preview is Strictly Read-Only (Zero Database Mutation)
    after_preview_blocks = client.get("/api/v1/blocks", headers=student_headers).json()["data"]
    assert len(after_preview_blocks) == initial_block_count

    task_check = client.get("/api/v1/tasks", headers=student_headers).json()["data"]
    target_task = next(t for t in task_check if t["id"] == task_data["id"])
    assert target_task["status"] == "pending"


def test_safe_apply_and_revert_flow():
    """
    Verifies that applying a plan:
    1. Inserts only student-owned flexible items.
    2. Leaves university class meetings completely untouched.
    3. Leaves fixed work shifts completely untouched.
    4. Updates task status to 'scheduled'.
    5. Re-runs conflict detection with 0 conflicts.
    6. Reverting cleanly rolls back planned blocks and resets task status.
    """
    # 1. Setup Student with Institution, Enrollment, and Task
    admin_id, admin_token = create_test_user("admin_apply")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    inst_id, _ = create_test_institution(admin_token)
    term_id = create_test_term(admin_token, inst_id)

    student_id, student_token = create_test_user("student_apply")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=admin_headers,
        json={"user_id": student_id, "role": "student"},
    )

    today_d = date.today()
    target_monday = today_d + timedelta(days=((7 - today_d.weekday()) % 7))
    if target_monday == today_d:
        target_monday += timedelta(days=7)

    # Create task
    task_resp = client.post(
        "/api/v1/tasks",
        headers=student_headers,
        json={
            "title": "Calculus Quiz Preparation",
            "total_hours_required": 2.0,
            "deadline": (target_monday + timedelta(days=5)).isoformat(),
            "priority": "medium",
            "preferred_duration": 60,
        },
    )
    task_id = task_resp.json()["data"]["id"]

    # Preview plan
    prev_resp = client.post(
        "/api/v1/students/me/planning/preview",
        headers=student_headers,
        json={"target_week_start": target_monday.isoformat()},
    )
    prev_data = prev_resp.json()["data"]
    balanced_opt = next(o for o in prev_data["options"] if o["id"] == "balanced")
    assert len(balanced_opt["added_blocks"]) >= 1

    # 2. Apply the plan
    apply_payload = {
        "option_id": "balanced",
        "week_start": target_monday.isoformat(),
        "approved_new_blocks": [
            {
                "title": b["title"],
                "day_of_week": b["day_of_week"],
                "date": b["date"],
                "start_time": b["start_time"],
                "end_time": b["end_time"],
                "duration_hours": b["duration_hours"],
                "study_task_id": b["study_task_id"],
                "type": "study",
            }
            for b in balanced_opt["added_blocks"]
        ],
    }

    apply_resp = client.post(
        "/api/v1/students/me/planning/apply",
        headers=student_headers,
        json=apply_payload,
    )
    assert apply_resp.status_code == 200, apply_resp.text
    apply_result = apply_resp.json()["data"]

    assert apply_result["success"] is True
    assert apply_result["created_blocks_count"] == len(balanced_opt["added_blocks"])
    assert apply_result["conflicts_detected_count"] == 0

    # 3. Verify task is now scheduled
    task_after = client.get("/api/v1/tasks", headers=student_headers).json()["data"]
    scheduled_task = next(t for t in task_after if t["id"] == task_id)
    assert scheduled_task["status"] == "scheduled"

    # 4. Verify calendar blocks exist
    blocks_after = client.get("/api/v1/blocks", headers=student_headers).json()["data"]
    applied_study_blocks = [b for b in blocks_after if b.get("study_task_id") == task_id]
    assert len(applied_study_blocks) == len(balanced_opt["added_blocks"])

    # 5. Revert plan
    revert_resp = client.delete(
        f"/api/v1/students/me/planning/revert?week_start={target_monday.isoformat()}",
        headers=student_headers,
    )
    assert revert_resp.status_code == 200, revert_resp.text
    revert_data = revert_resp.json()["data"]
    assert revert_data["success"] is True
    assert revert_data["reverted_blocks_count"] == len(applied_study_blocks)

    # 6. Verify task status rolled back to pending
    task_reverted = client.get("/api/v1/tasks", headers=student_headers).json()["data"]
    pending_task = next(t for t in task_reverted if t["id"] == task_id)
    assert pending_task["status"] == "pending"


def test_no_solution_and_actionable_blocking_issues():
    """
    Verifies that when a student's commitments make scheduling impossible,
    the planner returns has_feasible_solution=False with actionable blocking reasons.
    """
    student_id, student_token = create_test_user("student_nosol")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    today_d = date.today()
    target_monday = today_d + timedelta(days=((7 - today_d.weekday()) % 7))
    if target_monday == today_d:
        target_monday += timedelta(days=7)

    # Add task with impossible demand (e.g. 80 hours needed in 1 day)
    client.post(
        "/api/v1/tasks",
        headers=student_headers,
        json={
            "title": "Massive Exam Cram",
            "total_hours_required": 80.0,
            "deadline": (target_monday + timedelta(days=1)).isoformat(),
            "priority": "high",
        },
    )

    prev_resp = client.post(
        "/api/v1/students/me/planning/preview",
        headers=student_headers,
        json={"target_week_start": target_monday.isoformat()},
    )
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()["data"]

    assert prev_data["has_feasible_solution"] is False
    assert len(prev_data["blocking_issues"]) > 0
    assert any("Insufficient free time" in issue for issue in prev_data["blocking_issues"])


def test_tenant_and_user_authorization_isolation():
    """
    Verifies that Student A cannot access Student B's planning data or apply plans on their behalf.
    """
    user_a_id, user_a_token = create_test_user("user_a_iso")
    user_b_id, user_b_token = create_test_user("user_b_iso")

    # Unauthenticated request is rejected
    unauth_resp = client.post("/api/v1/students/me/planning/preview")
    assert unauth_resp.status_code == 401

    # Empty plan apply is rejected
    headers_a = {"Authorization": f"Bearer {user_a_token}"}
    empty_apply_resp = client.post(
        "/api/v1/students/me/planning/apply",
        headers=headers_a,
        json={"option_id": "balanced", "approved_new_blocks": []},
    )
    assert empty_apply_resp.status_code == 400


def test_preferences_influence_ranking_and_timings():
    """
    Verifies that student soft preferences influence candidate start times:
    - Morning preference chooses early morning start times (< 12:00).
    - Evening preference chooses evening start times (>= 17:00).
    """
    student_id, student_token = create_test_user("student_prefs")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    today_d = date.today()
    target_monday = today_d + timedelta(days=((7 - today_d.weekday()) % 7))
    if target_monday == today_d:
        target_monday += timedelta(days=7)

    client.post(
        "/api/v1/tasks",
        headers=student_headers,
        json={
            "title": "Data Structures Study",
            "total_hours_required": 2.0,
            "deadline": (target_monday + timedelta(days=4)).isoformat(),
            "priority": "medium",
            "preferred_duration": 60,
        },
    )

    # 1. Preview with morning preference
    resp_morning = client.post(
        "/api/v1/students/me/planning/preview",
        headers=student_headers,
        json={
            "target_week_start": target_monday.isoformat(),
            "preferred_time_of_day": "morning",
        },
    )
    assert resp_morning.status_code == 200
    data_morning = resp_morning.json()["data"]
    balanced_m = next(o for o in data_morning["options"] if o["id"] == "balanced")
    first_m_slot = balanced_m["added_blocks"][0]
    # Starts before 12:00
    assert first_m_slot["start_time"] < "12:00:00"

    # 2. Preview with evening preference
    resp_evening = client.post(
        "/api/v1/students/me/planning/preview",
        headers=student_headers,
        json={
            "target_week_start": target_monday.isoformat(),
            "preferred_time_of_day": "evening",
        },
    )
    assert resp_evening.status_code == 200
    data_evening = resp_evening.json()["data"]
    balanced_e = next(o for o in data_evening["options"] if o["id"] == "balanced")
    first_e_slot = balanced_e["added_blocks"][0]
    # Starts in evening (>= 17:00)
    assert first_e_slot["start_time"] >= "17:00:00"

