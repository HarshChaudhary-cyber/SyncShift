from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    country = Column(String(100), nullable=True)
    timezone = Column(String(64), nullable=False, default="Europe/London")
    email_domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    # Relationships
    memberships = relationship("InstitutionMembership", back_populates="institution", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="institution", cascade="all, delete-orphan")
    academic_terms = relationship("AcademicTerm", back_populates="institution", cascade="all, delete-orphan")
    academic_courses = relationship("AcademicCourse", back_populates="institution", cascade="all, delete-orphan")
    academic_sections = relationship("AcademicSection", back_populates="institution", cascade="all, delete-orphan")
    faculty_profiles = relationship("FacultyProfile", back_populates="institution", cascade="all, delete-orphan")
    student_profiles = relationship("StudentProfile", back_populates="institution", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="institution", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="institution", cascade="all, delete-orphan")
    course_meetings = relationship("CourseMeeting", back_populates="institution", cascade="all, delete-orphan")


class InstitutionMembership(Base):
    __tablename__ = "institution_memberships"

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
        nullable=False,
        index=True,
    )
    role = Column(String(32), nullable=False, default="student")  # 'student', 'professor', 'admin', 'super_admin'
    status = Column(String(32), nullable=False, default="active")  # 'active', 'inactive', 'pending'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("user_id", "institution_id", name="uq_user_institution_membership"),
    )

    # Relationships
    user = relationship("User", back_populates="institution_memberships")
    institution = relationship("Institution", back_populates="memberships")
