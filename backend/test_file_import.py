"""
test_file_import.py – pytest suite for the multi-format timetable import feature.

Tests cover:
  - Regex text extractor (day patterns, time normalisation, title/location splitting)
  - file_extractor validation (unsupported, legacy types)
  - /import/file endpoint (integration via TestClient)
  - /import/file/confirm endpoint
  - ICS path still works through /import/file
"""
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.text_extractor import text_to_blocks, _normalise_time, _parse_time


# ─── Shared test client ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Register a temp user and return auth headers."""
    import uuid
    email = f"filetest_{uuid.uuid4().hex[:6]}@test.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "timezone": "UTC", "weekly_work_hour_limit": 20},
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Time normalisation unit tests ────────────────────────────────────────────

class TestTimeNormalisation:
    def test_24h_passthrough(self):
        assert _normalise_time("09:00") == "09:00"
        assert _normalise_time("14:30") == "14:30"

    def test_am_conversion(self):
        assert _normalise_time("9am") == "09:00"
        assert _normalise_time("9 AM") == "09:00"
        assert _normalise_time("9:00am") == "09:00"
        assert _normalise_time("9:00 AM") == "09:00"

    def test_pm_conversion(self):
        assert _normalise_time("2pm") == "14:00"
        assert _normalise_time("2:30pm") == "14:30"
        assert _normalise_time("3:30 PM") == "15:30"

    def test_noon_midnight(self):
        assert _normalise_time("12pm") == "12:00"
        assert _normalise_time("12am") == "00:00"

    def test_invalid(self):
        assert _normalise_time("morning") == ""
        assert _normalise_time("noon") == ""


# ─── text_to_blocks unit tests ────────────────────────────────────────────────

class TestTextToBlocks:
    def test_pattern_a_basic(self):
        """'Mon 9:00-10:30 CS101' should parse correctly."""
        blocks = text_to_blocks("Mon 9:00-10:30 CS101", is_ocr=False)
        assert len(blocks) == 1
        b = blocks[0]
        assert b.day_of_week == 0  # Monday
        assert b.start_time == "09:00"
        assert b.end_time == "10:30"
        assert b.course_code == "CS101"

    def test_pattern_a_pm(self):
        """'Tue 2pm-3:30pm ENG102' should produce 14:00-15:30."""
        blocks = text_to_blocks("Tue 2pm-3:30pm ENG102", is_ocr=False)
        assert len(blocks) == 1
        b = blocks[0]
        assert b.day_of_week == 1  # Tuesday
        assert b.start_time == "14:00"
        assert b.end_time == "15:30"

    def test_pattern_a_long_day_name(self):
        """'Monday 09:00 - 11:00 CS101' should parse correctly."""
        blocks = text_to_blocks("Monday 09:00 - 11:00 CS101", is_ocr=False)
        assert len(blocks) == 1
        assert blocks[0].day_of_week == 0

    def test_multi_line(self):
        """Multiple timetable lines produce multiple blocks."""
        text = (
            "Mon 9:00-10:30 CS101 Room 204\n"
            "Wed 9:00-10:30 CS101 Room 204\n"
            "Fri 14:00-15:30 ENG102 Hall B"
        )
        blocks = text_to_blocks(text, is_ocr=False)
        assert len(blocks) == 3

    def test_pattern_b_time_first(self):
        """'9:00 AM - 10:30 AM Mon CS101' should parse correctly."""
        blocks = text_to_blocks("9:00 AM - 10:30 AM Mon CS101", is_ocr=False)
        assert len(blocks) == 1
        b = blocks[0]
        assert b.start_time == "09:00"
        assert b.end_time == "10:30"
        assert b.day_of_week == 0

    def test_ocr_low_confidence(self):
        """OCR results should have confidence='low'."""
        blocks = text_to_blocks("Mon 9:00-10:30 CS101", is_ocr=True)
        assert len(blocks) == 1
        assert blocks[0].confidence == "low"

    def test_non_ocr_high_confidence(self):
        """Non-OCR results should have confidence='high'."""
        blocks = text_to_blocks("Tue 14:00-15:30 ENG102", is_ocr=False)
        assert len(blocks) == 1
        assert blocks[0].confidence == "high"

    def test_empty_text_returns_empty_list(self):
        """Empty text returns no blocks."""
        assert text_to_blocks("", is_ocr=False) == []

    def test_no_timetable_returns_empty_list(self):
        """Text with no timetable entries returns no blocks."""
        result = text_to_blocks("This is just some random text without any schedule.", is_ocr=False)
        assert result == []

    def test_case_insensitive_day(self):
        """Day names are case-insensitive."""
        blocks = text_to_blocks("FRIDAY 10:00-11:30 MATH220", is_ocr=False)
        assert len(blocks) == 1
        assert blocks[0].day_of_week == 4  # Friday

    def test_location_extracted(self):
        """Location keyword 'Room' is split from title."""
        blocks = text_to_blocks("Mon 9:00-10:30 CS101 Room 204", is_ocr=False)
        assert len(blocks) == 1
        b = blocks[0]
        assert b.location is not None
        assert "Room" in (b.location or "")


# ─── file_extractor validation tests ─────────────────────────────────────────

