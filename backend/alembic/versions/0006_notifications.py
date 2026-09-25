"""add push_subscriptions, notification_prefs, and notification_log tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. push_subscriptions
    if "push_subscriptions" not in tables:
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("endpoint", sa.Text(), unique=True, nullable=False),
            sa.Column("p256dh", sa.Text(), nullable=False),
            sa.Column("auth", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_push_subscriptions_id", "push_subscriptions", ["id"])
        op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
        op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)

    # 2. notification_prefs
    if "notification_prefs" not in tables:
        op.create_table(
            "notification_prefs",
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
            sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("class_reminder_min", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("shift_reminder_min", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("study_reminder_min", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("deadline_reminder", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("conflict_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("quiet_hours_start", sa.Time(), nullable=True),
            sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        )

    # 3. notification_log
    if "notification_log" not in tables:
        op.create_table(
            "notification_log",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.String(length=500), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("channel", sa.String(length=20), nullable=False),
            sa.Column("dedup_key", sa.String(length=255), nullable=True),
        )
        op.create_index("ix_notification_log_id", "notification_log", ["id"])
        op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"])
        op.create_index("ix_notification_log_dedup_key", "notification_log", ["dedup_key"])



def downgrade() -> None:
    op.drop_index("ix_notification_log_dedup_key", table_name="notification_log")
    op.drop_index("ix_notification_log_user_id", table_name="notification_log")
    op.drop_index("ix_notification_log_id", table_name="notification_log")
    op.drop_table("notification_log")

    op.drop_table("notification_prefs")

    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
