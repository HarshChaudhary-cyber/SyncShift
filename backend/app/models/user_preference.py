from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    week_starts_on = Column(String(10), nullable=False, default="monday")
    time_format = Column(String(5), nullable=False, default="12h")
    default_calendar_view = Column(String(10), nullable=False, default="week")
    reduced_motion = Column(String(10), nullable=False, default="system")
    planning_hours_start = Column(Integer, nullable=False, default=9)
    planning_hours_end = Column(Integer, nullable=False, default=18)
    preferred_session_duration = Column(Integer, nullable=False, default=45)
    preferred_break_duration = Column(Integer, nullable=False, default=15)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="preferences")
