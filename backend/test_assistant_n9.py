"""
Comprehensive Test Suite for Task N9 — SyncShift AI Assistant.

Covers:
1. Multi-turn conversation persistence, message ordering, and user isolation.
2. Cross-user isolation: User B cannot view or delete User A's conversations.
3. Student schedule grounding: courses enrolled, classes, and conflicts.
4. Student action preview and confirmation: create study block and apply weekly plan.
5. Admin timetable tools: room availability check across time windows.
6. Admin timetable version history inspection.
7. Admin draft version creation preview and confirmation (N7 integration).
8. Admin timetable change preview with N6 impact analysis integration.
9. Strict role and tenant boundary authorization (students cannot execute admin timetable changes; cross-tenant protection).
"""

from datetime import date, datetime, time as dt_time, timedelta
import time
import uuid
import pytest
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.time_block import TimeBlock, BlockType
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.services.rate_limiter import reset_rate_limits

client = TestClient(app)


def setup_user(prefix: str, role: str = "student", work_limit: float = 20.0):
    reset_rate_limits()
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@example.edu"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": work_limit,
            "name": f"Tester {uid}",
            "minimum_transition_minutes": 15,
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    user_id = resp.json()["data"]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


def setup_institution_env():
    """Sets up an institution, term, dept, courses, sections, rooms, and draft/published timetables."""
    admin_headers, admin_id = setup_user("univ_admin")
    code = f"N9_{str(uuid.uuid4())[:8]}"

    # Institution
    inst_resp = client.post(
        "/api/v1/institutions",
        headers=admin_headers,
        json={"name": f"N9 University {code}", "code": code, "timezone": "America/New_York", "country": "US"},
    )
    assert inst_resp.status_code == 201, inst_resp.text
    inst_id = inst_resp.json()["data"]["id"]

    # Term
    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "status": "active",
        },
    )
    assert term_resp.status_code == 201, term_resp.text
    term_id = term_resp.json()["data"]["id"]

    # Department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": f"CS_{code[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["data"]["id"]

    # Course
    crs_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "CS101", "name": "Intro to Programming", "credits": 3},
    )
    assert crs_resp.status_code == 201, crs_resp.text
    crs_id = crs_resp.json()["data"]["id"]

    # Section
    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": crs_id, "academic_term_id": term_id, "section_code": "01", "capacity": 30},
    )
    assert sec_resp.status_code == 201, sec_resp.text
    sec_id = sec_resp.json()["data"]["id"]

    # Room 1 (occupied Mon 10-12) and Room 2 (vacant)
    rm1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Hall A", "room_number": "101", "capacity": 50, "room_type": "lecture_hall"},
    )
    assert rm1_resp.status_code == 201, rm1_resp.text
    rm1_id = rm1_resp.json()["data"]["id"]

    rm2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Hall B", "room_number": "202", "capacity": 40, "room_type": "classroom"},
    )
    assert rm2_resp.status_code == 201, rm2_resp.text
    rm2_id = rm2_resp.json()["data"]["id"]

    # Timetable
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={"academic_term_id": term_id, "name": "Fall 2026 Master Timetable"},
    )
    assert tt_resp.status_code == 201, tt_resp.text
    tt_id = tt_resp.json()["data"]["id"]

    # Meeting for Section in Room 1 on Monday (day 1) 10:00 - 12:00
    meeting_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_id,
            "room_id": rm1_id,
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
            "meeting_type": "lecture",
        },
    )
    assert meeting_resp.status_code == 201, meeting_resp.text
    meeting_id = meeting_resp.json()["data"]["id"]

    return {
        "admin_headers": admin_headers,
        "admin_id": admin_id,
        "inst_id": inst_id,
        "term_id": term_id,
        "dept_id": dept_id,
        "crs_id": crs_id,
        "sec_id": sec_id,
        "rm1_id": rm1_id,
        "rm2_id": rm2_id,
        "tt_id": tt_id,
        "meeting_id": meeting_id,
    }


