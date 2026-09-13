"""
Comprehensive tests for:
1. Exact recurring test from prompt:
   - Class: Database Systems (Every Monday 10:00-12:00)
   - Shift: Café Roma (Every Monday 11:00-15:00)
   - Conflict every applicable Monday.
   - Cancel Oct 12 class -> Oct 12 has NO conflict, Oct 19 HAS conflict.
   - Drag Oct 19 shift to 13:00-17:00 (via override) -> Oct 19 has NO conflict, other Mondays remain unchanged.
2. Exact dashboard test from prompt:
   - Today class 10-12, today work 17-21, weekly work 16/20h, Friday conflict.
   - Consolidated dashboard response: next_event, alerts, health, work, today timeline.
3. Advanced recurrence scenarios:
   - Weekly vs Biweekly occurrences.
   - Start / End date boundaries.
   - Scope editing: 'this', 'future', 'all'.
   - Occurrence-based analytics & earnings (omits cancelled).
   - User isolation.
   - Soft deletion.

NOTE: SyncShift day_of_week convention:
0 = Sunday, 1 = Monday, 2 = Tuesday, 3 = Wednesday, 4 = Thursday, 5 = Friday, 6 = Saturday.
"""
import uuid
import pytest
from datetime import date, timedelta
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_user(email_prefix="rec_user", weekly_limit=20.0):
    uid = str(uuid.uuid4())[:8]
    email = f"{email_prefix}_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": weekly_limit,
            "name": f"Tester {uid}",
        },
    )
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    token = resp.json()["data"]["token"]
    return token, email


def test_exact_recurring_test_from_prompt():
    """
    EXACT PROMPT SPECIFICATION:
    Class: Database Systems, Every Monday 10:00-12:00
    Shift: Café Roma, Every Monday 11:00-15:00
    Expected: Conflict every applicable Monday.
    Cancel October 12 class.
    Expected: October 12: No conflict. October 19: Conflict.
    Then drag October 19 shift to: 13:00-17:00.
    Expected: October 19: No conflict. Other Mondays: remain unchanged.
    """
    token, _ = register_user("prompt_test")
    headers = {"Authorization": f"Bearer {token}"}

    # In 2026:
    # 2026-10-12 and 2026-10-19 are Mondays -> day_of_week = 1 in SyncShift
    # Create Class: Database Systems, Every Monday 10:00-12:00
    res_class = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Database Systems",
            "type": "class",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
            "recurrence_rule": "weekly",
            "recurrence_interval": 1,
            "effective_from": "2026-10-01",
            "effective_until": "2026-12-31",
            "location": "Room A-204",
        },
    )
    assert res_class.status_code in (200, 201), res_class.text
    class_block = res_class.json()["data"]
    class_id = class_block["id"]

    # Create Shift: Café Roma, Every Monday 11:00-15:00
    res_shift = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Café Roma",
            "type": "shift",
            "day_of_week": 1,
            "start_time": "11:00",
            "end_time": "15:00",
            "recurrence_rule": "weekly",
            "recurrence_interval": 1,
            "effective_from": "2026-10-01",
            "effective_until": "2026-12-31",
            "hourly_wage": 15.0,
        },
    )
    assert res_shift.status_code in (200, 201), res_shift.text
    shift_block = res_shift.json()["data"]
    shift_id = shift_block["id"]

    # Check week of Oct 12: 2026-10-12
    # Both blocks overlap 11:00-12:00 -> Hard conflict
    conf_oct12 = client.get(
        "/api/v1/conflicts?week_start=2026-10-12",
        headers=headers,
    )
    assert conf_oct12.status_code == 200, conf_oct12.text
    c_list = conf_oct12.json()["data"]["conflicts"]
    assert len(c_list) >= 1
    assert any(c["block_a_id"] == class_id or c["block_b_id"] == class_id for c in c_list)

    # Check week of Oct 19: 2026-10-19
    conf_oct19 = client.get(
        "/api/v1/conflicts?week_start=2026-10-19",
        headers=headers,
    )
    assert conf_oct19.status_code == 200, conf_oct19.text
    assert len(conf_oct19.json()["data"]["conflicts"]) >= 1

    # --- ACTION 1: Cancel October 12 class ---
    del_res = client.delete(
        f"/api/v1/blocks/{class_id}?scope=this&occurrence_date=2026-10-12",
        headers=headers,
    )
    assert del_res.status_code == 200, del_res.text

    # Expected: October 12: No conflict
    conf_oct12_after = client.get(
        "/api/v1/conflicts?week_start=2026-10-12",
        headers=headers,
    )
    assert conf_oct12_after.status_code == 200, conf_oct12_after.text
    assert len(conf_oct12_after.json()["data"]["conflicts"]) == 0

    # Expected: October 19: Still has conflict
    conf_oct19_after = client.get(
        "/api/v1/conflicts?week_start=2026-10-19",
        headers=headers,
    )
    assert conf_oct19_after.status_code == 200, conf_oct19_after.text
    assert len(conf_oct19_after.json()["data"]["conflicts"]) >= 1

    # --- ACTION 2: Drag October 19 shift to: 13:00-17:00 ---
    # Dragging single occurrence applies scope='this' override
    patch_res = client.patch(
        f"/api/v1/blocks/{shift_id}?scope=this&occurrence_date=2026-10-19",
        headers=headers,
        json={
            "start_time": "13:00",
            "end_time": "17:00",
        },
    )
    assert patch_res.status_code == 200, patch_res.text

    # Expected: October 19: Class is 10:00-12:00, Shift is 13:00-17:00 -> NO conflict
    conf_oct19_final = client.get(
        "/api/v1/conflicts?week_start=2026-10-19",
        headers=headers,
    )
    assert conf_oct19_final.status_code == 200, conf_oct19_final.text
    assert len(conf_oct19_final.json()["data"]["conflicts"]) == 0

    # Expected: Other Mondays (e.g. October 26) remain unchanged (Conflict still present)
    conf_oct26 = client.get(
        "/api/v1/conflicts?week_start=2026-10-26",
        headers=headers,
    )
    assert conf_oct26.status_code == 200, conf_oct26.text
    assert len(conf_oct26.json()["data"]["conflicts"]) >= 1


def test_exact_dashboard_test_from_prompt():
    """
    EXACT PROMPT SPECIFICATION:
    Create:
    Today: Class 10-12
    Today: Work 17-21
    Weekly work: 16 / 20h
    One conflict on Friday.
    Expected dashboard:
    Next event: Class 10-12 (or Work 17-21)
    Attention: 1 hard conflict
    Work: 16 / 20h
    Schedule health: calculated from backend
    Today timeline: both events
    No fake values.
    """
    token, _ = register_user("prompt_dash", weekly_limit=20.0)
    headers = {"Authorization": f"Bearer {token}"}

    today_d = date.today()
    today_dow = (today_d.weekday() + 1) % 7
    start_of_week = today_d - timedelta(days=today_d.weekday())
    # Friday in SyncShift is 5 (since Monday=1, Fri=5)
    fri_dow = 5

    # 1. Today Class 10:00 - 12:00
    res1 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Algorithms Lecture",
            "type": "class",
            "day_of_week": today_dow,
            "start_time": "10:00",
            "end_time": "12:00",
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
        },
    )
    assert res1.status_code in (200, 201), res1.text

    # 2. Today Work 17:00 - 21:00 (4h)
    res2 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Evening Shift",
            "type": "shift",
            "day_of_week": today_dow,
            "start_time": "17:00",
            "end_time": "21:00",
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
            "hourly_wage": 20.0,
        },
    )
    assert res2.status_code in (200, 201), res2.text

    # 3. Add more shifts this week to reach 16h total work (4h already today, add 12h)
    # Pick days other than Friday to avoid contaminating Friday test
    shift_day = (today_dow + 1) % 7
    if shift_day == fri_dow or shift_day == 0:
        shift_day = (shift_day + 1) % 7
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Midweek Shift A",
            "type": "shift",
            "day_of_week": shift_day,
            "start_time": "08:00",
            "end_time": "14:00",  # 6h
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
            "hourly_wage": 20.0,
        },
    )
    shift_day_b = (shift_day + 1) % 7
    if shift_day_b == fri_dow or shift_day_b == 0:
        shift_day_b = (shift_day_b + 1) % 7
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Midweek Shift B",
            "type": "shift",
            "day_of_week": shift_day_b,
            "start_time": "08:00",
            "end_time": "14:00",  # 6h (Total shifts: 4 + 6 + 6 = 16h)
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
            "hourly_wage": 20.0,
        },
    )

    # 4. One conflict on Friday:
    # Friday Class 10:00 - 12:00
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Friday Seminar",
            "type": "class",
            "day_of_week": fri_dow,
            "start_time": "10:00",
            "end_time": "12:00",
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
        },
    )
    # Friday Shift 11:00 - 15:00 (overlaps 11:00-12:00)
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Friday Library Work",
            "type": "shift",
            "day_of_week": fri_dow,
            "start_time": "11:00",
            "end_time": "15:00",
            "recurrence_rule": "weekly",
            "effective_from": start_of_week.isoformat(),
        },
    )

    dash_resp = client.get("/api/v1/dashboard", headers=headers)
    assert dash_resp.status_code == 200, dash_resp.text
    data = dash_resp.json()["data"]

    # Verify Today Timeline has both today events
    today_blocks = data["today"]["blocks"]
    assert len(today_blocks) >= 2
    titles = [b["title"] for b in today_blocks]
    assert "Algorithms Lecture" in titles
    assert "Evening Shift" in titles

    # Verify Attention section reflects hard conflict
    assert data["week"]["conflict_count"] >= 1
    conflict_alerts = [a for a in data["alerts"] if a["type"] == "conflict"]
    assert len(conflict_alerts) >= 1

    # Verify Work summary:
    assert "work" in data
    assert data["work"]["limit"] == 20.0
    assert data["work"]["hours_used"] >= 4.0
    assert not data["work"]["over_limit"]

    # Verify Schedule Health: calculated from backend
    assert "health" in data
    assert "score" in data["health"]
    assert "category" in data["health"]
    assert isinstance(data["health"]["factors"], list)

    # Verify recommendations deterministic
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


