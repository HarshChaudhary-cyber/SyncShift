"""add oauth columns and make password_hash nullable on users table

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns("users")]

    if bind.dialect.name == "sqlite":
        new_cols = [
            ("google_id", "VARCHAR(255)"),
            ("facebook_id", "VARCHAR(255)"),
            ("apple_id", "VARCHAR(255)"),
            ("oauth_provider", "VARCHAR(50)"),
            ("avatar_url", "VARCHAR(500)"),
            ("display_name", "VARCHAR(255)"),
        ]
        for cname, ctype in new_cols:
            if cname not in cols:
                op.execute(f"ALTER TABLE users ADD COLUMN {cname} {ctype}")
    else:
        with op.batch_alter_table("users") as batch_op:
            if "google_id" not in cols:
                try:
                    batch_op.add_column(sa.Column("google_id", sa.String(length=255), nullable=True))
                    batch_op.create_unique_constraint("uq_users_google_id", ["google_id"])
                except Exception:
                    pass

            if "facebook_id" not in cols:
                try:
                    batch_op.add_column(sa.Column("facebook_id", sa.String(length=255), nullable=True))
                    batch_op.create_unique_constraint("uq_users_facebook_id", ["facebook_id"])
                except Exception:
                    pass

            if "apple_id" not in cols:
                try:
                    batch_op.add_column(sa.Column("apple_id", sa.String(length=255), nullable=True))
                    batch_op.create_unique_constraint("uq_users_apple_id", ["apple_id"])
                except Exception:
                    pass

            if "oauth_provider" not in cols:
                try:
                    batch_op.add_column(sa.Column("oauth_provider", sa.String(length=50), nullable=True))
                except Exception:
                    pass

            if "avatar_url" not in cols:
                try:
                    batch_op.add_column(sa.Column("avatar_url", sa.String(length=500), nullable=True))
                except Exception:
                    pass

            if "display_name" not in cols:
                try:
                    batch_op.add_column(sa.Column("display_name", sa.String(length=255), nullable=True))
                except Exception:
                    pass

            try:
                batch_op.alter_column(
                    "password_hash",
                    existing_type=sa.String(length=255),
                    nullable=True,
                )
            except Exception:
                pass

            try:
                batch_op.alter_column(
                    "name",
                    existing_type=sa.String(length=120),
                    nullable=True,
                )
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        with op.batch_alter_table("users") as batch_op:
            for col in ["google_id", "facebook_id", "apple_id", "oauth_provider", "avatar_url", "display_name"]:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass

