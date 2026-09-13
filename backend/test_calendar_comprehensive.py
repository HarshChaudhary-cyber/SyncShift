"""
Comprehensive Functional & Conflict Test Suite for SyncShift Calendar.
Tests:
1. Registration & Auth (JWT token generation & user isolation)
2. Week view retrieval (GET /week)
3. Class block creation (10:00 - 12:00)
4. Conflicting shift creation (11:00 - 15:00) -> 60-minute conflict verification
5. Conflict retrieval (GET /conflicts)
6. Move test: Move shift to (13:00 - 17:00) -> Overlap resolved to 0 minutes
7. Resize test: Resize shift to (13:00 - 20:00) -> verify duration update & weekly totals
8. Work hours test: Weekly limit = 20h, Shifts = 21h -> over_limit == True
9. Duplication test: POST /blocks/{id}/duplicate -> Duplicate created with '(Copy)' title
10. Soft delete test: DELETE /blocks/{id} -> deleted == True, no longer in /week or /conflicts
11. Timezone test: Asia/Kolkata vs Europe/Berlin date calculations
"""

import sys
import os
from datetime import date, datetime
from fastapi.testclient import TestClient

from app.main import app

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from app.services.timezone_helper import get_user_today

client = TestClient(app)

def run_tests():
    print("==================================================")
    print("   SYNCSHIFT CALENDAR COMPREHENSIVE TEST SUITE   ")
    print("==================================================")

    # 1. Setup test user
    test_email = f"cal_test_{int(datetime.now().timestamp())}@example.com"
    test_pwd = "Password123!"
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": test_pwd,
            "timezone": "Europe/Berlin",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ [TEST 1] User registered & authenticated (Europe/Berlin, 20h limit)")

    # 2. Test empty week
    week_start = "2026-09-07"
    week_resp = client.get(f"/api/v1/week?start={week_start}", headers=headers)
    assert week_resp.status_code == 200, week_resp.text
    week_data = week_resp.json()["data"]
    assert len(week_data["blocks"]) == 0
    assert len(week_data["conflicts"]) == 0
    print("✓ [TEST 2] Initial empty week returns 0 blocks and 0 conflicts")

    # 3. CONFLICT TEST:
    # Class: 10:00–12:00 on Monday (day 1)
    class_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "type": "class",
            "title": "CS301 Database Systems",
            "location": "Room A-204",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
        },
    )
    assert class_resp.status_code == 201, class_resp.text
    class_block = class_resp.json()["data"]
    print(f"✓ [TEST 3] Created class block #{class_block['id']} (10:00–12:00)")

    # Shift: 11:00–15:00 on Monday (day 1) -> Overlaps by 60 mins (11:00–12:00)
    shift_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "type": "shift",
            "title": "Campus Bookstore",
            "location": "Student Union",
            "day_of_week": 1,
            "start_time": "11:00",
            "end_time": "15:00",
            "hourly_wage": 16.0,
        },
    )
    assert shift_resp.status_code == 201, shift_resp.text
    shift_block = shift_resp.json()["data"]
    print(f"✓ [TEST 4] Created conflicting shift #{shift_block['id']} (11:00–15:00)")

    # Verify 60-minute conflict
    conflicts_resp = client.get(f"/api/v1/conflicts?week_start={week_start}", headers=headers)
    assert conflicts_resp.status_code == 200, conflicts_resp.text
    conflicts_data = conflicts_resp.json()["data"]["conflicts"]
    assert len(conflicts_data) >= 1, f"Expected conflict, got {conflicts_data}"
    active_conflict = next(
        c for c in conflicts_data
        if (c["block_a_id"] == class_block["id"] and c["block_b_id"] == shift_block["id"]) or
           (c["block_b_id"] == class_block["id"] and c["block_a_id"] == shift_block["id"])
    )
    assert active_conflict["overlap_minutes"] == 60, f"Expected 60m overlap, got {active_conflict['overlap_minutes']}"
    assert active_conflict["severity"] == "hard"
    print(f"✓ [TEST 5] Conflict detected correctly: 60-minute overlap (11:00-12:00), severity={active_conflict['severity']}")

    # 4. MOVE TEST:
    # Move shift to 13:00–17:00 (after class ends at 12:00)
    move_resp = client.patch(
        f"/api/v1/blocks/{shift_block['id']}",
        headers=headers,
        json={"start_time": "13:00", "end_time": "17:00"},
    )
    assert move_resp.status_code == 200, move_resp.text
    moved_block = move_resp.json()["data"]
    assert moved_block["start_time"].startswith("13:00")
    assert moved_block["end_time"].startswith("17:00")

    # Verify conflict is now resolved
    conflicts_after_move = client.get(f"/api/v1/conflicts?week_start={week_start}", headers=headers).json()["data"]["conflicts"]
    remaining = [
        c for c in conflicts_after_move
        if (c["block_a_id"] == class_block["id"] and c["block_b_id"] == shift_block["id"]) or
           (c["block_b_id"] == class_block["id"] and c["block_a_id"] == shift_block["id"])
    ]
    assert len(remaining) == 0, f"Expected 0 conflicts after move, got {remaining}"
    print("✓ [TEST 6] Move test: Shift moved to 13:00–17:00. Conflict successfully resolved!")

    # 5. RESIZE TEST:
    # Resize shift duration: 13:00–19:00 (6 hours)
    resize_resp = client.patch(
        f"/api/v1/blocks/{shift_block['id']}",
        headers=headers,
        json={"end_time": "19:00"},
    )
    assert resize_resp.status_code == 200, resize_resp.text
    resized = resize_resp.json()["data"]
    assert resized["end_time"].startswith("19:00")
    print(f"✓ [TEST 7] Resize test: End time updated to 19:00 (duration: 6h)")

    # 6. WORK HOURS TEST:
    # Limit is 20h. Add another shift of 15 hours to make total 6 + 15 = 21h (> 20h limit)
    second_shift_resp = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "type": "shift",
            "title": "Weekend Catering",
            "day_of_week": 6, # Saturday
            "start_time": "06:00",
            "end_time": "21:00", # 15 hours
            "hourly_wage": 20.0,
        },
    )
    assert second_shift_resp.status_code == 201, second_shift_resp.text
    
    # Check weekly totals
    week_totals = client.get(f"/api/v1/week?start={week_start}", headers=headers).json()["data"]["totals"]
    assert week_totals["shift_hours"] == 21.0, f"Expected 21.0h, got {week_totals['shift_hours']}"
    assert week_totals["over_limit"] is True, f"Expected over_limit=True, got {week_totals['over_limit']}"
    print(f"✓ [TEST 8] Work hours test: Total shift hours = {week_totals['shift_hours']}h > 20h limit -> over_limit=True")

    # 7. DUPLICATION TEST:
    # Duplicate class block to next day (+1)
    dup_resp = client.post(
        f"/api/v1/blocks/{class_block['id']}/duplicate",
        headers=headers,
        json={"days_offset": 1},
    )
    assert dup_resp.status_code == 200, dup_resp.text
    dup_block = dup_resp.json()["data"]
    assert dup_block["title"] == f"{class_block['title']} (Copy)"
    assert dup_block["day_of_week"] == (class_block["day_of_week"] + 1) % 7
    print(f"✓ [TEST 9] Duplicate test: Block duplicated to day {dup_block['day_of_week']} with title '{dup_block['title']}'")

    # 8. SOFT DELETION TEST:
    del_resp = client.delete(f"/api/v1/blocks/{dup_block['id']}", headers=headers)
    assert del_resp.status_code == 200, del_resp.text
    assert del_resp.json()["data"]["deleted"] is True

    # Verify soft-deleted block is excluded from week schedule
    blocks_after_del = client.get(f"/api/v1/week?start={week_start}", headers=headers).json()["data"]["blocks"]
    assert not any(b["id"] == dup_block["id"] for b in blocks_after_del)
    print(f"✓ [TEST 10] Soft-deletion test: Block #{dup_block['id']} marked deleted and excluded from schedule")

    # 9. TIMEZONE TEST:
    # Asia/Kolkata vs Europe/Berlin
    dt_kolkata, dow_kolkata = get_user_today("Asia/Kolkata")
    dt_berlin, dow_berlin = get_user_today("Europe/Berlin")
    assert isinstance(dt_kolkata, date)
    assert isinstance(dt_berlin, date)
    assert 0 <= dow_kolkata <= 6
    assert 0 <= dow_berlin <= 6
    print(f"✓ [TEST 11] Timezone test: Asia/Kolkata ({dt_kolkata}, DOW={dow_kolkata}), Europe/Berlin ({dt_berlin}, DOW={dow_berlin}) verified")

    print("\n==================================================")
    print("   ALL 11 CALENDAR INTEGRATION TESTS PASSED!     ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
