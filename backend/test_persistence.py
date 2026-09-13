"""
Persistence & User Isolation Automated Verification Suite
Validates:
1. Registration & Authentication with JWT
2. Creating 3 blocks for User A -> confirmed in DB
3. Creating 1 course for User A -> confirmed in DB
4. Soft delete test: DELETE /api/v1/blocks/{id} sets deleted=True, DB row remains, GET /blocks filters it out
5. GET /api/v1/debug/my-data returns accurate block_count, course_count, oldest_block
6. User B isolation: User B logs in and sees 0 blocks (does NOT see User A's data)
7. User A re-authentication (sign out -> sign in): User A still sees all active blocks
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.time_block import TimeBlock
from app.models.course import Course

client = TestClient(app)


def test_full_persistence_flow():
    # Generate unique test users
    uid_a = str(uuid.uuid4())[:8]
    uid_b = str(uuid.uuid4())[:8]
    email_a = f"student_{uid_a}@test.edu"
    email_b = f"student_{uid_b}@test.edu"
    password = "SecurePassword123!"

    # 1. Register User A
    res_reg_a = client.post("/api/v1/auth/register", json={
        "email": email_a,
        "password": password,
        "timezone": "Europe/London",
        "weekly_work_hour_limit": 20.0,
    })
    assert res_reg_a.status_code in (200, 201), f"User A registration failed: {res_reg_a.text}"
    token_a = res_reg_a.json()["data"]["token"]
    user_a_id = res_reg_a.json()["data"]["user_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify GET /auth/me returns 200
    res_me_a = client.get("/api/v1/auth/me", headers=headers_a)
    assert res_me_a.status_code == 200
    assert res_me_a.json()["data"]["user_id"] == user_a_id

    # 2. User A creates a course
    res_course = client.post("/api/v1/courses", headers=headers_a, json={
        "code": "CS210",
        "name": "Data Structures & Algorithms",
        "color": "#3b82f6",
    })
    assert res_course.status_code == 201
    course_id = res_course.json()["data"]["id"]

    # 3. User A adds 3 blocks
    block_payloads = [
        {
            "type": "class",
            "title": "CS210 Lecture",
            "location": "Room 101",
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "10:30:00",
            "course_id": course_id,
        },
        {
            "type": "shift",
            "title": "Campus Library Desk",
            "location": "Main Library",
            "day_of_week": 2,
            "start_time": "11:00:00",
            "end_time": "15:00:00",
            "hourly_wage": 16.50,
            "is_flexible": True,
        },
        {
            "type": "shift",
            "title": "IT Helpdesk",
            "location": "Student Hall",
            "day_of_week": 4,
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "hourly_wage": 18.00,
            "is_flexible": False,
        },
    ]

    created_blocks = []
    for p in block_payloads:
        res = client.post("/api/v1/blocks", headers=headers_a, json=p)
        assert res.status_code == 201, f"Failed to create block: {res.text}"
        created_blocks.append(res.json()["data"])

    assert len(created_blocks) == 3

    # Check database directly via SessionLocal to verify permanent DB persistence
    with SessionLocal() as db:
        db_blocks = db.query(TimeBlock).filter(TimeBlock.user_id == user_a_id).all()
        assert len(db_blocks) == 3, f"Expected 3 blocks in DB, found {len(db_blocks)}"
        for b in db_blocks:
            assert b.user_id == user_a_id
            assert b.deleted is False

        db_courses = db.query(Course).filter(Course.user_id == user_a_id).all()
        assert len(db_courses) == 1, f"Expected 1 course in DB, found {len(db_courses)}"
        assert db_courses[0].code == "CS210"

    # 4. Check debug endpoint GET /api/v1/debug/my-data
    res_debug = client.get("/api/v1/debug/my-data", headers=headers_a)
    assert res_debug.status_code == 200, f"Debug endpoint failed: {res_debug.text}"
    debug_data = res_debug.json()["data"]
    assert debug_data["user_id"] == user_a_id
    assert debug_data["block_count"] == 3
    assert debug_data["course_count"] == 1
    assert debug_data["oldest_block"]["title"] == "CS210 Lecture"

    # 5. Check User B Isolation: Register User B
    res_reg_b = client.post("/api/v1/auth/register", json={
        "email": email_b,
        "password": password,
        "timezone": "Europe/London",
    })
    assert res_reg_b.status_code in (200, 201)
    token_b = res_reg_b.json()["data"]["token"]
    user_b_id = res_reg_b.json()["data"]["user_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B fetches blocks -> must be 0 (isolated from User A)
    res_blocks_b = client.get("/api/v1/blocks", headers=headers_b)
    assert res_blocks_b.status_code == 200
    assert len(res_blocks_b.json()["data"]) == 0, "User B saw other user's blocks!"

    # User B debug endpoint -> block_count 0, course_count 0
    res_debug_b = client.get("/api/v1/debug/my-data", headers=headers_b)
    assert res_debug_b.status_code == 200
    assert res_debug_b.json()["data"]["block_count"] == 0
    assert res_debug_b.json()["data"]["course_count"] == 0
    assert res_debug_b.json()["data"]["oldest_block"] is None

    # 6. Simulate User A Signout and Re-login
    # Simulate signout: token is dropped.
    # Simulate signin: POST /api/v1/auth/login
    res_login_a = client.post("/api/v1/auth/login", json={
        "email": email_a,
        "password": password,
    })
    assert res_login_a.status_code == 200, f"User A login failed: {res_login_a.text}"
    new_token_a = res_login_a.json()["data"]["token"]
    new_headers_a = {"Authorization": f"Bearer {new_token_a}"}

    # After sign-in, fetch blocks -> all 3 blocks must still be there!
    res_relogin_blocks = client.get("/api/v1/blocks", headers=new_headers_a)
    assert res_relogin_blocks.status_code == 200
    active_blocks = res_relogin_blocks.json()["data"]
    assert len(active_blocks) == 3, f"Expected 3 blocks after sign-in, found {len(active_blocks)}"
    titles = [b["title"] for b in active_blocks]
    assert "CS210 Lecture" in titles
    assert "Campus Library Desk" in titles
    assert "IT Helpdesk" in titles

    # Also test /week view returns all 3 blocks
    res_week = client.get("/api/v1/week?start=2026-09-07", headers=new_headers_a)
    assert res_week.status_code == 200
    assert len(res_week.json()["data"]["blocks"]) == 3

    # Also test /dashboard returns data
    res_dash = client.get("/api/v1/dashboard", headers=new_headers_a)
    assert res_dash.status_code == 200

    # 7. Soft Delete Verification
    block_to_delete = created_blocks[0]
    res_del = client.delete(f"/api/v1/blocks/{block_to_delete['id']}", headers=new_headers_a)
    assert res_del.status_code == 200
    assert res_del.json()["data"]["deleted"] is True

    # Confirm block is NOT deleted from DB, but soft deleted (deleted == True)
    with SessionLocal() as db:
        deleted_block = db.query(TimeBlock).filter(TimeBlock.id == block_to_delete["id"]).first()
        assert deleted_block is not None, "Block was hard-deleted! Expected soft-delete."
        assert deleted_block.deleted is True, "Block.deleted flag was not set to True."

    # GET /api/v1/blocks must now return 2 blocks
    res_after_del = client.get("/api/v1/blocks", headers=new_headers_a)
    assert res_after_del.status_code == 200
    assert len(res_after_del.json()["data"]) == 2

    # Debug endpoint now shows block_count == 2
    res_debug_after = client.get("/api/v1/debug/my-data", headers=new_headers_a)
    assert res_debug_after.status_code == 200
    assert res_debug_after.json()["data"]["block_count"] == 2

    print("ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_full_persistence_flow()
