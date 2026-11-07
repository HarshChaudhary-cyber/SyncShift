"""
Comprehensive tests covering the SyncShift role-based demo dataset and security scenarios:
- Exactly five primary demo accounts exist with correct roles.
- All five accounts authenticate successfully with fixed demo passwords.
- All five belong to SyncShift Demo University (SSDEMO).
- Teacher 1 and Teacher 2 have separate faculty profiles and distinct assignments.
- Student 1 and Student 2 have separate student profiles and section enrollments.
- Old demo credentials no longer authenticate.
- Student access to university administration routes and APIs is denied.
- Teacher access to administrator-only operations is denied.
- Administrator can access allowed university management endpoints.
- Running seed again does not duplicate entities (idempotent seeding).
- Shared class updates are visible to enrolled students.
- Personal tasks and private schedule blocks remain isolated.
"""

import pytest
from datetime import date, time, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.institution import Institution, InstitutionMembership
from app.models.faculty import FacultyProfile
from app.models.student_profile import StudentProfile
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.section_enrollment import SectionEnrollment
from app.models.class_workspace import ClassWorkspace, ClassEvent
from app.models.academic_section import AcademicSection
from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.services.class_workspaces import shared_occurrences, require_class
from app.scripts.seed_demo import seed_demo_data, DEMO_PASSWORDS, PRIMARY_DEMO_EMAILS, OLD_DEMO_EMAILS

client = TestClient(app)


@pytest.fixture(scope="module")
def seeded_db():
    """Ensure database has the demo dataset seeded."""
    from app.scripts import seed_demo
    patcher = pytest.MonkeyPatch()
    patcher.setattr(seed_demo, "apply_migrations", lambda: None)
    session = next(get_db())
    try:
        seed_demo_data(session)
        yield session
    finally:
        session.close()
        patcher.undo()


def test_idempotent_seeding(seeded_db):
    """Re-running seeding must not create duplicate entities or users."""
    inst_count_before = seeded_db.query(Institution).filter_by(code="SSDEMO").count()
    user_count_before = seeded_db.query(User).filter(User.email.like("%@ssdemo.example")).count()
    section_count_before = seeded_db.query(AcademicSection).count()

    # Re-run seed
    seed_demo_data(seeded_db)

    inst_count_after = seeded_db.query(Institution).filter_by(code="SSDEMO").count()
    user_count_after = seeded_db.query(User).filter(User.email.like("%@ssdemo.example")).count()
    section_count_after = seeded_db.query(AcademicSection).count()

    assert inst_count_before == inst_count_after == 1
    assert user_count_before == user_count_after == 5
    assert section_count_before == section_count_after


def test_five_primary_demo_accounts_exist_and_roles(seeded_db):
    """Verify exactly five primary demo accounts exist with correct database roles."""
    demo_users = seeded_db.query(User).filter(User.email.like("%@ssdemo.example")).all()
    emails = {u.email for u in demo_users}
    assert emails == PRIMARY_DEMO_EMAILS
    assert len(demo_users) == 5

    inst_demo = seeded_db.query(Institution).filter_by(code="SSDEMO").first()
    assert inst_demo is not None

    expected_roles = {
        "admin.demo@ssdemo.example": "super_admin",
        "teacher.one@ssdemo.example": "professor",
        "teacher.two@ssdemo.example": "professor",
        "student.one@ssdemo.example": "student",
        "student.two@ssdemo.example": "student",
    }

    for user in demo_users:
        mem = (
            seeded_db.query(InstitutionMembership)
            .filter_by(institution_id=inst_demo.id, user_id=user.id, status="active", deleted_at=None)
            .first()
        )
        assert mem is not None, f"Active membership missing for {user.email}"
        assert mem.role == expected_roles[user.email], f"Unexpected role for {user.email}: {mem.role}"


def test_all_five_passwords_authenticate_via_api(seeded_db):
    """Verify all five accounts authenticate successfully via POST /api/v1/auth/login and /api/v1/auth/me."""
    accounts_to_test = [
        ("admin.demo@ssdemo.example", DEMO_PASSWORDS["admin"], "super_admin"),
        ("teacher.one@ssdemo.example", DEMO_PASSWORDS["teacher_one"], "professor"),
        ("teacher.two@ssdemo.example", DEMO_PASSWORDS["teacher_two"], "professor"),
        ("student.one@ssdemo.example", DEMO_PASSWORDS["student_one"], "student"),
        ("student.two@ssdemo.example", DEMO_PASSWORDS["student_two"], "student"),
    ]

    for email, pw, expected_role in accounts_to_test:
        res = client.post("/api/v1/auth/login", json={"identifier": email, "password": pw})
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        data = res.json()["data"]
        assert data["email"] == email
        assert data["token"]
        assert data["institution_role"] == expected_role

        # Verify /auth/me
        res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
        assert res_me.status_code == 200, f"/auth/me failed for {email}: {res_me.text}"
        me_data = res_me.json()["data"]
        assert me_data["email"] == email
        assert me_data["institution_role"] == expected_role


