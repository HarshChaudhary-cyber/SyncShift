"""
Focused tests for the effective_from default in block creation.

Issue: blocks.py and store.py previously used a hardcoded date(2026, 9, 1) as
the effective_from fallback when the client did not supply one.  This caused
any block created without an explicit start date to be invisible to queries
before September 2026 and introduced silent data-quality bugs for users in
other academic calendars.

The correct behaviour is to default to the server's current date so a new
block is immediately active.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}


@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=999, email="blocks_test@example.com"
    )
    yield
    app.dependency_overrides.clear()


class TestEffectiveFromDefault:
    """effective_from should default to today, not a hardcoded historical date."""

    def test_create_block_without_effective_from_defaults_to_today(self, override_auth):
        """When effective_from is omitted, the API should return today's date."""
        resp = client.post(
            "/api/v1/blocks",
            headers=AUTH_HEADER,
            json={
                "type": "class",
                "title": "No-date lecture",
                "day_of_week": 3,
                "start_time": "14:00:00",
                "end_time": "15:30:00",
            },
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()["data"]

        effective_from = date.fromisoformat(data["effective_from"])
        today = date.today()

        assert effective_from == today

    def test_create_block_with_explicit_effective_from_is_preserved(self, override_auth):
        """When an explicit effective_from is supplied it must be stored as-is."""
        explicit_date = "2025-01-15"
        resp = client.post(
            "/api/v1/blocks",
            headers=AUTH_HEADER,
            json={
                "type": "shift",
                "title": "Explicit-date shift",
                "day_of_week": 4,
                "start_time": "09:00:00",
                "end_time": "13:00:00",
                "effective_from": explicit_date,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()["data"]
        assert data["effective_from"] == explicit_date, (
            f"effective_from should be preserved as {explicit_date}, got {data['effective_from']}"
        )

    def test_create_block_future_effective_from_is_preserved(self, override_auth):
        """A future effective_from (e.g. semester start) must be stored correctly."""
        future_date = "2027-01-20"
        resp = client.post(
            "/api/v1/blocks",
            headers=AUTH_HEADER,
            json={
                "type": "class",
                "title": "Future semester block",
                "day_of_week": 1,
                "start_time": "10:00:00",
                "end_time": "11:30:00",
                "effective_from": future_date,
            },
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()["data"]
        assert data["effective_from"] == future_date, (
            f"effective_from should be {future_date}, got {data['effective_from']}"
        )
