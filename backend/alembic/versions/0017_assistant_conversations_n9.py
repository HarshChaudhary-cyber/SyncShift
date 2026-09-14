"""Add assistant_conversations and assistant_messages tables for N9

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Create assistant_conversations
    if "assistant_conversations" not in tables:
        op.create_table(
            "assistant_conversations",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("title", sa.String(length=255), server_default="New Conversation", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # 2. Create assistant_messages
    if "assistant_messages" not in tables:
        op.create_table(
            "assistant_messages",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("conversation_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("action_data", sa.Text(), nullable=True),
            sa.Column("tool_calls", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "assistant_messages" in tables:
        op.drop_table("assistant_messages")
    if "assistant_conversations" in tables:
        op.drop_table("assistant_conversations")
