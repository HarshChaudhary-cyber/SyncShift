"""add priority, preferred_duration, and completed_hours to study_tasks

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "study_tasks" in tables:
        cols = [c["name"] for c in insp.get_columns("study_tasks")]

        if bind.dialect.name == "sqlite":
            if "priority" not in cols:
                op.execute("ALTER TABLE study_tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'")
            if "preferred_duration" not in cols:
                op.execute("ALTER TABLE study_tasks ADD COLUMN preferred_duration INTEGER DEFAULT 90")
            if "completed_hours" not in cols:
                op.execute("ALTER TABLE study_tasks ADD COLUMN completed_hours NUMERIC(5, 2) DEFAULT 0.0")
        else:
            with op.batch_alter_table("study_tasks") as batch_op:
                if "priority" not in cols:
                    batch_op.add_column(
                        sa.Column("priority", sa.String(length=20), nullable=True, server_default="medium")
                    )
                if "preferred_duration" not in cols:
                    batch_op.add_column(
                        sa.Column("preferred_duration", sa.Integer(), nullable=True, server_default="90")
                    )
                if "completed_hours" not in cols:
                    batch_op.add_column(
                        sa.Column("completed_hours", sa.Numeric(precision=5, scale=2), nullable=True, server_default="0.0")
                    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        with op.batch_alter_table("study_tasks") as batch_op:
            for col in ["priority", "preferred_duration", "completed_hours"]:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass
