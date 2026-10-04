"""Add password_reset_jti column to users table for single-use reset token enforcement."""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "password_reset_jti" not in cols:
        op.add_column(
            "users",
            sa.Column("password_reset_jti", sa.String(length=128), nullable=True, default=None),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]
    if "password_reset_jti" in cols:
        op.drop_column("users", "password_reset_jti")
