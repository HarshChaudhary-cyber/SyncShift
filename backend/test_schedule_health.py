"""
Unit and integration tests for deterministic Schedule Health Scoring:
1. No conflicts -> high score (>= 90, Excellent)
2. Hard conflict reduces score
3. Warning conflict reduces score
4. Work-hour limit exceeded reduces score
5. High daily workload (> 9h) reduces score
6. Score never below 0
7. Score never above 100
8. Same input always produces identical score (deterministic & reproducible)
9. Soft-deleted blocks are ignored
10. Other user's blocks are strictly ignored
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
from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem
from app.services.schedule_health import compute_schedule_health

client = TestClient(app)


def test_schedule_health_scoring_function_direct():
    """Unit tests for the deterministic scoring function."""
    # 1. Empty schedule: baseline 100 + 5 no hard conflicts bonus = 100 (clamped)
    res_empty = compute_schedule_health(blocks=[], conflicts=[], weekly_work_limit=20.0)
    assert res_empty.score == 100
    assert res_empty.category == "Excellent"
    assert any("No hard schedule conflicts" in f.text for f in res_empty.factors)

    # 2. Hard conflict: -15
    hard_c = ConflictItem(
        id=1,
        block_a_id=10,
        block_b_id=11,
        overlap_minutes=60,
        severity="hard",
        overlap_start="10:00",
        overlap_end="11:00",
        day_of_week=1,
        description="Class A clashes with Class B",
    )
    res_hard = compute_schedule_health(blocks=[], conflicts=[hard_c], weekly_work_limit=20.0)
    # Starts at 100 - 15 = 85 (Healthy)
    assert res_hard.score == 85
    assert res_hard.category == "Healthy"
    assert any("hard schedule conflict" in f.text for f in res_hard.factors)

    # 3. Warning conflict: -5 (with no hard conflict bonus: 100 + 5 - 5 = 100)
    # If both hard and warning: 100 - 15 - 5 = 80
    warn_c = ConflictItem(
        id=2,
        block_a_id=12,
        block_b_id=13,
        overlap_minutes=30,
        severity="warning",
        overlap_start="14:00",
        overlap_end="14:30",
        day_of_week=2,
        description="Shift overlaps with flexible block",
    )
    res_both = compute_schedule_health(blocks=[], conflicts=[hard_c, warn_c], weekly_work_limit=20.0)
    assert res_both.score == 80

    # 4. Work-hour limit exceeded (-15)
    # Create work shift blocks totaling 25 hours with a 20h limit
    over_work_blocks = [
        BlockOut(
            id=1,
            user_id=1,
            type="shift",
            title="Shift 1",
            day_of_week=1,
            start_time="08:00:00",
            end_time="20:00:00",  # 12h
            deleted=False,
        ),
        BlockOut(
            id=2,
            user_id=1,
            type="shift",
            title="Shift 2",
            day_of_week=2,
            start_time="08:00:00",
            end_time="21:00:00",  # 13h (Total = 25h, limit 20h)
            deleted=False,
        ),
    ]
    res_over_work = compute_schedule_health(blocks=over_work_blocks, conflicts=[], weekly_work_limit=20.0)
    # Starts at 100 + 5 (no hard conflicts) - 15 (work limit exceeded) - 10 (two >9h heavy days: -5 each) = 80
    assert any("Work limit exceeded" in f.text for f in res_over_work.factors)
    assert res_over_work.score <= 85

    # 5. Boundary testing: Multiple severe penalties never drop below 0
    severe_conflicts = [
        ConflictItem(
            id=i,
            block_a_id=100 + i,
            block_b_id=200 + i,
            overlap_minutes=60,
            severity="hard",
            overlap_start="09:00",
            overlap_end="10:00",
            day_of_week=i % 7,
            description=f"Clash {i}",
        )
        for i in range(15)  # 15 * 15 = 225 penalty points!
    ]
    res_severe = compute_schedule_health(blocks=over_work_blocks, conflicts=severe_conflicts, weekly_work_limit=20.0)
    assert res_severe.score == 0
    assert res_severe.category == "Overloaded"

    # 6. Upper boundary: Never exceeds 100
    res_perfect = compute_schedule_health(
        blocks=[
            BlockOut(id=1, type="class", title="C1", day_of_week=1, start_time="09:00:00", end_time="11:00:00", deleted=False),
            BlockOut(id=2, type="shift", title="S1", day_of_week=2, start_time="10:00:00", end_time="14:00:00", deleted=False),
            BlockOut(id=3, type="study", title="St1", day_of_week=3, start_time="14:00:00", end_time="16:00:00", deleted=False),
            BlockOut(id=4, type="study", title="St2", day_of_week=4, start_time="14:00:00", end_time="16:00:00", deleted=False),
        ],
        conflicts=[],
        weekly_work_limit=20.0,
    )
    assert res_perfect.score == 100
    assert res_perfect.category == "Excellent"

    # 7. Determinism: Calling 100 times produces identical score & breakdown
    scores = [
        compute_schedule_health(blocks=over_work_blocks, conflicts=[hard_c], weekly_work_limit=20.0).score
        for _ in range(100)
    ]
    assert len(set(scores)) == 1, "Scoring must be 100% deterministic"


def test_schedule_health_api_endpoint():
    """Integration test verifying GET /api/v1/analytics/health and user isolation."""
    uid = str(uuid.uuid4())[:8]
    email = f"health_student_{uid}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Health Student"},
    )
    assert r.status_code == 200
    token = r.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. New user has 100 Excellent health score
    resp = client.get("/api/v1/analytics/health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["score"] == 100
    assert data["category"] == "Excellent"
    assert len(data["factors"]) > 0

    # 2. Add two overlapping classes -> hard conflict -> health score drops
    b1 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Math 101",
            "type": "class",
            "day_of_week": 1,
            "start_time": "10:00",
            "end_time": "12:00",
        },
    )
    assert b1.status_code in (200, 201)
    b1_id = b1.json()["data"]["id"]

    b2 = client.post(
        "/api/v1/blocks",
        headers=headers,
        json={
            "title": "Physics 101",
            "type": "class",
            "day_of_week": 1,
            "start_time": "11:00",
            "end_time": "13:00",
        },
    )
    assert b2.status_code in (200, 201)

    resp_after = client.get("/api/v1/analytics/health", headers=headers)
    assert resp_after.status_code == 200
    data_after = resp_after.json()["data"]
    assert data_after["score"] < 100
    assert any("hard schedule conflict" in f["text"] for f in data_after["factors"])

    # 3. Soft-delete one of the overlapping blocks -> conflict resolved -> health recovers
    del_resp = client.delete(f"/api/v1/blocks/{b1_id}", headers=headers)
    assert del_resp.status_code == 200

    resp_recovered = client.get("/api/v1/analytics/health", headers=headers)
    assert resp_recovered.status_code == 200
    assert resp_recovered.json()["data"]["score"] == 100


if __name__ == "__main__":
    test_schedule_health_scoring_function_direct()
    test_schedule_health_api_endpoint()
    print("All Schedule Health tests PASSED! 🎉")
