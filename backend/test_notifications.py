"""
Automated Test Suite for SyncShift Notification System.
Tests:
- Notification preferences (GET defaults, PUT updates, validation)
- Push subscription lifecycle (subscribe, delete, test notification)
- Notification logs (querying, today filter)
- Quiet hours evaluation
- Upcoming block matching and deduplication
- Conflict alert triggers
- Subscription expiration auto-cleanup
"""
from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from pywebpush import WebPushException

from app.database import SessionLocal, init_db
from app.main import app
from app.models.notification import NotificationLog, NotificationPrefs, PushSubscription
from app.models.user import User
from app.services.reminders import (
    check_deadline_reminders,
    check_upcoming_reminders,
    dispatch_notification,
    is_in_quiet_hours,
    notify_conflict_if_applicable,
    send_web_push,
)
from app.store import add_block_to_store

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer mock_token_1"}


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()
    # Ensure test user 1 exists
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email="student1@example.com",
            name="Test Student",
            timezone="Europe/London",
        )
        db.add(user)
    # Clean user 1 notification prefs, subscriptions, logs
    db.query(NotificationPrefs).filter(NotificationPrefs.user_id == 1).delete()
    db.query(NotificationLog).filter(NotificationLog.user_id == 1).delete()
    db.query(PushSubscription).filter(PushSubscription.user_id == 1).delete()
    db.commit()
    db.close()
    yield