class TestFileExtractorValidation:
    def test_unsupported_extension_raises(self):
        from app.services.file_extractor import extract_text
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(b"data", "malware.exe")

    def test_zip_raises(self):
        from app.services.file_extractor import extract_text
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(b"PK\x03\x04", "archive.zip")

    def test_legacy_doc_without_converter(self, monkeypatch):
        from app.services.file_extractor import extract_text
        monkeypatch.setattr("app.services.file_extractor.shutil.which", lambda name: None)
        with pytest.raises(ValueError, match="Legacy Word conversion is unavailable"):
            extract_text(b"\xd0\xcf\x11\xe0", "old_file.doc")

    def test_legacy_ppt_raises(self):
        from app.services.file_extractor import extract_text
        with pytest.raises(ValueError, match="Please save the file as .docx"):
            extract_text(b"\xd0\xcf\x11\xe0", "presentation.ppt")

    def test_txt_passthrough(self):
        from app.services.file_extractor import extract_text
        text, is_ocr = extract_text(b"Mon 9:00-10:30 CS101", "schedule.txt")
        assert "Mon" in text
        assert is_ocr is False

    def test_csv_passthrough(self):
        from app.services.file_extractor import extract_text
        text, is_ocr = extract_text(b"Day,Start,End\nMon,9:00,10:30", "data.csv")
        assert "Mon" in text
        assert is_ocr is False


# ─── /import/file endpoint integration tests ─────────────────────────────────

class TestImportFileEndpoint:
    def _upload(self, client, headers, content: bytes, filename: str, content_type: str = "text/plain"):
        return client.post(
            "/api/v1/import/file",
            files={"file": (filename, io.BytesIO(content), content_type)},
            headers=headers,
        )

    def test_txt_basic(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"Mon 9:00-10:30 CS101", "schedule.txt")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["preview"]) >= 1
        assert data["preview"][0]["day_of_week"] == 0
        assert data["preview"][0]["start_time"] == "09:00"

    def test_txt_pm_time(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"Tue 2pm-3:30pm ENG102", "t.txt")
        assert r.status_code == 200
        preview = r.json()["data"]["preview"]
        assert len(preview) >= 1
        assert preview[0]["start_time"] == "14:00"
        assert preview[0]["end_time"] == "15:30"

    def test_txt_no_timetable_returns_message(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"Hello, this is not a timetable.", "t.txt")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["preview"]) == 0
        assert data["message"] is not None

    def test_unsupported_extension_400(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"data", "file.exe", "application/octet-stream")
        assert r.status_code == 400
        assert "Supported" in r.json()["error"]["message"]

    def test_zip_extension_400(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"PK\x03\x04", "archive.zip", "application/zip")
        assert r.status_code == 400

    def test_corrupt_legacy_doc_422(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"\xd0\xcf\x11\xe0", "old.doc", "application/msword")
        assert r.status_code == 422
        assert "Could not read" in r.json()["error"]["message"]

    def test_empty_file_400(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"", "empty.txt")
        assert r.status_code == 400

    def test_multi_day_txt(self, client, auth_headers):
        content = b"Mon 9:00-10:30 CS101\nWed 9:00-10:30 CS101\n"
        r = self._upload(client, auth_headers, content, "two.txt")
        assert r.status_code == 200
        assert len(r.json()["data"]["preview"]) == 2

    def test_unauthenticated_401(self, client):
        r = client.post(
            "/api/v1/import/file",
            files={"file": ("t.txt", io.BytesIO(b"Mon 9:00-10:30 CS101"), "text/plain")},
        )
        assert r.status_code == 401

    def test_csv_extension(self, client, auth_headers):
        r = self._upload(client, auth_headers, b"Mon 9:00-10:30 CS101\n", "data.csv", "text/csv")
        assert r.status_code == 200


# ─── /import/file/confirm endpoint tests ─────────────────────────────────────

class TestImportFileConfirmEndpoint:
    def test_confirm_creates_blocks(self, client, auth_headers):
        payload = {
            "preview_blocks": [
                {
                    "title": "CS101 Data Structures",
                    "day_of_week": 0,
                    "start_time": "09:00",
                    "end_time": "10:30",
                    "location": "Room 204",
                }
            ]
        }
        r = client.post("/api/v1/import/file/confirm", json=payload, headers=auth_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["created_count"] == 1

    def test_confirm_empty_no_crash(self, client, auth_headers):
        payload = {"preview_blocks": []}
        r = client.post("/api/v1/import/file/confirm", json=payload, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["data"]["created_count"] == 0


# ─── ICS path still works through /import/file ───────────────────────────────

ICS_SAMPLE = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:CS210 Data Structures
DTSTART;TZID=America/New_York:20260902T090000
DTEND;TZID=America/New_York:20260902T103000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE
END:VEVENT
END:VCALENDAR
"""


class TestIcsViaFileEndpoint:
    def test_ics_still_works(self, client, auth_headers):
        r = client.post(
            "/api/v1/import/file",
            files={"file": ("timetable.ics", io.BytesIO(ICS_SAMPLE), "text/calendar")},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()["data"]
        # Expect 2 blocks (Mon + Wed recurring)
        assert len(data["preview"]) == 2
        # All should be high confidence
        for item in data["preview"]:
            assert item["confidence"] == "high"
