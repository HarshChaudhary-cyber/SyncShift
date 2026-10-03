"""Add class workspaces without replacing academic or personal records.

Revision ID: 0020
Revises: 0019
"""
import secrets
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("class_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("join_code", sa.String(64), nullable=False, unique=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("academic_sections.id"), unique=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_table("class_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.UniqueConstraint("class_id", "user_id", name="uq_class_member"))
    op.create_table("class_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("pending_json", sa.Text()))
    op.create_table("class_announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_table("class_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime()))
    for name in ("class_members", "class_events", "class_announcements", "class_invitations"):
        op.create_index(f"ix_{name}_class_id", name, ["class_id"])
    op.create_index("ix_class_members_user_id", "class_members", ["user_id"])
    # Only wrappers are added. Membership is resolved from the original records so
    # dropped enrollments/revoked faculty assignments do not retain stale access.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT s.id, s.section_code, c.code, c.name FROM academic_sections s JOIN academic_courses c ON c.id=s.course_id WHERE s.deleted_at IS NULL AND c.deleted_at IS NULL")).mappings()
    for row in rows:
        conn.execute(sa.text("INSERT INTO class_workspaces (name, description, join_code, section_id) VALUES (:name, '', :code, :section)"),
            {"name": f"{row['code']} · {row['name']} ({row['section_code']})"[:160], "code": secrets.token_urlsafe(12), "section": row["id"]})


def downgrade():
    raise RuntimeError("This additive migration preserves user data. Restore a reviewed backup instead of deleting class workspaces.")
