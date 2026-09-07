import enum
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class BlockType(str, enum.Enum):
    CLASS = "class"
    SHIFT = "shift"


class BlockStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    TENTATIVE = "tentative"
    DROPPED = "dropped"


class TimeBlock(Base):
    __tablename__ = "time_blocks"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        Enum(BlockType, name="block_type", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        Enum(BlockStatus, name="block_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BlockStatus.ENROLLED,
    )
    course_id = Column(
        BigInteger,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)

    # Recurrence & Timing
    is_recurring = Column(Boolean, nullable=False, default=True)
    specific_date = Column(Date, nullable=True)
    day_of_week = Column(SmallInteger, nullable=True)  # 0 = Sunday, 1 = Monday ... 6 = Saturday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    is_overnight = Column(Boolean, nullable=False, default=False)

    # Effective Range
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)

    # Work Shifts & Flexibility
    is_flexible = Column(Boolean, default=False, nullable=False)
    hourly_wage = Column(Numeric(10, 2), nullable=True)
    is_imported = Column(Boolean, default=False, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="check_day_of_week_range",
        ),
        CheckConstraint("duration_minutes > 0", name="check_positive_duration"),
    )

    # Relationships
    user = relationship("User", back_populates="time_blocks")
    course = relationship("Course", back_populates="time_blocks")
    overrides = relationship("BlockOverride", back_populates="time_block", cascade="all, delete-orphan")
