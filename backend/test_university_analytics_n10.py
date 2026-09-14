"""
Test Suite for Task N10 — University Analytics & Decision Dashboard.

Verifies:
1. Institutional overview KPIs (students, courses, sections, rooms, conflicts).
2. Term-aware filtering & progressive disclosure.
3. Enrollment demand analytics (capacity utilization, high demand >=90%, low utilization <=30%).
4. Room scheduled utilization (honest weekly scheduled hours, never physical occupancy).
5. Faculty scheduling insights (neutral operational teaching load, hours, overlap conflicts).
6. Timetable health & conflict breakdown (room collisions, faculty collisions, student clashes).
7. Departmental operational comparisons.
8. Role-based authorization (401 unauth, 403 student/non-admin, 200 admin).
9. Strict multi-tenant isolation & IDOR prevention (Institution A cannot see Institution B).
10. AI Assistant integration with deterministic N10 analytics tools.
"""

from datetime import date, datetime, time as dt_time, timedelta
import uuid
import pytest
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.course_meeting import CourseMeeting
from app.models.department import Department
from app.models.faculty import FacultyProfile
from app.models.institution import Institution, InstitutionMembership
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.student_profile import StudentProfile
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


def setup_institution(admin_headers, name_prefix="Test University"):
    code = f"N10_{str(uuid.uuid4())[:8]}"
    resp = client.post(
        "/api/v1/institutions",
        headers=admin_headers,
        json={"name": f"{name_prefix} {code}", "code": code, "timezone": "America/New_York", "country": "US"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def test_overview_and_enrollment_analytics():
    """Test overview KPIs and section enrollment demand calculation."""
    admin_headers, admin_id = setup_user("admin_n10")
    inst_id = setup_institution(admin_headers, "Analytics Univ")

    # Create Term
    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_active": True,
        },
    )
    assert term_resp.status_code == 201, term_resp.text
    term_id = term_resp.json()["data"]["id"]

    # Create Department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": f"CS_{str(uuid.uuid4())[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["data"]["id"]

    # Create Course
    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={
            "code": f"CS101_{str(uuid.uuid4())[:4]}",
            "name": "Intro to Programming",
            "department_id": dept_id,
            "credits": 4,
        },
    )
    assert course_resp.status_code == 201, course_resp.text
    course_id = course_resp.json()["data"]["id"]

    # Create 2 Sections:
    # Sec A: capacity 10 -> will have 10 enrolled (100% full)
    # Sec B: capacity 20 -> will have 2 enrolled (10% low utilization)
    sec_a_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "SEC-A", "academic_term_id": term_id, "capacity": 10},
    )
    assert sec_a_resp.status_code == 201, sec_a_resp.text
    sec_a_id = sec_a_resp.json()["data"]["id"]

    sec_b_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "SEC-B", "academic_term_id": term_id, "capacity": 20},
    )
    assert sec_b_resp.status_code == 201, sec_b_resp.text
    sec_b_id = sec_b_resp.json()["data"]["id"]

    # Enroll 10 students into Sec A, and 2 students into Sec B
    user_ids_a = []
    for i in range(10):
        _, s_uid = setup_user(f"st_a_{i}")
        user_ids_a.append(s_uid)

    user_ids_b = []
    for i in range(2):
        _, s_uid = setup_user(f"st_b_{i}")
        user_ids_b.append(s_uid)

    db = SessionLocal()
    try:
        for s_uid in user_ids_a:
            sp = StudentProfile(institution_id=inst_id, user_id=s_uid, status="active")
            db.add(sp)
            db.flush()
            enr = SectionEnrollment(
                institution_id=inst_id,
                student_id=s_uid,
                student_profile_id=sp.id,
                section_id=sec_a_id,
                status="active",
            )
            db.add(enr)

        for s_uid in user_ids_b:
            sp = StudentProfile(institution_id=inst_id, user_id=s_uid, status="active")
            db.add(sp)
            db.flush()
            enr = SectionEnrollment(
                institution_id=inst_id,
                student_id=s_uid,
                student_profile_id=sp.id,
                section_id=sec_b_id,
                status="active",
            )
            db.add(enr)
        db.commit()
    finally:
        db.close()

    # 1. Test Overview Endpoint
    ov_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/overview?term_id={term_id}",
        headers=admin_headers,
    )
    assert ov_resp.status_code == 200, ov_resp.text
    ov_data = ov_resp.json()
    assert ov_data["active_students_count"] >= 12
    assert ov_data["enrolled_students_count"] == 12
    assert ov_data["total_enrollments_count"] == 12
    assert ov_data["active_courses_count"] >= 1
    assert ov_data["active_sections_count"] == 2

    # 2. Test Enrollment Demand Endpoint
    enr_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/enrollment?term_id={term_id}",
        headers=admin_headers,
    )
    assert enr_resp.status_code == 200, enr_resp.text
    enr_data = enr_resp.json()
    assert enr_data["total_capacity"] == 30
    assert enr_data["total_enrolled"] == 12
    assert enr_data["overall_capacity_utilization_pct"] == 40.0

    # High Demand: Sec A (10/10 = 100%, full)
    high_demands = enr_data["high_demand_sections"]
    assert any(s["section_id"] == sec_a_id and s["demand_status"] == "full" and s["remaining_seats"] == 0 for s in high_demands)

    # Low Utilization: Sec B (2/20 = 10%, low_utilization)
    low_utils = enr_data["low_utilization_sections"]
    assert any(s["section_id"] == sec_b_id and s["demand_status"] == "low_utilization" and s["remaining_seats"] == 18 for s in low_utils)


