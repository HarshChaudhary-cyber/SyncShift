"""
test_role_routing_matrix.py — Comprehensive Test Matrix for Phase 10:
Student vs University Role Assignment and Login Routing.

Validates the full 20-scenario test matrix:
EMAIL/PASSWORD:
1. Student signup -> student role / unassigned
2. Student login -> maps to /student/dashboard

UNIVERSITY USERS:
3. Existing faculty login -> returns faculty -> /university/dashboard
4. Existing professor login -> returns professor -> /university/dashboard
5. Existing admin login -> returns admin -> /university/dashboard
6. Existing super_admin login -> returns super_admin -> /university/dashboard

SECURITY:
7. Public user cannot self-assign admin in signup payload
8. Public user cannot self-assign super_admin in signup payload
9. Public user cannot self-assign faculty in signup payload
10. Public user cannot self-assign professor in signup payload
11. Student cannot access /university/* endpoints (403 Forbidden)
12. University user cannot be downgraded/changed by frontend PATCH payload
13. Role comes strictly from backend/database institution_memberships

OAUTH:
14. Google existing user preserves role
15. Microsoft existing user preserves role
16. New OAuth user gets only safe unassigned student role (no elevated role)
17. OAuth provider cannot select an arbitrary privileged role

ROUTING:
18. Login does not always redirect to student dashboard
19. Correct portal is selected from authoritative role
20. Direct protected URL access remains protected (401 unauthenticated, 403 unauthorized)
"""

import uuid
from typing import Optional
import bcrypt
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.institution import Institution, InstitutionMembership
from app.models.user import User
from app.dependencies import create_access_token

# Disable rate limiting for unit tests so they pass without requiring a live Redis server
settings.RATE_LIMIT_ENABLED = False

client = TestClient(app)


def _hash_pwd(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _get_portal_redirect(role: Optional[str]) -> str:
    """Canonical frontend portal routing logic mirroring RoleGuard.getPortalRedirect()."""
    if not role:
        return "/student/dashboard"
    normalized = role.lower().strip()
    if normalized in ("faculty", "professor", "admin", "super_admin"):
        return "/university/dashboard"
    return "/student/dashboard"


def _create_test_institution(prefix="MatrixUni") -> Institution:
    uid = str(uuid.uuid4())[:6].upper()
    db = SessionLocal(expire_on_commit=False)
    try:
        inst = Institution(
            name=f"{prefix} {uid}",
            code=f"MUT_{uid}",
            timezone="Europe/London",
            is_active=True,
        )
        db.add(inst)
        db.commit()
        return inst
    finally:
        db.close()


def _create_user_with_membership(email: str, password: str, role: Optional[str] = None, inst_id: Optional[int] = None) -> User:
    db = SessionLocal(expire_on_commit=False)
    try:
        user = User(
            email=email.lower().strip(),
            name=email.split("@")[0],
            password_hash=_hash_pwd(password),
            timezone="Europe/London",
            weekly_work_hour_limit=20.0,
        )
        db.add(user)
        db.commit()

        if role and inst_id:
            m = InstitutionMembership(
                user_id=user.id,
                institution_id=inst_id,
                role=role,
                status="active",
            )
            db.add(m)
            db.commit()

        return user
    finally:
        db.close()


# ── EMAIL / PASSWORD SCENARIOS ────────────────────────────────────────────────

def test_01_student_signup_role():
    """1. Student signup produces student account with no elevated privileges."""
    uid = str(uuid.uuid4())[:8]
    email = f"student_signup_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == email
    # New registered user has no institution membership
    assert data["institution_role"] is None
    assert data["institution_id"] is None


def test_02_student_login_routes_to_student_dashboard():
    """2. Student login returns authoritative role that maps to /student/dashboard."""
    uid = str(uuid.uuid4())[:8]
    email = f"student_login_{uid}@example.com"
    pwd = "StudentPassword123!"
    _create_user_with_membership(email=email, password=pwd)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    token = data["token"]
    role = data["institution_role"]

    # Verify routing maps to student dashboard
    redirect = _get_portal_redirect(role)
    assert redirect == "/student/dashboard"

    # Verify GET /auth/me returns identical authoritative role
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert _get_portal_redirect(me_resp.json()["data"]["institution_role"]) == "/student/dashboard"


# ── UNIVERSITY USERS SCENARIOS ────────────────────────────────────────────────

def test_03_existing_faculty_login_routes_to_university_dashboard():
    """3. Existing faculty login returns role='faculty' and routes to /university/dashboard."""
    inst = _create_test_institution("FacultyUni")
    uid = str(uuid.uuid4())[:8]
    email = f"faculty_{uid}@facultyuni.edu"
    pwd = "FacultyPassword123!"
    _create_user_with_membership(email=email, password=pwd, role="faculty", inst_id=inst.id)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    assert data["institution_role"] == "faculty"
    assert data["institution_id"] == inst.id
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


def test_04_existing_professor_login_routes_to_university_dashboard():
    """4. Existing professor login returns role='professor' and routes to /university/dashboard."""
    inst = _create_test_institution("ProfUni")
    uid = str(uuid.uuid4())[:8]
    email = f"prof_{uid}@profuni.edu"
    pwd = "ProfPassword123!"
    _create_user_with_membership(email=email, password=pwd, role="professor", inst_id=inst.id)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    assert data["institution_role"] == "professor"
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


def test_05_existing_admin_login_routes_to_university_dashboard():
    """5. Existing admin login returns role='admin' and routes to /university/dashboard."""
    inst = _create_test_institution("AdminUni")
    uid = str(uuid.uuid4())[:8]
    email = f"admin_{uid}@adminuni.edu"
    pwd = "AdminPassword123!"
    _create_user_with_membership(email=email, password=pwd, role="admin", inst_id=inst.id)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    assert data["institution_role"] == "admin"
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


def test_06_existing_super_admin_login_routes_to_university_dashboard():
    """6. Existing super_admin login returns role='super_admin' and routes to /university/dashboard."""
    inst = _create_test_institution("SuperUni")
    uid = str(uuid.uuid4())[:8]
    email = f"superadmin_{uid}@superuni.edu"
    pwd = "SuperPassword123!"
    _create_user_with_membership(email=email, password=pwd, role="super_admin", inst_id=inst.id)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    assert data["institution_role"] == "super_admin"
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


# ── SECURITY SCENARIOS ────────────────────────────────────────────────────────

def test_07_public_user_cannot_self_assign_admin():
    """7. Public user cannot gain admin role by passing role='admin' in signup payload."""
    uid = str(uuid.uuid4())[:8]
    email = f"hacker_admin_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "role": "admin",
            "institution_role": "admin",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] != "admin"
    assert data["institution_role"] is None

    # Verify in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        mem = db.query(InstitutionMembership).filter(InstitutionMembership.user_id == user.id).first()
        assert mem is None
    finally:
        db.close()


