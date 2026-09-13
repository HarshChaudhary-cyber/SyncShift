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


class StudentProfile(Base):
    __tablename__ = "student_profiles"

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
    student_number = Column(String(64), nullable=True, index=True)
    program = Column(String(255), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="active")  # 'active', 'inactive', 'graduated', 'on_leave'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_student_profile_inst_user"),
    )

    # Relationships
    user = relationship("User", back_populates="student_profiles")
    institution = relationship("Institution", back_populates="student_profiles")
    department = relationship("Department", back_populates="student_profiles")
    enrollments = relationship("SectionEnrollment", back_populates="student_profile")
