import io
from datetime import datetime
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.ics_parser import (
    convert_rrule_dtstart_to_day_of_week,
    extract_recurring_days,
    format_time_hhmm,
)

from app.main import app
from app.dependencies import get_current_user, CurrentUser

@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=1, email="student1@example.com")
    yield
    app.dependency_overrides.clear()

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer test_token"}

SAMPLE_VALID_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SyncShift Timetable Test//EN
BEGIN:VEVENT
UID:class-1@syncshift.edu
SUMMARY:CS101 Lecture
LOCATION:Room 302
DTSTART:20260907T090000
DTEND:20260907T103000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE
END:VEVENT
BEGIN:VEVENT
UID:class-2@syncshift.edu
SUMMARY:MATH 220: Linear Algebra
LOCATION:Hall C
DTSTART:20260910T110000
DTEND:20260910T123000
RRULE:FREQ=WEEKLY;BYDAY=TH
END:VEVENT
BEGIN:VEVENT
UID:orientation@syncshift.edu
SUMMARY:Freshman Orientation (All Day)
DTSTART;VALUE=DATE:20260901
DTEND;VALUE=DATE:20260902
RRULE:FREQ=WEEKLY
END:VEVENT
BEGIN:VEVENT
UID:oneoff@syncshift.edu
SUMMARY:Guest Speaker (One-Off)
DTSTART:20260911T150000
DTEND:20260911T160000
END:VEVENT
END:VCALENDAR"""

SAMPLE_ZERO_EVENTS_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SyncShift Timetable Test//EN
BEGIN:VEVENT
UID:oneoff@syncshift.edu
SUMMARY:Guest Speaker Only (One-Off)
DTSTART:20260911T150000
DTEND:20260911T160000
END:VEVENT
BEGIN:VEVENT
UID:holiday@syncshift.edu
SUMMARY:Labor Day
DTSTART;VALUE=DATE:20260907
DTEND;VALUE=DATE:20260908
END:VEVENT
END:VCALENDAR"""

