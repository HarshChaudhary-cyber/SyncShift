"""
test_planner_preferences_integration.py
Demonstrates that changing planning preferences (planning_hours_start/end,
preferred_session_duration, preferred_break_duration) directly changes generated plans.
"""
from datetime import date, timedelta
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.store import create_task_in_store, add_block_to_store

client = TestClient(app)


def setup_planner_user(prefix="plan_pref"):
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": 20.0,
            "name": f"Planner User {uid}",
            "minimum_transition_minutes": 15,
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    user_id = resp.json()["data"]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


def test_planning_hours_window_constrains_generated_sessions():
    """
    Demonstrates that planning_hours_start and planning_hours_end strictly bound
    the generated study sessions.
    """
    headers, user_id = setup_planner_user("window_test")

    # Set user planning window to Afternoon only: 14:00 (2 PM) to 18:00 (6 PM)
    patch_res = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "planning_hours_start": 14,
            "planning_hours_end": 18,
            "preferred_session_duration": 60,
        },
    )
    assert patch_res.status_code == 200, patch_res.text
    profile = patch_res.json()["data"]
    assert profile["planning_hours_start"] == 14
    assert profile["planning_hours_end"] == 18

    # Create a study task needing 2 hours
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()))
    client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Quantum Mechanics Problem Set",
            "total_hours_required": 2.0,
            "deadline": (next_monday + timedelta(days=5)).isoformat(),
            "priority": "high",
        },
    )

    # Preview smart plan
    preview_res = client.post(
        "/api/v1/students/me/planning/preview",
        headers=headers,
        json={"target_week_start": next_monday.isoformat()},
    )
    assert preview_res.status_code == 200, preview_res.text
    options = preview_res.json()["data"]["options"]
    assert len(options) > 0

    # Verify that EVERY proposed slot in feasible options starts >= 14:00 and ends <= 18:00
    found_any_slots = False
    for opt in options:
        if opt.get("summary", {}).get("is_valid", True) and opt.get("added_blocks"):
            for slot in opt["added_blocks"]:
                found_any_slots = True
                st_hour = int(slot["start_time"].split(":")[0])
                et_hour = int(slot["end_time"].split(":")[0])
                et_min = int(slot["end_time"].split(":")[1])
                assert st_hour >= 14, f"Slot started too early: {slot['start_time']} (expected >= 14:00)"
                assert (et_hour < 18 or (et_hour == 18 and et_min == 0)), f"Slot ended too late: {slot['end_time']} (expected <= 18:00)"

    assert found_any_slots, "At least one plan option should have generated slots within 14:00-18:00"


def test_preferred_session_duration_changes_slot_lengths():
    """
    Demonstrates that changing preferred_session_duration in Settings directly changes
    the length of planned sessions.
    """
    headers, user_id = setup_planner_user("duration_test")
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()))

    # Case A: 30-minute sessions
    client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "preferred_session_duration": 30,
            "planning_hours_start": 9,
            "planning_hours_end": 17,
        },
    )

    client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Short Session Task",
            "total_hours_required": 2.0,
            "deadline": (next_monday + timedelta(days=4)).isoformat(),
            "priority": "medium",
        },
    )

    preview_30 = client.post(
        "/api/v1/students/me/planning/preview",
        headers=headers,
        json={"target_week_start": next_monday.isoformat()},
    )
    assert preview_30.status_code == 200
    balanced_30 = next(o for o in preview_30.json()["data"]["options"] if o["id"] == "balanced")
    durations_30 = [round(s["duration_hours"] * 60) for s in balanced_30["added_blocks"]]
    assert all(d <= 45 for d in durations_30), f"Expected 30m target sessions, got {durations_30}"

    # Case B: Update Settings to 90-minute sessions
    client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"preferred_session_duration": 90},
    )

    preview_90 = client.post(
        "/api/v1/students/me/planning/preview",
        headers=headers,
        json={"target_week_start": next_monday.isoformat()},
    )
    assert preview_90.status_code == 200
    balanced_90 = next(o for o in preview_90.json()["data"]["options"] if o["id"] == "balanced")
    durations_90 = [round(s["duration_hours"] * 60) for s in balanced_90["added_blocks"]]
    assert any(d >= 60 for d in durations_90), f"Expected longer sessions for 90m target, got {durations_90}"


def test_preferred_break_duration_enforces_spacing_between_sessions():
    """
    Demonstrates that preferred_break_duration enforces minimum spacing between
    consecutive study sessions on the same day.
    """
    headers, user_id = setup_planner_user("break_test")
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()))

    # Set 30-minute break buffer in Settings
    client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "preferred_session_duration": 45,
            "preferred_break_duration": 30,
            "planning_hours_start": 9,
            "planning_hours_end": 17,
        },
    )

    # 4 hours of study required to generate multiple sessions
    client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Heavy Reading Assignment",
            "total_hours_required": 4.0,
            "deadline": (next_monday + timedelta(days=5)).isoformat(),
            "priority": "high",
        },
    )

    preview = client.post(
        "/api/v1/students/me/planning/preview",
        headers=headers,
        json={"target_week_start": next_monday.isoformat()},
    )
    assert preview.status_code == 200
    options = preview.json()["data"]["options"]

    # Verify spacing between consecutive slots on the same date
    for opt in options:
        slots_by_date = {}
        for s in opt["added_blocks"]:
            d_str = s["date"]
            slots_by_date.setdefault(d_str, []).append(s)

        for d_str, day_slots in slots_by_date.items():
            if len(day_slots) > 1:
                sorted_slots = sorted(day_slots, key=lambda x: x["start_time"])
                for i in range(len(sorted_slots) - 1):
                    s1_end = int(sorted_slots[i]["end_time"].split(":")[0]) * 60 + int(sorted_slots[i]["end_time"].split(":")[1])
                    s2_start = int(sorted_slots[i+1]["start_time"].split(":")[0]) * 60 + int(sorted_slots[i+1]["start_time"].split(":")[1])
                    gap = s2_start - s1_end
                    assert gap >= 30, f"Break gap {gap}m on {d_str} is smaller than preferred 30m break"
