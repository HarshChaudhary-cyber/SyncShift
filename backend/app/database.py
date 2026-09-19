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


def init_db() -> None:
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Automatically add missing columns if upgrading existing database
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        if "users" in insp.get_table_names():
            cols = [c["name"] for c in insp.get_columns("users")]
            with engine.begin() as conn:
                if "currency" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN currency VARCHAR(8) DEFAULT 'INR'"))
                if "language" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN language VARCHAR(5) DEFAULT 'en'"))
                if "theme" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN theme VARCHAR(10) DEFAULT 'dark'"))
                if "minimum_transition_minutes" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN minimum_transition_minutes INTEGER DEFAULT 15"))
                if "deleted_at" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN deleted_at DATETIME"))
                if "microsoft_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN microsoft_id VARCHAR(255)"))
                if "google_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)"))
                if "oauth_provider" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)"))
                if "avatar_url" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
                if "display_name" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(255)"))
    except Exception as e:
        print("Warning during init_db column check:", e)



# Auto-initialize database tables for dev / testing
try:
    init_db()
except Exception:
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


