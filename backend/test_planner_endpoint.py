"""
Automated unit & integration tests for Smart Study Planner & Tasks endpoints:
- Task CRUD (GET, POST, PATCH, DELETE)
- Gap-finding & scheduling algorithm (POST /tasks/{id}/plan)
- Plan confirmation and safety check against class clashes (POST /tasks/{id}/plan/confirm)
- Replanning when schedule shifts occur (POST /tasks/{id}/replan)
- Cascade deletion of study blocks
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


def test_tasks_unauthorized():
    print("\n--- 1. Testing Unauthorized Access ---")
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    print("  [PASS] Missing token returns 401 Unauthorized")


def test_task_crud_and_planning():
    print("\n--- 2. Testing Task CRUD, Gap-Finding, Confirmation, and Replanning ---")
    # Register a fresh user
    uid = str(uuid.uuid4())[:8]
    email = f"planner_user_{uid}@example.com"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "name": "Planner Student",
        },
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup existing schedule for this student:
    # Monday (dow=1): Class 09:00 - 10:30, Shift 13:00 - 16:00
    # Tuesday (dow=2): Class 11:00 - 13:00
    b1 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "CS 210 Data Structures",
            "type": "class",
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "10:30",
        },
    )
    assert b1.status_code in (200, 201)

    b2 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Campus Library Desk",
            "type": "shift",
            "day_of_week": 1,
            "start_time": "13:00",
            "end_time": "16:00",
            "hourly_wage": 18.0,
        },
    )
    assert b2.status_code in (200, 201)

    # 1. Create a study task: "DBMS Project", 5.0 hours, deadline 5 days in the future
    deadline = date.today() + timedelta(days=5)
    create_resp = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "DBMS Project",
            "total_hours_required": 5.0,
            "deadline": deadline.isoformat(),
        },
    )
    assert create_resp.status_code == 201, f"Failed create task: {create_resp.text}"
    task = create_resp.json()["data"]
    task_id = task["id"]
    assert task["title"] == "DBMS Project"
    assert task["total_hours_required"] == 5.0
    assert task["status"] == "pending"
    print("  [PASS] Task created with status 'pending'")

    # 2. List tasks
    list_resp = client.get("/api/v1/tasks", headers=headers)
    assert list_resp.status_code == 200
    tasks_list = list_resp.json()["data"]
    assert any(t["id"] == task_id for t in tasks_list)
    print("  [PASS] List tasks returns newly created task")

    # 3. Plan task: POST /api/v1/tasks/{id}/plan
    plan_resp = client.post(f"/api/v1/tasks/{task_id}/plan", headers=headers)
    assert plan_resp.status_code == 200, f"Failed plan: {plan_resp.text}"
    plan_data = plan_resp.json()["data"]
    suggested = plan_data["suggested"]
    assert len(suggested) > 0, "Expected suggested study blocks"
    assert plan_data["hours_scheduled"] > 0
    print(f"  [PASS] Plan generated {len(suggested)} study sessions ({plan_data['hours_scheduled']}h)")

    # Verify no suggested block overlaps Monday class (09:00-10:30) or shift (13:00-16:00)
    # and verify 10-minute buffer:
    for s in suggested:
        if s["day_of_week"] == 1:
            # Check overlap with 09:00 - 10:30
            # With 10 min buffer, study cannot be in 08:50 - 10:40 (530m - 640m)
            s_min = int(s["start_time"].split(":")[0]) * 60 + int(s["start_time"].split(":")[1])
            e_min = int(s["end_time"].split(":")[0]) * 60 + int(s["end_time"].split(":")[1])
            assert not (s_min < 640 and 530 < e_min), f"Overlaps class or buffer: {s}"
            assert not (s_min < 970 and 770 < e_min), f"Overlaps shift or buffer: {s}"
    print("  [PASS] All suggested study sessions strictly avoid classes, shifts, and respect 10m buffer")

    # 4. Confirm plan: POST /api/v1/tasks/{id}/plan/confirm
    approved_blocks = [
        {
            "temp_id": s["temp_id"],
            "day_of_week": s["day_of_week"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "date": s["date"],
        }
        for s in suggested
    ]
    confirm_resp = client.post(
        f"/api/v1/tasks/{task_id}/plan/confirm",
        headers=headers,
        json={"approved_blocks": approved_blocks},
    )
    assert confirm_resp.status_code == 200, f"Failed confirm: {confirm_resp.text}"
    confirmed_task = confirm_resp.json()["data"]
    assert confirmed_task["status"] == "scheduled"
    assert confirmed_task["hours_scheduled"] > 0
    print("  [PASS] Plan confirmed, task marked 'scheduled'")

    # 5. Check study blocks appear in /api/v1/week
    week_start_str = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    week_resp = client.get(f"/api/v1/week?start={week_start_str}", headers=headers)
    assert week_resp.status_code == 200
    week_blocks = week_resp.json()["data"]["blocks"]
    study_blocks = [b for b in week_blocks if b.get("study_task_id") == task_id]
    assert len(study_blocks) == len(approved_blocks)
    assert all(b["type"] == "study" for b in study_blocks)
    assert all(b.get("color") == "#8B5CF6" for b in study_blocks)
    print(f"  [PASS] {len(study_blocks)} purple study blocks appear on calendar")

    # 6. Safety Net: Verify 422 Unprocessable Entity if an approved block overlaps a class
    clash_confirm = client.post(
        f"/api/v1/tasks/{task_id}/plan/confirm",
        headers=headers,
        json={
            "approved_blocks": [
                {
                    "day_of_week": 1,
                    "start_time": "09:30",  # Clashes with Monday 09:00-10:30 class!
                    "end_time": "11:00",
                }
            ]
        },
    )
    assert clash_confirm.status_code == 422, f"Expected 422 clash, got {clash_confirm.status_code}"
    error_code = clash_confirm.json().get("error", {}).get("code") or clash_confirm.json().get("detail", {}).get("code")
    assert error_code == "class_clash"
    print("  [PASS] Safety check successfully rejected artificial class clash with HTTP 422")

    # 7. Test Replan: POST /api/v1/tasks/{id}/replan
    replan_resp = client.post(f"/api/v1/tasks/{task_id}/replan", headers=headers)
    assert replan_resp.status_code == 200, f"Failed replan: {replan_resp.text}"
    replan_data = replan_resp.json()["data"]
    assert "suggested" in replan_data
    print("  [PASS] Replanning succeeded and returned fresh preview")

    # 8. Test Delete Task: DELETE /api/v1/tasks/{id}
    del_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert del_resp.status_code == 200
    # Verify study blocks are now gone from calendar
    week_resp2 = client.get(f"/api/v1/week?start={week_start_str}", headers=headers)
    week_blocks2 = week_resp2.json()["data"]["blocks"]
    remaining_study_blocks = [b for b in week_blocks2 if b.get("study_task_id") == task_id]
    assert len(remaining_study_blocks) == 0
    print("  [PASS] Deleting task cascades and deletes all associated study blocks")


if __name__ == "__main__":
    print("Running SyncShift Study Planner API tests...")
    test_tasks_unauthorized()
    test_task_crud_and_planning()
    print("\nAll Study Planner tests PASSED successfully! 🎉")
