from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TimetableVersion(Base):
    __tablename__ = "timetable_versions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timetable_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("timetables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="draft")  # draft, in_review, approved, published, archived, rejected
    change_summary = Column(Text, nullable=True)

    created_by_user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("timetable_id", "version_number", name="uq_timetable_version_number"),
    )

    # Relationships
    institution = relationship("Institution")
    timetable = relationship("Timetable", foreign_keys=[timetable_id], back_populates="versions")
    meetings = relationship("CourseMeeting", back_populates="version", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by_user_id])