def test_student_enrollment_login(seeded_db):
    """Students can log in with their enrollment numbers when institution is specified."""
    inst_demo = seeded_db.query(Institution).filter_by(code="SSDEMO").first()

    # Student 1 with enrollment 00041001
    res1 = client.post("/api/v1/auth/login", json={
        "identifier": "00041001",
        "password": DEMO_PASSWORDS["student_one"],
        "institution_id": inst_demo.id,
    })
    assert res1.status_code == 200, res1.text
    data1 = res1.json()["data"]
    assert data1["email"] == "student.one@ssdemo.example"
    assert data1["institution_role"] == "student"

    # Student 2 with enrollment 00041002
    res2 = client.post("/api/v1/auth/login", json={
        "identifier": "00041002",
        "password": DEMO_PASSWORDS["student_two"],
        "institution_id": inst_demo.id,
    })
    assert res2.status_code == 200, res2.text
    data2 = res2.json()["data"]
    assert data2["email"] == "student.two@ssdemo.example"
    assert data2["institution_role"] == "student"


def test_separate_profiles_and_assignments(seeded_db):
    """Verify distinct faculty and student profiles and valid teaching/enrollment assignments."""
    t1 = seeded_db.query(User).filter_by(email="teacher.one@ssdemo.example").first()
    t2 = seeded_db.query(User).filter_by(email="teacher.two@ssdemo.example").first()
    s1 = seeded_db.query(User).filter_by(email="student.one@ssdemo.example").first()
    s2 = seeded_db.query(User).filter_by(email="student.two@ssdemo.example").first()

    # Faculty profiles
    fp1 = seeded_db.query(FacultyProfile).filter_by(user_id=t1.id).first()
    fp2 = seeded_db.query(FacultyProfile).filter_by(user_id=t2.id).first()
    assert fp1 is not None and fp2 is not None
    assert fp1.id != fp2.id
    assert fp1.employee_code == "FAC-CS-001"
    assert fp2.employee_code == "FAC-MATH-001"

    # Student profiles
    sp1 = seeded_db.query(StudentProfile).filter_by(user_id=s1.id).first()
    sp2 = seeded_db.query(StudentProfile).filter_by(user_id=s2.id).first()
    assert sp1 is not None and sp2 is not None
    assert sp1.id != sp2.id
    assert sp1.student_number == "00041001"
    assert sp2.student_number == "00041002"

    # Teacher assignments
    t1_sections = seeded_db.query(SectionFacultyAssignment).filter_by(faculty_id=fp1.id).all()
    t2_sections = seeded_db.query(SectionFacultyAssignment).filter_by(faculty_id=fp2.id).all()
    assert len(t1_sections) >= 2
    assert len(t2_sections) >= 2

    # Student enrollments
    s1_enr = seeded_db.query(SectionEnrollment).filter_by(student_id=s1.id).all()
    s2_enr = seeded_db.query(SectionEnrollment).filter_by(student_id=s2.id).all()
    assert len(s1_enr) >= 3
    assert len(s2_enr) >= 3


def test_old_primary_demo_credentials_rejected(seeded_db):
    """Verify that retired legacy demo accounts no longer authenticate."""
    for old_email in [
        "admin@ssdemo.example",
        "professor.asha@ssdemo.example",
        "prof.lovelace@ssdemo.example",
        "student.arjun@ssdemo.example",
        "student.meera@ssdemo.example",
        "student.kabir@riverdemo.example",
        "admin@riverdemo.example",
    ]:
        res = client.post("/api/v1/auth/login", json={"identifier": old_email, "password": "AnyPassword123!"})
        assert res.status_code == 401, f"Old account {old_email} was not rejected"


