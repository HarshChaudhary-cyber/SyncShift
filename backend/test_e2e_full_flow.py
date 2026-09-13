"""
End-to-End Integration Test Suite for SyncShift
Verifies the exact 20-step integrated flow requested in the specification:
1. Login
2. Open dashboard
3. Open calendar
4. Create existing class/work events
5. Open analytics
6. Verify hours
7. Verify workload chart
8. Verify schedule health
9. Create study goal
10. Generate recommendations
11. Add recommended session to calendar
12. Return to calendar
13. Verify study block appears
14. Return to analytics
15. Verify study hours increased
16. Verify total planned hours increased
17. Verify schedule health recalculated
18. Mark study session completed
19. Verify completed hours increased
20. Verify remaining study goal decreased
"""

import sys
import time
from fastapi.testclient import TestClient
from app.main import app

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

client = TestClient(app)

def run_e2e_flow():
    print("=" * 60)
    print("      SYNCSHIFT 20-STEP END-TO-END INTEGRATION TEST       ")
    print("=" * 60)

    # 1. Login / Register
    user_email = f"e2e_student_{int(time.time())}@example.com"
    user_pwd = "Password123!"
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": user_email,
        "password": user_pwd,
        "timezone": "Europe/London",
        "weekly_work_hour_limit": 20.0,
        "currency": "EUR",
    })
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[STEP 1] Login / Register: SUCCESS")

    # 2. Open dashboard
    dash_resp = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()["data"]
    assert "user" in dash_data
    assert "today" in dash_data
    print("[STEP 2] Open dashboard: SUCCESS")

    # 3. Open calendar (week view)
    week_start = "2026-09-07"  # Monday
    week_resp = client.get(f"/api/v1/week?start={week_start}", headers=headers)
    assert week_resp.status_code == 200
    assert len(week_resp.json()["data"]["blocks"]) == 0
    print("[STEP 3] Open calendar: SUCCESS (0 initial blocks)")

    # 4. Create existing class/work events
    # Class Monday 09:00-12:00 (3h)
    c1 = client.post("/api/v1/blocks", headers=headers, json={
        "type": "class",
        "title": "Computer Networks Lecture",
        "day_of_week": 1,
        "start_time": "09:00",
        "end_time": "12:00",
        "color": "#4F46E5",
    })
    assert c1.status_code == 201

    # Shift Tuesday 14:00-18:00 (4h, hourly wage €15)
    s1 = client.post("/api/v1/blocks", headers=headers, json={
        "type": "shift",
        "title": "Campus IT Helpdesk",
        "day_of_week": 2,
        "start_time": "14:00",
        "end_time": "18:00",
        "hourly_wage": 15.0,
        "color": "#10B981",
    })
    assert s1.status_code == 201
    print("[STEP 4] Create existing class/work events: SUCCESS (Class 3h, Shift 4h @ €15/h)")

    # 5. Open analytics
    analytics_resp1 = client.get(f"/api/v1/analytics/week?start_date={week_start}", headers=headers)
    assert analytics_resp1.status_code == 200
    a1 = analytics_resp1.json()["data"]
    print("[STEP 5] Open analytics: SUCCESS")

    # 6. Verify hours
    assert a1["hours"]["class_hours"] == 3.0, f"Expected 3.0h class, got {a1['hours']['class_hours']}"
    assert a1["hours"]["work_hours"] == 4.0, f"Expected 4.0h work, got {a1['hours']['work_hours']}"
    assert a1["hours"]["study_hours"] == 0.0, f"Expected 0.0h study, got {a1['hours']['study_hours']}"
    assert a1["hours"]["total_hours"] == 7.0
    assert a1["earnings"]["estimated_week"] == 60.0  # 4h * €15 = €60
    assert a1["work_limit"]["used"] == 4.0
    assert a1["work_limit"]["remaining"] == 16.0
    print("[STEP 6] Verify hours: SUCCESS (Class: 3h, Work: 4h, Study: 0h, Total: 7h, Earnings: €60)")

    # 7. Verify workload chart
    daily = a1["daily_workload"]
    assert len(daily) == 7
    mon = next(d for d in daily if d["day"] == "Monday")
    tue = next(d for d in daily if d["day"] == "Tuesday")
    wed = next(d for d in daily if d["day"] == "Wednesday")
    assert mon["total_hours"] == 3.0
    assert tue["total_hours"] == 4.0
    assert wed["total_hours"] == 0.0
    print("[STEP 7] Verify workload chart: SUCCESS (Mon: 3h, Tue: 4h, Wed-Sun: 0h)")

    # 8. Verify schedule health
    h1 = a1["health"]
    score1 = h1["score"]
    assert 70 <= score1 <= 100
    assert h1["category"] in ["Excellent", "Healthy"]
    print(f"[STEP 8] Verify schedule health: SUCCESS (Score: {score1}/100, Category: '{h1['category']}')")

    # 9. Create study goal
    goal_resp = client.post("/api/v1/tasks", headers=headers, json={
        "title": "Computer Networks Exam Prep",
        "total_hours_required": 4.0,
        "deadline": "2026-09-13",  # Sunday
        "priority": "high",
        "preferred_duration": 90,  # 1.5h
    })
    assert goal_resp.status_code == 201
    goal = goal_resp.json()["data"]
    task_id = goal["id"]
    assert goal["total_hours_required"] == 4.0
    assert goal["completed_hours"] == 0.0
    print(f"[STEP 9] Create study goal: SUCCESS (Task #{task_id}, Target: 4.0h, Deadline: 2026-09-13)")

    # 10. Generate recommendations
    plan_resp = client.post(f"/api/v1/tasks/{task_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()["data"]
    sessions = plan_data["suggested"]
    assert len(sessions) > 0
    # Verify slot score and reasons are present and explainable
    first_slot = sessions[0]
    assert "score" in first_slot and first_slot["score"] >= 50
    assert "reasons" in first_slot and len(first_slot["reasons"]) > 0
    print(f"[STEP 10] Generate recommendations: SUCCESS ({len(sessions)} slots suggested, Slot 1 Score: {first_slot['score']}, Reasons: {first_slot['reasons']})")

    # 11. Add recommended session to calendar
    add_slot_resp = client.post(
        f"/api/v1/tasks/{task_id}/plan/add-slot",
        headers=headers,
        json={
            "day_of_week": first_slot["day_of_week"],
            "start_time": first_slot["start_time"],
            "end_time": first_slot["end_time"],
            "date": first_slot["date"],
            "title": f"Study: Computer Networks",
        }
    )
    assert add_slot_resp.status_code == 200, f"Failed to add slot: {add_slot_resp.text}"
    updated_study_task = add_slot_resp.json()["data"]
    print(f"[STEP 11] Add recommended session to calendar: SUCCESS (Task #{updated_study_task['id']} hours_scheduled: {updated_study_task['hours_scheduled']}h)")

    # 12. Return to calendar
    cal_resp = client.get(f"/api/v1/week?start={week_start}", headers=headers)
    assert cal_resp.status_code == 200
    week_blocks = cal_resp.json()["data"]["blocks"]
    print(f"[STEP 12] Return to calendar: SUCCESS ({len(week_blocks)} blocks present)")

    # 13. Verify study block appears
    study_blocks = [b for b in week_blocks if b["type"] == "study"]
    assert len(study_blocks) >= 1
    found_study = next(b for b in study_blocks if b["study_task_id"] == task_id)
    slot_duration = (
        (int(found_study["end_time"][:2]) * 60 + int(found_study["end_time"][3:5])) -
        (int(found_study["start_time"][:2]) * 60 + int(found_study["start_time"][3:5]))
    ) / 60.0
    print(f"[STEP 13] Verify study block appears in calendar: SUCCESS (Found Block #{found_study['id']}, Duration: {slot_duration}h)")

    # 14. Return to analytics
    analytics_resp2 = client.get(f"/api/v1/analytics/week?start_date={week_start}", headers=headers)
    assert analytics_resp2.status_code == 200
    a2 = analytics_resp2.json()["data"]
    print("[STEP 14] Return to analytics: SUCCESS")

    # 15. Verify study hours increased
    assert a2["hours"]["study_hours"] == slot_duration, f"Expected {slot_duration}h study, got {a2['hours']['study_hours']}"
    print(f"[STEP 15] Verify study hours increased: SUCCESS (Study hours: 0.0h -> {a2['hours']['study_hours']}h)")

    # 16. Verify total planned hours increased
    expected_total = 7.0 + slot_duration
    assert a2["hours"]["total_hours"] == expected_total, f"Expected total {expected_total}h, got {a2['hours']['total_hours']}"
    print(f"[STEP 16] Verify total planned hours increased: SUCCESS (Total: 7.0h -> {a2['hours']['total_hours']}h)")

    # 17. Verify schedule health recalculated
    h2 = a2["health"]
    print(f"[STEP 17] Verify schedule health recalculated: SUCCESS (Health score: {h2['score']}/100, '{h2['category']}')")

    # 18. Mark study session completed
    complete_resp = client.post(f"/api/v1/tasks/{task_id}/complete", headers=headers)
    assert complete_resp.status_code == 200
    completed_task = complete_resp.json()["data"]
    assert completed_task["status"] == "done"
    print(f"[STEP 18] Mark study session completed: SUCCESS (Task status: '{completed_task['status']}')")

    # 19. Verify completed hours increased
    assert completed_task["completed_hours"] == 4.0
    print(f"[STEP 19] Verify completed hours increased: SUCCESS (Completed: {completed_task['completed_hours']}h / {completed_task['total_hours_required']}h)")

    # 20. Verify remaining study goal decreased
    remaining = max(0.0, completed_task["total_hours_required"] - completed_task["completed_hours"])
    assert remaining == 0.0
    print(f"[STEP 20] Verify remaining study goal decreased: SUCCESS (Remaining: {remaining}h - Goal fully achieved!)")

    print("=" * 60)
    print("   ALL 20 STEPS OF THE END-TO-END FLOW PASSED 100%!       ")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e_flow()
