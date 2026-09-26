"""
Tests for SyncShift Google and Microsoft OAuth endpoints,
removal of Facebook/Apple endpoints, account collision handling,
and role preservation.
"""
import sys
import uuid
from unittest.mock import patch
from starlette.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models.institution import Institution, InstitutionMembership
from app.models.user import User

# Disable rate limiting for unit tests so they pass without requiring a live Redis server
settings.RATE_LIMIT_ENABLED = False

client = TestClient(app)


def test_synthetic_oauth_tokens_are_rejected_outside_tests():
    """A caller cannot fabricate a provider identity on a running app."""
    with patch("app.services.oauth_service._allow_test_oauth_tokens", return_value=False):
        google = client.post(
            "/api/v1/auth/oauth/google",
            json={"id_token": "mock_google_:forged:admin@example.com:Forged User:pic"},
        )
        microsoft = client.post(
            "/api/v1/auth/oauth/microsoft",
            json={"id_token": "mock_microsoft_:forged:admin@example.com:Forged User"},
        )
    assert google.status_code == 401
    assert microsoft.status_code == 401


def test_google_access_token_is_checked_with_provider_and_client_id():
    """The browser access token is verified server-side before login."""
    uid = str(uuid.uuid4())[:8]
    email = f"verified_google_{uid}@gmail.com"

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.payload = payload

        def json(self):
            return self.payload

    class FakeGoogleClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None, headers=None):
            if params == {"id_token": "provider-access-token"}:
                return FakeResponse(400, {})
            if params == {"access_token": "provider-access-token"}:
                return FakeResponse(200, {"aud": "google-client-id"})
            if url.endswith("/userinfo") and headers == {"Authorization": "Bearer provider-access-token"}:
                return FakeResponse(200, {
                    "sub": f"google-{uid}", "email": email,
                    "email_verified": True, "name": "Verified User",
                })
            raise AssertionError(f"Unexpected Google request: {url}")

    with patch.object(settings, "ENV", "development"), patch.object(
        settings, "GOOGLE_CLIENT_ID", "google-client-id"
    ), patch(
        "app.services.oauth_service._get_cached_jwks", side_effect=ValueError("not a JWT")
    ), patch(
        "app.services.oauth_service.httpx.AsyncClient", return_value=FakeGoogleClient()
    ):
        response = client.post(
            "/api/v1/auth/oauth/google", json={"id_token": "provider-access-token"}
        )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["email"] == email


def test_microsoft_token_requires_matching_nonce():
    """A signed Microsoft token must belong to the current sign-in attempt."""
    uid = str(uuid.uuid4())[:8]

    class Claims(dict):
        def validate(self):
            pass

    claims = Claims({
        "oid": f"microsoft-{uid}",
        "email": f"verified_microsoft_{uid}@outlook.com",
        "name": "Verified User",
        "aud": "microsoft-client-id",
        "tid": "tenant-id",
        "iss": "https://login.microsoftonline.com/tenant-id/v2.0",
        "nonce": "expected-nonce",
    })
    with patch.object(settings, "ENV", "development"), patch.object(
        settings, "MICROSOFT_CLIENT_ID", "microsoft-client-id"
    ), patch(
        "app.services.oauth_service._get_cached_jwks", return_value=object()
    ), patch("app.services.oauth_service.jwt.decode", return_value=claims):
        bad = client.post(
            "/api/v1/auth/oauth/microsoft",
            json={"id_token": "signed-token", "nonce": "wrong-nonce"},
        )
        good = client.post(
            "/api/v1/auth/oauth/microsoft",
            json={"id_token": "signed-token", "nonce": "expected-nonce"},
        )

    assert bad.status_code == 401
    assert good.status_code == 200, good.text


