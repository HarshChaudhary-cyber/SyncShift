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


class AcademicSection(Base):
    __tablename__ = "academic_sections"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_term_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_terms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_code = Column(String(32), nullable=False, index=True)
    capacity = Column(Integer, nullable=False, default=30)
    status = Column(String(32), nullable=False, default="active")  # 'active', 'cancelled', 'completed'
    description = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("course_id", "academic_term_id", "section_code", name="uq_academic_section_offering"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="academic_sections")
    course = relationship("AcademicCourse", back_populates="sections")
    term = relationship("AcademicTerm", back_populates="academic_sections")
    faculty_assignments = relationship(
        "SectionFacultyAssignment", back_populates="section", cascade="all, delete-orphan"
    )
    enrollments = relationship(
        "SectionEnrollment", back_populates="section", cascade="all, delete-orphan"
    )
    meetings = relationship(
        "CourseMeeting", back_populates="section", cascade="all, delete-orphan"
    )


# Alias for convenience
Section = AcademicSection
