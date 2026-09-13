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


class Room(Base):
    __tablename__ = "rooms"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    institution_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building = Column(String(100), nullable=False)
    room_number = Column(String(32), nullable=False)
    name = Column(String(255), nullable=True)
    capacity = Column(Integer, nullable=False)
    room_type = Column(String(32), nullable=False, default="classroom")  # 'classroom', 'laboratory', 'lecture_hall', 'seminar_room', 'auditorium', 'other'
    description = Column(String(500), nullable=True)
    basic_features = Column(String(500), nullable=True)  # e.g., 'Projector, Whiteboard, Audio System'
    status = Column(String(32), nullable=False, default="active")  # 'active', 'maintenance', 'inactive'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("institution_id", "building", "room_number", name="uq_room_institution_building_number"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="rooms")
    meetings = relationship("CourseMeeting", back_populates="room")