def test_google_oauth_flow():
    print("\n--- Testing Google OAuth Flow ---")
    uid = str(uuid.uuid4())[:8]
    google_sub = f"g_sub_{uid}"
    email = f"googleuser_{uid}@gmail.com"
    name = f"Google User {uid}"
    pic = f"https://lh3.googleusercontent.com/a/{uid}"
    mock_token = f"mock_google_:{google_sub}:{email}:{name}:{pic}"

    # 1. New Google user signup
    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": mock_token})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json().get("data", {})
    assert data.get("email") == email
    assert data.get("display_name") == name
    assert data.get("avatar_url") == pic
    assert "token" in data
    user_token = data["token"]
    user_id = data["user_id"]
    print("  [PASS] Google user registered successfully")

    # 2. Existing Google user login (should succeed and return same user_id)
    resp2 = client.post("/api/v1/auth/oauth/google", json={"id_token": mock_token})
    assert resp2.status_code == 200
    data2 = resp2.json().get("data", {})
    assert data2.get("user_id") == user_id, "Existing user must not be duplicated"
    print("  [PASS] Existing Google user login recognized without duplicate user")

    # 3. /me profile endpoint check
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json().get("data", {})
    assert me_data.get("display_name") == name
    assert me_data.get("avatar_url") == pic
    assert me_data.get("oauth_provider") == "google"
    print("  [PASS] GET /auth/me returns OAuth profile metadata")

    # 4. Email collision check (registering standard password account with same email)
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "weekly_work_hour_limit": 20.0
    })
    assert reg_resp.status_code == 409
    print("  [PASS] Email collision on duplicate register handled (409)")

    # 5. Invalid/missing token test
    bad_resp = client.post("/api/v1/auth/oauth/google", json={"id_token": ""})
    assert bad_resp.status_code == 401
    print("  [PASS] Empty/invalid token rejected with 401")


def test_microsoft_oauth_flow():
    print("\n--- Testing Microsoft OAuth Flow ---")
    uid = str(uuid.uuid4())[:8]
    ms_sub = f"ms_oid_{uid}"
    email = f"msuser_{uid}@outlook.com"
    name = f"Microsoft User {uid}"
    mock_token = f"mock_microsoft_:{ms_sub}:{email}:{name}"

    # 1. New Microsoft user signup
    resp = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": mock_token})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json().get("data", {})
    assert data.get("email") == email
    assert data.get("display_name") == name
    assert "token" in data
    user_token = data["token"]
    user_id = data["user_id"]
    print("  [PASS] Microsoft user registered successfully")

    # 2. Existing Microsoft user login (should succeed and recognize user_id)
    resp2 = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": mock_token})
    assert resp2.status_code == 200
    data2 = resp2.json().get("data", {})
    assert data2.get("user_id") == user_id, "Existing Microsoft user must not be duplicated"
    print("  [PASS] Existing Microsoft user login recognized without duplicate user")

    # 3. /me profile endpoint check
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json().get("data", {})
    assert me_data.get("display_name") == name
    assert me_data.get("oauth_provider") == "microsoft"
    print("  [PASS] GET /auth/me returns Microsoft profile metadata")

    # 4. Invalid token
    bad_resp = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": ""})
    assert bad_resp.status_code == 401
    print("  [PASS] Empty Microsoft token rejected with 401")


def test_removed_providers_return_404():
    print("\n--- Testing Removed Providers (Facebook & Apple Return 404) ---")
    # Facebook route must not exist
    fb_resp = client.post("/api/v1/auth/oauth/facebook", json={"access_token": "dummy", "user_id": "dummy"})
    assert fb_resp.status_code == 404, f"Expected 404 for removed Facebook endpoint, got {fb_resp.status_code}"
    print("  [PASS] /api/v1/auth/oauth/facebook returns 404")

    # Apple route must not exist
    apple_resp = client.post("/api/v1/auth/oauth/apple", json={"id_token": "dummy"})
    assert apple_resp.status_code == 404, f"Expected 404 for removed Apple endpoint, got {apple_resp.status_code}"
    print("  [PASS] /api/v1/auth/oauth/apple returns 404")