SAMPLE_EXPIRED_EVENTS_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SyncShift Timetable Test//EN
BEGIN:VEVENT
UID:old-class@syncshift.edu
SUMMARY:Old CS101 from 2024
DTSTART:20240902T090000
DTEND:20240902T103000
RRULE:FREQ=WEEKLY;UNTIL=20241215T235959Z
END:VEVENT
END:VCALENDAR"""


def test_valid_ics_upload():
    """
    Test Case 1: Valid .ics file with recurring weekly events.
    Verifies that recurring classes are extracted with proper 0-6 day mapping,
    start/end times, and returned in the preview list.
    """
    file_bytes = io.BytesIO(SAMPLE_VALID_ICS)
    response = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("timetable.ics", file_bytes, "text/calendar")},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    preview = data["preview"]
    unmatched = data["unmatched"]

    # 3 preview items: CS101 on Mon(0), CS101 on Wed(2), MATH 220 on Thu(3)
    assert len(preview) == 3

    # Check CS101 Monday
    mon_cs = [p for p in preview if p["title"] == "CS101 Lecture" and p["day_of_week"] == 0]
    assert len(mon_cs) == 1
    assert mon_cs[0]["start_time"] == "09:00"
    assert mon_cs[0]["end_time"] == "10:30"
    assert mon_cs[0]["location"] == "Room 302"
    assert mon_cs[0]["is_recurring"] is True
    assert "temp_id" in mon_cs[0]

    # Check CS101 Wednesday
    wed_cs = [p for p in preview if p["title"] == "CS101 Lecture" and p["day_of_week"] == 2]
    assert len(wed_cs) == 1

    # Check MATH 220 Thursday (3)
    thu_math = [p for p in preview if "MATH 220" in p["title"]]
    assert len(thu_math) == 1
    assert thu_math[0]["day_of_week"] == 3
    assert thu_math[0]["start_time"] == "11:00"
    assert thu_math[0]["end_time"] == "12:30"

    # Check unmatched (Orientation all-day event and one-off guest speaker)
    assert len(unmatched) >= 2
    reasons = [u["reason"] for u in unmatched]
    assert any("All-day" in r for r in reasons)
    assert any("One-off" in r for r in reasons)


def test_invalid_file_type():
    """
    Test Case 2: Upload is not .ics (e.g., .txt).
    Verifies HTTP 400 with code 'invalid_file_type'.
    """
    file_bytes = io.BytesIO(b"Title: My Classes\nMonday 9am")
    response = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("schedule.txt", file_bytes, "text/plain")},
    )
    assert response.status_code == 400
    res_json = response.json()
    assert "error" in res_json
    assert res_json["error"]["code"] == "invalid_file_type"
    assert "must be a .ics" in res_json["error"]["message"].lower()


def test_zero_weekly_events_found():
    """
    Test Case 3: Valid .ics file with 0 weekly recurring events.
    Verifies HTTP 400 with code 'invalid_ics'.
    """
    file_bytes = io.BytesIO(SAMPLE_ZERO_EVENTS_ICS)
    response = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("events.ics", file_bytes, "text/calendar")},
    )
    assert response.status_code == 400
    res_json = response.json()
    assert "error" in res_json
    assert res_json["error"]["code"] == "invalid_ics"
    assert "no weekly events found" in res_json["error"]["message"].lower()


def test_malformed_ics_content():
    """
    Test Case 4: File ending in .ics with corrupted/malformed data.
    Verifies HTTP 400 with code 'invalid_ics'.
    """
    file_bytes = io.BytesIO(b"This is completely invalid non-calendar junk data @!#$%%^")
    response = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("corrupted.ics", file_bytes, "text/calendar")},
    )
    assert response.status_code == 400
    res_json = response.json()
    assert "error" in res_json
    assert res_json["error"]["code"] == "invalid_ics"


def test_events_older_than_six_months_skipped():
    """
    Test Case 5: Timetable containing only expired events (> 6 months old).
    Verifies they are skipped and resulting in invalid_ics (0 active weekly events).
    """
    file_bytes = io.BytesIO(SAMPLE_EXPIRED_EVENTS_ICS)
    response = client.post(
        "/api/v1/import/ics",
        headers=AUTH_HEADER,
        files={"file": ("old_classes.ics", file_bytes, "text/calendar")},
    )
    assert response.status_code == 400
    res_json = response.json()
    assert res_json["error"]["code"] == "invalid_ics"


def test_helper_convert_rrule_dtstart():
    """
    Test Case 6: Directly test convert_rrule_dtstart_to_day_of_week and extract_recurring_days.
    """
    dt_monday = datetime(2026, 9, 7, 9, 0)
    assert dt_monday.weekday() == 0  # Mon

    # Default without BYDAY
    assert convert_rrule_dtstart_to_day_of_week(None, dt_monday) == 0
    assert extract_recurring_days(None, dt_monday) == [0]

    # With BYDAY dict
    rrule_tue = {"BYDAY": ["TU"]}
    assert convert_rrule_dtstart_to_day_of_week(rrule_tue, dt_monday) == 1

    rrule_multi = {"BYDAY": ["MO", "WE", "FR"]}
    assert extract_recurring_days(rrule_multi, dt_monday) == [0, 2, 4]


def test_confirm_ics_import_saves_blocks():
    """
    Test Case 7: Confirming parsed preview blocks persists them into active schedule.
    """
    response = client.post(
        "/api/v1/import/ics/confirm",
        headers=AUTH_HEADER,
        json={
            "preview_blocks": [
                {
                    "title": "Imported Biology 101",
                    "day_of_week": 1,
                    "start_time": "14:00",
                    "end_time": "15:30",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["created_count"] == 1
    assert "conflicts_detected" in data
