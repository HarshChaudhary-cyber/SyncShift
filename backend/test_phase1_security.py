"""
Security tests for Phase 1 hardening:
- forgot_password no longer leaks reset_token in response
- reset_password requires valid JTI (single-use enforcement)
- Recovery tokens cannot be used as Bearer access tokens
"""
import pytest
import jwt
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.user import User
from app.dependencies import create_access_token
from app.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_recovery_delivery(monkeypatch):
    """Deliver through a fake trusted channel; never read a token from logs."""
    from app.routers import auth
    delivered = []
    monkeypatch.setattr(auth, "delivery_available", lambda: True)
    monkeypatch.setattr(auth, "send_reset_link", lambda address, token: delivered.append((address, token)))
    return delivered

REGISTER_PAYLOAD = {
    "email": "security_phase1_test@example.com",
    "password": "SecurePass123",
    "timezone": "Asia/Kolkata",
    "weekly_work_hour_limit": 20,
}


@pytest.fixture(scope="module")
def test_user():
    """Create a test user and clean up after tests."""
    resp = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    # Accept both 200 (new) and 409 (existing) — clean up either way
    if resp.status_code == 200:
        user_id = resp.json()["data"]["user_id"]
    else:
        # Login to get user_id
        lr = client.post("/api/v1/auth/login", json={"identifier": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]})
        user_id = lr.json()["data"]["user_id"]
    yield user_id


class TestForgotPasswordNoTokenLeak:
    """forgot_password must never return reset_token in the response body."""

    def test_forgot_password_does_not_return_reset_token_for_existing_user(self, test_user):
        resp = client.post("/api/v1/auth/forgot-password", json={"email": REGISTER_PAYLOAD["email"]})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # The token must NOT be in the response
        assert "reset_token" not in data, "reset_token must not be exposed in API response"
        assert data.get("message"), "A generic message should still be returned"

    def test_forgot_password_does_not_return_reset_token_for_unknown_user(self):
        """Account enumeration: same response for unknown email."""
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "no-such-user@example.com"})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "reset_token" not in data

    def test_forgot_password_stores_jti_in_db(self, test_user):
        """JTI should be persisted to the users table after a valid request."""
        client.post("/api/v1/auth/forgot-password", json={"email": REGISTER_PAYLOAD["email"]})
        # Check DB directly
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.email == REGISTER_PAYLOAD["email"]).first()
            assert user is not None
            assert user.password_reset_jti is not None, "JTI should be stored after forgot-password"
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    def test_unconfigured_delivery_creates_no_token(self, test_user, monkeypatch):
        from app.routers import auth
        monkeypatch.setattr(auth, "delivery_available", lambda: False)
        db = next(get_db())
        user = db.query(User).filter_by(email=REGISTER_PAYLOAD["email"]).first()
        user.password_reset_jti = None
        db.commit()
        db.close()
        response = client.post("/api/v1/auth/forgot-password", json={"email": REGISTER_PAYLOAD["email"]})
        assert response.status_code == 200
        db = next(get_db())
        assert db.query(User).filter_by(email=REGISTER_PAYLOAD["email"]).first().password_reset_jti is None
        db.close()


class TestSingleUseResetToken:
    """reset_password must enforce single-use via JTI."""

    def _get_valid_reset_token(self, email: str) -> str:
        """Helper: trigger forgot-password and extract token from DB."""
        client.post("/api/v1/auth/forgot-password", json={"email": email})
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.email == email).first()
            assert user and user.password_reset_jti
            jti = user.password_reset_jti
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            "user_id": user.id,
            "email": email,
            "purpose": "password_reset",
            "jti": jti,
            "exp": now + datetime.timedelta(minutes=30),
            "iat": now,
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    def test_valid_token_resets_password(self, test_user):
        token = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        resp = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPass456"})
        assert resp.status_code == 200, resp.text
        # Reset back for cleanup
        token2 = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        assert client.post("/api/v1/auth/reset-password", json={"token": token2, "new_password": REGISTER_PAYLOAD["password"]}).status_code == 200

    def test_replayed_token_is_rejected(self, test_user):
        token = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        # First use — should succeed
        r1 = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "ReplayPass789"})
        assert r1.status_code == 200, r1.text
        # Second use of same token — must be rejected
        r2 = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "ReplayPass789"})
        assert r2.status_code == 400, f"Replay should be rejected, got {r2.status_code}: {r2.text}"
        assert r2.json()["error"]["code"] == "invalid_token"
        # Restore password
        token3 = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        assert client.post("/api/v1/auth/reset-password", json={"token": token3, "new_password": REGISTER_PAYLOAD["password"]}).status_code == 200

    def test_old_access_session_revoked_after_reset(self, test_user):
        login = client.post("/api/v1/auth/login", json={"identifier": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]})
        assert login.status_code == 200
        old_token = login.json()["data"]["token"]
        reset_token = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        assert client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "RevokedPass123"}).status_code == 200
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"identifier": REGISTER_PAYLOAD["email"], "password": "RevokedPass123"}).status_code == 200
        restore = self._get_valid_reset_token(REGISTER_PAYLOAD["email"])
        assert client.post("/api/v1/auth/reset-password", json={"token": restore, "new_password": REGISTER_PAYLOAD["password"]}).status_code == 200

    def test_reset_without_jti_in_token_is_rejected(self, test_user):
        """Tokens generated before the JTI migration (no jti claim) should be rejected."""
        import datetime
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.email == REGISTER_PAYLOAD["email"]).first()
            user_id = user.id
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        now = datetime.datetime.now(datetime.timezone.utc)
        old_style_token = jwt.encode({
            "user_id": user_id,
            "email": REGISTER_PAYLOAD["email"],
            "purpose": "password_reset",
            # No "jti" claim
            "exp": now + datetime.timedelta(minutes=30),
            "iat": now,
        }, settings.JWT_SECRET, algorithm="HS256")

        resp = client.post("/api/v1/auth/reset-password", json={"token": old_style_token, "new_password": "NoJtiPass789"})
        assert resp.status_code == 400, f"Token without JTI should be rejected, got {resp.status_code}"


class TestRecoveryTokenCannotBeAccessToken:
    """A password_reset token must not be accepted as a Bearer access token."""

    def _get_recovery_token(self, email: str) -> str:
        import datetime
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = db.query(User).filter(User.email == email).first()
            assert user
            user_id = user.id
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

        import secrets
        jti = secrets.token_urlsafe(32)
        now = datetime.datetime.now(datetime.timezone.utc)
        return jwt.encode({
            "user_id": user_id,
            "email": email,
            "purpose": "password_reset",
            "jti": jti,
            "exp": now + datetime.timedelta(minutes=30),
            "iat": now,
        }, settings.JWT_SECRET, algorithm="HS256")

    def test_recovery_token_rejected_as_bearer(self, test_user):
        recovery_token = self._get_recovery_token(REGISTER_PAYLOAD["email"])
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {recovery_token}"})
        assert resp.status_code == 401, (
            f"Recovery token should not be accepted as access token, got {resp.status_code}: {resp.text}"
        )
        detail = resp.json().get("error", {})
        assert detail.get("code") == "unauthorized"

    def test_valid_access_token_still_works(self, test_user):
        login = client.post("/api/v1/auth/login", json={
            "identifier": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        })
        assert login.status_code == 200
        access_token = login.json()["data"]["token"]
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert resp.status_code == 200, f"Valid access token should work: {resp.text}"
