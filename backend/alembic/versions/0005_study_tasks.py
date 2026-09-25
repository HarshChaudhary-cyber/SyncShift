"""add study_tasks table and study_task_id to time_blocks

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Create study_tasks table if it doesn't exist
    if "study_tasks" not in tables:
        op.create_table(
            "study_tasks",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
            sa.Column("total_hours_required", sa.Numeric(precision=5, scale=2), nullable=False),
            sa.Column("deadline", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_study_tasks_user_id", "study_tasks", ["user_id"])
        op.create_index("ix_study_tasks_id", "study_tasks", ["id"])

    # 2. Add study_task_id column to time_blocks table if missing
    tb_cols = [c["name"] for c in insp.get_columns("time_blocks")]
    if "study_task_id" not in tb_cols:
        if bind.dialect.name == "sqlite":
            op.execute("ALTER TABLE time_blocks ADD COLUMN study_task_id BIGINT REFERENCES study_tasks(id) ON DELETE CASCADE")
        else:
            with op.batch_alter_table("time_blocks") as batch_op:
                try:
                    batch_op.add_column(
                        sa.Column("study_task_id", sa.BigInteger(), sa.ForeignKey("study_tasks.id", ondelete="CASCADE"), nullable=True)
                    )
                    batch_op.create_index("ix_time_blocks_study_task_id", ["study_task_id"])
                except Exception:
                    pass



def downgrade() -> None:
    with op.batch_alter_table("time_blocks") as batch_op:
        try:
            batch_op.drop_index("ix_time_blocks_study_task_id")
            batch_op.drop_column("study_task_id")
        except Exception:
            pass

    op.drop_index("ix_study_tasks_id", table_name="study_tasks")
    op.drop_index("ix_study_tasks_user_id", table_name="study_tasks")
    op.drop_table("study_tasks")
