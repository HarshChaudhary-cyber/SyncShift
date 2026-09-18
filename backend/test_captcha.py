"""
Tests for SyncShift CAPTCHA and Bot Protection service.
Verifies server-side Turnstile verification, mock tokens, rejection of invalid tokens,
and registration/login bot defense.
"""
import uuid
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.captcha_service import verify_captcha_token
from fastapi import HTTPException

client = TestClient(app)


@pytest.mark.anyio
async def test_captcha_mock_tokens():
    # Pass tokens
    assert await verify_captcha_token("mock_captcha_pass_123") is True
    assert await verify_captcha_token("test_captcha_pass_456") is True
    assert await verify_captcha_token("1x00000000000000000000AA") is True

    # Fail tokens
    with pytest.raises(HTTPException) as exc_info:
        await verify_captcha_token("mock_captcha_fail_token")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "captcha_failed"

    with pytest.raises(HTTPException) as exc_fail:
        await verify_captcha_token("2x00000000000000000000AB")
    assert exc_fail.value.status_code == 400


def test_registration_with_valid_captcha():
    uid = str(uuid.uuid4())[:8]
    resp = client.post("/api/v1/auth/register", json={
        "email": f"captcha_user_{uid}@test.edu",
        "password": "Password123!",
        "weekly_work_hour_limit": 20.0,
        "captcha_token": "mock_captcha_pass_abc",
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert "token" in data
    assert "SECRET" not in resp.text
    assert "CAPTCHA_SECRET_KEY" not in resp.text


def test_registration_with_invalid_captcha():
    uid = str(uuid.uuid4())[:8]
    resp = client.post("/api/v1/auth/register", json={
        "email": f"captcha_bad_{uid}@test.edu",
        "password": "Password123!",
        "weekly_work_hour_limit": 20.0,
        "captcha_token": "mock_captcha_fail_xyz",
    })
    assert resp.status_code == 400
    err = resp.json().get("error", {}) or resp.json().get("detail", {})
    assert err.get("code") == "captcha_failed"


def test_login_with_valid_captcha():
    uid = str(uuid.uuid4())[:8]
    email = f"captcha_login_{uid}@test.edu"
    pwd = "Password123!"

    # Register
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "weekly_work_hour_limit": 20.0,
    })

    # Login with valid token
    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
        "captcha_token": "mock_captcha_pass_login",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()["data"]


def test_login_with_invalid_captcha():
    uid = str(uuid.uuid4())[:8]
    email = f"captcha_bad_login_{uid}@test.edu"
    pwd = "Password123!"

    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "weekly_work_hour_limit": 20.0,
    })

    resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
        "captcha_token": "mock_captcha_fail_bad",
    })
    assert resp.status_code == 400
    err = resp.json().get("error", {}) or resp.json().get("detail", {})
    assert err.get("code") == "captcha_failed"


def test_oauth_with_invalid_captcha():
    g_token = "mock_google_:test_g:test@gmail.com:Test:pic"
    resp = client.post("/api/v1/auth/oauth/google", json={
        "id_token": g_token,
        "captcha_token": "mock_captcha_fail_oauth",
    })
    assert resp.status_code == 400
    err = resp.json().get("error", {}) or resp.json().get("detail", {})
    assert err.get("code") == "captcha_failed"
