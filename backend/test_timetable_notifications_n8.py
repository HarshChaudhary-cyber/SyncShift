"""
Comprehensive Test Suite for Task N8 — Automatic Timetable Change Notifications.

Covers:
1. Notification generation on timetable publish (only affected enrolled students notified).
2. Unrelated, dropped, and cross-tenant students excluded.
3. Accurate before/after change details and priority calculation.
4. Work shift conflict detection escalates to URGENT + SCHEDULE_CONFLICT.
5. Notification idempotency (re-running does not duplicate notifications).
6. Channel failure resilience (email/push failure does NOT roll back publication).
7. Student schedule synchronization (academic schedule auto-updates; work/personal unchanged).
8. ICS export reflects official published schedule.
9. Student notification center APIs and authorization (read/unread, mark read, tenant isolation).
10. University admin notification summary and tenant boundary enforcement.
"""

import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.notification import NotificationLog, NotificationPrefs
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.time_block import TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.services.timetable_notification_service import (
    detect_version_changes,
    process_timetable_publication_notifications,
    get_version_notification_summary,
)

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


def create_test_institution(admin_token: str, name_prefix: str = "N8 Univ") -> tuple[int, str]:
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"N8_{int(time.time() * 1000)}"[:16]
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
    return resp.json()["data"]["id"], code


def create_test_term(admin_token: str, inst_id: int, name: str = "Fall 2026") -> int:
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
            "status": "active",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def add_member(admin_token: str, inst_id: int, user_id: int, role: str = "student"):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def setup_n8_environment():
    """Sets up a realistic environment with 2 sections, rooms, and initial timetable."""
    admin_id, admin_token = create_test_user("admin_n8")
    inst_id, _ = create_test_institution(admin_token, "N8 State University")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Dept
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": "CS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    # Term
    term_id = create_test_term(admin_token, inst_id, "Fall 2026")

    # Courses
    crs_resp1 = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "CS301", "name": "Database Systems", "credits": 3},
    )
    crs1_id = crs_resp1.json()["data"]["id"]

    crs_resp2 = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "CS302", "name": "Operating Systems", "credits": 3},
    )
    crs2_id = crs_resp2.json()["data"]["id"]

    # Sections
    sec_a_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": crs1_id, "academic_term_id": term_id, "section_code": "A", "capacity": 40},
    )
    sec_a_id = sec_a_resp.json()["data"]["id"]

    sec_b_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": crs2_id, "academic_term_id": term_id, "section_code": "B", "capacity": 40},
    )
    sec_b_id = sec_b_resp.json()["data"]["id"]

    # Rooms
    room1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Turing Hall", "room_number": "B204", "capacity": 50, "room_type": "lecture_hall"},
    )
    room1_id = room1_resp.json()["data"]["id"]

    room2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Lovelace Hall", "room_number": "L101", "capacity": 50, "room_type": "lecture_hall"},
    )
    room2_id = room2_resp.json()["data"]["id"]

    # Timetable (Active baseline creates Version 1 automatically)
    tt_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables",
        headers=admin_headers,
        json={"academic_term_id": term_id, "name": "Fall 2026 Master Timetable", "status": "active"},
    )
    tt_id = tt_resp.json()["data"]["id"]
    tt_data = tt_resp.json()["data"]
    v1_id = tt_data["published_version_id"]

    # Meeting 1 in Section A: Monday 10:00-11:00 in Room B204 (belongs to V1)
    m1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_a_id,
            "day_of_week": 1,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room_id": room1_id,
            "meeting_type": "lecture",
        },
    )
    assert m1_resp.status_code == 201, m1_resp.text
    m1_id = m1_resp.json()["data"]["id"]

    # Meeting 2 in Section B: Tuesday 14:00-15:00 in Room L101
    m2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/meetings",
        headers=admin_headers,
        json={
            "section_id": sec_b_id,
            "day_of_week": 2,
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "room_id": room2_id,
            "meeting_type": "lecture",
        },
    )
    assert m2_resp.status_code == 201, m2_resp.text
    m2_id = m2_resp.json()["data"]["id"]

    # Ensure meetings are linked to V1
    db = SessionLocal()
    db.query(CourseMeeting).filter(CourseMeeting.id.in_([m1_id, m2_id])).update(
        {"version_id": v1_id}, synchronize_session=False
    )
    db.commit()
    db.close()

    return {
        "admin_id": admin_id,
        "admin_token": admin_token,
        "admin_headers": admin_headers,
        "inst_id": inst_id,
        "term_id": term_id,
        "crs1_id": crs1_id,
        "crs2_id": crs2_id,
        "sec_a_id": sec_a_id,
        "sec_b_id": sec_b_id,
        "room1_id": room1_id,
        "room2_id": room2_id,
        "tt_id": tt_id,
        "v1_id": v1_id,
        "m1_id": m1_id,
        "m2_id": m2_id,
    }


