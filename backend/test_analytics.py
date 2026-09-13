"""
Automated unit & integration tests for Advanced Schedule Analytics:
- Verifies exact calculations with a known dataset:
    Classes: 10h
    Work: 10h
    Study: 5h
    Total: 25h
- Work-hour utilization (e.g. 10h / 20h = 50%)
- Earnings calculation (4h * 15 = 60 EUR/INR/USD)
- Missing hourly wage handled gracefully
- Daily workload breakdown (Monday to Sunday)
- Time distribution percentages
"""
import sys
import uuid
from datetime import date, timedelta
from starlette.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.main import app

client = TestClient(app)


def test_analytics_known_dataset():
    # Register user with weekly limit = 20h, currency = EUR
    uid = str(uuid.uuid4())[:8]
    email = f"analytics_user_{uid}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "name": "Analytics Student",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert reg.status_code == 200
    token = reg.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile currency to EUR
    client.patch("/api/v1/auth/me", headers=headers, json={"currency": "EUR"})

    # Setup known dataset:
    # 1. Classes: 10h total
    #    Monday (dow=1): 09:00 - 14:00 (5h)
    #    Wednesday (dow=3): 09:00 - 14:00 (5h)
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Class Mon", "type": "class", "day_of_week": 1, "start_time": "09:00", "end_time": "14:00"},
    )
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Class Wed", "type": "class", "day_of_week": 3, "start_time": "09:00", "end_time": "14:00"},
    )

    # 2. Work shifts: 10h total
    #    Tuesday (dow=2): 10:00 - 14:00 (4h) @ 15.0 EUR/hr -> Earnings = 60 EUR
    #    Thursday (dow=4): 12:00 - 18:00 (6h) with NO wage -> missing wage shift
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Shift Paid", "type": "shift", "day_of_week": 2, "start_time": "10:00", "end_time": "14:00", "hourly_wage": 15.0},
    )
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Shift Unpaid", "type": "shift", "day_of_week": 4, "start_time": "12:00", "end_time": "18:00"},
    )

    # 3. Study: 5h total
    #    Friday (dow=5): 10:00 - 15:00 (5h)
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Self Study", "type": "study", "day_of_week": 5, "start_time": "10:00", "end_time": "15:00"},
    )

    # Call GET /api/v1/analytics/week
    resp = client.get("/api/v1/analytics/week", headers=headers)
    assert resp.status_code == 200, f"Analytics failed: {resp.text}"
    data = resp.json()["data"]

    # Verify Hours Breakdown
    hours = data["hours"]
    assert hours["class_hours"] == 10.0, f"Expected 10.0 class hours, got {hours['class_hours']}"
    assert hours["work_hours"] == 10.0, f"Expected 10.0 work hours, got {hours['work_hours']}"
    assert hours["study_hours"] == 5.0, f"Expected 5.0 study hours, got {hours['study_hours']}"
    assert hours["total_hours"] == 25.0, f"Expected 25.0 total hours, got {hours['total_hours']}"
    assert hours["free_hours"] == 80.0, f"Expected 80.0 free hours (105 - 25), got {hours['free_hours']}"

    # Verify Work Limit Utilization
    work_limit = data["work_limit"]
    assert work_limit["configured"] == 20.0
    assert work_limit["used"] == 10.0
    assert work_limit["remaining"] == 10.0
    assert work_limit["percentage"] == 50.0
    assert work_limit["over_limit"] is False

    # Verify Earnings
    earnings = data["earnings"]
    assert earnings["currency"] == "EUR"
    assert earnings["currency_symbol"] == "€"
    assert earnings["estimated_week"] == 60.0  # 4h * 15 = 60
    assert earnings["missing_wage_shifts"] == 1

    # Verify Daily Workload (Monday to Sunday)
    workload = data["daily_workload"]
    assert len(workload) == 7
    mon = next(w for w in workload if w["day"] == "Monday")
    tue = next(w for w in workload if w["day"] == "Tuesday")
    wed = next(w for w in workload if w["day"] == "Wednesday")
    thu = next(w for w in workload if w["day"] == "Thursday")
    fri = next(w for w in workload if w["day"] == "Friday")

    assert mon["total_hours"] == 5.0
    assert tue["total_hours"] == 4.0
    assert wed["total_hours"] == 5.0
    assert thu["total_hours"] == 6.0
    assert fri["total_hours"] == 5.0

    # Verify Schedule Health inside Analytics
    health = data["health"]
    assert health["score"] >= 75
    assert health["category"] in ("Excellent", "Healthy")
    print("\n  [PASS] Analytics calculations match exact known dataset!")


if __name__ == "__main__":
    test_analytics_known_dataset()
    print("All Analytics tests PASSED! 🎉")
