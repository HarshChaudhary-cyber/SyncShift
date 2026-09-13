from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint = Column(Text, unique=True, nullable=False, index=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="push_subscriptions")


class NotificationPrefs(Base):
    __tablename__ = "notification_prefs"

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    push_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    class_reminder_min = Column(Integer, default=30, nullable=False)
    shift_reminder_min = Column(Integer, default=60, nullable=False)
    study_reminder_min = Column(Integer, default=15, nullable=False)
    deadline_reminder = Column(Boolean, default=True, nullable=False)
    conflict_alerts = Column(Boolean, default=True, nullable=False)
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notification_prefs")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(50), nullable=False)  # class, shift, study, deadline, conflict, test
    title = Column(String(255), nullable=False)
    body = Column(String(500), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    channel = Column(String(20), nullable=False)  # push | email
    dedup_key = Column(String(255), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="notification_logs")