def test_room_utilization_and_faculty_schedule():
    """Test room scheduled utilization calculation and faculty workload metrics."""
    admin_headers, admin_id = setup_user("admin_rooms")
    inst_id = setup_institution(admin_headers, "Facilities Univ")

    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Spring 2027",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2027-01-15",
            "end_date": "2027-05-15",
            "is_active": True,
        },
    )
    term_id = term_resp.json()["data"]["id"]

    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Mathematics", "code": f"MATH_{str(uuid.uuid4())[:4]}"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"code": f"MATH201_{str(uuid.uuid4())[:4]}", "name": "Calculus II", "department_id": dept_id},
    )
    course_id = course_resp.json()["data"]["id"]

    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "SEC-01", "academic_term_id": term_id, "capacity": 40},
    )
    sec_id = sec_resp.json()["data"]["id"]

    # Create 2 Rooms: Room 101 and Room 102
    r1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Hall A", "room_number": "101", "capacity": 50, "room_type": "lecture_hall"},
    )
    r1_id = r1_resp.json()["data"]["id"]

    r2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Hall A", "room_number": "102", "capacity": 30, "room_type": "classroom"},
    )
    r2_id = r2_resp.json()["data"]["id"]

    # Create Faculty Profile
    _, prof_uid = setup_user("prof_math")
    db = SessionLocal()
    fac = FacultyProfile(
        institution_id=inst_id,
        user_id=prof_uid,
        department_id=dept_id,
        title="Associate Professor",
        status="active",
    )
    db.add(fac)
    db.flush()

    # Create Timetable & Meetings
    tt = Timetable(
        institution_id=inst_id,
        academic_term_id=term_id,
        name="Spring Timetable",
        status="active",
    )
    db.add(tt)
    db.flush()

    # Meeting 1: Room 101 on Mon 09:00-11:00 (2 hours)
    m1 = CourseMeeting(
        institution_id=inst_id,
        timetable_id=tt.id,
        section_id=sec_id,
        academic_term_id=term_id,
        day_of_week=1,
        start_time=dt_time(9, 0),
        end_time=dt_time(11, 0),
        room_id=r1_id,
        faculty_id=fac.id,
        status="active",
    )
    # Meeting 2: Room 101 on Wed 09:00-11:00 (2 hours)
    m2 = CourseMeeting(
        institution_id=inst_id,
        timetable_id=tt.id,
        section_id=sec_id,
        academic_term_id=term_id,
        day_of_week=3,
        start_time=dt_time(9, 0),
        end_time=dt_time(11, 0),
        room_id=r1_id,
        faculty_id=fac.id,
        status="active",
    )
    # Room 102 has 0 meetings (0 hours)
    db.add_all([m1, m2])
    db.commit()
    db.close()

    # 1. Test Room Utilization
    room_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/rooms?term_id={term_id}",
        headers=admin_headers,
    )
    assert room_resp.status_code == 200, room_resp.text
    room_data = room_resp.json()
    assert room_data["total_rooms"] == 2
    assert room_data["total_weekly_scheduled_hours"] == 4.0
    # Baseline: 2 rooms * 45h = 90h capacity. 4h / 90h = 4.4%
    assert room_data["average_utilization_pct"] == 4.4

    # Room 101 has 4 scheduled hours; (4/45)*100 = 8.9%
    r1_stat = next(r for r in room_data["rooms"] if r["room_id"] == r1_id)
    assert r1_stat["weekly_scheduled_hours"] == 4.0
    assert r1_stat["scheduled_utilization_pct"] == 8.9
    assert r1_stat["meetings_count"] == 2

    # Room 102 has 0 scheduled hours
    r2_stat = next(r for r in room_data["rooms"] if r["room_id"] == r2_id)
    assert r2_stat["weekly_scheduled_hours"] == 0.0
    assert r2_stat["scheduled_utilization_pct"] == 0.0

    # 2. Test Faculty Analytics
    fac_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/faculty?term_id={term_id}",
        headers=admin_headers,
    )
    assert fac_resp.status_code == 200, fac_resp.text
    fac_data = fac_resp.json()
    assert fac_data["teaching_faculty_count"] == 1
    assert fac_data["average_teaching_hours"] == 4.0
    assert len(fac_data["faculty_list"]) >= 1
    fac_item = fac_data["faculty_list"][0]
    assert fac_item["weekly_teaching_hours"] == 4.0
    assert fac_item["sections_count"] == 1
    assert fac_item["has_schedule_conflicts"] is False


