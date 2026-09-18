"""
test_gemini_import.py – Automated test suite for Gemini-powered timetable file import.
Tests error status codes (400, 413, 422, 500, 503) and timetable extraction and confirmation.
"""
import io
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.assistant_gemini import gemini_answer_general_question
from app.store import get_all_blocks
from app.dependencies import get_current_user, CurrentUser

client = TestClient(app)

# Dummy current user for dependency override
TEST_USER = CurrentUser(
    user_id=8888,
    email="gemini_test_user@example.com",
)


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


def get_error(resp):
    body = resp.json()
    return body.get("error") or body.get("detail") or {}


def test_reject_unsupported_file_extension():
    """Unsupported extension like .exe or .zip must return 400."""
    response = client.post(
        "/api/v1/import/file",
        files={"file": ("malicious.exe", b"binary content", "application/octet-stream")},
    )
    assert response.status_code == 400
    err = get_error(response)
    assert err.get("code") == "unsupported_format"
    assert "Supported: PDF, Word, PowerPoint, images" in err.get("message", "")


def test_reject_oversized_file():
    """File larger than 20MB must return 413."""
    # 21MB fake payload
    oversized = b"0" * (21 * 1024 * 1024)
    response = client.post(
        "/api/v1/import/file",
        files={"file": ("huge_schedule.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413
    err = get_error(response)
    assert err.get("code") == "file_too_large"
    assert "20MB" in err.get("message", "")


def test_empty_file():
    """Empty file bytes must return 400."""
    response = client.post(
        "/api/v1/import/file",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    err = get_error(response)
    assert err.get("code") == "empty_file"


def test_gemini_not_configured():
    """Missing GEMINI_API_KEY must return 500."""
    with patch.object(settings, "GEMINI_API_KEY", None):
        response = client.post(
            "/api/v1/import/file",
            files={"file": ("schedule.png", b"\x89PNG\r\n\x1a\nfakeimage", "image/png")},
        )
        assert response.status_code == 500
        err = get_error(response)
        assert err.get("code") == "service_not_configured"
        assert "Import service not configured" in err.get("message", "")


def test_gemini_successful_answer_is_preserved():
    """A successful Gemini answer should return the model text unchanged."""
    with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel") as mock_model:
        mock_response = type("Resp", (), {"candidates": [type("Cand", (), {"content": type("Content", (), {"parts": [type("Part", (), {"text": "Gemini API connection successful"})()]})})()]})()
        mock_model.return_value.start_chat.return_value.send_message.return_value = mock_response

        result = gemini_answer_general_question("Reply with exactly: Gemini API connection successful", [])
        assert result == "Gemini API connection successful"


def test_gemini_quota_response_is_sanitized():
    """429 quota errors should be translated into a safe app-level message."""
    with patch.object(settings, "GEMINI_API_KEY", "test-key"), patch(
        "google.generativeai.GenerativeModel",
        side_effect=Exception("429 ResourceExhausted: quota exceeded. Please retry in 36 seconds."),
    ):
        result = gemini_answer_general_question("Hello", [])
        assert "SyncShift AI is temporarily unavailable because the AI service quota has been reached" in result
        assert "429" not in result
        assert "Please retry in 36 seconds" not in result


def test_gemini_generic_error_is_sanitized():
    """Other Gemini API failures should not expose raw provider details."""
    with patch.object(settings, "GEMINI_API_KEY", "test-key"), patch(
        "google.generativeai.GenerativeModel",
        side_effect=Exception("500 internal server error from upstream"),
    ):
        result = gemini_answer_general_question("Hello", [])
        assert result == "SyncShift AI is temporarily unavailable. Please try again later."
        assert "500" not in result


def test_gemini_missing_api_key_is_sanitized():
    """Missing configuration should return an app-level message, not a raw SDK error."""
    with patch.object(settings, "GEMINI_API_KEY", None):
        result = gemini_answer_general_question("Hello", [])
        assert result == "SyncShift AI is temporarily unavailable because the AI service is not configured."


def test_gemini_returns_empty_or_non_timetable():
    """Gemini returning [] must return 422 with timetable guidance."""
    with patch("app.services.gemini_timetable.call_gemini_model", return_value="[]"):
        response = client.post(
            "/api/v1/import/file",
            files={"file": ("random_photo.jpg", b"\xff\xd8\xfffakejpeg", "image/jpeg")},
        )
        assert response.status_code == 422
        err = get_error(response)
        assert err.get("code") == "no_timetable_found"
        assert "No timetable found in this file" in err.get("message", "")


def test_gemini_unreadable_json_triggers_retry_and_422():
    """Corrupted response even after retry returns 422."""
    with patch("app.services.gemini_timetable.call_gemini_model", return_value="Not valid JSON at all"):
        response = client.post(
            "/api/v1/import/file",
            files={"file": ("corrupt.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 422
        err = get_error(response)
        assert err.get("code") == "unreadable_file"
        assert "Couldn't read this file" in err.get("message", "")


def test_gemini_successful_extraction_and_confirm_flow():
    """Mock a successful Gemini timetable extraction and verify the full preview & confirm flow."""
    mock_gemini_json = json.dumps([
        {
            "title": "CS101 Lecture",
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "10:30",
            "location": "Room 302",
            "course_code": "CS101",
            "is_recurring": True
        },
        {
            "title": "MATH201 Tutorial",
            "day_of_week": 3,
            "start_time": "14:00",
            "end_time": "15:00",
            "location": "Hall B",
            "course_code": "MATH201",
            "is_recurring": True
        }
    ])

    with patch("app.services.gemini_timetable.call_gemini_model", return_value=mock_gemini_json):
        response = client.post(
            "/api/v1/import/file",
            files={"file": ("timetable.png", b"\x89PNG\r\n\x1a\nsample", "image/png")},
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["total_found"] == 2
        assert data["file_type"] == "png"
        assert "Found 2 classes" in data["message"]
        
        preview = data["preview"]
        assert len(preview) == 2
        assert preview[0]["temp_id"] == "gemini-0"
        assert preview[0]["title"] == "CS101 Lecture"
        assert preview[0]["day_of_week"] == 1
        assert preview[0]["start_time"] == "09:00"
        assert preview[0]["end_time"] == "10:30"
        assert preview[0]["confidence"] == "high"

        assert preview[1]["temp_id"] == "gemini-1"
        assert preview[1]["title"] == "MATH201 Tutorial"
        assert preview[1]["confidence"] == "high"

        # Now confirm the first item only (simulate unchecking the second item)
        confirm_payload = {
            "preview_blocks": [
                {
                    "title": preview[0]["title"],
                    "day_of_week": preview[0]["day_of_week"],
                    "start_time": preview[0]["start_time"],
                    "end_time": preview[0]["end_time"],
                    "location": preview[0]["location"],
                }
            ]
        }
        confirm_resp = client.post("/api/v1/import/file/confirm", json=confirm_payload)
        assert confirm_resp.status_code == 200
        confirm_data = confirm_resp.json()["data"]
        assert confirm_data["created_count"] == 1

        # Verify block was persisted in DB for TEST_USER
        blocks = get_all_blocks(user_id=TEST_USER.user_id)
        user_blocks = [b for b in blocks if b.title == "CS101 Lecture"]
        assert len(user_blocks) >= 1
        assert user_blocks[0].day_of_week == 1
        assert str(user_blocks[0].start_time).startswith("09:00")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
