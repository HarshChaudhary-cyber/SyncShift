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


class StudentAvailability(Base):
    __tablename__ = "student_availabilities"

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
    day_of_week = Column(SmallInteger, nullable=False)  # 0 = Sunday, 1 = Monday ... 6 = Saturday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)  # True = preferred/available; False = unavailable/blackout
    title = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_student_avail_day"),
        CheckConstraint("start_time < end_time", name="ck_student_avail_times"),
    )

    # Relationships
    user = relationship("User", back_populates="student_availabilities")
    institution = relationship("Institution")