def test_timetable_health_and_conflicts():
    """Test collision detection (room double-booking and student conflicts)."""
    admin_headers, admin_id = setup_user("admin_health")
    inst_id = setup_institution(admin_headers, "Health Univ")

    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_active": True,
        },
    )
    term_id = term_resp.json()["data"]["id"]

    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Physics", "code": f"PHYS_{str(uuid.uuid4())[:4]}"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"code": f"PHYS101_{str(uuid.uuid4())[:4]}", "name": "General Physics", "department_id": dept_id},
    )
    course_id = course_resp.json()["data"]["id"]

    sec1_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "SEC-01", "academic_term_id": term_id, "capacity": 30},
    )
    sec1_id = sec1_resp.json()["data"]["id"]

    sec2_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "SEC-02", "academic_term_id": term_id, "capacity": 30},
    )
    sec2_id = sec2_resp.json()["data"]["id"]

    # Room 201
    r_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=admin_headers,
        json={"building": "Science Hall", "room_number": "201", "capacity": 40},
    )
    r_id = r_resp.json()["data"]["id"]

    # Create student enrolled in both sections
    _, s_uid = setup_user("student_conflict")
    db = SessionLocal()
    sp = StudentProfile(institution_id=inst_id, user_id=s_uid, status="active")
    db.add(sp)
    db.flush()

    enr1 = SectionEnrollment(institution_id=inst_id, student_id=s_uid, student_profile_id=sp.id, section_id=sec1_id, status="active")
    enr2 = SectionEnrollment(institution_id=inst_id, student_id=s_uid, student_profile_id=sp.id, section_id=sec2_id, status="active")
    db.add_all([enr1, enr2])

    tt = Timetable(institution_id=inst_id, academic_term_id=term_id, name="Collision Timetable", status="active")
    db.add(tt)
    db.flush()

    # Create overlapping meetings for Sec 1 and Sec 2 in the same room at the same time:
    # Mon 10:00 - 11:30 and Mon 11:00 - 12:30
    m1 = CourseMeeting(
        institution_id=inst_id,
        timetable_id=tt.id,
        section_id=sec1_id,
        academic_term_id=term_id,
        day_of_week=1,
        start_time=dt_time(10, 0),
        end_time=dt_time(11, 30),
        room_id=r_id,
        status="active",
    )
    m2 = CourseMeeting(
        institution_id=inst_id,
        timetable_id=tt.id,
        section_id=sec2_id,
        academic_term_id=term_id,
        day_of_week=1,
        start_time=dt_time(11, 0),
        end_time=dt_time(12, 30),
        room_id=r_id,
        status="active",
    )
    db.add_all([m1, m2])
    db.commit()
    db.close()

    # Query Timetable Health
    th_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/timetable?term_id={term_id}",
        headers=admin_headers,
    )
    assert th_resp.status_code == 200, th_resp.text
    th_data = th_resp.json()
    conflicts = th_data["conflicts"]

    # Must detect the 1 room collision (m1 and m2 share Room 201 from 11:00 to 11:30)
    assert conflicts["room_double_bookings"] == 1
    # Must detect the 1 student class conflict (student is enrolled in both sec1 and sec2)
    assert conflicts["student_class_conflicts"] == 1
    assert conflicts["total_conflicts"] >= 2


