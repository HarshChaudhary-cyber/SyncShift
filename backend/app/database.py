from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Configure engine with SQLite compatibility for tests/dev fallback
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db(target_engine=None) -> None:
    """
    Initialize database schema directly via metadata.create_all().

    IMPORTANT: This is strictly reserved for test harnesses (e.g., in-memory SQLite
    test fixtures). The application runtime and production deployments must ALWAYS
    manage schema via Alembic migrations (`alembic upgrade head`).
    """
    from app import models  # noqa: F401
    bind_engine = target_engine or engine
    Base.metadata.create_all(bind=bind_engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


