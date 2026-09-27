import os
import tempfile
from pathlib import Path

import pytest

# Never let pytest inherit the developer's database, API key or CAPTCHA settings.
# File-backed SQLite supports TestClient's worker threads without sharing live data.
_test_directory = tempfile.TemporaryDirectory(prefix="syncshift-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_test_directory.name) / "tests.db").as_posix()
os.environ["ENV"] = "test"
os.environ["CAPTCHA_SECRET_KEY"] = ""
os.environ["CAPTCHA_ENFORCE"] = "false"
os.environ["GEMINI_API_KEY"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"
from app.config import settings
from app.database import Base, engine, init_db


@pytest.fixture(autouse=True)
def disable_live_gemini_for_tests(monkeypatch):
    """Keep routine tests independent of API credentials, quotas, and network access.

    Tests of the Gemini integration opt in with a fake key and mock the SDK.
    """
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)


@pytest.fixture(autouse=True)
def enable_synthetic_oauth_only_in_tests(monkeypatch):
    """Mock OAuth tokens must never be accepted by a running app."""
    from app.services import oauth_service
    monkeypatch.setattr(oauth_service, "_allow_test_oauth_tokens", lambda: True)
    from app.services import captcha_service
    monkeypatch.setattr(captcha_service, "_allow_test_captcha_tokens", lambda: True)

# If Redis is unavailable or paused, disable rate limiting for test suite execution
try:
    import redis
    _r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.3, socket_timeout=0.3, retry_on_timeout=False)
    if not _r.ping():
        settings.RATE_LIMIT_ENABLED = False
except Exception:
    settings.RATE_LIMIT_ENABLED = False


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Session-wide fixture for pytest suite.
    Initialises tables via init_db() (create_all) strictly for test isolation,
    completely independent of production Alembic migration workflows.

    Individual test files are responsible for seeding the specific data their
    tests need (see e.g. test_today_endpoint.py::monday_sample_blocks).  A
    function-scoped fixture in each test file guarantees isolation and correct
    behaviour regardless of test ordering.
    """
    init_db(engine)

    # Reserve the owner of fixture events before real test accounts register.
    # Otherwise the first registration inherits these orphaned sample rows.
    from app.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        if db.get(User, 1) is None:
            db.add(User(id=1, email="fixture-owner@example.test", name="Fixture owner"))
            db.commit()
    finally:
        db.close()

    yield
    engine.dispose()
    _test_directory.cleanup()
