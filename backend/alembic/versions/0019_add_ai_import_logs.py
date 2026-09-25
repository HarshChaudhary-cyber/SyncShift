"""add ai_import_logs table

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "ai_import_logs" not in tables:
        op.create_table(
            "ai_import_logs",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
            sa.Column("file_type", sa.String(length=32), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("events_extracted", sa.Integer(), server_default="0", nullable=False),
            sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_import_logs_id", "ai_import_logs", ["id"])
        op.create_index("ix_ai_import_logs_user_id", "ai_import_logs", ["user_id"])
        op.create_index("ix_ai_import_logs_created_at", "ai_import_logs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "ai_import_logs" in tables:
        op.drop_index("ix_ai_import_logs_created_at", table_name="ai_import_logs")
        op.drop_index("ix_ai_import_logs_user_id", table_name="ai_import_logs")
        op.drop_index("ix_ai_import_logs_id", table_name="ai_import_logs")
        op.drop_table("ai_import_logs")
