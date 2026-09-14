"""
Assistant Conversation & Message Models for SyncShift.
Provides persistent, tenant-isolated conversation history for both Student and University Administrator.
"""
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id = Column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger().with_variant(Integer(), "sqlite"),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_id = Column(
        BigInteger().with_variant(Integer(), "sqlite"),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), default="New Conversation", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    institution = relationship("Institution")
    messages = relationship(
        "AssistantMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at.asc()",
    )


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True)
    conversation_id = Column(
        BigInteger().with_variant(Integer(), "sqlite"),
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    action_data = Column(Text, nullable=True)  # JSON-serialized ActionPreview / card
    tool_calls = Column(Text, nullable=True)  # JSON-serialized tool call metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("AssistantConversation", back_populates="messages")
