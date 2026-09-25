import pytest
from app.config import settings
from app.database import Base, engine, init_db

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
    Initializes tables via init_db() (create_all) strictly for test isolation,
    completely independent of production Alembic migration workflows.
    """
    init_db(engine)

    from datetime import date, time
    from app.database import SessionLocal
    from app.models.time_block import TimeBlock, BlockType

    db = SessionLocal()
    try:
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

    yield
