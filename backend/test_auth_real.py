import time
from datetime import datetime, timedelta, timezone as dt_timezone
import jwt
from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app
from app.models.user import User
from app.database import SessionLocal

client = TestClient(app)


def test_auth_registration_success():
    """Test successful user registration with auto-login token."""
    email = f"student_new_{int(time.time())}@university.edu"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["email"] == email
    assert "token" in data
    assert isinstance(data["user_id"], int)

    # Verify password was hashed in DB (never plaintext)
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    assert user.password_hash != "Password123!"
    assert user.password_hash.startswith("$2b$")
    db.close()


def test_auth_registration_duplicate_email():
    """Duplicate email registration must return 409 Conflict with email_exists code."""
    email = f"student_dup_{int(time.time())}@university.edu"
    payload = {
        "email": email,
        "password": "Password123!",
        "timezone": "America/New_York",
        "weekly_work_hour_limit": 15.0,
    }
    # First registration
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 200

    # Second registration with same email
    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409, resp2.text
    err = resp2.json()["error"]
    assert err["code"] == "email_exists"
    assert "already registered" in err["message"].lower()


def test_auth_registration_password_rules():
    """Password must be at least 8 characters long, contain 1 uppercase, and 1 number."""
    base_payload = {
        "email": f"student_pw_{int(time.time())}@university.edu",
        "timezone": "Europe/London",
        "weekly_work_hour_limit": 20.0,
    }

    # Too short (<8 chars)
    resp = client.post("/api/v1/auth/register", json={**base_payload, "password": "Pass1"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_password"

    # No uppercase
    resp = client.post("/api/v1/auth/register", json={**base_payload, "password": "password123"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_password"

    # No number
    resp = client.post("/api/v1/auth/register", json={**base_payload, "password": "PasswordOnly"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_password"


def test_auth_registration_invalid_timezone():
    """Timezone must be a valid IANA string."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"student_tz_{int(time.time())}@university.edu",
            "password": "Password123!",
            "timezone": "Invalid/Timezone_Not_Real",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "validation_error"


def test_auth_registration_invalid_weekly_limit():
    """weekly_work_hour_limit must be > 0."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"student_limit_{int(time.time())}@university.edu",
            "password": "Password123!",
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 0,
        },
    )
    assert resp.status_code in (400, 422)
    assert resp.json()["error"]["code"] == "validation_error"


def test_auth_login_success_and_failures():
    """Test login with correct and incorrect credentials."""
    email = f"student_login_{int(time.time())}@university.edu"
    password = "CorrectPassword123"

    # Register user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "timezone": "Europe/Berlin",
            "weekly_work_hour_limit": 18.0,
        },
    )
    assert reg_resp.status_code == 200

    # Successful login
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    login_data = login_resp.json()["data"]
    assert login_data["email"] == email
    assert login_data["timezone"] == "Europe/Berlin"
    token = login_data["token"]

    # Verify JWT payload claims
    decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert decoded["email"] == email
    assert "exp" in decoded
    assert "iat" in decoded
    exp_dt = datetime.fromtimestamp(decoded["exp"], tz=dt_timezone.utc)
    now_dt = datetime.now(dt_timezone.utc)
    assert (exp_dt - now_dt).days >= 6  # ~7 days

    # Failed login: wrong password
    bad_pw_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword999"})
    assert bad_pw_resp.status_code == 401
    assert "Invalid email or password" in bad_pw_resp.json()["error"]["message"]

    # Failed login: nonexistent email
    bad_email_resp = client.post("/api/v1/auth/login", json={"email": "nobody@nowhere.com", "password": password})
    assert bad_email_resp.status_code == 401
    assert "Invalid email or password" in bad_email_resp.json()["error"]["message"]


def test_auth_me_endpoint():
    """GET /auth/me returns authenticated user details."""
    email = f"student_me_{int(time.time())}@university.edu"
    password = "Password123"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "timezone": "Asia/Tokyo",
            "weekly_work_hour_limit": 25.0,
        },
    )
    token = reg_resp.json()["data"]["token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    me = resp.json()["data"]
    assert me["email"] == email
    assert me["timezone"] == "Asia/Tokyo"
    assert me["weekly_work_hour_limit"] == 25.0


def test_jwt_expired_token():
    """Expired JWT token must be rejected with 401."""
    expired_payload = {
        "user_id": 9999,
        "sub": "9999",
        "email": "expired@example.com",
        "exp": datetime.now(dt_timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(dt_timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm="HS256")

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_user_data_isolation():
    """
    Ensure complete data isolation between two students:
    - Student A creates blocks and courses
    - Student B cannot see, update, or delete Student A's blocks
    - Student B's GET /blocks and GET /week returns only Student B's data
    """
    # 1. Register Student A
    email_a = f"student_a_{int(time.time())}@university.edu"
    resp_a = client.post(
        "/api/v1/auth/register",
        json={"email": email_a, "password": "Password123!", "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    token_a = resp_a.json()["data"]["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Student B
    email_b = f"student_b_{int(time.time())}@university.edu"
    resp_b = client.post(
        "/api/v1/auth/register",
        json={"email": email_b, "password": "Password123!", "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    token_b = resp_b.json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Student A creates a shift
    create_resp = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "type": "shift",
            "title": "Student A Secret Shift",
            "day_of_week": 1,
            "start_time": "12:00:00",
            "end_time": "16:00:00",
            "hourly_wage": 22.50,
            "user_id": 999999,  # Privilege escalation attempt: should be ignored!
        },
    )
    assert create_resp.status_code in (200, 201)
    block_a = create_resp.json()["data"]
    block_a_id = block_a["id"]
    assert block_a["title"] == "Student A Secret Shift"

    # Student B queries GET /blocks -> MUST NOT see Student A's block
    b_blocks_resp = client.get("/api/v1/blocks", headers=headers_b)
    assert b_blocks_resp.status_code == 200
    b_blocks = b_blocks_resp.json()["data"]
    assert not any(b["id"] == block_a_id for b in b_blocks), "Student B saw Student A's block!"

    # Student B queries GET /week -> MUST NOT see Student A's block
    b_week_resp = client.get("/api/v1/week?start=2026-09-07", headers=headers_b)
    assert b_week_resp.status_code == 200
    assert not any(b["id"] == block_a_id for b in b_week_resp.json()["data"]["blocks"])

    # Student B attempts to update Student A's block -> MUST receive 404
    b_patch_resp = client.patch(
        f"/api/v1/blocks/{block_a_id}",
        headers=headers_b,
        json={"title": "Hacked Title"},
    )
    assert b_patch_resp.status_code == 404

    # Student B attempts to delete Student A's block -> MUST receive 404
    b_del_resp = client.delete(f"/api/v1/blocks/{block_a_id}", headers=headers_b)
    assert b_del_resp.status_code == 404

    # Student A can still query their own block
    a_blocks_resp = client.get("/api/v1/blocks", headers=headers_a)
    assert any(b["id"] == block_a_id for b in a_blocks_resp.json()["data"])
