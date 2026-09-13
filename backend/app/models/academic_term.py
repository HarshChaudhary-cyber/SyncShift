from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class AcademicTerm(Base):
    __tablename__ = "academic_terms"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    academic_year = Column(String(32), nullable=False)  # e.g., '2026-2027'
    term_type = Column(String(32), nullable=False, default="semester")  # 'semester', 'trimester', 'quarter', 'custom'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="upcoming")  # 'draft', 'upcoming', 'active', 'completed', 'archived'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    # Relationships
    institution = relationship("Institution", back_populates="academic_terms")
    academic_sections = relationship("AcademicSection", back_populates="term", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="term", cascade="all, delete-orphan")
    course_meetings = relationship("CourseMeeting", back_populates="term", cascade="all, delete-orphan")
