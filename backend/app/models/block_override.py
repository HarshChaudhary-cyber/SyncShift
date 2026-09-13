from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class BlockOverride(Base):
    __tablename__ = "block_overrides"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    time_block_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("time_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_date = Column(Date, nullable=False)
    override_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("time_block_id", "original_date", name="uq_block_override_occurrence"),
    )

    # Relationships
    user = relationship("User", back_populates="overrides")
    time_block = relationship("TimeBlock", back_populates="overrides")
