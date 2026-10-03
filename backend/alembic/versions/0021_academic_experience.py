"""Role experiences, explicit completion and selected event audiences (additive)."""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable ownership preserves standalone legacy workspaces without guessing a tenant.
    with op.batch_alter_table("class_workspaces") as batch:
        batch.add_column(sa.Column("institution_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("course_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_workspace_institution", "institutions", ["institution_id"], ["id"])
        batch.create_foreign_key("fk_workspace_course", "academic_courses", ["course_id"], ["id"])
    op.execute("UPDATE class_workspaces SET institution_id=(SELECT institution_id FROM academic_sections WHERE id=class_workspaces.section_id), course_id=(SELECT course_id FROM academic_sections WHERE id=class_workspaces.section_id) WHERE section_id IS NOT NULL")
    op.create_table("professional_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("introduction", sa.Text(), nullable=False),
        sa.Column("specializations", sa.String(1000), nullable=False),
        sa.Column("professional_phone", sa.String(64), nullable=False),
        sa.Column("office_hours", sa.String(500), nullable=False),
        sa.Column("office_location", sa.String(255), nullable=False))
    op.create_table("academic_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), sa.ForeignKey("institutions.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False), sa.Column("role", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False), sa.Column("accepted_at", sa.DateTime()))
    op.create_table("lecture_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), nullable=False, index=True),
        sa.Column("event_key", sa.String(64), nullable=False), sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("class_id", "event_key", "event_date", name="uq_lecture_occurrence"))
    op.create_table("academic_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), sa.ForeignKey("institutions.id"), index=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), index=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False), sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_table("shared_appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("location", sa.String(255), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False), sa.Column("start_time", sa.String(5), nullable=False),
        sa.Column("end_time", sa.String(5), nullable=False))
    op.create_table("appointment_audiences",
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("shared_appointments.id"), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("class_workspaces.id"), primary_key=True))


def downgrade():
    raise RuntimeError("Restore a reviewed backup; do not delete academic history or existing user data.")