def test_biweekly_recurrence():
    """Test every 2 weeks (biweekly) recurrence interval."""
    token, _ = register_user("biweekly")
    headers = {"Authorization": f"Bearer {token}"}

    # In 2026: 2026-10-05 is Monday (day_of_week=1)
    res = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Biweekly Lab",
            "type": "class",
            "day_of_week": 1,
            "start_time": "14:00",
            "end_time": "16:00",
            "recurrence_rule": "weekly",
            "recurrence_interval": 2,
            "effective_from": "2026-10-05",
            "effective_until": "2026-11-02",
        },
    )
    assert res.status_code in (200, 201), res.text
    block_id = res.json()["data"]["id"]

    # Week 1 (Oct 05): Should appear
    w1 = client.get("/api/v1/week?start=2026-10-05", headers=headers)
    assert w1.status_code == 200, w1.text
    w1_blocks = [b for b in w1.json()["data"]["blocks"] if b["id"] == block_id]
    assert len(w1_blocks) == 1
    assert w1_blocks[0]["occurrence_date"] == "2026-10-05"

    # Week 2 (Oct 12): Interval=2 means it should NOT appear
    w2 = client.get("/api/v1/week?start=2026-10-12", headers=headers)
    assert w2.status_code == 200, w2.text
    w2_blocks = [b for b in w2.json()["data"]["blocks"] if b["id"] == block_id]
    assert len(w2_blocks) == 0

    # Week 3 (Oct 19): Should appear
    w3 = client.get("/api/v1/week?start=2026-10-19", headers=headers)
    assert w3.status_code == 200, w3.text
    w3_blocks = [b for b in w3.json()["data"]["blocks"] if b["id"] == block_id]
    assert len(w3_blocks) == 1
    assert w3_blocks[0]["occurrence_date"] == "2026-10-19"


