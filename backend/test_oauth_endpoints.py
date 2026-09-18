"""
Tests for SyncShift Google and Microsoft OAuth endpoints,
removal of Facebook/Apple endpoints, account collision handling,
and role preservation.
"""
import sys
import uuid
from starlette.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.database import SessionLocal
from app.main import app
from app.models.institution import Institution, InstitutionMembership
from app.models.user import User

client = TestClient(app)


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


if __name__ == "__main__":
    test_google_oauth_flow()
    test_microsoft_oauth_flow()
    test_removed_providers_return_404()
    test_cross_provider_collision()
    test_oauth_preserves_institution_role()
    print("\n=== ALL OAUTH TESTS PASSED! ===")
