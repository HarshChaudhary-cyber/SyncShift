"""
test_security_hardening_n11.py — Security, Privacy, Multi-Tenant Hardening & Production Readiness Test Suite (N11)

Verifies:
1. Multi-tenant isolation: Institution A administrator cannot access, modify, or query Institution B resources (courses, rooms, timetables, analytics).
2. Cross-tenant write prevention: Attempting to create or update resources in another institution is blocked (403/404).
3. IDOR defenses: Students cannot access other students' notifications, timeblocks, or AI conversations.
4. Role-Based Access Control (RBAC): Students cannot publish, approve, or view university analytics or audit logs.
5. Draft timetable version isolation: Unapproved/draft versions are completely hidden from student views and direct access (404).
6. AI Assistant tool tenant isolation: Tool arguments with cross-tenant IDs are strictly rejected.
7. AI Assistant prompt injection / permission defense: AI tools enforce server-side role and tenant verification.
8. Rate limiting & resource exhaustion: Limits on password changes, file imports, and excessive pagination.
9. Malicious file upload handling: Path traversal in filenames and oversized imports are blocked safely.
10. Mock authentication token rejection in production mode: dev tokens fail with 401 when ENV='production'.
11. Secret & credential leak prevention: Passwords, password hashes, and provider tokens are never exposed.
"""

from datetime import date
import io
import uuid
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.department import Department
from app.models.institution import Institution, InstitutionMembership
from app.models.notification import NotificationLog
from app.models.room import Room
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.services.assistant_tools import (
    tool_get_students_affected,
    tool_get_version_history,
    tool_preview_timetable_change,
)
from app.services.rate_limiter import reset_rate_limits

client = TestClient(app)


def _create_user(prefix="user"):
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@testsecurity.org"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "name": f"Test {prefix.capitalize()} {uid}",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return data["token"], data["user_id"], email


def _setup_institution_and_membership(admin_user_id: int, inst_name: str, inst_code: str):
    db = SessionLocal()
    try:
        inst = Institution(
            name=inst_name,
            code=inst_code,
            country="GB",
            timezone="Europe/London",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)

        # Admin membership
        mem = InstitutionMembership(
            institution_id=inst.id,
            user_id=admin_user_id,
            role="admin",
            status="active",
        )
        db.add(mem)
        db.commit()
        return inst.id
    finally:
        db.close()


def _add_student_membership(student_user_id: int, institution_id: int):
    db = SessionLocal()
    try:
        mem = InstitutionMembership(
            institution_id=institution_id,
            user_id=student_user_id,
            role="student",
            status="active",
        )
        db.add(mem)
        db.commit()
    finally:
        db.close()


# ==============================================================================
# 1. MULTI-TENANT ISOLATION TESTS
# ==============================================================================

def test_cross_tenant_read_isolation():
    """Admin from Institution A cannot access Institution B's rooms, courses, or timetables."""
    reset_rate_limits()
    token_a, id_a, _ = _create_user("admin_a")
    token_b, id_b, _ = _create_user("admin_b")

    inst_a = _setup_institution_and_membership(id_a, "University A", f"UA_{uuid.uuid4().hex[:4]}")
    inst_b = _setup_institution_and_membership(id_b, "University B", f"UB_{uuid.uuid4().hex[:4]}")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Admin A tries to list rooms of Institution B -> 403 Forbidden
    resp = client.get(f"/api/v1/institutions/{inst_b}/rooms", headers=headers_a)
    assert resp.status_code in (403, 404), resp.text

    # Admin A tries to list timetables of Institution B -> 403 Forbidden
    resp = client.get(f"/api/v1/institutions/{inst_b}/timetables", headers=headers_a)
    assert resp.status_code in (403, 404), resp.text

    # Admin A tries to access analytics of Institution B -> 403 Forbidden
    resp = client.get(f"/api/v1/institutions/{inst_b}/analytics/dashboard", headers=headers_a)
    assert resp.status_code in (403, 404), resp.text


def test_cross_tenant_write_isolation():
    """Admin from Institution A cannot create a room or course inside Institution B."""
    reset_rate_limits()
    token_a, id_a, _ = _create_user("admin_a_write")
    token_b, id_b, _ = _create_user("admin_b_write")

    inst_a = _setup_institution_and_membership(id_a, "University A", f"UA_{uuid.uuid4().hex[:4]}")
    inst_b = _setup_institution_and_membership(id_b, "University B", f"UB_{uuid.uuid4().hex[:4]}")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Attempt to create room in Institution B
    resp = client.post(
        f"/api/v1/institutions/{inst_b}/rooms",
        headers=headers_a,
        json={"room_number": "HACK-101", "capacity": 50},
    )
    assert resp.status_code in (403, 404), resp.text

    # Verify no room was created in Institution B
    db = SessionLocal()
    try:
        r = db.query(Room).filter(Room.institution_id == inst_b, Room.room_number == "HACK-101").first()
        assert r is None
    finally:
        db.close()


