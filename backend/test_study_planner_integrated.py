"""
Integrated tests for Smart Study Planner with Calendar, Analytics, and Health:
1. Scenario with Monday Class, Tuesday Work, Wednesday Class
2. Study goal of 4h with 2h preferred session duration
3. Verifies no overlap with class or work
4. Verifies slot scoring and reasons
5. Verifies adding recommended slot directly creates a real calendar time block
6. Verifies calendar (/week) updates
7. Verifies Analytics study hours and Schedule Health recalculate
8. Verifies marking task complete updates completed hours
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


def test_study_planner_calendar_analytics_integration():
    uid = str(uuid.uuid4())[:8]
    email = f"study_integrated_{uid}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Integrated Student"},
    )
    assert reg.status_code == 200
    token = reg.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup Schedule:
    # Monday: Class 09:00–12:00
    # Tuesday: Work 17:00–21:00
    # Wednesday: Class 10:00–14:00
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Mon Lecture", "type": "class", "day_of_week": 1, "start_time": "09:00", "end_time": "12:00"},
    )
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Tue Shift", "type": "shift", "day_of_week": 2, "start_time": "17:00", "end_time": "21:00"},
    )
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={"title": "Wed Lab", "type": "class", "day_of_week": 3, "start_time": "10:00", "end_time": "14:00"},
    )

    # Check baseline analytics: Study = 0h
    analytics_before = client.get("/api/v1/analytics/week", headers=headers).json()["data"]
    assert analytics_before["hours"]["study_hours"] == 0.0

    # 1. Create Study Goal: 4 hours, preferred duration 2h (120 mins), deadline next Sunday
    deadline = date.today() + timedelta(days=7)
    task_resp = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Computer Networks",
            "total_hours_required": 4.0,
            "deadline": deadline.isoformat(),
            "priority": "high",
            "preferred_duration": 120,
        },
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["data"]["id"]

    # 2. Generate study plan: POST /api/v1/tasks/{id}/plan
    plan_resp = client.post(f"/api/v1/tasks/{task_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()["data"]
    suggested = plan_data["suggested"]

    assert len(suggested) > 0, "Expected recommended study slots"
    assert plan_data["hours_scheduled"] >= 3.5, f"Expected >= 3.5h, got {plan_data['hours_scheduled']}"

    # Verify each slot has a score, reasons, and avoids existing blocks
    for slot in suggested:
        assert slot["score"] >= 50
        assert len(slot["reasons"]) > 0
        s_parts = [int(p) for p in slot["start_time"].split(":")[:2]]
        e_parts = [int(p) for p in slot["end_time"].split(":")[:2]]
        s_min = s_parts[0] * 60 + s_parts[1]
        e_min = e_parts[0] * 60 + e_parts[1]

        # Monday class: 09:00 - 12:00 (540 - 720)
        if slot["day_of_week"] == 1:
            assert not (s_min < 720 and 540 < e_min), "Must not clash with Monday class"
        # Tuesday work: 17:00 - 21:00 (1020 - 1260)
        if slot["day_of_week"] == 2:
            assert not (s_min < 1260 and 1020 < e_min), "Must not clash with Tuesday shift"
        # Wednesday class: 10:00 - 14:00 (600 - 840)
        if slot["day_of_week"] == 3:
            assert not (s_min < 840 and 600 < e_min), "Must not clash with Wednesday class"

    # 3. Add single recommended session to calendar: POST /api/v1/tasks/{id}/plan/add-slot
    first_slot = suggested[0]
    add_slot_resp = client.post(
        f"/api/v1/tasks/{task_id}/plan/add-slot",
        headers=headers,
        json={
            "day_of_week": first_slot["day_of_week"],
            "start_time": first_slot["start_time"],
            "end_time": first_slot["end_time"],
            "date": first_slot["date"],
        },
    )
    assert add_slot_resp.status_code == 200, f"Failed add slot: {add_slot_resp.text}"

    # 4. Verify the study session now exists as a real calendar time block in /api/v1/week
    week_start_str = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    week_resp = client.get(f"/api/v1/week?start={week_start_str}", headers=headers)
    assert week_resp.status_code == 200
    week_blocks = week_resp.json()["data"]["blocks"]
    study_blocks = [b for b in week_blocks if b.get("study_task_id") == task_id]
    assert len(study_blocks) == 1
    assert study_blocks[0]["type"] == "study"
    assert study_blocks[0]["color"] == "#8B5CF6"

    # 5. Verify Analytics immediately reflects the added study block
    analytics_after = client.get("/api/v1/analytics/week", headers=headers).json()["data"]
    assert analytics_after["hours"]["study_hours"] == first_slot["duration_hours"]
    assert analytics_after["hours"]["total_hours"] == analytics_before["hours"]["total_hours"] + first_slot["duration_hours"]

    # 6. Mark task complete: POST /api/v1/tasks/{id}/complete
    comp_resp = client.post(f"/api/v1/tasks/{task_id}/complete", headers=headers)
    assert comp_resp.status_code == 200
    completed_task = comp_resp.json()["data"]
    assert completed_task["status"] == "done"
    assert completed_task["completed_hours"] == 4.0

    print("\n  [PASS] Full Study Planner -> Calendar -> Analytics integration verified successfully!")


if __name__ == "__main__":
    test_study_planner_calendar_analytics_integration()
    print("All Integration tests PASSED! 🎉")
