"""add recurrence_interval to time_blocks and end_time, title, location to block_overrides

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Update time_blocks
    if "time_blocks" in tables:
        tb_cols = [c["name"] for c in insp.get_columns("time_blocks")]
        if bind.dialect.name == "sqlite":
            if "recurrence_interval" not in tb_cols:
                op.execute("ALTER TABLE time_blocks ADD COLUMN recurrence_interval INTEGER DEFAULT 1 NOT NULL")
        else:
            with op.batch_alter_table("time_blocks") as batch_op:
                if "recurrence_interval" not in tb_cols:
                    batch_op.add_column(
                        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1")
                    )

    # 2. Update block_overrides
    if "block_overrides" in tables:
        bo_cols = [c["name"] for c in insp.get_columns("block_overrides")]
        if bind.dialect.name == "sqlite":
            if "end_time" not in bo_cols:
                op.execute("ALTER TABLE block_overrides ADD COLUMN end_time TIME")
            if "title" not in bo_cols:
                op.execute("ALTER TABLE block_overrides ADD COLUMN title VARCHAR(255)")
            if "location" not in bo_cols:
                op.execute("ALTER TABLE block_overrides ADD COLUMN location VARCHAR(255)")
        else:
            with op.batch_alter_table("block_overrides") as batch_op:
                if "end_time" not in bo_cols:
                    batch_op.add_column(sa.Column("end_time", sa.Time(), nullable=True))
                if "title" not in bo_cols:
                    batch_op.add_column(sa.Column("title", sa.String(length=255), nullable=True))
                if "location" not in bo_cols:
                    batch_op.add_column(sa.Column("location", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        with op.batch_alter_table("block_overrides") as batch_op:
            for col in ["end_time", "title", "location"]:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass
        with op.batch_alter_table("time_blocks") as batch_op:
            try:
                batch_op.drop_column("recurrence_interval")
            except Exception:
                pass
