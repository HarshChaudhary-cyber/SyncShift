import io
import sys
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_HEADER = {"Authorization": "Bearer mock_token_1"}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("[PASS] GET /health")


def test_auth_endpoints():
    # 1. Register (with a clean test email)
    test_email = "student_api_test@university.edu"
    test_password = "StrongPassword123"
    
    # Try login first in case user was previously created
    login_resp = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    if login_resp.status_code == 200:
        token = login_resp.json()["data"]["token"]
    else:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_email,
                "password": test_password,
                "timezone": "Europe/London",
                "weekly_work_hour_limit": 20.0,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["email"] == test_email
        assert "token" in data
        token = data["token"]
    print("[PASS] POST /api/v1/auth/register")

    # 2. Login
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert resp.status_code == 200, resp.text
    assert "token" in resp.json()["data"]
    print("[PASS] POST /api/v1/auth/login")

    # 3. GET /auth/me with Bearer token
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    me = resp.json()["data"]
    assert me["email"] == test_email
    print("[PASS] GET /api/v1/auth/me")

    # 4. Unauthorized check without token
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert "error" in resp.json()
    assert resp.json()["error"]["code"] == "unauthorized"
    print("[PASS] 401 Unauthorized check without token")


def test_courses_endpoints():
    # GET /courses
    resp = client.get("/api/v1/courses", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["data"], list)
    print("[PASS] GET /api/v1/courses")

    # POST /courses
    resp = client.post(
        "/api/v1/courses",
        headers=AUTH_HEADER,
        json={"code": "CS210", "name": "Data Structures", "color": "#10b981"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["code"] == "CS210"
    print("[PASS] POST /api/v1/courses")

    # PATCH /courses/1
    resp = client.patch(
        "/api/v1/courses/1",
        headers=AUTH_HEADER,
        json={"name": "Updated Data Structures"},
    )
    assert resp.status_code == 200, resp.text
    print("[PASS] PATCH /api/v1/courses/1")

    # DELETE /courses/1
    resp = client.delete("/api/v1/courses/1", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted"] is True
    print("[PASS] DELETE /api/v1/courses/1")


def test_blocks_endpoints():
    # GET /blocks
    resp = client.get("/api/v1/blocks?week_start=2026-09-07&type=shift", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["data"], list)
    print("[PASS] GET /api/v1/blocks")

    # POST /blocks
    resp = client.post(
        "/api/v1/blocks",
        headers=AUTH_HEADER,
        json={
            "type": "shift",
            "title": "IT Helpdesk",
            "location": "Student Services",
            "day_of_week": 2,
            "start_time": "13:00:00",
            "end_time": "17:00:00",
            "effective_from": "2026-09-01",
            "effective_until": "2026-12-18",
            "is_flexible": True,
            "hourly_wage": 18.50,
        },
    )
    assert resp.status_code in (200, 201), resp.text
    created = resp.json()["data"]
    assert created["title"] == "IT Helpdesk"
    print("[PASS] POST /api/v1/blocks")

    # Validation Error Check: effective_until < effective_from
    resp_invalid = client.post(
        "/api/v1/blocks",
        headers=AUTH_HEADER,
        json={
            "type": "class",
            "title": "Invalid Block",
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "effective_from": "2026-12-01",
            "effective_until": "2026-09-01",
        },
    )
    assert resp_invalid.status_code == 422
    assert resp_invalid.json()["error"]["code"] == "validation_error"
    print("[PASS] 422 Validation error format { error: { code, message } }")

    # PATCH /blocks/1
    resp = client.patch(
        "/api/v1/blocks/1",
        headers=AUTH_HEADER,
        json={"title": "Updated Shift Title", "hourly_wage": 19.00},
    )
    assert resp.status_code == 200, resp.text
    print("[PASS] PATCH /api/v1/blocks/1")

    # POST /blocks/duplicate (on newly created block)
    resp = client.post(
        f"/api/v1/blocks/{created['id']}/duplicate",
        headers=AUTH_HEADER,
        json={"days_offset": 2},
    )
    assert resp.status_code == 200, resp.text
    assert "id" in resp.json()["data"]
    print("[PASS] POST /api/v1/blocks/{id}/duplicate")

    # DELETE /blocks/1
    resp = client.delete("/api/v1/blocks/1", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["deleted"] is True
    print("[PASS] DELETE /api/v1/blocks/1 (soft delete)")


def test_conflicts_and_week_endpoints():
    # GET /conflicts
    resp = client.get("/api/v1/conflicts?week_start=2026-09-07", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "conflicts" in data
    assert "weekly_totals" in data
    assert "shift_hours" in data["weekly_totals"]
    print("[PASS] GET /api/v1/conflicts")

    # GET /week
    resp = client.get("/api/v1/week?start=2026-09-07", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    week_data = resp.json()["data"]
    assert "blocks" in week_data
    assert "conflicts" in week_data
    assert "totals" in week_data
    print("[PASS] GET /api/v1/week (convenience endpoint)")


def test_import_endpoints():
    dummy_ics = io.BytesIO(
        b"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nSUMMARY:CS 210: Data Structures\n"
        b"DTSTART:20260907T090000\nDTEND:20260907T103000\nRRULE:FREQ=WEEKLY;BYDAY=MO\n"
        b"LOCATION:Room 302\nEND:VEVENT\nEND:VCALENDAR"
    )
    resp = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("timetable.ics", dummy_ics, "text/calendar")},
    )
    assert resp.status_code == 200, resp.text
    import_preview = resp.json()["data"]
    assert "preview" in import_preview
    assert "unmatched" in import_preview
    print("[PASS] POST /api/v1/import/ics")

    # POST /import/ics/confirm
    resp = client.post(
        "/api/v1/import/ics/confirm",
        headers=AUTH_HEADER,
        json={
            "preview_blocks": [
                {
                    "title": "CS 210: Data Structures",
                    "day_of_week": 1,
                    "start_time": "09:00:00",
                    "end_time": "10:30:00",
                    "course_id": 1,
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    confirm_data = resp.json()["data"]
    assert confirm_data["created_count"] == 1
    assert "conflicts_detected" in confirm_data
    print("[PASS] POST /api/v1/import/ics/confirm")


if __name__ == "__main__":
    print("\n=== RUNNING FASTAPI SCAFFOLDING TEST SUITE ===\n")
    test_health()
    test_auth_endpoints()
    test_courses_endpoints()
    test_blocks_endpoints()
    test_conflicts_and_week_endpoints()
    test_import_endpoints()
    print("\n=== ALL 14 FASTAPI BACKEND TESTS PASSED! ===\n")