def test_role_authorization_and_tenant_isolation():
    """Verifies RBAC protection and cross-institution tenant isolation."""
    admin_a_headers, _ = setup_user("admin_tenant_a")
    admin_b_headers, _ = setup_user("admin_tenant_b")
    student_headers, _ = setup_user("student_unauth")

    inst_a_id = setup_institution(admin_a_headers, "Inst A")
    inst_b_id = setup_institution(admin_b_headers, "Inst B")

    # 1. Unauthenticated blocked (401)
    unauth_resp = client.get(f"/api/v1/institutions/{inst_a_id}/analytics/dashboard")
    assert unauth_resp.status_code in (401, 403), unauth_resp.text

    # 2. Student user blocked (403 Forbidden)
    stud_resp = client.get(f"/api/v1/institutions/{inst_a_id}/analytics/dashboard", headers=student_headers)
    assert stud_resp.status_code == 403, stud_resp.text
    assert "forbidden" in stud_resp.text.lower() or "member" in stud_resp.text.lower() or "privileges" in stud_resp.text.lower()

    # 3. Cross-tenant IDOR: Admin A attempts to view Institution B analytics
    idor_resp = client.get(f"/api/v1/institutions/{inst_b_id}/analytics/dashboard", headers=admin_a_headers)
    assert idor_resp.status_code == 403, idor_resp.text

    # 4. Admin A accessing Institution A succeeds (200 OK)
    ok_resp = client.get(f"/api/v1/institutions/{inst_a_id}/analytics/dashboard", headers=admin_a_headers)
    assert ok_resp.status_code == 200, ok_resp.text
    body = ok_resp.json()
    assert body["institution_id"] == inst_a_id

    # 5. Cross-tenant filter query parameter: Admin A supplies term_id belonging to Institution B
    # Create term in Inst B
    term_b_resp = client.post(
        f"/api/v1/institutions/{inst_b_id}/terms",
        headers=admin_b_headers,
        json={
            "name": "B Term",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2026-09-01",
            "end_date": "2026-12-20",
            "is_active": True,
        },
    )
    term_b_id = term_b_resp.json()["data"]["id"]

    # Admin A attempts to filter Inst A by Inst B's term_id -> must be rejected with 404
    cross_term_resp = client.get(
        f"/api/v1/institutions/{inst_a_id}/analytics/dashboard?term_id={term_b_id}",
        headers=admin_a_headers,
    )
    assert cross_term_resp.status_code == 404, cross_term_resp.text
    assert "term_not_found" in cross_term_resp.text