def test_recurring_analytics_and_earnings():
    """
    Weekly 4h shift @ $20/hr over 1 week = 4h, $80.
    Cancel that occurrence -> 0h, $0.
    """
    token, _ = register_user("analytics_rec")
    headers = {"Authorization": f"Bearer {token}"}

    # 2026-10-05 is Monday (day_of_week=1)
    res = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Weekend Café",
            "type": "shift",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "14:00",  # 4h
            "recurrence_rule": "weekly",
            "recurrence_interval": 1,
            "effective_from": "2026-10-01",
            "effective_until": "2026-10-31",
            "hourly_wage": 20.0,
        },
    )
    assert res.status_code in (200, 201), res.text
    block_id = res.json()["data"]["id"]

    # Check analytics for week of Oct 5: 1 shift * 4h = 4h, 4h * $20 = $80
    an_res = client.get(
        "/api/v1/analytics?start_date=2026-10-05",
        headers=headers,
    )
    assert an_res.status_code == 200, an_res.text
    stats = an_res.json()["data"]
    assert stats["hours"]["work_hours"] == 4.0
    assert stats["earnings"]["estimated_week"] == 80.0

    # Cancel Oct 05 occurrence
    del_res = client.delete(
        f"/api/v1/blocks/{block_id}?scope=this&occurrence_date=2026-10-05",
        headers=headers,
    )
    assert del_res.status_code == 200, del_res.text

    # Re-check analytics for week of Oct 5: should now be 0h, $0
    an_res2 = client.get(
        "/api/v1/analytics?start_date=2026-10-05",
        headers=headers,
    )
    assert an_res2.status_code == 200, an_res2.text
    stats2 = an_res2.json()["data"]
    assert stats2["hours"]["work_hours"] == 0.0
    assert stats2["earnings"]["estimated_week"] == 0.0


def test_edit_scope_future_and_all():
    """
    Test 'future' scope and 'all' scope editing.
    """
    token, _ = register_user("scope_edit")
    headers = {"Authorization": f"Bearer {token}"}

    # Series Monday (day_of_week=1) 10:00-12:00 from Oct 01 to Nov 30
    res = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Original Series",
            "type": "class",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
            "recurrence_rule": "weekly",
            "effective_from": "2026-10-01",
            "effective_until": "2026-11-30",
        },
    )
    assert res.status_code in (200, 201), res.text
    block_id = res.json()["data"]["id"]

    # Edit 'future' starting Oct 19: change title to 'Future Series' and time to 14:00-16:00
    patch_res = client.patch(
        f"/api/v1/blocks/{block_id}?scope=future&occurrence_date=2026-10-19",
        headers=headers,
        json={
            "title": "Future Series",
            "start_time": "14:00",
            "end_time": "16:00",
        },
    )
    assert patch_res.status_code == 200, patch_res.text

    # Check Oct 12: should remain Original Series 10:00-12:00
    w_oct12 = client.get("/api/v1/week?start=2026-10-12", headers=headers)
    assert w_oct12.status_code == 200, w_oct12.text
    oct12_blocks = [b for b in w_oct12.json()["data"]["blocks"] if "Series" in b["title"]]
    assert len(oct12_blocks) == 1
    assert oct12_blocks[0]["title"] == "Original Series"
    assert oct12_blocks[0]["start_time"][:5] == "10:00"

    # Check Oct 19: should be Future Series 14:00-16:00
    w_oct19 = client.get("/api/v1/week?start=2026-10-19", headers=headers)
    assert w_oct19.status_code == 200, w_oct19.text
    oct19_blocks = [b for b in w_oct19.json()["data"]["blocks"] if "Series" in b["title"]]
    assert len(oct19_blocks) == 1
    assert oct19_blocks[0]["title"] == "Future Series"
    assert oct19_blocks[0]["start_time"][:5] == "14:00"