def test_publish_notifications_affected_students_only():
    """
    Verifies that upon publishing a new timetable version:
    1. Students actively enrolled in changed sections receive targeted notifications.
    2. Students in unrelated sections receive ZERO notifications.
    3. Dropped students receive ZERO notifications.
    4. Cross-tenant students receive ZERO notifications.
    5. Notification contains human-readable before/after change details.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    sec_b_id = env["sec_b_id"]
    v1_id = env["v1_id"]

    # 1. Setup Student 1: Enrolled in Section A (Affected)
    s1_id, s1_tok = create_test_user("s1_affected")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # 2. Setup Student 2: Enrolled in Section B only (Unrelated)
    s2_id, s2_tok = create_test_user("s2_unrelated")
    s2_headers = {"Authorization": f"Bearer {s2_tok}"}
    add_member(env["admin_token"], inst_id, s2_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s2_headers, json={"section_id": sec_b_id})

    # 3. Setup Student 3: Dropped from Section A
    s3_id, s3_tok = create_test_user("s3_dropped")
    s3_headers = {"Authorization": f"Bearer {s3_tok}"}
    add_member(env["admin_token"], inst_id, s3_id, "student")
    enr3_resp = client.post("/api/v1/students/me/enrollments", headers=s3_headers, json={"section_id": sec_a_id})
    # Mark enrollment as dropped using student_id
    db = SessionLocal()
    db.query(SectionEnrollment).filter(
        SectionEnrollment.student_id == s3_id,
        SectionEnrollment.section_id == sec_a_id,
    ).update({"status": "dropped"})
    db.commit()
    db.close()

    # 4. Setup Student 4: Cross-tenant (in Institution 2)
    admin2_id, admin2_tok = create_test_user("admin_inst2")
    inst2_id, _ = create_test_institution(admin2_tok, "Other University")
    s4_id, s4_tok = create_test_user("s4_crosstenant")
    s4_headers = {"Authorization": f"Bearer {s4_tok}"}
    add_member(admin2_tok, inst2_id, s4_id, "student")

    # 5. Create Version 2 (draft) cloning from Version 1
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "Version 2 — Time Adjustments", "source_version_id": v1_id},
    )
    assert v2_resp.status_code == 201, v2_resp.text
    v2_id = v2_resp.json()["data"]["id"]

    # 6. In Version 2, move Section A meeting: Mon 10:00-11:00 -> Mon 14:00-15:00
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(
        CourseMeeting.version_id == v2_id,
        CourseMeeting.section_id == sec_a_id,
    ).first()
    assert v2_m1 is not None
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    # 7. Transition V2: draft -> review -> approve
    rev_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review",
        headers=admin_headers,
    )
    assert rev_resp.status_code == 200, rev_resp.text

    app_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve",
        headers=admin_headers,
    )
    assert app_resp.status_code == 200, app_resp.text

    # 8. Publish Version 2
    pub_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish",
        headers=admin_headers,
        json={"notes": "Moved Database Systems class to afternoon"},
    )
    assert pub_resp.status_code == 200, pub_resp.text
    pub_data = pub_resp.json()["data"]
    summary = pub_data["notification_summary"]

    assert summary["students_affected"] == 1
    assert summary["classes_changed"] == 1
    assert summary["notifications_created"] == 1

    # 9. Verify Student 1 received targeted in-app notification
    s1_notifs_resp = client.get("/api/v1/notifications", headers=s1_headers)
    assert s1_notifs_resp.status_code == 200
    s1_notifs = s1_notifs_resp.json()["data"]["items"]
    assert len(s1_notifs) == 1
    notif = s1_notifs[0]
    assert notif["type"] in ("TIMETABLE_UPDATE", "CLASS_MOVED")
    assert "Database Systems" in notif["body"] or "CS301" in notif["body"]
    assert "Monday 10:00" in notif["body"] or "10:00" in notif["body"]
    assert "14:00" in notif["body"]
    assert notif["priority"] in ("IMPORTANT", "INFO")
    assert notif["read_at"] is None
    assert notif["action_url"] in ("/calendar", "/app/calendar")

    # 10. Verify Student 2 (unrelated section) received 0 notifications
    s2_notifs_resp = client.get("/api/v1/notifications", headers=s2_headers)
    assert s2_notifs_resp.status_code == 200
    assert len(s2_notifs_resp.json()["data"]["items"]) == 0

    # 11. Verify Student 3 (dropped) received 0 notifications
    s3_notifs_resp = client.get("/api/v1/notifications", headers=s3_headers)
    assert s3_notifs_resp.status_code == 200
    assert len(s3_notifs_resp.json()["data"]["items"]) == 0

    # 12. Verify Student 4 (cross-tenant) received 0 notifications
    s4_notifs_resp = client.get("/api/v1/notifications", headers=s4_headers)
    assert s4_notifs_resp.status_code == 200
    assert len(s4_notifs_resp.json()["data"]["items"]) == 0


def test_work_shift_conflict_escalates_to_urgent():
    """
    Verifies that when a timetable change creates a collision with a student's
    existing work shift:
    1. The notification is escalated to priority URGENT.
    2. Notification type is SCHEDULE_CONFLICT.
    3. The message explicitly identifies the work shift conflict.
    4. A student with NO shift conflict receives normal IMPORTANT priority.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    # Student 1: Enrolled in Sec A, HAS a fixed work shift Monday 14:00 - 18:00
    s1_id, s1_tok = create_test_user("s1_with_shift")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # Add work shift
    client.post(
        "/api/v1/blocks",
        headers=s1_headers,
        json={
            "title": "Campus Bookstore Shift",
            "type": "shift",
            "day_of_week": 1,  # Monday
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "is_flexible": False,
            "location": "Bookstore",
        },
    )

    # Student 2: Enrolled in Sec A, NO work shift on Monday
    s2_id, s2_tok = create_test_user("s2_no_shift")
    s2_headers = {"Authorization": f"Bearer {s2_tok}"}
    add_member(env["admin_token"], inst_id, s2_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s2_headers, json={"section_id": sec_a_id})

    # Create V2 cloning V1
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Shift Collision Test", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]

    # In V2, move class from Mon 10:00-11:00 to Mon 14:00-15:00 (collides with S1 shift)
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(
        CourseMeeting.version_id == v2_id,
        CourseMeeting.section_id == sec_a_id,
    ).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    # Submit for review, approve, publish
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)
    pub_resp = client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)
    assert pub_resp.status_code == 200

    summary = pub_resp.json()["data"]["notification_summary"]
    assert summary["students_affected"] == 2
    assert summary["new_conflicts"] == 1

    # Check Student 1 (has conflict)
    s1_notifs = client.get("/api/v1/notifications", headers=s1_headers).json()["data"]["items"]
    assert len(s1_notifs) == 1
    s1_n = s1_notifs[0]
    assert s1_n["type"] == "SCHEDULE_CONFLICT"
    assert s1_n["priority"] == "URGENT"
    assert "overlaps with your work shift" in s1_n["body"] or "conflict with your scheduled work shift" in s1_n["body"]

    # Check Student 2 (NO conflict)
    s2_notifs = client.get("/api/v1/notifications", headers=s2_headers).json()["data"]["items"]
    assert len(s2_notifs) == 1
    s2_n = s2_notifs[0]
    assert s2_n["type"] != "SCHEDULE_CONFLICT"
    assert s2_n["priority"] != "URGENT"
    assert "conflict" not in s2_n["body"].lower()


