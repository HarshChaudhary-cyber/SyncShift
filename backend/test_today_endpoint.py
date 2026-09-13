from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer mock_token_1"}


def test_today_endpoint_unauthorized():
    resp = client.get("/api/v1/today")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert err["code"] == "unauthorized"


def test_today_endpoint_authenticated():
    resp = client.get("/api/v1/today", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert "date" in data
    assert "day_of_week" in data
    assert 0 <= data["day_of_week"] <= 6
    assert "blocks" in data
    assert "conflicts" in data
    assert "shift_hours" in data
    assert "expected_earnings" in data
    assert "class_hours" in data

    # All returned blocks must match today's day_of_week
    for block in data["blocks"]:
        assert block["day_of_week"] == data["day_of_week"]
        assert "start_time" in block
        assert "end_time" in block
        assert "color" in block


def test_today_endpoint_specific_date():
    # 2026-09-07 is Monday -> day_of_week 1
    resp = client.get("/api/v1/today?date=2026-09-07", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["date"] == "2026-09-07"
    assert data["day_of_week"] == 1
    assert len(data["blocks"]) >= 2

    # Blocks should be sorted chronologically by start_time
    times = [b["start_time"] for b in data["blocks"]]
    assert times == sorted(times)

    # Monday has CS 210 (09:00-10:30, class, 1.5h) and Library Desk (10:00-14:00, shift, 4h @ $17.50)
    assert data["class_hours"] >= 1.5
    assert data["shift_hours"] >= 4.0
    assert data["expected_earnings"] >= 70.0

    # There is an overlap conflict between CS 210 and Library Desk (10:00-10:30)
    assert len(data["conflicts"]) >= 1
    assert any(c["overlap_minutes"] == 30 for c in data["conflicts"])


def test_today_endpoint_empty_day():
    # 2026-09-12 is Saturday -> day_of_week 6 (no seed blocks on Saturday)
    resp = client.get("/api/v1/today?date=2026-09-12", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["date"] == "2026-09-12"
    assert data["day_of_week"] == 6
    assert data["blocks"] == []
    assert data["conflicts"] == []
    assert data["shift_hours"] == 0.0
    assert data["expected_earnings"] == 0.0
    assert data["class_hours"] == 0.0
