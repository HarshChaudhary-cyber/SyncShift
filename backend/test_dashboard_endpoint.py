"""
Unit and integration tests for GET /api/v1/dashboard endpoint.
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


def test_dashboard_unauthorized():
    print("\n--- 1. Testing Unauthorized Dashboard Access ---")
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("  [PASS] Missing token returns 401 Unauthorized")


def test_dashboard_empty_user():
    print("\n--- 2. Testing Dashboard for Newly Registered User ---")
    uid = str(uuid.uuid4())[:8]
    email = f"dash_{uid}@example.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": 20.0,
            "name": "Dashboard Tester",
        },
    )
    assert reg_resp.status_code == 200, f"Register failed: {reg_resp.text}"
    token = reg_resp.json()["data"]["token"]

    resp = client.get("/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Dashboard failed: {resp.text}"
    body = resp.json()
    assert "data" in body
    data = body["data"]

    # Verify user section
    assert data["user"]["email"] == email
    assert data["user"]["weekly_work_hour_limit"] == 20.0
    assert "display_name" in data["user"]
    assert "timezone" in data["user"]

    # Verify today section
    assert "date" in data["today"]
    assert "day_name" in data["today"]
    assert isinstance(data["today"]["blocks"], list)
    assert data["today"]["shift_hours"] == 0.0
    assert data["today"]["class_hours"] == 0.0
    assert data["today"]["expected_earnings"] == 0.0

    # Verify next_up is None for empty schedule
    assert data["next_up"] is None

    # Verify week section
    assert "start" in data["week"]
    assert "end" in data["week"]
    assert data["week"]["total_shift_hours"] == 0.0
    assert data["week"]["conflict_count"] == 0
    assert data["week"]["over_work_limit"] is False

    # Verify alerts empty
    assert isinstance(data["alerts"], list)
    assert len(data["alerts"]) == 0
    print("  [PASS] Empty user dashboard structure verified successfully")


def test_dashboard_with_schedule_and_alerts():
    print("\n--- 3. Testing Dashboard With Blocks, Conflict, and Alerts ---")
    uid = str(uuid.uuid4())[:8]
    email = f"dash_alerts_{uid}@example.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": 20.0,
            "name": "Dashboard Alerts Tester",
        },
    )
    assert reg_resp.status_code == 200, f"Register failed: {reg_resp.text}"
    token = reg_resp.json()["data"]["token"]

    from datetime import date
    today_d = date.today()
    # day_of_week in SyncShift: 0=Sun, 1=Mon, ..., 6=Sat
    today_dow = (today_d.weekday() + 1) % 7

    headers = {"Authorization": f"Bearer {token}"}

    # Add Class 1: 09:00 - 11:00
    b1_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "CS101 Algorithms",
            "type": "class",
            "day_of_week": today_dow,
            "start_time": "09:00",
            "end_time": "11:00",
            "location": "Room 101",
        },
    )
    assert b1_resp.status_code in (200, 201), f"Failed to create block 1: {b1_resp.text}"

    # Add Shift 1: 10:00 - 14:00 (Creates a 10:00-11:00 hard conflict with Class 1)
    b2_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Campus Library Shift",
            "type": "shift",
            "day_of_week": today_dow,
            "start_time": "10:00",
            "end_time": "14:00",
            "location": "Main Library",
            "hourly_wage": 250.0,
        },
    )
    assert b2_resp.status_code in (200, 201), f"Failed to create block 2: {b2_resp.text}"

    # Query dashboard
    dash_resp = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp.status_code == 200, f"Failed dashboard: {dash_resp.text}"
    data = dash_resp.json()["data"]

    # Check today blocks: should have 2 blocks, sorted chronologically (09:00, then 10:00)
    blocks = data["today"]["blocks"]
    assert len(blocks) == 2, f"Expected 2 blocks, got {len(blocks)}"
    assert blocks[0]["start_time"] == "09:00"
    assert blocks[1]["start_time"] == "10:00"
    assert blocks[0]["type"] == "class"
    assert blocks[1]["type"] == "shift"

    # Today stats
    assert data["today"]["class_hours"] == 2.0
    assert data["today"]["shift_hours"] == 4.0
    assert data["today"]["expected_earnings"] == 1000.0  # 4h * 250

    # Week stats
    assert data["week"]["total_shift_hours"] == 4.0
    assert data["week"]["total_class_hours"] == 2.0
    assert data["week"]["conflict_count"] >= 1

    # Alerts: Hard conflict alert should be present!
    alerts = data["alerts"]
    conflict_alerts = [a for a in alerts if a["type"] == "conflict"]
    assert len(conflict_alerts) >= 1, "Expected hard conflict alert"
    assert conflict_alerts[0]["severity"] == "hard"
    print(f"  [PASS] Conflict alert detected: {conflict_alerts[0]['message']}")

    # Now test over-work-limit alert by adding a massive shift
    # Add a 20h shift to push total shift hours to 24h (over 20h limit)
    other_dow = (today_dow + 1) % 7
    b3_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Weekend Mega Shift",
            "type": "shift",
            "day_of_week": other_dow,
            "start_time": "04:00",
            "end_time": "23:00",  # 19 hours
            "hourly_wage": 200.0,
        },
    )
    assert b3_resp.status_code in (200, 201), f"Failed to create block 3: {b3_resp.text}"

    dash_resp2 = client.get("/api/v1/dashboard", headers=headers)
    data2 = dash_resp2.json()["data"]
    assert data2["week"]["over_work_limit"] is True, "Expected over_work_limit to be True"
    work_limit_alerts = [a for a in data2["alerts"] if a["type"] == "work_limit"]
    assert len(work_limit_alerts) == 1, "Expected work_limit alert"
    print(f"  [PASS] Work limit alert detected: {work_limit_alerts[0]['message']}")


if __name__ == "__main__":
    print("Running SyncShift Dashboard API tests...")
    test_dashboard_unauthorized()
    test_dashboard_empty_user()
    test_dashboard_with_schedule_and_alerts()
    print("\nAll Dashboard tests PASSED successfully! 🎉")
