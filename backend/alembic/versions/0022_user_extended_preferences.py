"""Add user_preferences table for week start, time format, calendar view, motion, and planning hours."""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "user_preferences" not in tables:
        op.create_table(
            "user_preferences",
            sa.Column(
                "user_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("week_starts_on", sa.String(length=10), nullable=False, server_default="monday"),
            sa.Column("time_format", sa.String(length=5), nullable=False, server_default="12h"),
            sa.Column("default_calendar_view", sa.String(length=10), nullable=False, server_default="week"),
            sa.Column("reduced_motion", sa.String(length=10), nullable=False, server_default="system"),
            sa.Column("planning_hours_start", sa.Integer(), nullable=False, server_default="9"),
            sa.Column("planning_hours_end", sa.Integer(), nullable=False, server_default="18"),
            sa.Column("preferred_session_duration", sa.Integer(), nullable=False, server_default="45"),
            sa.Column("preferred_break_duration", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    if "user_preferences" in tables:
        op.drop_table("user_preferences")
