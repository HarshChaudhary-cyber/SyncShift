import uuid
from datetime import date, timedelta
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.rate_limiter import reset_rate_limits

client = TestClient(app)

def test_part_62_and_63_complete_e2e_flow():
    reset_rate_limits()
    
    # -------------------------------------------------------------
    # 1. SETUP USER A (30m min transition buffer) and USER B (15m buffer)
    # -------------------------------------------------------------
    uid_a = str(uuid.uuid4())[:8]
    email_a = f"alex_{uid_a}@syncshift.edu"
    res_reg_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": email_a,
            "password": "Password123!",
            "name": "Alex Student",
            "weekly_work_hour_limit": 20.0,
            "minimum_transition_minutes": 30,
        },
    )
    assert res_reg_a.status_code == 200, res_reg_a.text
    token_a = res_reg_a.json()["data"]["token"]
    user_a_id = res_reg_a.json()["data"]["user_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    uid_b = str(uuid.uuid4())[:8]
    email_b = f"bob_{uid_b}@syncshift.edu"
    res_reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": email_b,
            "password": "Password123!",
            "name": "Bob Student",
            "weekly_work_hour_limit": 20.0,
            "minimum_transition_minutes": 15,
        },
    )
    assert res_reg_b.status_code == 200, res_reg_b.text
    token_b = res_reg_b.json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create User B private block
    res_b_block = client.post(
        "/api/v1/blocks",
        headers=headers_b,
        json={
            "title": "Bob Confidential Session",
            "type": "study",
            "day_of_week": 3,
            "start_time": "14:00",
            "end_time": "15:00",
            "location": "Medical Clinic",
        },
    )
    assert res_b_block.status_code in (200, 201)
    block_b_id = res_b_block.json()["data"]["id"]

    # -------------------------------------------------------------
    # PART 62: SCHEDULE SETUP FOR USER A
    # Monday:
    #   Class: 09:00-12:00 (Campus A)
    #   Work:  14:00-18:00 (Café) -> 120m gap >= 30m => Clean!
    # Wednesday:
    #   Class: 10:00-12:00 (Campus B)
    #   Work:  12:10-16:00 (Café) -> 10m gap < 30m => WARNING!
    # -------------------------------------------------------------
    today_d = date.today()
    week_start = today_d - timedelta(days=today_d.weekday())

    # Monday Class: 09:00 - 12:00 @ Campus A
    r_mon_class = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "title": "Computer Networks",
            "type": "class",
            "day_of_week": 1,  # Monday
            "start_time": "09:00",
            "end_time": "12:00",
            "location": "Campus A",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )
    assert r_mon_class.status_code in (200, 201)

    # Monday Work: 14:00 - 18:00 @ Café (120m transition -> clean)
    r_mon_work = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "title": "Café Barista Shift Mon",
            "type": "shift",
            "day_of_week": 1,
            "start_time": "14:00",
            "end_time": "18:00",
            "location": "Café",
            "hourly_wage": 15.0,
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )
    assert r_mon_work.status_code in (200, 201)

    # Wednesday Class: 10:00 - 12:00 @ Campus B
    r_wed_class = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "title": "Operating Systems",
            "type": "class",
            "day_of_week": 3,  # Wednesday
            "start_time": "10:00",
            "end_time": "12:00",
            "location": "Campus B",
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )
    assert r_wed_class.status_code in (200, 201)

    # Wednesday Work: 12:10 - 16:00 @ Café (10m transition < 30m -> WARNING!)
    r_wed_work = client.post(
        "/api/v1/blocks",
        headers=headers_a,
        json={
            "title": "Café Barista Shift Wed",
            "type": "shift",
            "day_of_week": 3,
            "start_time": "12:10",
            "end_time": "16:00",
            "location": "Café",
            "hourly_wage": 15.0,
            "recurrence_rule": "weekly",
            "effective_from": week_start.isoformat(),
        },
    )
    assert r_wed_work.status_code in (200, 201)
    wed_work_id = r_wed_work.json()["data"]["id"]

    # -------------------------------------------------------------
    # 2. CHECK CONFLICTS FOR WEEK
    # -------------------------------------------------------------
    conflicts_res = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers_a)
    assert conflicts_res.status_code == 200
    conflicts_list = conflicts_res.json()["data"]["conflicts"]

    # Expect: Monday has NO warnings; Wednesday has exactly 1 transition warning
    transition_warnings = [c for c in conflicts_list if c.get("conflict_type") == "transition"]
    assert len(transition_warnings) == 1
    w = transition_warnings[0]
    assert w["severity"] == "warning"
    assert w["available_transition_minutes"] == 10
    assert w["required_transition_minutes"] == 30
    assert "Campus B" in (w.get("location_a") or "") or "Campus B" in (w.get("location_b") or "")

    # -------------------------------------------------------------
    # 3. ASK ASSISTANT: "Move Wednesday shift to 1 PM"
    # -------------------------------------------------------------
    chat_res = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Move Wednesday shift to 1 PM"},
        headers=headers_a
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()["data"]
    assert chat_data["requires_confirmation"] is True
    assert chat_data["action"] is not None

    action_preview = chat_data["action"]
    assert action_preview["action_type"] == "MOVE_EVENT"
    assert action_preview["block_id"] == wed_work_id
    assert action_preview["target"]["start_time"] == "13:00"
    
    checks = action_preview["checks"]
    check_labels = [c["label"] for c in checks]
    assert "No class conflict" in check_labels
    assert "Work-hour limit respected" in check_labels
    assert "Transition buffer respected" in check_labels

    # -------------------------------------------------------------
    # 4. CONFIRM ASSISTANT ACTION
    # -------------------------------------------------------------
    confirm_res = client.post(
        "/api/v1/assistant/confirm",
        json={"action": action_preview},
        headers=headers_a
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()["data"]
    assert confirm_data["success"] is True
    assert confirm_data["updated_block"]["start_time"] == "13:00"

    # -------------------------------------------------------------
    # 5. VERIFY DATABASE UPDATED & CONFLICTS RESOLVED
    # Class ends at 12:00, shift now starts at 13:00 (60m gap >= 30m required)
    # -------------------------------------------------------------
    recheck_conflicts = client.get(f"/api/v1/conflicts?week_start={week_start.isoformat()}", headers=headers_a)
    assert recheck_conflicts.status_code == 200
    recheck_list = recheck_conflicts.json()["data"]["conflicts"]
    recheck_transitions = [c for c in recheck_list if c.get("conflict_type") == "transition"]
    assert len(recheck_transitions) == 0, "Wednesday transition warning should now be cleared!"

    # -------------------------------------------------------------
    # 6. VERIFY AUDIT LOG RECORDED
    # -------------------------------------------------------------
    audit_res = client.get("/api/v1/audit-logs", headers=headers_a)
    assert audit_res.status_code == 200
    logs = audit_res.json()["data"]["items"]
    ai_actions = [l for l in logs if l["action"] == "AI_ACTION_CONFIRMED"]
    assert len(ai_actions) >= 1
    assert ai_actions[0]["entity_id"] == wed_work_id

    # -------------------------------------------------------------
    # PART 63: SECURITY END-TO-END VERIFICATION
    # -------------------------------------------------------------
    # A. User A attempts GET /blocks/{block_b_id} -> Denied (404)
    res_idor = client.get(f"/api/v1/blocks/{block_b_id}", headers=headers_a)
    assert res_idor.status_code == 404

    # B. User A attempts GET User B's audit logs -> Only User A's logs returned
    for l in logs:
        assert l["user_id"] == user_a_id

    # C. Privacy Export:
    export_res = client.get("/api/v1/privacy/export", headers=headers_a)
    assert export_res.status_code == 200
    export_data = export_res.json()["data"]
    assert export_data["user"]["id"] == user_a_id
    assert "hashed_password" not in export_data["user"]

    # D. User A uploads malicious filename ../../secret.txt -> Rejected
    malicious_upload = client.post(
        "/api/v1/import/file",
        files={"file": ("../../secret.txt", b"malicious payload", "text/plain")},
        headers=headers_a
    )
    assert malicious_upload.status_code in (400, 422)
    assert "traversal" in malicious_upload.text.lower() or "invalid" in malicious_upload.text.lower()

    # E. Security headers present
    assert "X-Content-Type-Options" in conflicts_res.headers
    assert conflicts_res.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in conflicts_res.headers
    assert conflicts_res.headers["X-Frame-Options"] == "DENY"

    print("\n>>> ALL PART 62 & PART 63 E2E TESTS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    test_part_62_and_63_complete_e2e_flow()
