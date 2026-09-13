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


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    employee_code = Column(String(64), nullable=True, index=True)
    title = Column(String(64), nullable=True)  # 'Professor', 'Associate Professor', 'Assistant Professor', 'Lecturer', 'Adjunct'
    status = Column(String(32), nullable=False, default="active")  # 'active', 'on_leave', 'inactive'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_faculty_institution_user"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="faculty_profiles")
    user = relationship("User", back_populates="faculty_profiles")
    department = relationship("Department", back_populates="faculty_profiles")
    section_assignments = relationship(
        "SectionFacultyAssignment", back_populates="faculty", cascade="all, delete-orphan"
    )
    meetings = relationship("CourseMeeting", back_populates="faculty")


# Alias
Faculty = FacultyProfile
