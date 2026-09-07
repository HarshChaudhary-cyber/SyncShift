"""Initial SyncShift Schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-06 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. users
    # -------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Europe/London", nullable=False),
        sa.Column("weekly_work_hour_limit", sa.Numeric(precision=4, scale=1), server_default="20.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # -------------------------------------------------------------------------
    # 2. courses
    # -------------------------------------------------------------------------
    op.create_table(
        "courses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=32), server_default="#2563eb", nullable=False),
        sa.Column("term", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_courses_user_id", "courses", ["user_id"])

    # -------------------------------------------------------------------------
    # 3. time_blocks
    # -------------------------------------------------------------------------
    op.create_table(
        "time_blocks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),  # 'class' | 'shift'
        sa.Column("status", sa.String(length=16), server_default="enrolled", nullable=False),  # 'enrolled' | 'tentative' | 'dropped'
        sa.Column("course_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("specific_date", sa.Date(), nullable=True),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_overnight", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("is_flexible", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("hourly_wage", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("is_imported", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)", name="check_day_of_week_range"),
        sa.CheckConstraint("duration_minutes > 0", name="check_positive_duration"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_time_blocks_user_dow", "time_blocks", ["user_id", "day_of_week"])
    op.create_index("idx_time_blocks_active", "time_blocks", ["user_id", "status"])
    op.create_index("idx_time_blocks_deleted", "time_blocks", ["deleted"])

    # -------------------------------------------------------------------------
    # 4. block_overrides
    # -------------------------------------------------------------------------
    op.create_table(
        "block_overrides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("time_block_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("original_date", sa.Date(), nullable=False),
        sa.Column("override_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["time_block_id"], ["time_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("time_block_id", "original_date", name="uq_block_override_occurrence"),
    )
    op.create_index("idx_overrides_lookup", "block_overrides", ["user_id", "override_date"])

    # -------------------------------------------------------------------------
    # 5. conflicts
    # -------------------------------------------------------------------------
    op.create_table(
        "conflicts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("block_a_id", sa.BigInteger(), nullable=False),
        sa.Column("block_b_id", sa.BigInteger(), nullable=False),
        sa.Column("week_starting", sa.Date(), nullable=False),
        sa.Column("overlap_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="unresolved", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["block_a_id"], ["time_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["block_b_id"], ["time_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("block_a_id", "block_b_id", "week_starting", name="uq_conflict_pair_week"),
    )
    op.create_index("idx_conflicts_user_unresolved", "conflicts", ["user_id", "status"])


def downgrade() -> None:
    op.drop_table("conflicts")
    op.drop_table("block_overrides")
    op.drop_table("time_blocks")
    op.drop_table("courses")
    op.drop_table("users")
