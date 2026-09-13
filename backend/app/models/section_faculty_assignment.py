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


class SectionFacultyAssignment(Base):
    __tablename__ = "section_faculty_assignments"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("faculty_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(32), nullable=False, default="instructor")  # 'instructor', 'co_instructor', 'teaching_assistant'
    is_primary = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("section_id", "faculty_id", name="uq_section_faculty_assignment"),
    )

    # Relationships
    institution = relationship("Institution")
    section = relationship("AcademicSection", back_populates="faculty_assignments")
    faculty = relationship("FacultyProfile", back_populates="section_assignments")
