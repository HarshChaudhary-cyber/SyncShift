"""add microsoft_id column to users table

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]

    if "microsoft_id" not in cols:
        if bind.dialect.name == "sqlite":
            op.execute("ALTER TABLE users ADD COLUMN microsoft_id VARCHAR(255)")
            try:
                op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_microsoft_id ON users (microsoft_id)")
            except Exception:
                pass
        else:
            with op.batch_alter_table("users") as batch_op:
                batch_op.add_column(sa.Column("microsoft_id", sa.String(length=255), nullable=True))
                batch_op.create_unique_constraint("uq_users_microsoft_id", ["microsoft_id"])
                batch_op.create_index("ix_users_microsoft_id", ["microsoft_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]

    if "microsoft_id" in cols:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("microsoft_id")
