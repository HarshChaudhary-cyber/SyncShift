from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class CourseMeeting(Base):
    __tablename__ = "course_meetings"

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
    version_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("timetable_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    section_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_term_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("academic_terms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week = Column(SmallInteger, nullable=False, index=True)  # 0 = Sun, 1 = Mon ... 6 = Sat
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    room_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    faculty_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("faculty_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    meeting_type = Column(String(32), nullable=False, default="lecture")  # 'lecture', 'laboratory', 'tutorial', 'seminar', 'practical', 'other'
    status = Column(String(32), nullable=False, default="active")  # 'active', 'cancelled'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    # Relationships
    institution = relationship("Institution", back_populates="course_meetings")
    timetable = relationship("Timetable", back_populates="meetings")
    version = relationship("TimetableVersion", back_populates="meetings")
    section = relationship("AcademicSection", back_populates="meetings")
    term = relationship("AcademicTerm", back_populates="course_meetings")
    room = relationship("Room", back_populates="meetings")
    faculty = relationship("FacultyProfile", back_populates="meetings")


# Alias for convenience
SectionMeeting = CourseMeeting

