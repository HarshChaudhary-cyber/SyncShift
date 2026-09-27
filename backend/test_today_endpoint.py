from fastapi.testclient import TestClient
from app.main import app

import pytest
from datetime import date, time
from app.main import app
from app.dependencies import get_current_user, CurrentUser
from app.database import SessionLocal
from app.models.time_block import TimeBlock, BlockType
from app.models.user import User


@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=1, email="test_user@example.com")
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Isolated sample data fixture
# ---------------------------------------------------------------------------
# conftest.py creates user_id=1 and seeds two Monday blocks at session scope
# so that *other* test files that rely on the fixture owner also work.  We
# create the same blocks here with a function scope so that
# test_today_endpoint_specific_date always has exactly the data it needs,
# regardless of test ordering or whether the session-scoped fixture ran first.
# The idempotency guard (query-before-insert) prevents duplicate rows.

@pytest.fixture
def monday_sample_blocks():
    """Ensure the two Monday blocks required by the specific-date test exist."""
    db = SessionLocal()
    try:
        if db.get(User, 1) is None:
            db.add(User(id=1, email="fixture-owner@example.test", name="Fixture owner"))
            db.flush()

        has_shift = db.query(TimeBlock).filter(
            TimeBlock.user_id == 1,
            TimeBlock.title == "Library Desk",
            TimeBlock.day_of_week == 1,
            TimeBlock.deleted == False,
        ).first()
        if not has_shift:
            db.add(TimeBlock(
                user_id=1,
                title="Library Desk",
                type=BlockType.SHIFT,
                day_of_week=1,
                start_time=time(10, 0),
                end_time=time(14, 0),
                duration_minutes=240,
                hourly_wage=17.50,
                effective_from=date(2026, 9, 1),
                is_flexible=True,
                deleted=False,
            ))

        has_class = db.query(TimeBlock).filter(
            TimeBlock.user_id == 1,
            TimeBlock.title.like("%CS 210%"),
            TimeBlock.day_of_week == 1,
            TimeBlock.deleted == False,
        ).first()
        if not has_class:
            db.add(TimeBlock(
                user_id=1,
                title="CS 210: Data Structures",
                type=BlockType.CLASS,
                day_of_week=1,
                start_time=time(9, 0),
                end_time=time(10, 30),
                duration_minutes=90,
                effective_from=date(2026, 9, 1),
                deleted=False,
            ))

        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}


def test_today_endpoint_unauthorized():
    resp = client.get("/api/v1/today")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert err["code"] == "unauthorized"


def test_today_endpoint_authenticated(override_auth):
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


def test_today_endpoint_specific_date(override_auth, monday_sample_blocks):
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


def test_today_endpoint_empty_day(override_auth):
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
