"""
Focused tests covering the SyncShift demo dataset and connected multi-tenant scenarios:
- Idempotent seeding.
- Institution-scoped enrollment login (including cross-university duplicate handling).
- Shared class updates visible to enrolled students.
- Student rejection when attempting to edit official classes.
- Professor/student private-task isolation.
- Cross-university access rejection and unrelated student isolation.
"""

import pytest
from datetime import date, time, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.institution import Institution
from app.models.class_workspace import ClassWorkspace, ClassEvent
from app.models.academic_section import AcademicSection
from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.services.class_workspaces import shared_occurrences, require_class
from app.scripts.seed_demo import seed_demo_data, DEMO_PASSWORDS

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
    """Re-running seeding must not create duplicate entities."""
    # Count entities before second run
    inst_count_before = seeded_db.query(Institution).filter(Institution.code.in_(["SSDEMO", "RIVERDEMO"])).count()
    user_count_before = seeded_db.query(User).filter(
        (User.email.like("%@ssdemo.example")) | (User.email.like("%@riverdemo.example"))
    ).count()
    section_count_before = seeded_db.query(AcademicSection).count()

    # Re-run seed
    seed_demo_data(seeded_db)

    inst_count_after = seeded_db.query(Institution).filter(Institution.code.in_(["SSDEMO", "RIVERDEMO"])).count()
    user_count_after = seeded_db.query(User).filter(
        (User.email.like("%@ssdemo.example")) | (User.email.like("%@riverdemo.example"))
    ).count()
    section_count_after = seeded_db.query(AcademicSection).count()

    assert inst_count_before == inst_count_after == 2
    assert user_count_before == user_count_after
    assert section_count_before == section_count_after


def test_institution_scoped_enrollment_login(seeded_db):
    """
    Enrollment '00041001' exists in both Apex (Maya Lin) and Beacon (Marcus Wright).
    1. Authenticating without context must return 400 institution_selection_required (never guess first match).
    2. Authenticating with Apex institution context logs in Maya Lin.
    3. Authenticating with Beacon institution context logs in Marcus Wright.
    """
    inst_apex = seeded_db.query(Institution).filter_by(code="SSDEMO").first()
    inst_beacon = seeded_db.query(Institution).filter_by(code="RIVERDEMO").first()

    # 1. Ambiguous without institution context
    res_ambig = client.post("/api/v1/auth/login", json={
        "identifier": "00041001",
        "password": DEMO_PASSWORDS["student_primary"],
    })
    assert res_ambig.status_code == 400
    assert "select your university" in res_ambig.text.lower() or "institution" in res_ambig.text.lower()

    # 2. Login to Apex with institution_id
    res_apex = client.post("/api/v1/auth/login", json={
        "identifier": "  00041001  ",
        "password": DEMO_PASSWORDS["student_primary"],
        "institution_id": inst_apex.id,
    })
    assert res_apex.status_code == 200, res_apex.text
    data_apex = res_apex.json()["data"]
    assert data_apex["email"] == "student.arjun@ssdemo.example"
    assert data_apex["institution_role"] == "student"

    # 3. Login to Beacon with institution_id
    res_beacon = client.post("/api/v1/auth/login", json={
        "identifier": "00041001",
        "password": DEMO_PASSWORDS["beacon_student"],
        "institution_id": inst_beacon.id,
    })
    assert res_beacon.status_code == 200, res_beacon.text
    data_beacon = res_beacon.json()["data"]
    assert data_beacon["email"] == "student.kabir@riverdemo.example"
    assert data_beacon["institution_role"] == "student"


def test_shared_class_updates_visible_to_enrolled_students(seeded_db):
    """
    When a professor updates an official class or shared class event time,
    the enrolled student sees the updated time immediately upon calendar fetch.
    """
    maya = seeded_db.query(User).filter_by(email="student.arjun@ssdemo.example").first()
    turing = seeded_db.query(User).filter_by(email="professor.asha@ssdemo.example").first()

    # Find Dr. Turing's CS101 workspace
    sec_cs101 = seeded_db.query(AcademicSection).filter_by(section_code="CS101-SEC-A").first()
    ws = seeded_db.query(ClassWorkspace).filter_by(section_id=sec_cs101.id).first()

    # Dr. Turing updates a published class event
    test_date = date(2026, 10, 14)
    event = seeded_db.query(ClassEvent).filter_by(class_id=ws.id, title="Test Algorithm Workshop").first()
    if not event:
        event = ClassEvent(
            class_id=ws.id,
            title="Test Algorithm Workshop",
            location="Turing Lecture Hall (LH-101)",
            event_date=test_date,
            start_time="10:00",
            end_time="11:30",
            status="published",
        )
        seeded_db.add(event)
        seeded_db.commit()

    # Verify student sees the original time in shared calendar occurrences
    occurrences_before = shared_occurrences(seeded_db, maya.id, test_date - timedelta(days=1), test_date + timedelta(days=1))
    matching_before = [o for o in occurrences_before if o.title == "Test Algorithm Workshop"]
    assert len(matching_before) == 1
    assert matching_before[0].start_time == "10:00"

    # Professor modifies the shared event time to 15:00
    event.start_time = "15:00"
    event.end_time = "16:30"
    seeded_db.commit()

    # Student immediately sees the updated time on subsequent calendar query (source of truth)
    occurrences_after = shared_occurrences(seeded_db, maya.id, test_date - timedelta(days=1), test_date + timedelta(days=1))
    matching_after = [o for o in occurrences_after if o.title == "Test Algorithm Workshop"]
    assert len(matching_after) == 1
    assert matching_after[0].start_time == "15:00"
    assert matching_after[0].end_time == "16:30"