def test_idempotency_of_publication_notifications():
    """
    Verifies that calling process_timetable_publication_notifications multiple times
    for the same version/timetable does NOT create duplicate notifications.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    s1_id, s1_tok = create_test_user("s1_idempotent")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # Create & move V2
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Idempotent", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(CourseMeeting.version_id == v2_id, CourseMeeting.section_id == sec_a_id).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)
    pub_resp = client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)
    assert pub_resp.status_code == 200

    # First call created 1 notification
    s1_notifs_1 = client.get("/api/v1/notifications", headers=s1_headers).json()["data"]["items"]
    assert len(s1_notifs_1) == 1

    # Simulate retry by invoking service directly
    db = SessionLocal()
    summary_retry = process_timetable_publication_notifications(
        db=db,
        institution_id=inst_id,
        timetable_id=tt_id,
        published_version_id=v2_id,
        previous_version_id=v1_id,
        actor_user_id=env["admin_id"],
    )
    db.close()

    # Notifications created on retry should be 0 because dedup_key prevented duplicates
    assert summary_retry["notifications_created"] == 0

    # Student still only has 1 notification total
    s1_notifs_2 = client.get("/api/v1/notifications", headers=s1_headers).json()["data"]["items"]
    assert len(s1_notifs_2) == 1


def test_failure_handling_does_not_rollback_publication():
    """
    Verifies that external push or email service exceptions:
    1. Do NOT crash or roll back the publication transaction.
    2. The in-app notification is still safely stored and readable.
    3. The timetable version is successfully published.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    s1_id, s1_tok = create_test_user("s1_fail_resilient")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # Enable email in prefs to trigger email code path
    client.put("/api/v1/notifications/prefs", headers=s1_headers, json={"email_enabled": True})

    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Failure Resilience", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]

    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(CourseMeeting.version_id == v2_id, CourseMeeting.section_id == sec_a_id).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)

    # Patch external services to raise errors
    with patch("app.services.timetable_notification_service.send_email_alert", side_effect=Exception("SMTP server connection timeout")), \
         patch("app.services.timetable_notification_service.send_web_push", side_effect=Exception("WebPush gateway rejected")):

        pub_resp = client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)
        assert pub_resp.status_code == 200, pub_resp.text
        pub_data = pub_resp.json()["data"]

        # Publication succeeded
        assert pub_data["success"] is True
        assert pub_data["published_version"]["status"] == "published"

        # In-app notification still delivered
        summary = pub_data["notification_summary"]
        assert summary["in_app_delivered"] == 1
        assert summary["email_failed"] == 1

        # Student can still view in-app notification
        s1_notifs = client.get("/api/v1/notifications", headers=s1_headers).json()["data"]["items"]
        assert len(s1_notifs) == 1
        assert "Database Systems" in s1_notifs[0]["body"]