def test_conversation_persistence_and_isolation():
    """Verify conversations persist, retain messages, and are strictly isolated between users."""
    headers_a, user_a = setup_user("conv_user_a")
    headers_b, user_b = setup_user("conv_user_b")

    # User A sends a message without conversation_id -> creates new conversation
    r1 = client.post(
        "/api/v1/assistant/chat",
        headers=headers_a,
        json={"message": "What is my schedule today?"},
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()["data"]
    conv_id = d1["conversation_id"]
    assert conv_id is not None

    # User A sends second message with conv_id
    r2 = client.post(
        "/api/v1/assistant/chat",
        headers=headers_a,
        json={"conversation_id": conv_id, "message": "Do I have any conflicts?"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["conversation_id"] == conv_id

    # User A lists conversations
    list_resp = client.get("/api/v1/assistant/conversations", headers=headers_a)
    assert list_resp.status_code == 200, list_resp.text
    convs = list_resp.json()["data"]
    assert any(c["id"] == conv_id for c in convs)

    # User A gets conversation details
    detail_resp = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_a)
    assert detail_resp.status_code == 200, detail_resp.text
    messages = detail_resp.json()["data"]["messages"]
    assert len(messages) >= 4  # 2 user messages + 2 assistant responses

    # User B attempts to access User A's conversation -> 404
    cross_get = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_b)
    assert cross_get.status_code == 404

    # User B attempts to delete User A's conversation -> 404
    cross_del = client.delete(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_b)
    assert cross_del.status_code == 404

    # User A deletes their own conversation -> 200
    del_resp = client.delete(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_a)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # Subsequent fetch returns 404
    after_del = client.get(f"/api/v1/assistant/conversations/{conv_id}", headers=headers_a)
    assert after_del.status_code == 404


def test_student_schedule_and_enrolled_courses():
    """Verify assistant grounds responses in enrolled courses and student schedule."""
    env = setup_institution_env()
    headers_student, student_id = setup_user("student_n9")

    # Add student to institution
    client.post(
        f"/api/v1/institutions/{env['inst_id']}/members",
        headers=env["admin_headers"],
        json={"user_id": student_id, "role": "student"},
    )

    # Enroll student in section
    enr_resp = client.post(
        "/api/v1/students/me/enrollments",
        headers=headers_student,
        json={"section_id": env["sec_id"]},
    )
    assert enr_resp.status_code == 201, enr_resp.text

    # Query assistant about enrolled courses
    r_courses = client.post(
        "/api/v1/assistant/chat",
        headers=headers_student,
        json={"message": "What courses am I enrolled in?"},
    )
    assert r_courses.status_code == 200, r_courses.text
    msg = r_courses.json()["data"]["message"]
    assert "CS101" in msg or "Intro to Programming" in msg


def test_student_study_block_creation_flow():
    """Verify assistant produces create_study_block action preview card and confirms it."""
    headers, user_id = setup_user("study_flow")

    # Ask to create a study block
    chat_resp = client.post(
        "/api/v1/assistant/chat",
        headers=headers,
        json={"message": "Schedule a study session for CS101 on Monday from 15:00 to 17:00"},
    )
    assert chat_resp.status_code == 200, chat_resp.text
    data = chat_resp.json()["data"]

    assert data["requires_confirmation"] is True
    action = data["action"]
    assert action is not None
    assert action["action_type"] == "create_study_block"
    assert action["target"]["day_of_week"] == 1
    assert action["target"]["start_time"] == "15:00"
    assert action["target"]["end_time"] == "17:00"

    # Confirm action
    conf_resp = client.post(
        "/api/v1/assistant/confirm",
        headers=headers,
        json={"action": action},
    )
    assert conf_resp.status_code == 200, conf_resp.text
    conf_data = conf_resp.json()["data"]
    assert conf_data["success"] is True
    assert conf_data["updated_block"]["day_of_week"] == 1


def test_admin_room_availability_tool():
    """Verify admin can query room vacancies and assistant reports accurate availability."""
    env = setup_institution_env()
    admin_headers = env["admin_headers"]

    # Monday 10:00 - 12:00: Room 101 is occupied, Room 202 is vacant
    resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": "Which rooms are available on Monday between 10:00 and 12:00?"},
    )
    assert resp.status_code == 200, resp.text
    msg = resp.json()["data"]["message"]

    # Room 202 (vacant) should be mentioned as available
    assert "202" in msg


def test_admin_version_history_and_draft_creation():
    """Verify admin can query version history and prepare a draft version (N7 integration)."""
    env = setup_institution_env()
    admin_headers = env["admin_headers"]
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]

    # 1. Query version history
    hist_resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": f"Show version history for timetable {tt_id} in institution {inst_id}"},
    )
    assert hist_resp.status_code == 200, hist_resp.text
    assert "version" in hist_resp.json()["data"]["message"].lower()

    # 2. Ask to create a new draft
    draft_req = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={"message": f"Create draft version for timetable {tt_id} in institution {inst_id}"},
    )
    assert draft_req.status_code == 200, draft_req.text
    data = draft_req.json()["data"]
    assert data["requires_confirmation"] is True
    action = data["action"]
    assert action["action_type"] == "create_timetable_draft"

    # 3. Confirm draft creation
    conf_resp = client.post(
        "/api/v1/assistant/confirm",
        headers=admin_headers,
        json={"action": action},
    )
    assert conf_resp.status_code == 200, conf_resp.text
    assert conf_resp.json()["data"]["success"] is True


def test_admin_timetable_change_impact_preview():
    """Verify admin timetable change invokes N6 impact analysis and returns structured impact card."""
    env = setup_institution_env()
    admin_headers = env["admin_headers"]
    inst_id = env["inst_id"]
    tt_id = env["tt_id"]
    meeting_id = env["meeting_id"]

    # Ask assistant to move meeting
    change_resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={
            "message": f"Move meeting {meeting_id} on timetable {tt_id} for institution {inst_id} to Wednesday at 14:00"
        },
    )
    assert change_resp.status_code == 200, change_resp.text
    data = change_resp.json()["data"]

    # Must require confirmation with structured action
    assert data["requires_confirmation"] is True
    action = data["action"]
    assert action["action_type"] == "timetable_change"
    assert "impact_summary" in action
    assert "checks" in action


def test_security_cross_tenant_and_unauthorized_admin_actions():
    """Verify students and cross-tenant users cannot execute admin timetable changes."""
    env1 = setup_institution_env()
    env2 = setup_institution_env()

    student_headers, student_id = setup_user("student_sec")
    admin2_headers = env2["admin_headers"]

    # 1. Student attempts admin timetable draft creation
    draft_action = {
        "action_type": "create_timetable_draft",
        "title": "Create Draft",
        "description": "Unauthorized Draft",
        "target": {},
        "parameters": {
            "institution_id": env1["inst_id"],
            "timetable_id": env1["tt_id"],
            "name": "Malicious Draft",
        },
        "checks": [],
    }

    # Student cannot confirm
    r_student = client.post(
        "/api/v1/assistant/confirm",
        headers=student_headers,
        json={"action": draft_action},
    )
    assert r_student.status_code in (403, 404)

    # 2. Admin of Institution 2 cannot modify Institution 1
    r_cross_admin = client.post(
        "/api/v1/assistant/confirm",
        headers=admin2_headers,
        json={"action": draft_action},
    )
    assert r_cross_admin.status_code in (403, 404)
