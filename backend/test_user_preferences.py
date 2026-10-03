"""Regression coverage for preference persistence, validation, and account isolation."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.user_preference import UserPreference


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Keep isolated state if needed


def test_user_preferences_defaults_and_patch():
    client = TestClient(app)
    # Register user 1
    r1 = client.post("/api/v1/auth/register", json={"email": "pref1@example.com", "password": "Password123!"})
    assert r1.status_code == 200
    token1 = r1.json()["data"]["token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    # Verify defaults
    me1 = client.get("/api/v1/auth/me", headers=h1).json()["data"]
    assert me1["week_starts_on"] == "monday"
    assert me1["time_format"] == "12h"
    assert me1["default_calendar_view"] == "week"
    assert me1["reduced_motion"] == "system"
    assert me1["planning_hours_start"] == 9
    assert me1["planning_hours_end"] == 18
    assert me1["preferred_session_duration"] == 45
    assert me1["preferred_break_duration"] == 15

    # Update preferences
    patch1 = client.patch(
        "/api/v1/auth/me",
        headers=h1,
        json={
            "week_starts_on": "sunday",
            "time_format": "24h",
            "default_calendar_view": "day",
            "reduced_motion": "reduced",
            "planning_hours_start": 8,
            "planning_hours_end": 16,
            "preferred_session_duration": 60,
            "preferred_break_duration": 20,
        },
    )
    assert patch1.status_code == 200
    data1 = patch1.json()["data"]
    assert data1["week_starts_on"] == "sunday"
    assert data1["time_format"] == "24h"
    assert data1["default_calendar_view"] == "day"
    assert data1["reduced_motion"] == "reduced"
    assert data1["planning_hours_start"] == 8
    assert data1["planning_hours_end"] == 16
    assert data1["preferred_session_duration"] == 60
    assert data1["preferred_break_duration"] == 20


def test_user_preferences_account_isolation():
    client = TestClient(app)
    # Register user A
    r_a = client.post("/api/v1/auth/register", json={"email": "isolated_a@example.com", "password": "Password123!"})
    token_a = r_a.json()["data"]["token"]
    h_a = {"Authorization": f"Bearer {token_a}"}

    # Register user B
    r_b = client.post("/api/v1/auth/register", json={"email": "isolated_b@example.com", "password": "Password123!"})
    token_b = r_b.json()["data"]["token"]
    h_b = {"Authorization": f"Bearer {token_b}"}

    # User A updates to 24h & sunday
    client.patch("/api/v1/auth/me", headers=h_a, json={"time_format": "24h", "week_starts_on": "sunday"})

    # User B should still see defaults and NOT User A's preferences
    me_b = client.get("/api/v1/auth/me", headers=h_b).json()["data"]
    assert me_b["time_format"] == "12h"
    assert me_b["week_starts_on"] == "monday"


def test_user_preferences_validation():
    client = TestClient(app)
    r = client.post("/api/v1/auth/register", json={"email": "val_user@example.com", "password": "Password123!"})
    token = r.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid week_starts_on
    res_week = client.patch("/api/v1/auth/me", headers=headers, json={"week_starts_on": "wednesday"})
    assert res_week.status_code == 422

    # Invalid time_format
    res_time = client.patch("/api/v1/auth/me", headers=headers, json={"time_format": "48h"})
    assert res_time.status_code == 422

    # Invalid planning hours: start > end
    res_hours = client.patch("/api/v1/auth/me", headers=headers, json={"planning_hours_start": 18, "planning_hours_end": 9})
    assert res_hours.status_code == 400
    err_body = res_hours.json()
    code = err_body.get("error", {}).get("code") or err_body.get("detail", {}).get("code")
    assert code == "validation_error"
