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


class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_term_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_terms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="draft")  # 'draft', 'active', 'archived'
    description = Column(String(500), nullable=True)

    published_version_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("timetable_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("institution_id", "academic_term_id", "name", name="uq_timetable_institution_term_name"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="timetables")
    term = relationship("AcademicTerm", back_populates="timetables")
    meetings = relationship("CourseMeeting", back_populates="timetable", cascade="all, delete-orphan")
    published_version = relationship("TimetableVersion", foreign_keys=[published_version_id], post_update=True)
    versions = relationship("TimetableVersion", foreign_keys="TimetableVersion.timetable_id", back_populates="timetable", cascade="all, delete-orphan", order_by="TimetableVersion.version_number")