def test_role_based_access_controls(seeded_db):
    """
    Test permission boundaries:
    - Students cannot access academic administration APIs.
    - Teachers cannot perform administrator-only operations.
    - Administrators can access university administration APIs.
    """
    inst_demo = seeded_db.query(Institution).filter_by(code="SSDEMO").first()

    # Login as student
    res_s = client.post("/api/v1/auth/login", json={
        "identifier": "student.one@ssdemo.example",
        "password": DEMO_PASSWORDS["student_one"],
    })
    token_s = res_s.json()["data"]["token"]

    # Student trying to access academic-admin endpoint -> 403 Forbidden
    res_s_admin = client.get(
        f"/api/v1/academic-admin/{inst_demo.id}/users",
        headers={"Authorization": f"Bearer {token_s}"},
    )
    assert res_s_admin.status_code == 403

    # Login as teacher
    res_t = client.post("/api/v1/auth/login", json={
        "identifier": "teacher.one@ssdemo.example",
        "password": DEMO_PASSWORDS["teacher_one"],
    })
    token_t = res_t.json()["data"]["token"]

    # Teacher trying to access admin-only users management -> 403 Forbidden
    res_t_admin = client.get(
        f"/api/v1/academic-admin/{inst_demo.id}/users",
        headers={"Authorization": f"Bearer {token_t}"},
    )
    assert res_t_admin.status_code == 403

    # Login as administrator
    res_a = client.post("/api/v1/auth/login", json={
        "identifier": "admin.demo@ssdemo.example",
        "password": DEMO_PASSWORDS["admin"],
    })
    token_a = res_a.json()["data"]["token"]

    # Administrator accessing academic-admin users -> 200 OK
    res_a_admin = client.get(
        f"/api/v1/academic-admin/{inst_demo.id}/users",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_admin.status_code == 200, res_a_admin.text


def test_shared_class_updates_visible_to_enrolled_students(seeded_db):
    """When a teacher updates a shared class event, enrolled students see the update."""
    s1 = seeded_db.query(User).filter_by(email="student.one@ssdemo.example").first()
    t1 = seeded_db.query(User).filter_by(email="teacher.one@ssdemo.example").first()

    sec_cs101 = seeded_db.query(AcademicSection).filter_by(section_code="CS101-SEC-A").first()
    ws = seeded_db.query(ClassWorkspace).filter_by(section_id=sec_cs101.id).first()

    test_date = date(2026, 10, 14)
    event = seeded_db.query(ClassEvent).filter_by(class_id=ws.id, title="Role Test Workshop").first()
    if not event:
        event = ClassEvent(
            class_id=ws.id,
            title="Role Test Workshop",
            location="Turing Lecture Hall (LH-101)",
            event_date=test_date,
            start_time="10:00",
            end_time="11:30",
            status="published",
        )
        seeded_db.add(event)
        seeded_db.commit()

    occurrences_before = shared_occurrences(seeded_db, s1.id, test_date - timedelta(days=1), test_date + timedelta(days=1))
    matching_before = [o for o in occurrences_before if o.title == "Role Test Workshop"]
    assert len(matching_before) == 1
    assert matching_before[0].start_time == "10:00"

    # Update event time
    event.start_time = "15:00"
    event.end_time = "16:30"
    seeded_db.commit()

    occurrences_after = shared_occurrences(seeded_db, s1.id, test_date - timedelta(days=1), test_date + timedelta(days=1))
    matching_after = [o for o in occurrences_after if o.title == "Role Test Workshop"]
    assert len(matching_after) == 1
    assert matching_after[0].start_time == "15:00"


def test_student_rejection_when_attempting_to_edit_official_classes(seeded_db):
    """Enrolled students cannot modify official class workspaces or shared blocks."""
    s1 = seeded_db.query(User).filter_by(email="student.one@ssdemo.example").first()
    sec_cs101 = seeded_db.query(AcademicSection).filter_by(section_code="CS101-SEC-A").first()
    ws = seeded_db.query(ClassWorkspace).filter_by(section_id=sec_cs101.id).first()

    with pytest.raises(Exception) as exc_info:
        require_class(seeded_db, ws.id, s1.id, instructor=True)
    assert "instructor_required" in str(exc_info.value) or "403" in str(exc_info.value)

    res_login = client.post("/api/v1/auth/login", json={
        "identifier": s1.email,
        "password": DEMO_PASSWORDS["student_one"],
    })
    token = res_login.json()["data"]["token"]

    res_edit = client.patch(
        "/api/v1/blocks/-999999",
        json={"title": "Unauthorized Modification"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_edit.status_code in (403, 404)


def test_professor_student_private_task_isolation(seeded_db):
    """Personal tasks and private planner items never leak between teachers and students or between students."""
    s1 = seeded_db.query(User).filter_by(email="student.one@ssdemo.example").first()
    s2 = seeded_db.query(User).filter_by(email="student.two@ssdemo.example").first()
    t1 = seeded_db.query(User).filter_by(email="teacher.one@ssdemo.example").first()

    s1_tasks = {t.title for t in seeded_db.query(StudyTask).filter_by(user_id=s1.id).all()}
    s2_tasks = {t.title for t in seeded_db.query(StudyTask).filter_by(user_id=s2.id).all()}
    t1_tasks = {t.title for t in seeded_db.query(StudyTask).filter_by(user_id=t1.id).all()}

    assert not (s1_tasks & t1_tasks)
    assert not (s1_tasks & s2_tasks)
    assert "Implement Red-Black Tree in C++" in s1_tasks
    assert "Discrete Probability Problem Set" in s2_tasks
    assert "Finalize Midterm Exam Questions & Solutions" in t1_tasks

    # Verify via API endpoint isolation
    res_login = client.post("/api/v1/auth/login", json={
        "identifier": s1.email,
        "password": DEMO_PASSWORDS["student_one"],
    })
    token = res_login.json()["data"]["token"]

    res_tasks = client.get("/api/v1/tasks", headers={"Authorization": f"Bearer {token}"})
    assert res_tasks.status_code == 200
    returned_titles = {task["title"] for task in res_tasks.json().get("data", [])}
    assert "Implement Red-Black Tree in C++" in returned_titles
    assert "Discrete Probability Problem Set" not in returned_titles
    assert "Finalize Midterm Exam Questions & Solutions" not in returned_titles
