"""add currency and make weekly_work_hour_limit nullable on users table

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]

    if bind.dialect.name == "sqlite":
        if "currency" not in cols:
            op.execute("ALTER TABLE users ADD COLUMN currency VARCHAR(8) DEFAULT '₹'")
    else:
        with op.batch_alter_table("users") as batch_op:
            if "currency" not in cols:
                try:
                    batch_op.add_column(
                        sa.Column("currency", sa.String(length=8), nullable=True, server_default="₹")
                    )
                except Exception:
                    pass

            try:
                batch_op.alter_column(
                    "weekly_work_hour_limit",
                    existing_type=sa.Numeric(precision=4, scale=1),
                    nullable=True,
                    server_default=None,
                )
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        with op.batch_alter_table("users") as batch_op:
            try:
                batch_op.drop_column("currency")
            except Exception:
                pass