def test_08_public_user_cannot_self_assign_super_admin():
    """8. Public user cannot gain super_admin role by passing role='super_admin' in signup payload."""
    uid = str(uuid.uuid4())[:8]
    email = f"hacker_super_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "role": "super_admin",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None


def test_09_public_user_cannot_self_assign_faculty():
    """9. Public user cannot gain faculty role by passing role='faculty' in signup payload."""
    uid = str(uuid.uuid4())[:8]
    email = f"hacker_faculty_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "role": "faculty",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None


def test_10_public_user_cannot_self_assign_professor():
    """10. Public user cannot gain professor role by passing role='professor' in signup payload."""
    uid = str(uuid.uuid4())[:8]
    email = f"hacker_prof_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "role": "professor",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None


def test_11_student_cannot_access_university_endpoints():
    """11. Student attempting direct access to university endpoints is blocked with 403 Forbidden."""
    inst = _create_test_institution("ShieldUni")
    uid = str(uuid.uuid4())[:8]
    student = _create_user_with_membership(
        email=f"student_shield_{uid}@shield.edu",
        password="StudentPassword123!",
        role="student",
        inst_id=inst.id,
    )
    token = create_access_token(student.id, student.email)

    # Student tries to create a department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst.id}/departments",
        json={"name": "Forbidden Dept", "code": "FORBID"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dept_resp.status_code == 403
    assert dept_resp.json()["error"]["code"] == "forbidden"


def test_12_university_user_cannot_be_downgraded_or_changed_by_frontend_payload():
    """12. Role cannot be changed via PATCH /api/v1/auth/me payload."""
    inst = _create_test_institution("SecureUni")
    uid = str(uuid.uuid4())[:8]
    admin = _create_user_with_membership(
        email=f"admin_secure_{uid}@secure.edu",
        password="AdminPassword123!",
        role="admin",
        inst_id=inst.id,
    )
    token = create_access_token(admin.id, admin.email)

    # Attempt to tamper with role via profile update
    patch_resp = client.patch(
        "/api/v1/auth/me",
        json={"role": "student", "institution_role": "student", "display_name": "Tampered Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()["data"]
    # Role in database remains admin
    assert data["institution_role"] == "admin"
    assert data["display_name"] == "Tampered Name"


def test_13_role_comes_strictly_from_backend_database():
    """13. Role is authoritative and queried directly from institution_memberships table in DB."""
    inst = _create_test_institution("DbSourceUni")
    uid = str(uuid.uuid4())[:8]
    user = _create_user_with_membership(
        email=f"dbsource_{uid}@dbsource.edu",
        password="DbPassword123!",
        role="faculty",
        inst_id=inst.id,
    )
    token = create_access_token(user.id, user.email)

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.json()["data"]["institution_role"] == "faculty"

    # Update DB directly to professor
    db = SessionLocal()
    try:
        mem = db.query(InstitutionMembership).filter(InstitutionMembership.user_id == user.id).first()
        mem.role = "professor"
        db.commit()
    finally:
        db.close()

    # Next /auth/me immediately reflects DB update
    me_resp2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp2.json()["data"]["institution_role"] == "professor"


# ── OAUTH SCENARIOS ───────────────────────────────────────────────────────────

def test_14_google_existing_user_preserves_role():
    """14. Existing user logging in with Google OAuth preserves their backend institution role."""
    inst = _create_test_institution("GoogleUni")
    uid = str(uuid.uuid4())[:8]
    email = f"google_admin_{uid}@googleuni.edu"
    google_sub = f"sub_google_{uid}"

    db = SessionLocal()
    try:
        user = User(
            name="Google Admin",
            email=email,
            google_id=google_sub,
            oauth_provider="google",
            timezone="Europe/London",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        mem = InstitutionMembership(
            user_id=user.id,
            institution_id=inst.id,
            role="admin",
            status="active",
        )
        db.add(mem)
        db.commit()
    finally:
        db.close()

    mock_token = f"mock_google_:{google_sub}:{email}:Google Admin:pic"
    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": mock_token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] == "admin"
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


def test_15_microsoft_existing_user_preserves_role():
    """15. Existing user logging in with Microsoft OAuth preserves their backend institution role."""
    inst = _create_test_institution("MicrosoftUni")
    uid = str(uuid.uuid4())[:8]
    email = f"ms_faculty_{uid}@microsoftuni.edu"
    ms_oid = f"oid_ms_{uid}"

    db = SessionLocal()
    try:
        user = User(
            name="MS Faculty",
            email=email,
            microsoft_id=ms_oid,
            oauth_provider="microsoft",
            timezone="Europe/London",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        mem = InstitutionMembership(
            user_id=user.id,
            institution_id=inst.id,
            role="faculty",
            status="active",
        )
        db.add(mem)
        db.commit()
    finally:
        db.close()

    mock_token = f"mock_microsoft_:{ms_oid}:{email}:MS Faculty"
    resp = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": mock_token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] == "faculty"
    assert _get_portal_redirect(data["institution_role"]) == "/university/dashboard"


def test_16_new_oauth_user_gets_only_intended_role():
    """16. New OAuth user receives safe unassigned/student role, never an elevated university role."""
    uid = str(uuid.uuid4())[:8]
    email = f"fresh_oauth_{uid}@gmail.com"
    token = f"mock_google_:sub_fresh_{uid}:{email}:Fresh User:pic"

    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None
    assert _get_portal_redirect(data["institution_role"]) == "/student/dashboard"


def test_17_oauth_provider_cannot_select_arbitrary_privileged_role():
    """17. OAuth provider payload cannot inject a privileged role into the response."""
    uid = str(uuid.uuid4())[:8]
    email = f"injected_oauth_{uid}@university.edu"
    # Even if email domain is university.edu, no privileged role is granted without admin provisioning
    token = f"mock_google_:sub_inject_{uid}:{email}:Injected User:pic"

    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None
    assert _get_portal_redirect(data["institution_role"]) == "/student/dashboard"


# ── ROUTING MATRIX SCENARIOS ──────────────────────────────────────────────────

def test_18_login_does_not_always_redirect_to_student_dashboard():
    """18. Verify that university users redirect to /university/dashboard, not /student/dashboard."""
    inst = _create_test_institution("RoutingUni")
    uid = str(uuid.uuid4())[:8]
    admin = _create_user_with_membership(
        email=f"admin_routing_{uid}@routing.edu",
        password="AdminPassword123!",
        role="admin",
        inst_id=inst.id,
    )
    login_resp = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "AdminPassword123!"})
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    redirect = _get_portal_redirect(data["institution_role"])
    assert redirect != "/student/dashboard"
    assert redirect == "/university/dashboard"


def test_19_correct_portal_selected_from_authoritative_role():
    """19. Verify complete role-to-portal mapping matrix."""
    matrix = {
        None: "/student/dashboard",
        "": "/student/dashboard",
        "student": "/student/dashboard",
        "STUDENT": "/student/dashboard",
        "faculty": "/university/dashboard",
        "FACULTY": "/university/dashboard",
        "professor": "/university/dashboard",
        "PROFESSOR": "/university/dashboard",
        "admin": "/university/dashboard",
        "ADMIN": "/university/dashboard",
        "super_admin": "/university/dashboard",
        "SUPER_ADMIN": "/university/dashboard",
    }
    for role, expected_redirect in matrix.items():
        assert _get_portal_redirect(role) == expected_redirect, f"Role '{role}' should redirect to {expected_redirect}"


def test_20_direct_protected_url_access_remains_protected():
    """20. Unauthenticated access returns 401; unauthorized access to university routes returns 403."""
    inst = _create_test_institution("AccessTestUni")

    # 1. Unauthenticated access
    unauth_resp = client.post(f"/api/v1/institutions/{inst.id}/departments", json={"name": "No Auth", "code": "NOAUTH"})
    assert unauth_resp.status_code == 401

    # 2. Student access to university endpoint
    uid = str(uuid.uuid4())[:8]
    student = _create_user_with_membership(
        email=f"student_acc_{uid}@acc.edu",
        password="StudentPassword123!",
        role="student",
        inst_id=inst.id,
    )
    token = create_access_token(student.id, student.email)
    unauthz_resp = client.post(
        f"/api/v1/institutions/{inst.id}/departments",
        json={"name": "Unauthorized Dept", "code": "UNAUTHZ"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unauthz_resp.status_code == 403