def test_student_rejection_when_attempting_to_edit_official_classes(seeded_db):
    """
    Enrolled students have read-only access to official shared classes and cannot edit them.
    Attempting to modify the class via workspace or personal blocks API must be rejected.
    """
    maya = seeded_db.query(User).filter_by(email="student.arjun@ssdemo.example").first()
    sec_cs101 = seeded_db.query(AcademicSection).filter_by(section_code="CS101-SEC-A").first()
    ws = seeded_db.query(ClassWorkspace).filter_by(section_id=sec_cs101.id).first()

    # Maya tries to perform an instructor-only action on the workspace
    with pytest.raises(Exception) as exc_info:
        require_class(seeded_db, ws.id, maya.id, instructor=True)
    assert "instructor_required" in str(exc_info.value) or "403" in str(exc_info.value)

    # Attempting to edit a shared class block via personal blocks endpoint (negative ID)
    # Login as Maya to obtain token
    res_login = client.post("/api/v1/auth/login", json={
        "identifier": maya.email,
        "password": DEMO_PASSWORDS["student_primary"],
    })
    token = res_login.json()["data"]["token"]

    # Shared classes have negative IDs; personal block update on negative IDs must return 404
    res_edit = client.patch(
        "/api/v1/blocks/-999999",
        json={"title": "Hacked Class Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_edit.status_code in (403, 404)


def test_professor_student_private_task_isolation(seeded_db):
    """
    Personal tasks and private planner items must never leak between professors and students.
    """
    maya = seeded_db.query(User).filter_by(email="student.arjun@ssdemo.example").first()
    turing = seeded_db.query(User).filter_by(email="professor.asha@ssdemo.example").first()

    # Query tasks directly from DB
    maya_tasks = seeded_db.query(StudyTask).filter_by(user_id=maya.id).all()
    turing_tasks = seeded_db.query(StudyTask).filter_by(user_id=turing.id).all()

    maya_titles = {t.title for t in maya_tasks}
    turing_titles = {t.title for t in turing_tasks}

    # Verify no overlap between private tasks
    assert not (maya_titles & turing_titles)
    assert "Implement Red-Black Tree in C++" in maya_titles
    assert "Finalize Midterm Exam Questions & Solutions" in turing_titles

    # Verify via API endpoint isolation
    res_login_maya = client.post("/api/v1/auth/login", json={
        "identifier": maya.email,
        "password": DEMO_PASSWORDS["student_primary"],
    })
    token_maya = res_login_maya.json()["data"]["token"]

    res_tasks_maya = client.get("/api/v1/tasks", headers={"Authorization": f"Bearer {token_maya}"})
    assert res_tasks_maya.status_code == 200
    returned_titles = {task["title"] for task in res_tasks_maya.json().get("data", [])}
    assert "Implement Red-Black Tree in C++" in returned_titles
    assert "Finalize Midterm Exam Questions & Solutions" not in returned_titles


def test_cross_university_access_rejection(seeded_db):
    """
    Users in Beacon University must not access Apex University classes or resources.
    Unrelated students in Apex cannot access classes they are not enrolled in.
    """
    marcus = seeded_db.query(User).filter_by(email="student.kabir@riverdemo.example").first()
    liam = seeded_db.query(User).filter_by(email="student.meera@ssdemo.example").first()
    sec_cs101 = seeded_db.query(AcademicSection).filter_by(section_code="CS101-SEC-A").first()
    ws_cs101 = seeded_db.query(ClassWorkspace).filter_by(section_id=sec_cs101.id).first()

    # 1. Cross-university student (Marcus at Beacon) trying to access Apex CS101 class
    res_login_marcus = client.post("/api/v1/auth/login", json={
        "identifier": marcus.email,
        "password": DEMO_PASSWORDS["beacon_student"],
    })
    token_marcus = res_login_marcus.json()["data"]["token"]

    res_class_marcus = client.get(
        f"/api/v1/classes/{ws_cs101.id}",
        headers={"Authorization": f"Bearer {token_marcus}"},
    )
    assert res_class_marcus.status_code in (403, 404)

    # 2. Unrelated student (Liam at Apex, enrolled only in EE101) trying to access CS101
    res_login_liam = client.post("/api/v1/auth/login", json={
        "identifier": liam.email,
        "password": DEMO_PASSWORDS["student_unrelated"],
    })
    token_liam = res_login_liam.json()["data"]["token"]

    res_class_liam = client.get(
        f"/api/v1/classes/{ws_cs101.id}",
        headers={"Authorization": f"Bearer {token_liam}"},
    )
    assert res_class_liam.status_code in (403, 404)
