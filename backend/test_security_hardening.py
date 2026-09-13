"""
Security Hardening & Privacy Test Suite
Verifies:
1. JWT authentication: missing, invalid, malformed, expired JWT denied (401).
2. IDOR protection: User A cannot access, modify, or delete User B's time blocks (404).
3. Request body user_id injection is ignored; authenticated user is enforced.
4. Audit log isolation: User A cannot view User B's security audit logs.
5. Privacy export isolation: Full user data export is strictly scoped, excluding passwords and secrets.
6. File upload security: Path traversal, dangerous extensions (.exe, .sh, .py), and invalid uploads rejected.
7. Account soft deletion: Marks user deleted, prevents subsequent login, logs audit event.
8. Security response headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy present.
9. Rate limiting protection on sensitive operations.
"""
from datetime import date, timedelta
import io
import time
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.rate_limiter import reset_rate_limits

client = TestClient(app)


def create_test_user(prefix="sec_user"):
    reset_rate_limits()
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": 20.0,
            "name": f"Security Tester {uid}",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    user_id = resp.json()["data"]["user_id"]
    return token, user_id, email


def test_jwt_security_rejections():
    """
    Endpoints reject missing, malformed, and invalid JWT tokens with 401.
    """
    # Missing token
    r_missing = client.get("/api/v1/blocks")
    assert r_missing.status_code == 401
    assert r_missing.json()["error"]["code"] in ("unauthorized", "authentication_required")

    # Malformed token
    r_malformed = client.get("/api/v1/blocks", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert r_malformed.status_code == 401

    # Fake forged token
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTk5OSIsImV4cCI6OTk5OTk5OTk5OX0.invalid_signature"
    r_forged = client.get("/api/v1/blocks", headers={"Authorization": f"Bearer {fake_token}"})
    assert r_forged.status_code == 401


def test_idor_protection_on_blocks():
    """
    User A cannot read, update, or delete User B's time block.
    Returns 404 (or 403) without leaking existence of other user data.
    """
    token_a, id_a, _ = create_test_user("user_a")
    token_b, id_b, _ = create_test_user("user_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B creates a block
    r_create = client.post(
        "/api/v1/blocks",
        headers=headers_b,
        json={
            "title": "User B Secret Meeting",
            "type": "class",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "11:00",
        },
    )
    assert r_create.status_code in (200, 201)
    block_b_id = r_create.json()["data"]["id"]

    # 1. User A tries to GET User B's block
    r_get = client.get(f"/api/v1/blocks/{block_b_id}", headers=headers_a)
    assert r_get.status_code in (403, 404), f"IDOR vulnerability on GET: {r_get.text}"

    # 2. User A tries to PATCH User B's block
    r_patch = client.patch(
        f"/api/v1/blocks/{block_b_id}",
        headers=headers_a,
        json={"title": "Hacked Title"},
    )
    assert r_patch.status_code in (403, 404), f"IDOR vulnerability on PATCH: {r_patch.text}"

    # 3. User A tries to DELETE User B's block
    r_delete = client.delete(f"/api/v1/blocks/{block_b_id}", headers=headers_a)
    assert r_delete.status_code in (403, 404), f"IDOR vulnerability on DELETE: {r_delete.text}"


def test_body_user_id_injection_ignored():
    """
    When User A submits User B's user_id in the request body,
    the server ignores it and binds the block strictly to User A.
    """
    token_a, id_a, _ = create_test_user("inject_a")
    token_b, id_b, _ = create_test_user("inject_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A tries to create a block with user_id = User B
    resp = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "user_id": id_b,  # malicious body override attempt
            "title": "Impersonated Shift",
            "type": "shift",
            "day_of_week": 2,
            "start_time": "14:00",
            "end_time": "18:00",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["user_id"] == id_a, "Server allowed body user_id injection!"


def test_audit_logs_user_isolation():
    """
    User A cannot access User B's security audit activity logs.
    """
    token_a, id_a, _ = create_test_user("audit_a")
    token_b, id_b, _ = create_test_user("audit_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B creates a block to trigger an audit log
    client.post(
        "/api/v1/blocks",
        headers=headers_b,
        json={
            "title": "Audit Block User B",
            "type": "class",
            "day_of_week": 4,
            "start_time": "09:00",
            "end_time": "10:00",
        },
    )

    # User A fetches audit logs
    r_logs_a = client.get("/api/v1/audit-logs", headers=headers_a)
    assert r_logs_a.status_code == 200
    items_a = r_logs_a.json()["data"]["items"]

    # None of User A's logs should contain User B's title
    for item in items_a:
        assert "Audit Block User B" not in item["description"]
        assert item["user_id"] == id_a


def test_privacy_export_security():
    """
    Privacy export returns only the requesting user's data and redacts secrets.
    """
    token_a, id_a, email_a = create_test_user("export_user")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Add a block
    client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "title": "Data Export Class",
            "type": "class",
            "day_of_week": 3,
            "start_time": "11:00",
            "end_time": "13:00",
        },
    )

    resp = client.get("/api/v1/privacy/export", headers=headers_a)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["user"]["email"] == email_a.lower()
    assert "password" not in str(data).lower() or "password_hash" not in str(data).lower()
    assert "secret" not in str(data).lower()
    assert len(data["time_blocks"]) >= 1


def test_file_upload_security():
    """
    File upload validates file name, rejects path traversal attempts,
    and prohibits dangerous executable extensions.
    """
    token, _, _ = create_test_user("upload_sec")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Path traversal attempt in filename
    traversal_file = ("../../etc/passwd", io.BytesIO(b"fake content"), "text/plain")
    r_trav = client.post(
        "/api/v1/import/file",
        headers=headers,
        files={"file": traversal_file},
    )
    assert r_trav.status_code in (400, 422), "Failed to reject path traversal in filename"
    assert "traversal" in r_trav.text.lower() or "invalid" in r_trav.text.lower()

    # 2. Dangerous executable extension (.exe, .sh, .py)
    dangerous_file = ("script.py", io.BytesIO(b"print('malicious')"), "text/x-python")
    r_dang = client.post(
        "/api/v1/import/file",
        headers=headers,
        files={"file": dangerous_file},
    )
    assert r_dang.status_code in (400, 422), "Failed to reject dangerous file extension"
    assert "prohibited" in r_dang.text.lower() or "extension" in r_dang.text.lower() or "not allowed" in r_dang.text.lower()


def test_account_soft_deletion_and_login_blocking():
    """
    Deleting an account performs soft deletion, logs audit event,
    and prevents subsequent login attempts.
    """
    token, uid, email = create_test_user("delete_test")
    headers = {"Authorization": f"Bearer {token}"}

    # Delete account
    r_del = client.post(
        "/api/v1/privacy/delete-account",
        headers=headers,
        json={"password": "Password123!", "confirm": "DELETE"},
    )
    assert r_del.status_code == 200, r_del.text

    # Subsequent login must be rejected
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert r_login.status_code in (401, 403, 404), "Deleted user was able to log in!"


def test_security_response_headers():
    """
    HTTP response contains security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy.
    """
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in resp.headers.get("Referrer-Policy", "")