def test_student_schedule_synchronization():
    """
    Verifies that:
    1. Before publication, student academic schedule reflects Version 1.
    2. After publication, student academic schedule reflects Version 2 automatically.
    3. Student's existing work shifts and personal events remain completely unchanged.
    4. Timetable meetings are NOT duplicated into time_blocks.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    s1_id, s1_tok = create_test_user("s1_sync")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # Student personal shift: Tuesday 09:00 - 13:00
    shift_resp = client.post(
        "/api/v1/blocks",
        headers=s1_headers,
        json={
            "title": "Barista Shift",
            "type": "shift",
            "day_of_week": 2,
            "start_time": "09:00:00",
            "end_time": "13:00:00",
            "is_flexible": False,
        },
    )
    assert shift_resp.status_code == 201
    shift_id = shift_resp.json()["data"]["id"]

    # Student study session: Wednesday 18:00 - 19:00
    event_resp = client.post(
        "/api/v1/blocks",
        headers=s1_headers,
        json={
            "title": "Gym Session",
            "type": "study",
            "day_of_week": 3,
            "start_time": "18:00:00",
            "end_time": "19:00:00",
            "is_flexible": False,
        },
    )
    assert event_resp.status_code == 201
    event_id = event_resp.json()["data"]["id"]

    # 1. Check schedule before publish: class is Monday 10:00-11:00
    sched_v1 = client.get("/api/v1/students/me/schedule", headers=s1_headers).json()["data"]
    assert len(sched_v1["meetings"]) == 1
    cls_v1 = sched_v1["meetings"][0]
    assert cls_v1["day_of_week"] == 1
    assert "10:00" in cls_v1["start_time"]
    assert "11:00" in cls_v1["end_time"]

    # 2. Create and publish Version 2: moves class to Monday 14:00-15:00
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Schedule Sync", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(CourseMeeting.version_id == v2_id, CourseMeeting.section_id == sec_a_id).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)

    # 3. Check schedule after publish: class automatically reflects new 14:00-15:00 time
    sched_v2 = client.get("/api/v1/students/me/schedule", headers=s1_headers).json()["data"]
    assert len(sched_v2["meetings"]) == 1
    cls_v2 = sched_v2["meetings"][0]
    assert cls_v2["day_of_week"] == 1
    assert "14:00" in cls_v2["start_time"]
    assert "15:00" in cls_v2["end_time"]

    # 4. Verify student's work shift and personal event are COMPLETELY UNCHANGED
    db = SessionLocal()
    shift_block = db.query(TimeBlock).filter(TimeBlock.id == shift_id).first()
    assert shift_block.title == "Barista Shift"
    assert shift_block.day_of_week == 2
    assert str(shift_block.start_time).startswith("09:00")
    assert str(shift_block.end_time).startswith("13:00")

    event_block = db.query(TimeBlock).filter(TimeBlock.id == event_id).first()
    assert event_block.title == "Gym Session"
    assert event_block.day_of_week == 3
    assert str(event_block.start_time).startswith("18:00")
    assert str(event_block.end_time).startswith("19:00")

    # 5. Verify timetable meetings are NOT copied into TimeBlock table
    tb_classes = db.query(TimeBlock).filter(
        TimeBlock.user_id == s1_id,
        TimeBlock.type == "class",
    ).all()
    assert len(tb_classes) == 0
    db.close()


def test_ics_export_reflects_official_schedule():
    """
    Verifies that the student's ICS export endpoint (/api/v1/students/me/schedule/export.ics)
    returns valid iCalendar format containing official published meetings.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    sec_a_id = env["sec_a_id"]

    s1_id, s1_tok = create_test_user("s1_ics")
    s1_headers = {"Authorization": f"Bearer {s1_tok}"}
    add_member(env["admin_token"], inst_id, s1_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=s1_headers, json={"section_id": sec_a_id})

    # Export ICS
    resp = client.get("/api/v1/students/me/schedule/export.ics", headers=s1_headers)
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers.get("content-type", "")
    ics_text = resp.text
    assert "BEGIN:VCALENDAR" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "CS301" in ics_text or "Database Systems" in ics_text


