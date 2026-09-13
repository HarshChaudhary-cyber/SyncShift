from sqlalchemy import (
    BigInteger,
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


class SectionEnrollment(Base):
    __tablename__ = "section_enrollments"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_profile_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("student_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    section_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default="active")  # 'active', 'dropped', 'waitlisted', 'completed'
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    dropped_at = Column(DateTime(timezone=True), nullable=True, default=None)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("section_id", "student_id", name="uq_section_enrollment_student_section"),
    )

    # Relationships
    institution = relationship("Institution")
    student = relationship("User", back_populates="section_enrollments")
    student_profile = relationship("StudentProfile", back_populates="enrollments")
    section = relationship("AcademicSection", back_populates="enrollments")


# Alias for convenience
Enrollment = SectionEnrollment