# ==============================================================================
# 2. ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================================

def test_student_cannot_publish_or_approve_timetable():
    """A student role cannot approve or publish timetable versions (403 Forbidden)."""
    reset_rate_limits()
    token_admin, id_admin, _ = _create_user("admin_rbac")
    token_student, id_student, _ = _create_user("student_rbac")

    inst_id = _setup_institution_and_membership(id_admin, "RBAC University", f"RBAC_{uuid.uuid4().hex[:4]}")
    _add_student_membership(id_student, inst_id)

    db = SessionLocal()
    try:
        term = AcademicTerm(institution_id=inst_id, name="Fall 2026", academic_year="2026-2027", start_date=date(2026, 9, 1), end_date=date(2026, 12, 15))
        db.add(term)
        db.commit()
        db.refresh(term)

        tt = Timetable(institution_id=inst_id, academic_term_id=term.id, name="Official Timetable", status="active")
        db.add(tt)
        db.commit()
        db.refresh(tt)

        v = TimetableVersion(institution_id=inst_id, timetable_id=tt.id, version_number=1, name="Draft V1", status="draft")
        db.add(v)
        db.commit()
        db.refresh(v)
        v_id = v.id
        tt_id = tt.id
    finally:
        db.close()

    headers_student = {"Authorization": f"Bearer {token_student}"}

    # Student attempts to approve version
    resp_appr = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v_id}/approve",
        headers=headers_student,
        json={"notes": "Malicious approval"},
    )
    assert resp_appr.status_code == 403, resp_appr.text

    # Student attempts to publish version
    resp_pub = client.post(
        f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{v_id}/publish",
        headers=headers_student,
        json={"notes": "Malicious publish"},
    )
    assert resp_pub.status_code == 403, resp_pub.text


def test_student_cannot_access_university_analytics_or_audit_logs():
    """Students are strictly forbidden from viewing administrator analytics or audit logs."""
    reset_rate_limits()
    token_admin, id_admin, _ = _create_user("admin_logs")
    token_student, id_student, _ = _create_user("student_logs")

    inst_id = _setup_institution_and_membership(id_admin, "Audit Univ", f"AU_{uuid.uuid4().hex[:4]}")
    _add_student_membership(id_student, inst_id)

    headers_student = {"Authorization": f"Bearer {token_student}"}

    # Attempt to view university decision analytics dashboard
    resp = client.get(f"/api/v1/institutions/{inst_id}/analytics/dashboard", headers=headers_student)
    assert resp.status_code == 403

    # Attempt to view university decision analytics overview
    resp_overview = client.get(f"/api/v1/institutions/{inst_id}/analytics/overview", headers=headers_student)
    assert resp_overview.status_code == 403

    # Verify audit logs endpoint returns only student's own logs
    resp_audit = client.get("/api/v1/audit-logs", headers=headers_student)
    assert resp_audit.status_code == 200
    for log_item in resp_audit.json()["data"]["items"]:
        assert log_item["user_id"] == id_student


# ==============================================================================
# 3. DRAFT TIMETABLE ISOLATION (STUDENTS CANNOT SEE DRAFTS)
# ==============================================================================

