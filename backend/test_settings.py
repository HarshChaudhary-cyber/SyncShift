import time
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.time_block import TimeBlock, BlockType, BlockStatus

client = TestClient(app)


def test_settings_patch_profile():
    """Verify PATCH /auth/me updates profile fields including currency, language, theme, and 0-168 limits."""
    email = f"settings_user_{int(time.time()*1000)}@test.com"
    pwd = "Password123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    assert reg_resp.status_code == 200, reg_resp.text
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify GET /auth/me initial defaults
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()["data"]
    assert me_data["has_password"] is True
    assert me_data["currency"] in ("INR", "₹")

    # Update with new values
    update_payload = {
        "display_name": "Harsh Patel",
        "timezone": "Asia/Kolkata",
        "weekly_work_hour_limit": 30.0,
        "currency": "USD",
        "language": "en",
        "theme": "dark",
    }
    patch_resp = client.patch("/api/v1/auth/me", json=update_payload, headers=headers)
    assert patch_resp.status_code == 200, patch_resp.text
    updated = patch_resp.json()["data"]
    assert updated["display_name"] == "Harsh Patel"
    assert updated["timezone"] == "Asia/Kolkata"
    assert updated["weekly_work_hour_limit"] == 30.0
    assert updated["currency"] == "USD"
    assert updated["language"] == "en"
    assert updated["theme"] == "dark"

    # Verify invalid timezone rejection
    invalid_tz_resp = client.patch("/api/v1/auth/me", json={"timezone": "Invalid/Timezone"}, headers=headers)
    assert invalid_tz_resp.status_code == 400

    # Verify weekly limit > 168 rejection
    invalid_limit_resp = client.patch("/api/v1/auth/me", json={"weekly_work_hour_limit": 170.0}, headers=headers)
    assert invalid_limit_resp.status_code == 422 or invalid_limit_resp.status_code == 400


def test_settings_change_password():
    """Verify POST /auth/change-password behaves correctly for email/password users."""
    email = f"pwd_user_{int(time.time()*1000)}@test.com"
    old_pwd = "OldPassword123!"
    new_pwd = "NewPassword456!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": old_pwd, "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password -> 401
    bad_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPassword999!", "new_password": new_pwd},
        headers=headers,
    )
    assert bad_resp.status_code == 401

    # Invalid new password (missing number) -> 400
    invalid_pwd_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": old_pwd, "new_password": "NoNumbersHere!"},
        headers=headers,
    )
    assert invalid_pwd_resp.status_code == 400

    # Valid change
    ok_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": old_pwd, "new_password": new_pwd},
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert "Password changed" in ok_resp.json()["data"]["message"]

    # Old password no longer works
    login_old = client.post("/api/v1/auth/login", json={"email": email, "password": old_pwd})
    assert login_old.status_code == 401

    # New password works
    login_new = client.post("/api/v1/auth/login", json={"email": email, "password": new_pwd})
    assert login_new.status_code == 200


def test_settings_delete_account_and_soft_delete():
    """Verify POST /auth/delete-account soft-deletes user, marks time_blocks deleted, and blocks future logins."""
    email = f"del_user_{int(time.time()*1000)}@test.com"
    pwd = "DeletePassword123!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["data"]["token"]
    user_id = reg_resp.json()["data"]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a time block for this user
    blk_resp = client.post(
        "/api/v1/blocks",
        json={
            "type": "class",
            "title": "ToDeleteClass",
            "day_of_week": 1,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )
    assert blk_resp.status_code == 201

    # Call delete account with wrong password -> 401
    bad_del = client.post("/api/v1/auth/delete-account", json={"password": "WrongPassword!"}, headers=headers)
    assert bad_del.status_code == 401

    # Call delete account with valid password
    del_resp = client.post("/api/v1/auth/delete-account", json={"password": pwd}, headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["message"] == "Account deleted"

    # Subsequent request with old token should fail (401)
    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401

    # Subsequent login attempt fails (401)
    login_after = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_after.status_code == 401

    # Verify in DB: user has deleted_at set and time block has deleted = True
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    assert user.deleted_at is not None

    blocks = db.query(TimeBlock).filter(TimeBlock.user_id == user_id).all()
    assert all(b.deleted is True for b in blocks)
    db.close()


def test_settings_export_data():
    """Verify GET /auth/export returns structured schedule and profile data."""
    email = f"export_user_{int(time.time()*1000)}@test.com"
    pwd = "ExportPassword123!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    export_resp = client.get("/api/v1/auth/export", headers=headers)
    assert export_resp.status_code == 200
    data = export_resp.json()["data"]
    assert "user" in data
    assert "courses" in data
    assert "time_blocks" in data
    assert "study_tasks" in data
    assert "exported_at" in data
    assert data["user"]["email"] == email


def test_settings_currency_and_dashboard_integration():
    """Verify currency and timezone updates in /auth/me propagate to /dashboard."""
    email = f"currency_dash_{int(time.time()*1000)}@test.com"
    pwd = "Password123!"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "timezone": "Europe/London", "weekly_work_hour_limit": 20.0},
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initial dashboard currency should be ₹ (or INR)
    dash_resp1 = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp1.status_code == 200
    assert dash_resp1.json()["data"]["user"]["currency"] in ("₹", "INR")

    # 2. Update currency to USD
    client.patch("/api/v1/auth/me", json={"currency": "USD", "weekly_work_hour_limit": 25.0}, headers=headers)
    dash_resp2 = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp2.status_code == 200
    assert dash_resp2.json()["data"]["user"]["currency"] == "$"
    assert dash_resp2.json()["data"]["user"]["weekly_work_hour_limit"] == 25.0

    # 3. Update currency to GBP
    client.patch("/api/v1/auth/me", json={"currency": "GBP"}, headers=headers)
    dash_resp3 = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp3.status_code == 200
    assert dash_resp3.json()["data"]["user"]["currency"] == "£"

    # 4. Update currency to EUR
    client.patch("/api/v1/auth/me", json={"currency": "EUR"}, headers=headers)
    dash_resp4 = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp4.status_code == 200
    assert dash_resp4.json()["data"]["user"]["currency"] == "€"

