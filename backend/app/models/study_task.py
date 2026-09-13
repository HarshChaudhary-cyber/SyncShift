import enum
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    DONE = "done"


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    course_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_hours_required = Column(Numeric(5, 2), nullable=False)
    deadline = Column(Date, nullable=False)
    status = Column(
        Enum(TaskStatus, name="task_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    priority = Column(String(20), nullable=True, default="medium")
    preferred_duration = Column(Integer, nullable=True, default=90)  # minutes
    completed_hours = Column(Numeric(5, 2), nullable=True, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="study_tasks")
    course = relationship("Course")
    study_blocks = relationship("TimeBlock", back_populates="study_task", cascade="all, delete-orphan")