def test_ai_assistant_analytics_integration():
    """Verifies that Ask SyncShift calls deterministic analytics tools for administrator queries."""
    admin_headers, admin_id = setup_user("admin_ai_ask")
    inst_id = setup_institution(admin_headers, "AI Analytics Univ")

    # 1. Query overview analytics via assistant
    chat_resp = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={
            "message": "Give me a university overview of our campus enrollment and facilities",
            "institution_id": inst_id,
        },
    )
    assert chat_resp.status_code == 200, chat_resp.text
    data = chat_resp.json()["data"]
    assert "University Operational Overview" in data["message"]
    assert any(tc["tool"] == "get_university_analytics_overview" for tc in data["tool_calls"])

    # 2. Query room utilization via assistant
    chat_resp2 = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={
            "message": "Which rooms are most used in our university?",
            "institution_id": inst_id,
        },
    )
    assert chat_resp2.status_code == 200, chat_resp2.text
    data2 = chat_resp2.json()["data"]
    assert "Scheduled Room Utilization" in data2["message"]
    assert any(tc["tool"] == "get_room_utilization_analytics" for tc in data2["tool_calls"])

    # 3. Query section capacity demand via assistant
    chat_resp3 = client.post(
        "/api/v1/assistant/chat",
        headers=admin_headers,
        json={
            "message": "Which sections are nearly full?",
            "institution_id": inst_id,
        },
    )
    assert chat_resp3.status_code == 200, chat_resp3.text
    data3 = chat_resp3.json()["data"]
    assert "Enrollment Demand & Section Capacity" in data3["message"]
    assert any(tc["tool"] == "get_enrollment_analytics" for tc in data3["tool_calls"])


def test_department_comparison_and_empty_states():
    """Verifies departmental comparisons and zero/small-data graceful behavior."""
    admin_headers, admin_id = setup_user("admin_empty_dept")
    inst_id = setup_institution(admin_headers, "Empty Univ")

    # 1. New institution with no data -> check dashboard returns 200 with clean zeros
    dash_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/dashboard",
        headers=admin_headers,
    )
    assert dash_resp.status_code == 200, dash_resp.text
    dash_data = dash_resp.json()
    assert dash_data["overview"]["active_students_count"] == 0
    assert dash_data["overview"]["total_conflicts_count"] == 0
    assert dash_data["enrollment"]["total_capacity"] == 0
    assert dash_data["enrollment"]["all_sections"] == []
    assert dash_data["rooms"]["total_rooms"] == 0
    assert dash_data["faculty"]["total_faculty"] == 0
    assert dash_data["departments"] == []

    # 2. Add department, course, section with real numbers and verify departments comparison
    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=admin_headers,
        json={
            "name": "Summer 2027",
            "academic_year": "2026-2027",
            "term_type": "summer",
            "start_date": "2027-06-01",
            "end_date": "2027-08-15",
            "is_active": True,
        },
    )
    term_id = term_resp.json()["data"]["id"]

    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Economics", "code": f"ECON_{str(uuid.uuid4())[:4]}"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"code": f"ECON101_{str(uuid.uuid4())[:4]}", "name": "Microeconomics", "department_id": dept_id},
    )
    course_id = course_resp.json()["data"]["id"]

    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=admin_headers,
        json={"course_id": course_id, "section_code": "01", "academic_term_id": term_id, "capacity": 50},
    )
    sec_id = sec_resp.json()["data"]["id"]

    # Query departments endpoint
    dept_comp_resp = client.get(
        f"/api/v1/institutions/{inst_id}/analytics/departments?term_id={term_id}",
        headers=admin_headers,
    )
    assert dept_comp_resp.status_code == 200, dept_comp_resp.text
    dept_comp = dept_comp_resp.json()
    assert len(dept_comp) == 1
    assert dept_comp[0]["department_id"] == dept_id
    assert dept_comp[0]["name"] == "Economics"
    assert dept_comp[0]["courses_count"] == 1
    assert dept_comp[0]["sections_count"] == 1
    assert dept_comp[0]["total_capacity"] == 50
    assert dept_comp[0]["total_enrolled"] == 0
    assert dept_comp[0]["capacity_utilization_pct"] == 0.0