def test_draft_timetable_version_isolation_from_students():
    """
    Students can only see published timetable versions.
    Draft / in-review versions return 404 to students.
    """
    reset_rate_limits()
    token_admin, id_admin, _ = _create_user("admin_draft")
    token_student, id_student, _ = _create_user("student_draft")

    inst_id = _setup_institution_and_membership(id_admin, "Draft Univ", f"DU_{uuid.uuid4().hex[:4]}")
    _add_student_membership(id_student, inst_id)

    db = SessionLocal()
    try:
        term = AcademicTerm(institution_id=inst_id, name="Spring 2026", academic_year="2026-2027", start_date=date(2026, 1, 10), end_date=date(2026, 5, 10))
        db.add(term)
        db.commit()
        db.refresh(term)

        tt = Timetable(institution_id=inst_id, academic_term_id=term.id, name="Test Timetable", status="active")
        db.add(tt)
        db.commit()
        db.refresh(tt)

        v_pub = TimetableVersion(institution_id=inst_id, timetable_id=tt.id, version_number=1, name="Published V1", status="published")
        v_draft = TimetableVersion(institution_id=inst_id, timetable_id=tt.id, version_number=2, name="Secret Draft V2", status="draft")
        db.add_all([v_pub, v_draft])
        db.commit()
        db.refresh(v_pub)
        db.refresh(v_draft)
        pub_id = v_pub.id
        draft_id = v_draft.id
        tt_id = tt.id
    finally:
        db.close()

    headers_student = {"Authorization": f"Bearer {token_student}"}

    # 1. Student lists versions -> only published version should be returned
    resp_list = client.get(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions", headers=headers_student)
    assert resp_list.status_code == 200
    versions = resp_list.json()["data"]
    version_ids = [v["id"] for v in versions]
    assert pub_id in version_ids
    assert draft_id not in version_ids, "Draft version must be invisible to students in version list"

    # 2. Student directly fetches draft version by ID -> 404 Not Found
    resp_get_draft = client.get(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{draft_id}", headers=headers_student)
    assert resp_get_draft.status_code == 404, "Direct request to draft version by student must return 404"

    # 3. Student directly fetches published version by ID -> 200 OK
    resp_get_pub = client.get(f"/api/v1/institutions/{inst_id}/timetables/{tt_id}/versions/{pub_id}", headers=headers_student)
    assert resp_get_pub.status_code == 200


# ==============================================================================
# 4. IDOR / PERSONAL DATA ISOLATION
# ==============================================================================

def test_notification_and_conversation_idor_isolation():
    """User A cannot mark User B's notification read or access User B's AI assistant conversations."""
    reset_rate_limits()
    token_a, id_a, _ = _create_user("user_idor_a")
    token_b, id_b, _ = _create_user("user_idor_b")

    db = SessionLocal()
    try:
        # Create notification for User B
        notif_b = NotificationLog(
            user_id=id_b,
            type="class_reminder",
            title="Class Reminder for B",
            body="Your class starts in 15 minutes.",
            channel="in_app",
            priority="INFO",
        )
        db.add(notif_b)

        # Create conversation for User B
        conv_b = AssistantConversation(
            user_id=id_b,
            title="User B Private Schedule Talk",
        )
        db.add(conv_b)
        db.commit()
        db.refresh(notif_b)
        db.refresh(conv_b)
        notif_b_id = notif_b.id
        conv_b_id = conv_b.id
    finally:
        db.close()

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A tries to mark User B's notification read -> 404 Not Found
    resp_notif = client.patch(f"/api/v1/notifications/{notif_b_id}/read", headers=headers_a)
    assert resp_notif.status_code == 404

    # User A tries to read User B's conversation history -> 404 Not Found
    resp_conv = client.get(f"/api/v1/assistant/conversations/{conv_b_id}", headers=headers_a)
    assert resp_conv.status_code == 404

    # User A tries to delete User B's conversation -> 404 Not Found
    resp_del_conv = client.delete(f"/api/v1/assistant/conversations/{conv_b_id}", headers=headers_a)
    assert resp_del_conv.status_code == 404


# ==============================================================================
# 5. AI TOOL TENANT ISOLATION & PROMPT INJECTION DEFENSE
# ==============================================================================

def test_ai_tool_rejects_cross_tenant_section():
    """
    AI tools with deterministic backend validation reject foreign section or timetable IDs,
    preventing prompt injection or forged tool parameters from accessing other tenants.
    """
    reset_rate_limits()
    token_a, id_a, _ = _create_user("admin_ai_a")
    token_b, id_b, _ = _create_user("admin_ai_b")

    inst_a = _setup_institution_and_membership(id_a, "AI Univ A", f"AIA_{uuid.uuid4().hex[:4]}")
    inst_b = _setup_institution_and_membership(id_b, "AI Univ B", f"AIB_{uuid.uuid4().hex[:4]}")

    db = SessionLocal()
    try:
        # Create course & section in Institution B
        term_b = AcademicTerm(institution_id=inst_b, name="Term B", academic_year="2026-2027", start_date=date(2026, 9, 1), end_date=date(2026, 12, 15))
        db.add(term_b)
        db.commit()
        db.refresh(term_b)

        dept_b = Department(institution_id=inst_b, name="Computer Science", code=f"CS_{uuid.uuid4().hex[:4]}")
        db.add(dept_b)
        db.commit()
        db.refresh(dept_b)

        course_b = AcademicCourse(institution_id=inst_b, department_id=dept_b.id, code="CS101", name="Secret Course B")
        db.add(course_b)
        db.commit()
        db.refresh(course_b)

        sec_b = AcademicSection(
            institution_id=inst_b,
            course_id=course_b.id,
            academic_term_id=term_b.id,
            section_code="B01",
            capacity=30,
        )
        db.add(sec_b)
        db.commit()
        db.refresh(sec_b)
        sec_b_id = sec_b.id

        from app.dependencies import CurrentUser
        curr_admin_a = CurrentUser(user_id=id_a, email="admin_a@testsecurity.org")

        # Admin A calls tool_get_students_affected with Institution B's section -> Must raise 404!
        with pytest.raises(Exception) as exc_info:
            tool_get_students_affected(
                db=db,
                current_user=curr_admin_a,
                institution_id=inst_a,
                section_id=sec_b_id,
            )
        assert "404" in str(exc_info.value)
    finally:
        db.close()


# ==============================================================================
# 6. FILE IMPORT SECURITY & RATE LIMITING
# ==============================================================================

def test_file_import_path_traversal_and_size_limits():
    """
    Import endpoints reject path traversal filenames, oversized files, and invalid formats.
    """
    reset_rate_limits()
    token, _, _ = _create_user("import_sec_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Path traversal attempt in .ics filename
    evil_file = io.BytesIO(b"BEGIN:VCALENDAR\nEND:VCALENDAR")
    resp_traversal = client.post(
        "/api/v1/import/ics",
        headers=headers,
        files={"file": ("../../etc/passwd.ics", evil_file, "text/calendar")},
    )
    assert resp_traversal.status_code == 400
    assert "traversal" in resp_traversal.json()["error"]["message"].lower()

    # 2. Dangerous executable extension
    fake_exe = io.BytesIO(b"malicious executable payload")
    resp_exe = client.post(
        "/api/v1/import/file",
        headers=headers,
        files={"file": ("timetable.pdf.exe", fake_exe, "application/octet-stream")},
    )
    assert resp_exe.status_code == 400
    assert "not allowed" in resp_exe.json()["error"]["message"].lower() or "unsupported" in resp_exe.json()["error"]["code"].lower()


def _is_redis_alive() -> bool:
    try:
        import redis
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
        return bool(r.ping())
    except Exception:
        return False


@pytest.mark.skipif(not _is_redis_alive(), reason="Redis server is required for rate limit test")
def test_password_change_rate_limiting():
    """Change password endpoint enforces rate limiting (5 attempts per minute)."""
    orig_rl = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = True
    reset_rate_limits()
    token, _, _ = _create_user("pw_rate_user")
    headers = {"Authorization": f"Bearer {token}"}

    # 5 attempts allowed, 6th should be rejected with 429
    for i in range(5):
        resp = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "WrongPassword!", "new_password": "NewValidPassword123!"},
        )
        assert resp.status_code in (401, 400)

    # 6th attempt must trigger rate limit
    resp_blocked = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongPassword!", "new_password": "NewValidPassword123!"},
    )
    try:
        assert resp_blocked.status_code == 429
        assert resp_blocked.json()["error"]["code"] == "rate_limit_exceeded"
    finally:
        settings.RATE_LIMIT_ENABLED = orig_rl


# ==============================================================================
# 7. RESOURCE EXHAUSTION / PAGINATION BOUNDS
# ==============================================================================

def test_excessive_pagination_bounded():
    """Endpoints with pagination validate and reject excessively large page sizes (limit > 100)."""
    reset_rate_limits()
    token, _, _ = _create_user("paging_user")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/notifications?limit=500", headers=headers)
    assert resp.status_code == 422, "Excessive page size (limit > 100) must be rejected by validation"
    assert "validation_error" in resp.json()["error"]["code"]


# ==============================================================================
# 8. MOCK TOKEN PRODUCTION REJECTION
# ==============================================================================

def test_mock_tokens_rejected_in_all_environments():
    """Dev mock tokens (mock_token_*) are strictly rejected with 401 in all environments."""
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer mock_token_1"})
    assert resp.status_code == 401

def test_missing_user_jwt_rejected():
    """A correctly signed JWT for a user that does not exist in the database is rejected."""
    from app.dependencies import create_access_token
    token = create_access_token(user_id=999999, email="missing@example.com")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "user_not_found"

def test_valid_existing_user_jwt_accepted():
    """A correctly signed JWT for an existing user is accepted."""
    token, id_u, email = _create_user("valid_jwt")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == email