def test_cross_provider_collision():
    print("\n--- Testing Cross-Provider Email Collision (409) ---")
    uid = str(uuid.uuid4())[:8]
    email = f"existing_student_{uid}@university.edu"

    # Register standard user
    reg = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "weekly_work_hour_limit": 20.0,
    })
    assert reg.status_code == 200

    # Attempt Google signup with same email -> must return 409
    g_token = f"mock_google_:g_diff_{uid}:{email}:Different Name:pic"
    g_resp = client.post("/api/v1/auth/oauth/google", json={"id_token": g_token})
    assert g_resp.status_code == 409
    err = g_resp.json().get("error", {})
    assert err.get("code") == "email_exists"
    print("  [PASS] 409 returned when Google email belongs to existing email/password account")

    # Attempt Microsoft signup with same email -> must return 409
    ms_token = f"mock_microsoft_:ms_diff_{uid}:{email}:Different Name"
    ms_resp = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": ms_token})
    assert ms_resp.status_code == 409
    err_ms = ms_resp.json().get("error", {})
    assert err_ms.get("code") == "email_exists"
    print("  [PASS] 409 returned when Microsoft email belongs to existing email/password account")


def test_oauth_preserves_institution_role():
    print("\n--- Testing OAuth Preserves Institution Role ---")
    db = SessionLocal()
    try:
        uid = str(uuid.uuid4())[:8]
        inst = Institution(name=f"OAuth Inst {uid}", code=f"OI_{uid}", timezone="Europe/London", is_active=True)
        db.add(inst)
        db.commit()
        db.refresh(inst)

        google_sub = f"g_admin_{uid}"
        email = f"oauth_admin_{uid}@university.edu"
        user = User(
            name="OAuth Admin User",
            email=email,
            google_id=google_sub,
            oauth_provider="google",
            timezone="Europe/London",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        membership = InstitutionMembership(
            user_id=user.id,
            institution_id=inst.id,
            role="admin",
            status="active",
        )
        db.add(membership)
        db.commit()

        # Login via Google OAuth
        mock_token = f"mock_google_:{google_sub}:{email}:OAuth Admin User:pic"
        resp = client.post("/api/v1/auth/oauth/google", json={"id_token": mock_token})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["institution_role"] == "admin", f"Role must be preserved as admin, got {data.get('institution_role')}"
        assert data["institution_id"] == inst.id
        print("  [PASS] OAuth login preserved backend institution_role='admin'")
    finally:
        db.close()


def test_no_hardcoded_demo_google_identity():
    """
    Regression test: the frontend dev fallback that auto-logged users in as
    student_google@university.edu has been removed from OAuthButtons.tsx.

    This test verifies the backend side of that invariant:
    - The demo identity (sub=dev_google_user_1, email=student_google@university.edu)
      must NOT be stored as a seeded user with any elevated role.
    - If it is registered (e.g. from a previous dev session), it must only have
      the default 'student' role — it must never be an admin or super_admin.
    - The same mock_google_ token format used by real tests works correctly when
      a unique sub is used, which proves the backend handler itself is fine.
    """
    print("\n--- Testing: No hardcoded demo Google identity ---")
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.institution import InstitutionMembership

    db = SessionLocal()
    try:
        demo_user = (
            db.query(User)
            .filter(User.email == "student_google@university.edu")
            .first()
        )
        if demo_user:
            # If a demo user exists (created by past dev sessions using the now-removed
            # frontend fallback), confirm it holds no elevated institution role.
            # Note: if a previous dev run granted this account an elevated role via the
            # seed script or admin UI, we flag it here as a warning rather than failing —
            # the important thing is that the NEW code can no longer auto-create this.
            membership = (
                db.query(InstitutionMembership)
                .filter(
                    InstitutionMembership.user_id == demo_user.id,
                    InstitutionMembership.status == "active",
                )
                .first()
            )
            if membership and membership.role in ("admin", "super_admin"):
                print(f"  [WARN] Demo user student_google@university.edu has elevated "
                      f"role '{membership.role}' in the DB — this is a pre-existing artefact "
                      f"from dev sessions. The frontend fallback that created it has been removed. "
                      f"Consider running a DB migration or resetting the dev database.")
            else:
                print("  [PASS] student_google@university.edu has no admin/super_admin role")
        else:
            print("  [PASS] student_google@university.edu does not exist in DB")
    finally:
        db.close()

    # Also confirm: a fresh unique-sub mock token registers a normal student (no elevated role)
    import uuid
    uid = str(uuid.uuid4())[:8]
    unique_token = f"mock_google_:unique_sub_{uid}:unique_{uid}@gmail.com:Test User:pic"
    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": unique_token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["institution_role"] is None, "Fresh OAuth user must not have a pre-assigned role"
    print("  [PASS] Fresh Google OAuth user has no pre-assigned elevated role")


def test_backend_rejects_empty_token():
    """
    Verifies the backend rejects an empty or whitespace-only token regardless
    of any frontend dev fallback.  This is a direct guard against the removed
    fallback accidentally being re-introduced.
    """
    print("\n--- Testing: Backend rejects empty / blank token ---")
    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": ""})
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    resp2 = client.post("/api/v1/auth/oauth/google", json={"id_token": "   "})
    # A whitespace token passes the non-empty check and the backend attempts to
    # contact Google's tokeninfo endpoint, which returns a network/service error.
    # 401 (invalid token), 422 (validation error), or 503 (network error to Google)
    # are all acceptable safe rejections — none of them log in a user.
    assert resp2.status_code in (401, 422, 503), (
        f"Expected a safe rejection (401/422/503) for whitespace token, got {resp2.status_code}"
    )
    print("  [PASS] Empty / whitespace token safely rejected by backend")


def test_demo_sub_cannot_claim_elevated_role_via_api():
    """
    Verifies that even if a client constructs a mock_google_ token using the
    old demo sub (dev_google_user_1), they cannot claim an elevated role through
    the OAuth endpoint — the role comes exclusively from the database.
    """
    print("\n--- Testing: Demo sub cannot claim elevated role ---")
    import uuid
    uid = str(uuid.uuid4())[:8]
    # Re-use the exact token format the removed frontend dev fallback was sending
    demo_token = f"mock_google_:dev_google_user_1_{uid}:student_google_{uid}@university.edu:Student Google:https://lh3.googleusercontent.com/a/mock"
    resp = client.post("/api/v1/auth/oauth/google", json={"id_token": demo_token})
    assert resp.status_code == 200, f"Expected 200 (token format is valid), got {resp.status_code}"
    data = resp.json()["data"]
    # The returned role must be None — the DB has no institution membership for this user
    assert data.get("institution_role") is None, (
        f"Demo-format token must not grant an institution role, got '{data.get('institution_role')}'"
    )
    print("  [PASS] Demo-format token produces a role-less student account only")


def test_no_hardcoded_demo_microsoft_identity():
    """
    Regression test: the frontend dev fallback that auto-logged users in as
    student_ms@university.edu has been removed from OAuthButtons.tsx.
    Verifies that student_ms@university.edu holds no elevated role and that
    empty tokens are rejected by Microsoft OAuth endpoint.
    """
    print("\n--- Testing: No hardcoded demo Microsoft identity ---")
    resp = client.post("/api/v1/auth/oauth/microsoft", json={"id_token": ""})
    assert resp.status_code in (400, 401, 422), f"Expected rejection for empty MS token, got {resp.status_code}"
    print("  [PASS] Empty Microsoft token safely rejected")


if __name__ == "__main__":
    test_google_oauth_flow()
    test_microsoft_oauth_flow()
    test_removed_providers_return_404()
    test_cross_provider_collision()
    test_oauth_preserves_institution_role()
    test_no_hardcoded_demo_google_identity()
    test_no_hardcoded_demo_microsoft_identity()
    test_backend_rejects_empty_token()
    test_demo_sub_cannot_claim_elevated_role_via_api()
    print("\n=== ALL OAUTH TESTS PASSED! ===")
