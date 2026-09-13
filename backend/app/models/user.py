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

    name = Column(String(120), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    timezone = Column(String(64), nullable=True, default=None)
    weekly_work_hour_limit = Column(Numeric(4, 1), nullable=True, default=20.0)
    currency = Column(String(8), nullable=True, default="INR")
    language = Column(String(5), nullable=True, default="en")
    theme = Column(String(10), nullable=True, default="dark")
    minimum_transition_minutes = Column(Integer, nullable=False, default=15)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    # OAuth columns
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    facebook_id = Column(String(255), unique=True, index=True, nullable=True)
    apple_id = Column(String(255), unique=True, index=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)  # 'google' | 'facebook' | 'apple' | None
    avatar_url = Column(String(500), nullable=True)
    display_name = Column(String(255), nullable=True)

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
    study_tasks = relationship("StudyTask", back_populates="user", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
    notification_prefs = relationship("NotificationPrefs", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    institution_memberships = relationship("InstitutionMembership", back_populates="user", cascade="all, delete-orphan")
    faculty_profiles = relationship("FacultyProfile", back_populates="user", cascade="all, delete-orphan")
    student_profiles = relationship("StudentProfile", back_populates="user", cascade="all, delete-orphan")
    section_enrollments = relationship("SectionEnrollment", back_populates="student", cascade="all, delete-orphan")
    student_availabilities = relationship("StudentAvailability", back_populates="user", cascade="all, delete-orphan")
    student_constraints = relationship("StudentConstraint", back_populates="user", cascade="all, delete-orphan")
    student_preference = relationship("StudentPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")


