"""add user settings columns (currency, language, theme) and soft delete (deleted_at)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]

    if bind.dialect.name == "sqlite":
        if "currency" not in cols:
            op.execute("ALTER TABLE users ADD COLUMN currency VARCHAR(8) DEFAULT 'INR'")
        if "language" not in cols:
            op.execute("ALTER TABLE users ADD COLUMN language VARCHAR(5) DEFAULT 'en'")
        if "theme" not in cols:
            op.execute("ALTER TABLE users ADD COLUMN theme VARCHAR(10) DEFAULT 'dark'")
        if "deleted_at" not in cols:
            op.execute("ALTER TABLE users ADD COLUMN deleted_at DATETIME")
    else:
        with op.batch_alter_table("users") as batch_op:
            if "currency" not in cols:
                batch_op.add_column(
                    sa.Column("currency", sa.String(length=8), nullable=True, server_default="INR")
                )
            if "language" not in cols:
                batch_op.add_column(
                    sa.Column("language", sa.String(length=5), nullable=True, server_default="en")
                )
            if "theme" not in cols:
                batch_op.add_column(
                    sa.Column("theme", sa.String(length=10), nullable=True, server_default="dark")
                )
            if "deleted_at" not in cols:
                batch_op.add_column(
                    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, server_default=None)
                )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        with op.batch_alter_table("users") as batch_op:
            for col in ["language", "theme", "deleted_at"]:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass
