from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)

    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    timezone = Column(String(64), nullable=False, default="Europe/London")
    weekly_work_hour_limit = Column(Numeric(4, 1), nullable=False, default=20.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    time_blocks = relationship("TimeBlock", back_populates="user", cascade="all, delete-orphan")
    overrides = relationship("BlockOverride", back_populates="user", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="user", cascade="all, delete-orphan")
