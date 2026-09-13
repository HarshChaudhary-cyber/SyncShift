import time
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.institution import Institution, InstitutionMembership
from app.models.department import Department
from app.models.academic_term import AcademicTerm

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


def test_unauthenticated_requests_rejected():
    """Unauthenticated requests must be rejected with 401."""
    resp = client.get("/api/v1/institutions/me")
    assert resp.status_code == 401

    resp = client.post("/api/v1/institutions", json={"name": "Test", "code": "TEST"})
    assert resp.status_code == 401

    resp = client.get("/api/v1/institutions/1/departments")
    assert resp.status_code == 401


def test_onboarding_and_institution_creation():
    """User can create an institution and automatically becomes ADMIN."""
    admin_id, admin_token = create_test_user("admin_onboard")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Initial status check before institution
    me_resp = client.get("/api/v1/institutions/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["has_institution"] is False

    # Create institution
    inst_code = f"MIT_{int(time.time())}"
    resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={
            "name": "Massachusetts Institute of Technology",
            "code": inst_code,
            "country": "United States",
            "timezone": "America/New_York",
            "email_domain": "mit.edu",
        },
    )
    assert resp.status_code == 201, resp.text
    inst_data = resp.json()["data"]
    inst_id = inst_data["id"]
    assert inst_data["code"] == inst_code
    assert inst_data["is_active"] is True

    # Status check after creation
    me_resp2 = client.get("/api/v1/institutions/me", headers=headers)
    assert me_resp2.status_code == 200
    status_data = me_resp2.json()["data"]
    assert status_data["has_institution"] is True
    assert status_data["institution"]["id"] == inst_id
    assert status_data["membership"]["role"] == "admin"


def test_role_based_access_control():
    """Verify that STUDENTS and PROFESSORS cannot perform ADMIN-only actions."""
    admin_id, admin_token = create_test_user("admin_rbac")
    student_id, student_token = create_test_user("student_rbac")
    prof_id, prof_token = create_test_user("prof_rbac")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    prof_headers = {"Authorization": f"Bearer {prof_token}"}

    # Admin creates institution
    inst_code = f"STAN_{int(time.time())}"
    inst_resp = client.post(
        "/api/v1/institutions",
        headers=admin_headers,
        json={"name": "Stanford University", "code": inst_code},
    )
    inst_id = inst_resp.json()["data"]["id"]

    # Admin adds student and professor members
    add_student_resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=admin_headers,
        json={"user_id": student_id, "role": "student"},
    )
    assert add_student_resp.status_code == 201

    add_prof_resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=admin_headers,
        json={"user_id": prof_id, "role": "professor"},
    )
    assert add_prof_resp.status_code == 201

    # Admin creates a department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Computer Science", "code": "CS"},
    )
    assert dept_resp.status_code == 201
    dept_id = dept_resp.json()["data"]["id"]

    # Student CAN view department
    student_dept_resp = client.get(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=student_headers,
    )
    assert student_dept_resp.status_code == 200
    assert len(student_dept_resp.json()["data"]) == 1

    # Student CANNOT create department (403)
    student_create_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=student_headers,
        json={"name": "Physics", "code": "PHYS"},
    )
    assert student_create_resp.status_code == 403
    assert student_create_resp.json()["error"]["code"] == "forbidden"

    # Professor CANNOT create department (403)
    prof_create_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=prof_headers,
        json={"name": "Mathematics", "code": "MATH"},
    )
    assert prof_create_resp.status_code == 403

    # Student CANNOT update department (403)
    student_update_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/departments/{dept_id}",
        headers=student_headers,
        json={"name": "Hacked CS"},
    )
    assert student_update_resp.status_code == 403

    # Student CANNOT delete department (403)
    student_del_resp = client.delete(
        f"/api/v1/institutions/{inst_id}/departments/{dept_id}",
        headers=student_headers,
    )
    assert student_del_resp.status_code == 403

    # Student CANNOT view member list (403)
    student_members_resp = client.get(
        f"/api/v1/institutions/{inst_id}/members",
        headers=student_headers,
    )
    assert student_members_resp.status_code == 403


