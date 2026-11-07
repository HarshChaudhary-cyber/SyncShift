"""
Comprehensive test suite for University Login & Academic Identifier Authentication.
Tests:
- Existing email/password login for students, professors, and admins
- Enrollment/roll-number login with password
- Preservation and exact matching of leading zeros in enrollment numbers
- Unknown identifiers and incorrect passwords returning generic "Invalid login details"
- Duplicate enrollment numbers across different universities (ambiguous without context, succeeds with institution context)
- Deleted and inactive account rejection
- Verified membership role resolution (client cannot choose role)
- Account transition for provider-only accounts (forgot password -> reset password -> successful login)
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.institution import Institution, InstitutionMembership
from app.models.student_profile import StudentProfile
from app.routers.auth import hash_password

client = TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    """Yield a database session from get_db dependency."""
    session = next(get_db())
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def auth_test_data(db_session: Session):
    """Set up test institutions, users, memberships, and student profiles."""
    u = uuid.uuid4().hex[:8]

    # Institution A
    inst_a = Institution(
        name=f"Apex Technical University {u}",
        code=f"APEX_{u}",
        is_active=True,
    )
    # Institution B
    inst_b = Institution(
        name=f"Beacon State University {u}",
        code=f"BEACON_{u}",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()
    db_session.refresh(inst_a)
    db_session.refresh(inst_b)

    # 1. Student at Inst A with leading zero enrollment "00789"
    email_student_a = f"alice_{u}@apex.edu"
    student_a = User(
        email=email_student_a,
        display_name="Alice Student",
        password_hash=hash_password("ApexSecurePass123!"),
    )
    db_session.add(student_a)
    db_session.commit()
    db_session.refresh(student_a)

    mem_student_a = InstitutionMembership(
        institution_id=inst_a.id,
        user_id=student_a.id,
        role="student",
        status="active",
    )
    profile_student_a = StudentProfile(
        institution_id=inst_a.id,
        user_id=student_a.id,
        student_number=f"00789_{u}",
        status="active",
    )
    db_session.add_all([mem_student_a, profile_student_a])

    # 2. Student at Inst B with identical leading zero enrollment "00789"
    email_student_b = f"bob_{u}@beacon.edu"
    student_b = User(
        email=email_student_b,
        display_name="Bob Student",
        password_hash=hash_password("BeaconPass456!"),
    )
    db_session.add(student_b)
    db_session.commit()
    db_session.refresh(student_b)

    mem_student_b = InstitutionMembership(
        institution_id=inst_b.id,
        user_id=student_b.id,
        role="student",
        status="active",
    )
    profile_student_b = StudentProfile(
        institution_id=inst_b.id,
        user_id=student_b.id,
        student_number=f"00789_{u}",  # same enrollment number as student_a
        status="active",
    )
    db_session.add_all([mem_student_b, profile_student_b])

    # 3. Professor at Inst A
    email_prof_a = f"dr.smith_{u}@apex.edu"
    prof_a = User(
        email=email_prof_a,
        display_name="Dr. Smith",
        password_hash=hash_password("ProfApexPass789!"),
    )
    db_session.add(prof_a)
    db_session.commit()
    db_session.refresh(prof_a)

    mem_prof_a = InstitutionMembership(
        institution_id=inst_a.id,
        user_id=prof_a.id,
        role="professor",
        status="active",
    )
    db_session.add(mem_prof_a)

    # 4. Super Admin at Inst A
    email_admin_a = f"admin_{u}@apex.edu"
    admin_a = User(
        email=email_admin_a,
        display_name="Apex Admin",
        password_hash=hash_password("AdminApexPass000!"),
    )
    db_session.add(admin_a)
    db_session.commit()
    db_session.refresh(admin_a)

    mem_admin_a = InstitutionMembership(
        institution_id=inst_a.id,
        user_id=admin_a.id,
        role="super_admin",
        status="active",
    )
    db_session.add(mem_admin_a)

    # 5. Inactive membership student & Deleted user
    email_disabled = f"disabled_{u}@apex.edu"
    disabled_student = User(
        email=email_disabled,
        display_name="Disabled Student",
        password_hash=hash_password("DisabledPass123!"),
    )
    email_deleted = f"deleted_{u}@apex.edu"
    deleted_student = User(
        email=email_deleted,
        display_name="Deleted Student",
        password_hash=hash_password("DeletedPass123!"),
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([disabled_student, deleted_student])
    db_session.commit()
    db_session.refresh(disabled_student)

    mem_disabled = InstitutionMembership(
        institution_id=inst_a.id,
        user_id=disabled_student.id,
        role="student",
        status="inactive",
    )
    db_session.add(mem_disabled)

    # 6. OAuth-only User (password_hash is None)
    email_oauth = f"oauth_{u}@apex.edu"
    oauth_user = User(
        email=email_oauth,
        display_name="OAuth User",
        password_hash=None,
        oauth_provider="google",
        google_id=f"google-sub-{u}",
    )
    db_session.add(oauth_user)
    db_session.commit()
    db_session.refresh(oauth_user)

    mem_oauth = InstitutionMembership(
        institution_id=inst_a.id,
        user_id=oauth_user.id,
        role="student",
        status="active",
    )
    db_session.add(mem_oauth)
    db_session.commit()

    return {
        "uid": u,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "student_a": student_a,
        "student_b": student_b,
        "prof_a": prof_a,
        "admin_a": admin_a,
        "disabled_student": disabled_student,
        "deleted_student": deleted_student,
        "oauth_user": oauth_user,
        "shared_enrollment": f"00789_{u}",
    }


def test_email_password_login_all_roles(auth_test_data):
    """Test traditional email/password login for student, professor, and admin."""
    # Student
    res = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["student_a"].email,
        "password": "ApexSecurePass123!",
    })
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["token"]
    assert data["institution_role"] == "student"

    # Professor
    res = client.post("/api/v1/auth/login", json={
        "email": auth_test_data["prof_a"].email,  # backwards-compatible email key
        "password": "ProfApexPass789!",
    })
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["token"]
    assert data["institution_role"] == "professor"

    # Super Admin
    res = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["admin_a"].email,
        "password": "AdminApexPass000!",
    })
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["token"]
    assert data["institution_role"] == "super_admin"


def test_enrollment_number_login_with_leading_zeros(auth_test_data):
    """Test enrollment number login preserving leading zeros (e.g. '00789')."""
    inst_a = auth_test_data["inst_a"]
    shared_enrollment = auth_test_data["shared_enrollment"]

    # When institution_id is provided, single match is found
    res = client.post("/api/v1/auth/login", json={
        "identifier": f"  {shared_enrollment}  ",  # tests trimming whitespace as well
        "password": "ApexSecurePass123!",
        "institution_id": inst_a.id,
    })
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["email"] == auth_test_data["student_a"].email
    assert data["institution_role"] == "student"


def test_duplicate_enrollment_across_universities_requires_context(auth_test_data):
    """
    Enrollment exists in both Apex and Beacon universities.
    Without institution context, authentication MUST NOT take the first match across institutions,
    and must return a 400 asking to select university.
    """
    shared_enrollment = auth_test_data["shared_enrollment"]
    res = client.post("/api/v1/auth/login", json={
        "identifier": shared_enrollment,
        "password": "ApexSecurePass123!",
    })
    assert res.status_code == 400
    assert "select your university" in res.text.lower() or "institution" in res.text.lower()

    # Now authenticate to University B specifically with institution_id
    inst_b = auth_test_data["inst_b"]
    res_b = client.post("/api/v1/auth/login", json={
        "identifier": shared_enrollment,
        "password": "BeaconPass456!",
        "institution_id": inst_b.id,
    })
    assert res_b.status_code == 200, res_b.text
    assert res_b.json()["data"]["email"] == auth_test_data["student_b"].email


def test_generic_invalid_login_details_response(auth_test_data):
    """Unknown identifiers and wrong passwords must return the same generic error."""
    # Unknown email
    res1 = client.post("/api/v1/auth/login", json={
        "identifier": "nobody_exists_12345@apex.edu",
        "password": "WrongPassword123!",
    })
    assert res1.status_code == 401
    assert "Invalid login details" in res1.text

    # Existing email, wrong password
    res2 = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["student_a"].email,
        "password": "WrongPassword123!",
    })
    assert res2.status_code == 401
    assert "Invalid login details" in res2.text

    # Unknown enrollment number
    res3 = client.post("/api/v1/auth/login", json={
        "identifier": "999999_nonexistent",
        "password": "SomePassword123!",
        "institution_id": auth_test_data["inst_a"].id,
    })
    assert res3.status_code == 401
    assert "Invalid login details" in res3.text

    # Valid enrollment, wrong password
    res4 = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["shared_enrollment"],
        "password": "WrongPassword123!",
        "institution_id": auth_test_data["inst_a"].id,
    })
    assert res4.status_code == 401
    assert "Invalid login details" in res4.text


def test_deleted_and_inactive_accounts_rejected(auth_test_data):
    """Deleted or disabled accounts must be rejected with generic 401."""
    # Inactive membership
    res1 = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["disabled_student"].email,
        "password": "DisabledPass123!",
    })
    assert res1.status_code == 401
    assert "Invalid login details" in res1.text

    # Deleted user
    res2 = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["deleted_student"].email,
        "password": "DeletedPass123!",
    })
    assert res2.status_code == 401
    assert "Invalid login details" in res2.text


def test_role_cannot_be_selected_by_client(auth_test_data):
    """Role is derived purely from verified database membership, not client request."""
    # Client sends role="super_admin" while authenticating as student
    res = client.post("/api/v1/auth/login", json={
        "identifier": auth_test_data["student_a"].email,
        "password": "ApexSecurePass123!",
        "role": "super_admin",
    })
    assert res.status_code == 200
    data = res.json()["data"]
    # Verified role is student
    assert data["institution_role"] == "student"


def test_oauth_transition_forgot_and_reset_password(auth_test_data, monkeypatch):
    """Existing OAuth-only user transitions smoothly by setting a password via recovery flow."""
    from app.routers import auth
    monkeypatch.setattr(auth, "delivery_available", lambda: True)
    monkeypatch.setattr(auth, "send_reset_link", lambda address, token: None)
    oauth_user = auth_test_data["oauth_user"]

    # 1. Attempting login without password or with empty password fails
    res = client.post("/api/v1/auth/login", json={
        "identifier": oauth_user.email,
        "password": "",
    })
    assert res.status_code == 401

    # 2. Request password reset / setup token
    res_forgot = client.post("/api/v1/auth/forgot-password", json={
        "email": oauth_user.email,
    })
    assert res_forgot.status_code == 200
    
    # Retrieve JTI from db to build token
    from app.database import SessionLocal
    from app.models.user import User
    from app.config import settings
    import jwt, datetime
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == oauth_user.email).first()
        jti = user.password_reset_jti
    finally:
        db.close()
        
    assert jti
    now = datetime.datetime.now(datetime.timezone.utc)
    token = jwt.encode({
        "user_id": oauth_user.id,
        "email": oauth_user.email,
        "purpose": "password_reset",
        "jti": jti,
        "exp": now + datetime.timedelta(minutes=30),
        "iat": now,
    }, settings.JWT_SECRET, algorithm="HS256")


    # 3. Set a new strong password
    res_reset = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "NewStrongTransitionPassword123!",
    })
    assert res_reset.status_code == 200
    assert "Password has been updated" in res_reset.json()["data"]["message"]

    # 4. Now the user can log in with email and new password
    res_login = client.post("/api/v1/auth/login", json={
        "identifier": oauth_user.email,
        "password": "NewStrongTransitionPassword123!",
    })
    assert res_login.status_code == 200
    assert res_login.json()["data"]["email"] == oauth_user.email
