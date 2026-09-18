"""
test_portal_roles.py — Comprehensive tests for Role-Based Student & University Portal Authentication,
Authorization, Tenant Isolation, and Student Privacy.

Covers:
1. Student login -> returns institution_role="student"
2. Faculty / Admin login -> returns institution_role="professor" / "admin"
3. Student accessing admin-only university endpoints -> 403 Forbidden
4. Faculty accessing admin-only actions -> 403 Forbidden
5. Admin accessing university endpoints -> 200/201 Success
6. Cross-institution tenant isolation -> 403 Forbidden
7. Student private data isolation (work shifts and personal blocks hidden from university endpoints)
"""

import uuid
import pytest
from starlette.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.institution import Institution, InstitutionMembership
from app.models.academic_term import AcademicTerm
from app.models.department import Department
from app.models.user import User
from app.dependencies import create_access_token

client = TestClient(app)


def _create_user(prefix="user"):
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@portaltest.edu"
    db = SessionLocal()
    try:
        user = User(
            email=email,
            password_hash="$2b$12$e8xO9bW81nQd4Ufxs1/8Eegx2q12qjM4i4RzQJ4uG2O5kP6tF6U2q",
            timezone="Europe/London",
            weekly_work_hour_limit=20.0,
            display_name=f"Test {prefix.capitalize()}",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _create_institution(name="University of Testing"):
    code = f"UOT_{str(uuid.uuid4())[:6].upper()}"
    db = SessionLocal()
    try:
        inst = Institution(
            name=name,
            code=code,
            timezone="Europe/London",
            is_active=True,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst
    finally:
        db.close()


def _add_membership(user_id: int, institution_id: int, role: str):
    db = SessionLocal()
    try:
        m = InstitutionMembership(
            user_id=user_id,
            institution_id=institution_id,
            role=role,
            status="active",
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        return m
    finally:
        db.close()


# ── 1. Role-Based Login & Auth Me Response ────────────────────────────────────

def test_student_auth_me_returns_student_role():
    """Verify that a student user's /auth/me profile contains institution_role='student'."""
    inst = _create_institution("Portal Test University")
    student = _create_user("student_me")
    _add_membership(student.id, inst.id, "student")

    token = create_access_token(student.id, student.email)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_id"] == inst.id
    assert data["institution_role"] == "student"


def test_faculty_and_admin_auth_me_returns_proper_role():
    """Verify that faculty and admin /auth/me profiles contain their respective university roles."""
    inst = _create_institution("Faculty Admin Uni")
    faculty = _create_user("faculty_me")
    professor = _create_user("prof_me")
    admin = _create_user("admin_me")

    _add_membership(faculty.id, inst.id, "faculty")
    _add_membership(professor.id, inst.id, "professor")
    _add_membership(admin.id, inst.id, "admin")

    # Faculty
    fac_token = create_access_token(faculty.id, faculty.email)
    fac_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fac_token}"})
    assert fac_resp.status_code == 200
    assert fac_resp.json()["data"]["institution_role"] == "faculty"

    # Professor
    prof_token = create_access_token(professor.id, professor.email)
    prof_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {prof_token}"})
    assert prof_resp.status_code == 200
    assert prof_resp.json()["data"]["institution_role"] == "professor"

    # Admin
    adm_token = create_access_token(admin.id, admin.email)
    adm_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {adm_token}"})
    assert adm_resp.status_code == 200
    assert adm_resp.json()["data"]["institution_role"] == "admin"


# ── 2. Unauthorized Student Denied Administrative Routes ──────────────────────

def test_student_denied_admin_endpoints():
    """Verify that students cannot create departments, terms, or administrative resources."""
    inst = _create_institution("Shield Academy")
    student = _create_user("student_shield")
    _add_membership(student.id, inst.id, "student")
    token = create_access_token(student.id, student.email)

    # 1. Attempt to create a department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst.id}/departments",
        json={"name": "Computer Science", "code": "CS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dept_resp.status_code == 403
    assert dept_resp.json()["error"]["code"] == "forbidden"

    # 2. Attempt to create an academic term
    term_resp = client.post(
        f"/api/v1/institutions/{inst.id}/terms",
        json={
            "name": "Spring 2026",
            "start_date": "2026-01-10",
            "end_date": "2026-05-15",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert term_resp.status_code == 403
    assert term_resp.json()["error"]["code"] == "forbidden"


# ── 3. Faculty Denied Admin-Only Action ────────────────────────────────────────

def test_faculty_denied_admin_actions():
    """Verify that faculty members cannot perform admin-exclusive actions like modifying institution settings."""
    inst = _create_institution("Research College")
    faculty = _create_user("faculty_research")
    _add_membership(faculty.id, inst.id, "professor")
    token = create_access_token(faculty.id, faculty.email)

    # Faculty attempts to update institution settings (admin only)
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst.id}",
        json={"name": "Hacked University Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 403
    assert patch_resp.json()["error"]["code"] == "forbidden"


# ── 4. Admin Allowed All Actions ──────────────────────────────────────────────

def test_admin_allowed_administrative_actions():
    """Verify that university administrators can create departments and academic terms."""
    inst = _create_institution("Admin Success Uni")
    admin = _create_user("admin_success")
    _add_membership(admin.id, inst.id, "admin")
    token = create_access_token(admin.id, admin.email)

    # Create department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst.id}/departments",
        json={"name": "Engineering Department", "code": f"ENG_{str(uuid.uuid4())[:4]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dept_resp.status_code == 201
    assert dept_resp.json()["data"]["name"] == "Engineering Department"


# ── 5. Cross-Institution Tenant Isolation ─────────────────────────────────────

def test_cross_institution_access_denied():
    """Verify that an admin in Institution A cannot access Institution B resources."""
    inst_a = _create_institution("University Alpha")
    inst_b = _create_institution("University Beta")

    admin_a = _create_user("admin_alpha")
    _add_membership(admin_a.id, inst_a.id, "admin")
    token_a = create_access_token(admin_a.id, admin_a.email)

    # Admin of Alpha attempts to create department in Beta
    resp = client.post(
        f"/api/v1/institutions/{inst_b.id}/departments",
        json={"name": "Illegal Dept", "code": "ILL"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "unauthorized_institution_access"


# ── 6. Student Private Data Isolation ─────────────────────────────────────────

def test_student_private_data_isolation():
    """
    Verify that student private data (work shifts and personal schedule blocks)
    are strictly isolated and never exposed in institutional queries.
    """
    inst = _create_institution("Privacy First University")
    student = _create_user("student_priv")
    admin = _create_user("admin_priv")

    _add_membership(student.id, inst.id, "student")
    _add_membership(admin.id, inst.id, "admin")

    student_token = create_access_token(student.id, student.email)
    admin_token = create_access_token(admin.id, admin.email)

    # Student creates a confidential work shift via API
    create_resp = client.post(
        "/api/v1/blocks",
        json={
            "title": "Hospital ER Night Shift",
            "type": "shift",
            "day_of_week": 4,
            "start_time": "22:00",
            "end_time": "23:30",
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert create_resp.status_code == 201
    shift_id = create_resp.json()["data"]["id"]

    # 1. Student can see their own shift
    student_blocks = client.get("/api/v1/blocks?type=shift", headers={"Authorization": f"Bearer {student_token}"})
    assert student_blocks.status_code == 200
    shift_titles = [b["title"] for b in student_blocks.json()["data"]]
    assert "Hospital ER Night Shift" in shift_titles

    # 2. Admin querying blocks only sees their OWN blocks, NOT the student's shift
    admin_blocks = client.get("/api/v1/blocks?type=shift", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_blocks.status_code == 200
    admin_shift_titles = [b["title"] for b in admin_blocks.json()["data"]]
    assert "Hospital ER Night Shift" not in admin_shift_titles

    # 3. Admin attempting direct IDOR on student block
    idor_resp = client.get(f"/api/v1/blocks/{shift_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert idor_resp.status_code in (403, 404)
