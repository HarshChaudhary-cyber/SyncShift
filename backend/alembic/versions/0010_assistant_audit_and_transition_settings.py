"""Add minimum_transition_minutes to users and create audit_logs table

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Add minimum_transition_minutes to users
    if "users" in tables:
        user_cols = [c["name"] for c in insp.get_columns("users")]
        if "minimum_transition_minutes" not in user_cols:
            if bind.dialect.name == "sqlite":
                op.execute("ALTER TABLE users ADD COLUMN minimum_transition_minutes INTEGER DEFAULT 15 NOT NULL")
            else:
                with op.batch_alter_table("users") as batch_op:
                    batch_op.add_column(
                        sa.Column("minimum_transition_minutes", sa.Integer(), nullable=False, server_default="15")
                    )

    # 2. Create audit_logs table if not present
    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("action", sa.String(length=64), nullable=False, index=True),
            sa.Column("entity_type", sa.String(length=64), nullable=True),
            sa.Column("entity_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "audit_logs" in tables:
        op.drop_table("audit_logs")

    if "users" in tables and bind.dialect.name != "sqlite":
        with op.batch_alter_table("users") as batch_op:
            try:
                batch_op.drop_column("minimum_transition_minutes")
            except Exception:
                pass
