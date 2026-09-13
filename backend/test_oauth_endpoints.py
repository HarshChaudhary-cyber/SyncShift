"""
Tests for SyncShift Google, Facebook, and Apple OAuth endpoints.
Verifies signup, login, collision handling (409), invalid token (401),
and response contract shapes.
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

from app.main import app

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
    print("  [PASS] Google user registered successfully")

    # 2. Existing Google user login (should succeed and return token)
    resp2 = client.post("/api/v1/auth/oauth/google", json={"id_token": mock_token})
    assert resp2.status_code == 200
    data2 = resp2.json().get("data", {})
    assert data2.get("user_id") == data["user_id"]
    print("  [PASS] Existing Google user login recognized")

    # 3. /me profile endpoint check
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json().get("data", {})
    assert me_data.get("display_name") == name
    assert me_data.get("avatar_url") == pic
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


def test_facebook_oauth_flow():
    print("\n--- Testing Facebook OAuth Flow ---")
    uid = str(uuid.uuid4())[:8]
    fb_user_id = f"fb_id_{uid}"
    mock_token = f"mock_fb_{uid}"

    # 1. New Facebook user signup
    resp = client.post("/api/v1/auth/oauth/facebook", json={
        "access_token": mock_token,
        "user_id": fb_user_id,
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json().get("data", {})
    assert data.get("email") == f"fb_{fb_user_id}@facebook.com".lower()
    assert "token" in data
    print("  [PASS] Facebook user registered successfully")

    # 2. Existing Facebook user login
    resp2 = client.post("/api/v1/auth/oauth/facebook", json={
        "access_token": mock_token,
        "user_id": fb_user_id,
    })
    assert resp2.status_code == 200
    data2 = resp2.json().get("data", {})
    assert data2.get("user_id") == data["user_id"]
    print("  [PASS] Existing Facebook user login recognized")

    # 3. Invalid token
    bad_resp = client.post("/api/v1/auth/oauth/facebook", json={
        "access_token": "",
        "user_id": "",
    })
    assert bad_resp.status_code == 401
    print("  [PASS] Empty Facebook token rejected with 401")


def test_apple_oauth_flow():
    print("\n--- Testing Apple OAuth Flow ---")
    uid = str(uuid.uuid4())[:8]
    apple_sub = f"apple_sub_{uid}"
    email = f"apple_{uid}@privaterelay.appleid.com"
    name = f"Apple User {uid}"
    mock_token = f"mock_apple_:{apple_sub}:{email}:{name}"

    # 1. New Apple user signup
    resp = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": mock_token,
        "display_name": name,
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json().get("data", {})
    assert data.get("email") == email
    assert data.get("display_name") == name
    assert "token" in data
    print("  [PASS] Apple user registered successfully")

    # 2. Existing Apple user login
    resp2 = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": mock_token,
    })
    assert resp2.status_code == 200
    data2 = resp2.json().get("data", {})
    assert data2.get("user_id") == data["user_id"]
    print("  [PASS] Existing Apple user login recognized")

    # 3. Invalid token
    bad_resp = client.post("/api/v1/auth/oauth/apple", json={"id_token": ""})
    assert bad_resp.status_code == 401
    print("  [PASS] Empty Apple token rejected with 401")


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


if __name__ == "__main__":
    test_google_oauth_flow()
    test_facebook_oauth_flow()
    test_apple_oauth_flow()
    test_cross_provider_collision()
    print("\n=== ALL OAUTH TESTS PASSED! ===")