def test_student_notification_endpoints_and_authorization():
    """
    Tests student notification interactions:
    1. Querying unread notifications and unread count.
    2. Marking a single notification as read.
    3. Marking all as read.
    4. Authorization: Student A cannot mark Student B's notification as read.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    # Student A and Student B both enrolled in Section A
    sa_id, sa_tok = create_test_user("sa_auth")
    sb_id, sb_tok = create_test_user("sb_auth")
    sa_headers = {"Authorization": f"Bearer {sa_tok}"}
    sb_headers = {"Authorization": f"Bearer {sb_tok}"}

    add_member(env["admin_token"], inst_id, sa_id, "student")
    add_member(env["admin_token"], inst_id, sb_id, "student")
    client.post("/api/v1/students/me/enrollments", headers=sa_headers, json={"section_id": sec_a_id})
    client.post("/api/v1/students/me/enrollments", headers=sb_headers, json={"section_id": sec_a_id})

    # Publish V2 to generate notifications for both students
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Auth Test", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(CourseMeeting.version_id == v2_id, CourseMeeting.section_id == sec_a_id).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)

    # Check unread count for Student A
    count_resp = client.get("/api/v1/notifications/unread-count", headers=sa_headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["data"]["unread_count"] == 1

    # Student A lists notifications
    sa_notifs = client.get("/api/v1/notifications", headers=sa_headers).json()["data"]["items"]
    assert len(sa_notifs) == 1
    sa_notif_id = sa_notifs[0]["id"]

    # Student B lists notifications
    sb_notifs = client.get("/api/v1/notifications", headers=sb_headers).json()["data"]["items"]
    assert len(sb_notifs) == 1
    sb_notif_id = sb_notifs[0]["id"]
    assert sa_notif_id != sb_notif_id

    # Security check: Student A tries to mark Student B's notification as read
    hacker_resp = client.patch(f"/api/v1/notifications/{sb_notif_id}/read", headers=sa_headers)
    assert hacker_resp.status_code in (404, 403), "Student A should not be allowed to mark Student B's notification"

    # Student A marks own notification as read
    read_resp = client.patch(f"/api/v1/notifications/{sa_notif_id}/read", headers=sa_headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["data"]["ok"] is True

    # Student A unread count is now 0
    count_after = client.get("/api/v1/notifications/unread-count", headers=sa_headers).json()["data"]["unread_count"]
    assert count_after == 0

    # Student B marks all as read
    mark_all_resp = client.post("/api/v1/notifications/read-all", headers=sb_headers)
    assert mark_all_resp.status_code == 200
    assert mark_all_resp.json()["data"]["marked_count"] == 1

    count_b_after = client.get("/api/v1/notifications/unread-count", headers=sb_headers).json()["data"]["unread_count"]
    assert count_b_after == 0


def test_tenant_isolation_and_admin_notification_summary():
    """
    Verifies that:
    1. Admin can fetch version notification delivery summary.
    2. Admin of Institution B CANNOT access Institution A's notification data.
    """
    env = setup_n8_environment()
    inst_id = env["inst_id"]
    admin_headers = env["admin_headers"]
    tt_id = env["tt_id"]
    sec_a_id = env["sec_a_id"]
    v1_id = env["v1_id"]

    # Student in Inst A
    sa_id, sa_tok = create_test_user("sa_tenant")
    add_member(env["admin_token"], inst_id, sa_id, "student")
    client.post("/api/v1/students/me/enrollments", headers={"Authorization": f"Bearer {sa_tok}"}, json={"section_id": sec_a_id})

    # Publish V2 in Inst A
    v2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions",
        headers=admin_headers,
        json={"name": "V2 Tenant Test", "source_version_id": v1_id},
    )
    v2_id = v2_resp.json()["data"]["id"]
    db = SessionLocal()
    v2_m1 = db.query(CourseMeeting).filter(CourseMeeting.version_id == v2_id, CourseMeeting.section_id == sec_a_id).first()
    v2_m1.start_time = dt_time(14, 0)
    v2_m1.end_time = dt_time(15, 0)
    db.commit()
    db.close()

    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/review", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/approve", headers=admin_headers)
    client.post(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/publish", headers=admin_headers)

    # Admin A queries delivery summary
    summary_resp = client.get(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/notifications",
        headers=admin_headers,
    )
    assert summary_resp.status_code == 200, summary_resp.text
    s_data = summary_resp.json()["data"]
    assert s_data["students_affected"] == 1
    assert s_data["total_notifications"] == 1
    assert len(s_data["logs"]) == 1
    assert s_data["logs"][0]["student_name"] is not None

    # Institution B Admin
    admin_b_id, admin_b_tok = create_test_user("admin_inst_b")
    inst_b_id, _ = create_test_institution(admin_b_tok, "Rival College")
    admin_b_headers = {"Authorization": f"Bearer {admin_b_tok}"}

    # Admin B attempts to access Inst A's publication notification summary
    cross_resp = client.get(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v2_id}/notifications",
        headers=admin_b_headers,
    )
    assert cross_resp.status_code in (403, 404), "Admin B must not access Institution A's notification metrics"