def test_notification_prefs_get_and_put():
    # 1. GET prefs (should auto-create default prefs)
    resp = client.get("/api/v1/notifications/prefs", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["user_id"] == 1
    assert data["push_enabled"] is True
    assert data["email_enabled"] is False
    assert data["class_reminder_min"] == 30
    assert data["shift_reminder_min"] == 60
    assert data["study_reminder_min"] == 15
    assert data["deadline_reminder"] is True
    assert data["conflict_alerts"] is True

    # 2. PUT update prefs
    update_payload = {
        "push_enabled": True,
        "email_enabled": True,
        "class_reminder_min": 15,
        "shift_reminder_min": 60,
        "study_reminder_min": 30,
        "deadline_reminder": True,
        "conflict_alerts": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
    }
    resp = client.put("/api/v1/notifications/prefs", json=update_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["class_reminder_min"] == 15
    assert updated["study_reminder_min"] == 30
    assert updated["email_enabled"] is True
    assert updated["quiet_hours_start"] == "22:00"
    assert updated["quiet_hours_end"] == "08:00"

    # 3. Validation: reminder minutes outside [0, 1440]
    resp = client.put(
        "/api/v1/notifications/prefs",
        json={"class_reminder_min": 2000},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 422

    # 4. Validation: mismatched quiet hours (only start without end)
    resp = client.put(
        "/api/v1/notifications/prefs",
        json={"quiet_hours_start": "22:00", "quiet_hours_end": None},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 422


def test_push_subscriptions_and_test_notification():
    db = SessionLocal()
    # Clean subscriptions for user 1
    db.query(PushSubscription).filter(PushSubscription.user_id == 1).delete()
    db.commit()
    db.close()

    # 1. Test notification with no subscriptions -> 404
    resp = client.post("/api/v1/notifications/test", headers=AUTH_HEADER)
    assert resp.status_code == 404, resp.text
    assert "No push subscription found" in resp.json()["error"]

    # 2. Subscribe endpoint
    sub_payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test_subscription_endpoint_123",
        "keys": {
            "p256dh": "mock_p256dh_key_sample",
            "auth": "mock_auth_secret_sample",
        },
    }
    resp = client.post("/api/v1/notifications/subscribe", json=sub_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    # Verify subscription in DB
    db = SessionLocal()
    sub = db.query(PushSubscription).filter(PushSubscription.user_id == 1).first()
    assert sub is not None
    assert sub.endpoint == sub_payload["endpoint"]
    db.close()

    # 3. Test notification now sends successfully
    with patch("app.routers.notifications.send_web_push", return_value=True):
        resp = client.post("/api/v1/notifications/test", headers=AUTH_HEADER)
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

    # 4. Check notification log
    resp = client.get("/api/v1/notifications/log?today=true", headers=AUTH_HEADER)
    assert resp.status_code == 200, resp.text
    logs = resp.json()["data"]
    assert len(logs) > 0
    assert logs[0]["type"] == "test"
    assert logs[0]["title"] == "SyncShift"

    # 5. Delete subscription
    resp = client.request(
        "DELETE",
        "/api/v1/notifications/subscribe",
        json={"endpoint": sub_payload["endpoint"]},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    # 6. Test again returns 404
    resp = client.post("/api/v1/notifications/test", headers=AUTH_HEADER)
    assert resp.status_code == 404


def test_quiet_hours_evaluation():
    # Overnight interval: 22:00 -> 08:00
    assert is_in_quiet_hours(time(22, 0), "22:00", "08:00") is True
    assert is_in_quiet_hours(time(23, 30), "22:00", "08:00") is True
    assert is_in_quiet_hours(time(2, 15), "22:00", "08:00") is True
    assert is_in_quiet_hours(time(7, 59), "22:00", "08:00") is True
    assert is_in_quiet_hours(time(8, 0), "22:00", "08:00") is False
    assert is_in_quiet_hours(time(14, 0), "22:00", "08:00") is False

    # Daytime interval: 13:00 -> 15:00
    assert is_in_quiet_hours(time(12, 59), "13:00", "15:00") is False
    assert is_in_quiet_hours(time(13, 0), "13:00", "15:00") is True
    assert is_in_quiet_hours(time(14, 30), "13:00", "15:00") is True
    assert is_in_quiet_hours(time(15, 0), "13:00", "15:00") is False

    # None or equal: no quiet hours
    assert is_in_quiet_hours(time(12, 0), None, None) is False
    assert is_in_quiet_hours(time(12, 0), "12:00", "12:00") is False


def test_reminder_matching_and_deduplication():
    db = SessionLocal()
    # Configure user 1 prefs with 30 min class reminder, quiet hours disabled
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == 1).first()
    if not prefs:
        prefs = NotificationPrefs(user_id=1)
        db.add(prefs)
    prefs.push_enabled = True
    prefs.class_reminder_min = 30
    prefs.quiet_hours_start = None
    prefs.quiet_hours_end = None
    # Add active push subscription for user 1
    sub = PushSubscription(
        user_id=1,
        endpoint="https://fcm.googleapis.com/fcm/send/test_sub_reminder",
        p256dh="mock_p256dh_key_sample",
        auth="mock_auth_secret_sample",
    )
    db.add(sub)
    # Clear prior logs for user 1
    db.query(NotificationLog).filter(NotificationLog.user_id == 1).delete()
    db.commit()
    db.close()


    # Create a test block matching fixed now + 30 minutes in user timezone (Europe/London)
    from app.services.schedule import get_user_zoneinfo
    from app.models.time_block import TimeBlock
    tz = get_user_zoneinfo("Europe/London")
    fixed_now = datetime(2026, 9, 14, 10, 0, 0, tzinfo=tz) # Monday 10:00
    target_start = fixed_now + timedelta(minutes=30) # 10:30
    dow = (fixed_now.date().weekday() + 1) % 7
    start_str = f"{target_start.hour:02d}:{target_start.minute:02d}:00"
    end_str = f"{(target_start.hour + 1) % 24:02d}:{target_start.minute:02d}:00"

    # Clean up prior test blocks and class logs for user 1
    db_clean = SessionLocal()
    db_clean.query(TimeBlock).filter(
        TimeBlock.user_id == 1,
        TimeBlock.title == "Automated Testing Class",
    ).delete()
    db_clean.query(NotificationLog).filter(
        NotificationLog.user_id == 1,
        NotificationLog.type == "class",
    ).delete()
    db_clean.commit()
    db_clean.close()

    test_block = {
        "type": "class",
        "title": "Automated Testing Class",
        "location": "Auditorium 1",
        "day_of_week": dow,
        "start_time": start_str,
        "end_time": end_str,
        "is_recurring": True,
        "deleted": False,
    }
    created = add_block_to_store(test_block, user_id=1)

    with patch("app.services.reminders.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        mock_datetime.combine = datetime.combine
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        with patch("app.services.reminders.send_web_push", return_value=True):
            # Run 1: Should send reminder
            check_upcoming_reminders()

            db = SessionLocal()
            logs_1 = db.query(NotificationLog).filter(
                NotificationLog.user_id == 1,
                NotificationLog.type == "class",
                NotificationLog.body.like("%Automated Testing Class%"),
            ).all()
            assert len(logs_1) == 1
            assert "Class starting soon" in logs_1[0].title
            assert "Automated Testing Class" in logs_1[0].body
            db.close()

            # Run 2: Re-run in same minute -> must NOT create duplicate!
            check_upcoming_reminders()

            db = SessionLocal()
            logs_2 = db.query(NotificationLog).filter(
                NotificationLog.user_id == 1,
                NotificationLog.type == "class",
                NotificationLog.body.like("%Automated Testing Class%"),
            ).all()
            assert len(logs_2) == 1, "Duplicate reminder sent on re-check"
            db.close()


def test_conflict_alert_on_block_clash():
    db = SessionLocal()
    # Ensure conflict alerts enabled for user 1 and add subscription
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == 1).first()

    if not prefs:
        prefs = NotificationPrefs(user_id=1)
        db.add(prefs)
    prefs.push_enabled = True
    prefs.conflict_alerts = True
    prefs.quiet_hours_start = None
    prefs.quiet_hours_end = None

    sub = PushSubscription(
        user_id=1,
        endpoint="https://fcm.googleapis.com/fcm/send/test_sub_conflict",
        p256dh="mock_p256dh_key_sample",
        auth="mock_auth_secret_sample",
    )
    db.add(sub)
    db.commit()
    db.close()


    # Create a clashing block via API
    block_a_payload = {
        "type": "class",
        "title": "Morning Biology",
        "day_of_week": 4,  # Thursday
        "start_time": "10:00:00",
        "end_time": "12:00:00",
    }
    resp_a = client.post("/api/v1/blocks", json=block_a_payload, headers=AUTH_HEADER)
    assert resp_a.status_code == 201

    block_b_payload = {
        "type": "shift",
        "title": "Bookstore Shift",
        "day_of_week": 4,  # Thursday
        "start_time": "11:00:00",  # Clashes with 10:00-12:00!
        "end_time": "14:00:00",
        "is_flexible": True,
        "hourly_wage": 16.50,
    }

    with patch("app.services.reminders.send_web_push", return_value=True):
        resp_b = client.post("/api/v1/blocks", json=block_b_payload, headers=AUTH_HEADER)
        assert resp_b.status_code == 201

        # Check notification log for conflict alert
        db = SessionLocal()
        conflict_log = db.query(NotificationLog).filter(
            NotificationLog.user_id == 1,
            NotificationLog.type == "conflict",
        ).first()
        assert conflict_log is not None
        assert "clashes with" in conflict_log.body
        db.close()


def test_expired_subscription_autodelete():
    db = SessionLocal()
    # Add a dummy subscription
    endpoint = "https://fcm.googleapis.com/fcm/send/expired_sub_410"
    sub = PushSubscription(
        user_id=1,
        endpoint=endpoint,
        p256dh="mock_p256",
        auth="mock_auth",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    # Mock WebPushException with status 410 Gone
    mock_resp = MagicMock()
    mock_resp.status_code = 410
    mock_ex = WebPushException("Subscription expired", response=mock_resp)

    with patch("app.services.reminders.webpush", side_effect=mock_ex):
        result = send_web_push(sub, {"title": "Test"}, db=db)
        assert result is False

    # Check that subscription was auto-deleted
    deleted_sub = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    assert deleted_sub is None
    db.close()


def test_deadline_reminder_trigger():
    from app.services.schedule import get_user_zoneinfo
    from app.store import create_task_in_store

    tz = get_user_zoneinfo("Europe/London")
    now_dt = datetime.now(tz)
    tomorrow = now_dt.date() + timedelta(days=1)

    db = SessionLocal()
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == 1).first()
    if not prefs:
        prefs = NotificationPrefs(user_id=1)
        db.add(prefs)
    prefs.push_enabled = True
    prefs.deadline_reminder = True
    prefs.quiet_hours_start = None
    prefs.quiet_hours_end = None

    sub = PushSubscription(
        user_id=1,
        endpoint="https://fcm.googleapis.com/fcm/send/test_sub_deadline",
        p256dh="mock_p256",
        auth="mock_auth",
    )
    db.add(sub)
    db.commit()
    db.close()

    from app.models.study_task import StudyTask
    # Clean up prior test tasks and deadline logs for user 1 to ensure test isolation
    db_clean = SessionLocal()
    db_clean.query(StudyTask).filter(
        StudyTask.user_id == 1,
        StudyTask.title == "Machine Learning Assignment",
    ).delete()
    db_clean.query(NotificationLog).filter(
        NotificationLog.user_id == 1,
        NotificationLog.type == "deadline",
    ).delete()
    db_clean.commit()
    db_clean.close()

    # Create task due tomorrow
    task = create_task_in_store({
        "title": "Machine Learning Assignment",
        "deadline": tomorrow.isoformat(),
        "total_hours_required": 4.0,
        "status": "pending",
    }, user_id=1)

    # Mock datetime.now to return 08:00
    mock_0800 = datetime(now_dt.year, now_dt.month, now_dt.day, 8, 0, 0, tzinfo=tz)

    with patch("app.services.reminders.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_0800
        mock_datetime.combine = datetime.combine
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        with patch("app.services.reminders.send_web_push", return_value=True):
            check_deadline_reminders()

            db = SessionLocal()
            log = db.query(NotificationLog).filter(
                NotificationLog.user_id == 1,
                NotificationLog.type == "deadline",
            ).first()
            assert log is not None
            assert "Due tomorrow: Machine Learning Assignment" in log.body
            db.close()

            # Re-run check -> duplicate prevention!
            check_deadline_reminders()
            db = SessionLocal()
            logs = db.query(NotificationLog).filter(
                NotificationLog.user_id == 1,
                NotificationLog.type == "deadline",
            ).all()
            assert len(logs) == 1
            db.close()
