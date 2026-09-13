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


class AcademicCourse(Base):
    __tablename__ = "academic_courses"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    credits = Column(Integer, nullable=False, default=3)
    level = Column(String(32), nullable=True, default="undergraduate")  # 'undergraduate', 'postgraduate', 'doctorate', 'diploma'
    status = Column(String(32), nullable=False, default="active")  # 'active', 'archived', 'draft'

    # Resource Requirements (Prepares for future timetable optimization)
    min_room_capacity = Column(Integer, nullable=True)
    required_room_type = Column(String(32), nullable=True)  # 'classroom', 'laboratory', 'lecture_hall', etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_course_institution_code"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="academic_courses")
    department = relationship("Department", back_populates="academic_courses")
    sections = relationship("AcademicSection", back_populates="course", cascade="all, delete-orphan")


# Alias for academic context convenience
Course = AcademicCourse