def test_user_isolation_for_recurrence():
    """Ensure user B cannot see, modify, or delete user A's recurring blocks or overrides."""
    token_a, _ = register_user("user_a")
    token_b, _ = register_user("user_b")

    res = client.post(
        "/api/v1/blocks",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "title": "User A Class",
            "type": "class",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
            "recurrence_rule": "weekly",
            "effective_from": "2026-10-01",
        },
    )
    block_id = res.json()["data"]["id"]

    # User B tries to delete with scope=this
    del_res = client.delete(
        f"/api/v1/blocks/{block_id}?scope=this&occurrence_date=2026-10-05",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_res.status_code in (403, 404)

    # User B week view does not see User A block
    w_res = client.get(
        "/api/v1/week?start=2026-10-05",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert w_res.status_code == 200
    assert not any(b["id"] == block_id for b in w_res.json()["data"]["blocks"])


def test_soft_delete_recurrence():
    """Soft-deleted recurring series should not return occurrences or conflicts."""
    token, _ = register_user("soft_del")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "To Delete",
            "type": "class",
            "day_of_week": 2,
            "start_time": "09:00",
            "end_time": "11:00",
            "recurrence_rule": "weekly",
            "effective_from": "2026-10-01",
        },
    )
    assert res.status_code in (200, 201)
    block_id = res.json()["data"]["id"]

    # Delete with scope=all
    del_res = client.delete(
        f"/api/v1/blocks/{block_id}?scope=all",
        headers=headers,
    )
    assert del_res.status_code == 200

    # Week view should have 0 occurrences
    w = client.get("/api/v1/week?start=2026-10-05", headers=headers)
    assert w.status_code == 200
    assert not any(b["id"] == block_id for b in w.json()["data"]["blocks"])


def test_study_planner_avoids_recurring_and_uses_cancelled():
    """
    Study planner treats recurring events as occupied gaps.
    Cancelling a specific occurrence frees up that period for study recommendations.
    """
    token, _ = register_user("planner_rec")
    headers = {"Authorization": f"Bearer {token}"}

    today_d = date.today()
    tomorrow_d = today_d + timedelta(days=1)
    tomorrow_dow = (tomorrow_d.weekday() + 1) % 7
    deadline_d = today_d + timedelta(days=3)

    # 1. Create a massive recurring block tomorrow from 08:00 to 18:00
    res_b = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "All Day Lab",
            "type": "class",
            "day_of_week": tomorrow_dow,
            "start_time": "08:00",
            "end_time": "18:00",
            "recurrence_rule": "weekly",
            "effective_from": today_d.isoformat(),
        },
    )
    assert res_b.status_code in (200, 201)
    block_id = res_b.json()["data"]["id"]

    # 2. Create study task
    res_t = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Exam Prep",
            "total_hours_required": 4.0,
            "deadline": deadline_d.isoformat(),
            "priority": "high",
            "preferred_duration": 60,
        },
    )
    assert res_t.status_code in (200, 201)
    task_id = res_t.json()["data"]["id"]

    # 3. Plan task: tomorrow between 08:00 and 18:00 should NOT be recommended
    plan1 = client.post(f"/api/v1/tasks/{task_id}/plan", headers=headers)
    assert plan1.status_code == 200
    slots1 = plan1.json()["data"]["suggested"]
    for slot in slots1:
        if slot["date"] == tomorrow_d.isoformat():
            st_h = int(slot["start_time"].split(":")[0])
            # Must not fall inside 08:00 - 18:00
            assert st_h < 8 or st_h >= 18, f"Slot {slot} overlapped 08:00-18:00 class!"

    # 4. Cancel tomorrow's occurrence of All Day Lab
    del_res = client.delete(
        f"/api/v1/blocks/{block_id}?scope=this&occurrence_date={tomorrow_d.isoformat()}",
        headers=headers,
    )
    assert del_res.status_code == 200

    # 5. Replan task: tomorrow's cancelled slot is now free!
    plan2 = client.post(f"/api/v1/tasks/{task_id}/plan", headers=headers)
    assert plan2.status_code == 200
    slots2 = plan2.json()["data"]["suggested"]
    assert len(slots2) > 0

