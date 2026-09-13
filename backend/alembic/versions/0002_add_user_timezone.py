"""add timezone column to users table with default NULL

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure timezone column exists and is nullable with default NULL
    with op.batch_alter_table("users") as batch_op:
        try:
            batch_op.alter_column(
                "timezone",
                existing_type=sa.String(length=64),
                nullable=True,
                server_default=None,
            )
        except Exception:
            batch_op.add_column(
                sa.Column("timezone", sa.String(length=64), nullable=True, server_default=None)
            )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "timezone",
            existing_type=sa.String(length=64),
            nullable=False,
            server_default="Europe/London",
        )
