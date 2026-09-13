from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class StudentConstraint(Base):
    __tablename__ = "student_constraints"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    constraint_type = Column(String(64), nullable=False)  # 'earliest_start', 'latest_end', 'max_hours_per_day', 'max_consecutive_hours', 'day_off', 'protect_work_shifts', 'custom'
    is_hard = Column(Boolean, nullable=False, default=True)  # True = hard constraint; False = soft preference
    day_of_week = Column(SmallInteger, nullable=True)  # 0-6 if specific to a day
    time_value = Column(Time, nullable=True)  # For time thresholds
    int_value = Column(Integer, nullable=True)  # For counts / minutes / hours
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)", name="ck_student_constraint_day"),
    )

    # Relationships
    user = relationship("User", back_populates="student_constraints")
    institution = relationship("Institution")


class StudentPreference(Base):
    __tablename__ = "student_preferences"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    preferred_time_of_day = Column(String(32), nullable=False, default="any")  # 'morning', 'afternoon', 'evening', 'any'
    schedule_density = Column(String(32), nullable=False, default="balanced")  # 'compact', 'balanced', 'spread'
    preferred_break_duration_minutes = Column(Integer, nullable=False, default=30)
    max_campus_days_per_week = Column(Integer, nullable=True)
    preferred_days_off = Column(String(32), nullable=True)  # Comma-separated day numbers e.g. "5,6"
    work_study_balance_weight = Column(Integer, nullable=False, default=3)  # 1 to 5 scale

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="student_preference")
    institution = relationship("Institution")
