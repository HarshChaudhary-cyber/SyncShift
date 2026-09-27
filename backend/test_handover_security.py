"""Regression checks for issues discovered during the university handover review."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import create_access_token
from app.main import app
from app.services import captcha_service


@pytest.mark.parametrize("token", ["mock_captcha_pass_anything", "XXXX.forged", "1x00000000000000000000AA"])
def test_runtime_captcha_tokens_must_reach_provider(monkeypatch, token):
    monkeypatch.setattr(captcha_service, "_allow_test_captcha_tokens", lambda: False)
    monkeypatch.setattr(settings, "CAPTCHA_SECRET_KEY", "configured-test-secret")
    response = MagicMock(status_code=200)
    response.json.return_value = {"success": False}
    provider = AsyncMock()
    provider.post.return_value = response
    with patch.object(captcha_service.httpx, "AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = provider
        with pytest.raises(HTTPException) as error:
            asyncio.run(captcha_service.verify_captcha_token(token))
        assert error.value.detail["code"] == "captcha_failed"
        provider.post.assert_awaited_once()


def test_login_respects_captcha_enforcement_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENFORCE", True)
    monkeypatch.setattr(settings, "CAPTCHA_SECRET_KEY", None)
    response = TestClient(app).post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "Password123!",
    })
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "captcha_not_configured"


@pytest.mark.parametrize("origin", ["https://localhost.attacker.example", "https://127.0.0.1.attacker.example"])
def test_error_cors_rejects_lookalike_origins(origin):
    response = TestClient(app).get("/api/v1/auth/me", headers={"Origin": origin})
    assert response.status_code == 401
    assert "access-control-allow-origin" not in response.headers


def test_error_cors_allows_configured_origin(monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", ["http://localhost:3000"])
    response = TestClient(app).get("/api/v1/auth/me", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_token_uses_configured_lifetime(monkeypatch):
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    claims = jwt.decode(create_access_token(1, "user@example.com"), settings.JWT_SECRET, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 30 * 60


@pytest.mark.parametrize("password", ["A1" + "x" * 71, "A1" + "é" * 36])
def test_registration_rejects_passwords_over_bcrypt_byte_limit(password):
    response = TestClient(app).post("/api/v1/auth/register", json={
        "email": f"long-{uuid.uuid4().hex}@example.com", "password": password,
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_password"


def test_unconfigured_production_email_is_not_reported_as_delivered(monkeypatch, capsys):
    from app.services.reminders import send_email_alert
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    assert send_email_alert("private@example.com", "Private schedule", "Personal shift") is False
    assert "Personal shift" not in capsys.readouterr().out


def test_zero_schedule_preferences_survive_profile_and_assistant_reads():
    client = TestClient(app)
    response = client.post("/api/v1/auth/register", json={
        "email": f"zero-{uuid.uuid4().hex}@example.com", "password": "Password123!",
    })
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["data"]["token"]}
    changed = client.patch("/api/v1/auth/me", headers=headers, json={
        "weekly_work_hour_limit": 0, "minimum_transition_minutes": 0,
    })
    assert changed.status_code == 200
    for profile in [changed.json()["data"], client.get("/api/v1/auth/me", headers=headers).json()["data"]]:
        assert profile["weekly_work_hour_limit"] == 0
        assert profile["minimum_transition_minutes"] == 0
