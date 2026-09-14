"""Add N8 notification enhancements: read_at, priority, action_url, institution_id, timetable_version_id, delivery_status, metadata_json, timetable_changes_enabled

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Update notification_log columns
    nl_cols = [col["name"] for col in insp.get_columns("notification_log")]

    if "read_at" not in nl_cols:
        op.add_column("notification_log", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))

    if "priority" not in nl_cols:
        op.add_column("notification_log", sa.Column("priority", sa.String(length=20), server_default="INFO", nullable=False))

    if "action_url" not in nl_cols:
        op.add_column("notification_log", sa.Column("action_url", sa.String(length=255), nullable=True))

    if "institution_id" not in nl_cols:
        if is_sqlite:
            op.add_column("notification_log", sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
        else:
            op.add_column(
                "notification_log",
                sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True),
            )
        try:
            op.create_index("ix_notification_log_institution_id", "notification_log", ["institution_id"])
        except Exception:
            pass

    if "timetable_version_id" not in nl_cols:
        if is_sqlite:
            op.add_column("notification_log", sa.Column("timetable_version_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
        else:
            op.add_column(
                "notification_log",
                sa.Column("timetable_version_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("timetable_versions.id", ondelete="CASCADE"), nullable=True),
            )
        try:
            op.create_index("ix_notification_log_timetable_version_id", "notification_log", ["timetable_version_id"])
        except Exception:
            pass

    if "delivery_status" not in nl_cols:
        op.add_column("notification_log", sa.Column("delivery_status", sa.String(length=20), server_default="delivered", nullable=False))

    if "metadata_json" not in nl_cols:
        op.add_column("notification_log", sa.Column("metadata_json", sa.Text(), nullable=True))

    # 2. Update notification_prefs columns
    np_cols = [col["name"] for col in insp.get_columns("notification_prefs")]
    if "timetable_changes_enabled" not in np_cols:
        op.add_column("notification_prefs", sa.Column("timetable_changes_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    np_cols = [col["name"] for col in insp.get_columns("notification_prefs")]
    if "timetable_changes_enabled" in np_cols:
        op.drop_column("notification_prefs", "timetable_changes_enabled")

    nl_cols = [col["name"] for col in insp.get_columns("notification_log")]
    if "metadata_json" in nl_cols:
        op.drop_column("notification_log", "metadata_json")
    if "delivery_status" in nl_cols:
        op.drop_column("notification_log", "delivery_status")
    if "timetable_version_id" in nl_cols:
        try:
            op.drop_index("ix_notification_log_timetable_version_id", table_name="notification_log")
        except Exception:
            pass
        op.drop_column("notification_log", "timetable_version_id")
    if "institution_id" in nl_cols:
        try:
            op.drop_index("ix_notification_log_institution_id", table_name="notification_log")
        except Exception:
            pass
        op.drop_column("notification_log", "institution_id")
    if "action_url" in nl_cols:
        op.drop_column("notification_log", "action_url")
    if "priority" in nl_cols:
        op.drop_column("notification_log", "priority")
    if "read_at" in nl_cols:
        op.drop_column("notification_log", "read_at")
