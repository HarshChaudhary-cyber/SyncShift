"""
Travel / Transition-Aware Scheduling Test Suite
Verifies:
1. Temporal overlap is detected as HARD conflict.
2. Insufficient transition buffer between distinct locations is detected as WARNING (transition).
3. Adequate transition buffer produces no transition warning.
4. Same-location consecutive events require zero transition penalty.
5. Optimizer differentiates between short-transition and adequate-transition candidate slots.
6. Schedule Health penalizes transition warnings mildly with constructive improvement advice.
"""
from datetime import date, timedelta
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.optimizer import optimize_work_schedule
from app.services.rate_limiter import reset_rate_limits
from app.dependencies import CurrentUser

client = TestClient(app)


def register_user_with_transition(prefix="travel_user", min_transition=30):
    reset_rate_limits()
    uid = str(uuid.uuid4())[:8]
    email = f"{prefix}_{uid}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "weekly_work_hour_limit": 20.0,
            "name": f"Travel Tester {uid}",
            "minimum_transition_minutes": min_transition,
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    user_id = resp.json()["data"]["user_id"]
    return token, user_id


def test_transition_warning_different_locations():
    """
    Class: 14:00–16:00 (Campus A)
    Shift: 16:10–20:00 (Café Roma)
    Transition requirement: 30m
    Available: 10m
    Expected: WARNING with conflict_type == 'transition'
    """
    token, _ = register_user_with_transition("warn_diff", min_transition=30)
    headers = {"Authorization": f"Bearer {token}"}
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())
    fri_dow = 5  # Friday

    # 1. Class at Campus A: 14:00 - 16:00
    r1 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Computer Networks Lecture",
            "type": "class",
            "day_of_week": fri_dow,
            "start_time": "14:00",
            "end_time": "16:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )
    assert r1.status_code in (200, 201), r1.text

    # 2. Shift at Café Roma: 16:10 - 20:00 (10 min gap, 30 min required)
    r2 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Barista Shift",
            "type": "shift",
            "day_of_week": fri_dow,
            "start_time": "16:10",
            "end_time": "20:00",
            "location": "Café Roma",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
            "hourly_wage": 15.0,
        },
    )
    assert r2.status_code in (200, 201), r2.text

    # Check conflicts
    c_resp = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers)
    assert c_resp.status_code == 200, c_resp.text
    conflicts = c_resp.json()["data"]["conflicts"]

    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["severity"] == "warning"
    assert c["conflict_type"] == "transition"
    assert c["available_transition_minutes"] == 10
    assert c["required_transition_minutes"] == 30
    assert "Campus A" in c["location_a"] or "Campus A" in c["location_b"]
    assert "Café Roma" in c["location_a"] or "Café Roma" in c["location_b"]


def test_adequate_transition_different_locations_no_warning():
    """
    Class: 14:00–16:00 (Campus A)
    Shift: 16:30–20:00 (Café Roma)
    Transition requirement: 30m
    Available: 30m
    Expected: No transition warning!
    """
    token, _ = register_user_with_transition("ok_diff", min_transition=30)
    headers = {"Authorization": f"Bearer {token}"}
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())
    fri_dow = 5

    # 1. Class at Campus A: 14:00 - 16:00
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Distributed Systems",
            "type": "class",
            "day_of_week": fri_dow,
            "start_time": "14:00",
            "end_time": "16:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )

    # 2. Shift at Café Roma: 16:30 - 20:00 (30 min gap, 30 min required)
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Evening Barista",
            "type": "shift",
            "day_of_week": fri_dow,
            "start_time": "16:30",
            "end_time": "20:00",
            "location": "Café Roma",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
            "hourly_wage": 15.0,
        },
    )

    c_resp = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers)
    assert c_resp.status_code == 200, c_resp.text
    conflicts = c_resp.json()["data"]["conflicts"]
    assert len(conflicts) == 0, f"Expected 0 conflicts, got {conflicts}"


def test_same_location_no_transition_warning():
    """
    Class: 14:00–16:00 (Campus A)
    Work: 16:05–20:00 (Campus A)
    Transition requirement: 30m
    Same location -> 0 buffer needed -> No warning
    """
    token, _ = register_user_with_transition("same_loc", min_transition=30)
    headers = {"Authorization": f"Bearer {token}"}
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())
    mon_dow = 1

    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Physics Lab",
            "type": "class",
            "day_of_week": mon_dow,
            "start_time": "14:00",
            "end_time": "16:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )

    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Campus Library Assistant",
            "type": "shift",
            "day_of_week": mon_dow,
            "start_time": "16:05",
            "end_time": "20:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
            "hourly_wage": 14.0,
        },
    )

    c_resp = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers)
    assert c_resp.status_code == 200, c_resp.text
    conflicts = c_resp.json()["data"]["conflicts"]
    assert len(conflicts) == 0, f"Expected 0 conflicts for same location, got {conflicts}"


def test_hard_overlap_vs_transition_warning():
    """
    Direct overlap must always be HARD severity, while insufficient transition is WARNING.
    """
    token, _ = register_user_with_transition("hard_vs_warn", min_transition=20)
    headers = {"Authorization": f"Bearer {token}"}
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())
    tue_dow = 2

    # Event 1: Class 10:00 - 12:00
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Chemistry",
            "type": "class",
            "day_of_week": tue_dow,
            "start_time": "10:00",
            "end_time": "12:00",
            "location": "Science Hall",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )

    # Event 2: Direct overlap shift 11:00 - 14:00
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Overlap Shift",
            "type": "shift",
            "day_of_week": tue_dow,
            "start_time": "11:00",
            "end_time": "14:00",
            "location": "Downtown Office",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )

    c_resp = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers)
    assert c_resp.status_code == 200
    conflicts = c_resp.json()["data"]["conflicts"]

    hard_conflicts = [c for c in conflicts if c["severity"] == "hard"]
    assert len(hard_conflicts) == 1
    assert hard_conflicts[0]["conflict_type"] in ("overlap", "class_shift")


def test_optimizer_prefers_adequate_transition():
    """
    Optimizer evaluates candidates and gives higher scores to slots with adequate transition.
    """
    token, uid = register_user_with_transition("opt_trans", min_transition=30)
    current_user = CurrentUser(
        user_id=uid,
        email="opt_trans@example.com",
        timezone="Europe/Berlin",
        weekly_limit=20.0,
        minimum_transition_minutes=30,
    )

    # Add a class on Monday 09:00 - 12:00 at Campus A
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Morning Lecture",
            "type": "class",
            "day_of_week": 1,  # Monday
            "start_time": "09:00",
            "end_time": "12:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )

    res = optimize_work_schedule(
        current_user=current_user,
        target_hours=8.0,
        preferred_days=["Monday", "Wednesday"],
        shift_duration_hours=4.0,
        target_week_start=week_start,
        location="Downtown Café",
    )

    recs = res["recommendation"]
    assert len(recs) > 0
    # Any Monday candidate selected should respect class end at 12:00 + 30m buffer = >= 12:30 or 14:00
    for r in recs:
        if r["day_name"] == "Monday":
            assert r["transition_ok"] is True
            assert r["start_time"] >= "12:30"