def test_multi_tenant_data_isolation():
    """Verify strict tenant isolation: Institution A cannot access Institution B data."""
    # Institution A
    admin_a_id, admin_a_token = create_test_user("admin_a")
    headers_a = {"Authorization": f"Bearer {admin_a_token}"}
    inst_a_resp = client.post(
        "/api/v1/institutions",
        headers=headers_a,
        json={"name": "University of Oxford", "code": f"OX_{int(time.time())}"},
    )
    inst_a_id = inst_a_resp.json()["data"]["id"]

    dept_a_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/departments",
        headers=headers_a,
        json={"name": "Engineering Science", "code": "ENG"},
    )
    dept_a_id = dept_a_resp.json()["data"]["id"]

    term_a_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/terms",
        headers=headers_a,
        json={
            "name": "Michaelmas Term 2026",
            "academic_year": "2026-2027",
            "term_type": "trimester",
            "start_date": "2026-10-01",
            "end_date": "2026-12-15",
        },
    )
    term_a_id = term_a_resp.json()["data"]["id"]

    # Institution B
    admin_b_id, admin_b_token = create_test_user("admin_b")
    headers_b = {"Authorization": f"Bearer {admin_b_token}"}
    inst_b_resp = client.post(
        "/api/v1/institutions",
        headers=headers_b,
        json={"name": "University of Cambridge", "code": f"CAM_{int(time.time())}"},
    )
    inst_b_id = inst_b_resp.json()["data"]["id"]

    # 1. Admin B tries to list Institution A's departments -> 403 Forbidden
    cross_list_resp = client.get(
        f"/api/v1/institutions/{inst_a_id}/departments",
        headers=headers_b,
    )
    assert cross_list_resp.status_code == 403
    assert cross_list_resp.json()["error"]["code"] == "unauthorized_institution_access"

    # 2. Admin B tries to read Institution A's department through Institution B's endpoint -> 404
    cross_get_resp = client.get(
        f"/api/v1/institutions/{inst_b_id}/departments/{dept_a_id}",
        headers=headers_b,
    )
    assert cross_get_resp.status_code == 404

    # 3. Admin B tries to update Institution A's department through Institution B's endpoint -> 404
    cross_update_resp = client.patch(
        f"/api/v1/institutions/{inst_b_id}/departments/{dept_a_id}",
        headers=headers_b,
        json={"name": "Malicious Update"},
    )
    assert cross_update_resp.status_code == 404

    # 4. Admin B tries to delete Institution A's department through Institution A's endpoint -> 403
    cross_del_resp = client.delete(
        f"/api/v1/institutions/{inst_a_id}/departments/{dept_a_id}",
        headers=headers_b,
    )
    assert cross_del_resp.status_code == 403

    # 5. Admin B tries to read Institution A's terms -> 403
    cross_terms_resp = client.get(
        f"/api/v1/institutions/{inst_a_id}/terms",
        headers=headers_b,
    )
    assert cross_terms_resp.status_code == 403

    # 6. Admin B tries to view Institution A's members -> 403
    cross_members_resp = client.get(
        f"/api/v1/institutions/{inst_a_id}/members",
        headers=headers_b,
    )
    assert cross_members_resp.status_code == 403


def test_department_crud_and_code_uniqueness():
    """Test full department CRUD and code uniqueness within institution."""
    admin_id, token = create_test_user("dept_crud")
    headers = {"Authorization": f"Bearer {token}"}

    inst_resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={"name": "Caltech", "code": f"CIT_{int(time.time())}"},
    )
    inst_id = inst_resp.json()["data"]["id"]

    # 1. Create department
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Computer Science", "code": "CS", "description": "Computing dept"},
    )
    assert resp.status_code == 201
    dept_id = resp.json()["data"]["id"]
    assert resp.json()["data"]["code"] == "CS"

    # 2. Duplicate code within same institution -> 409 Conflict
    dup_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Cyber Systems", "code": "cs"},
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "duplicate_department_code"

    # 3. Update department
    update_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/departments/{dept_id}",
        headers=headers,
        json={"name": "Computer Science & Engineering", "description": "Expanded CSE"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Computer Science & Engineering"

    # 4. Soft delete department
    del_resp = client.delete(
        f"/api/v1/institutions/{inst_id}/departments/{dept_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 5. Get deleted department -> 404
    get_resp = client.get(
        f"/api/v1/institutions/{inst_id}/departments/{dept_id}",
        headers=headers,
    )
    assert get_resp.status_code == 404


def test_academic_term_crud_and_validation():
    """Test academic term CRUD and date validation."""
    admin_id, token = create_test_user("term_crud")
    headers = {"Authorization": f"Bearer {token}"}

    inst_resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={"name": "Princeton University", "code": f"PRINCE_{int(time.time())}"},
    )
    inst_id = inst_resp.json()["data"]["id"]

    # 1. Invalid dates: end_date before start_date -> 422
    bad_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "start_date": "2026-12-01",
            "end_date": "2026-09-01",
        },
    )
    assert bad_resp.status_code == 422

    # 2. Invalid dates: end_date equals start_date -> 422
    equal_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "One Day Term",
            "academic_year": "2026-2027",
            "start_date": "2026-09-01",
            "end_date": "2026-09-01",
        },
    )
    assert equal_resp.status_code == 422

    # 3. Valid term creation
    term_resp = client.post(
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
    assert term_resp.status_code == 201
    term_id = term_resp.json()["data"]["id"]
    assert term_resp.json()["data"]["status"] == "active"

    # 4. List terms
    list_resp = client.get(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) >= 1

    # 5. Update term
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/terms/{term_id}",
        headers=headers,
        json={"name": "Fall 2026 Regular", "status": "active"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["name"] == "Fall 2026 Regular"

    # 6. Delete term
    del_resp = client.delete(
        f"/api/v1/institutions/{inst_id}/terms/{term_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True


def test_university_dashboard_endpoint():
    """Verify that university dashboard returns institution info, metrics, and role."""
    admin_id, token = create_test_user("dash_test")
    headers = {"Authorization": f"Bearer {token}"}

    inst_resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={"name": "Harvard University", "code": f"HARV_{int(time.time())}"},
    )
    inst_id = inst_resp.json()["data"]["id"]

    # Create dept & term
    client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Department of Physics", "code": "PHYS"},
    )
    client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "Spring 2027",
            "academic_year": "2026-2027",
            "term_type": "semester",
            "start_date": "2027-01-15",
            "end_date": "2027-05-20",
            "status": "active",
        },
    )

    dash_resp = client.get(
        f"/api/v1/institutions/{inst_id}/dashboard",
        headers=headers,
    )
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()["data"]
    assert dash_data["department_count"] == 1
    assert dash_data["member_count"] == 1
    assert dash_data["membership"]["role"] == "admin"
    assert dash_data["active_term"]["name"] == "Spring 2027"
