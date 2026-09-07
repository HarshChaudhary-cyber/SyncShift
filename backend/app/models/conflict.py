import enum
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ConflictStatus(str, enum.Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_a_id = Column(
        BigInteger,
        ForeignKey("time_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_b_id = Column(
        BigInteger,
        ForeignKey("time_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_starting = Column(Date, nullable=False)
    overlap_minutes = Column(Integer, nullable=False)
    status = Column(
        Enum(ConflictStatus, name="conflict_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ConflictStatus.UNRESOLVED,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("block_a_id", "block_b_id", "week_starting", name="uq_conflict_pair_week"),
    )

    # Relationships
    user = relationship("User", back_populates="conflicts")
    block_a = relationship("TimeBlock", foreign_keys=[block_a_id])
    block_b = relationship("TimeBlock", foreign_keys=[block_b_id])
