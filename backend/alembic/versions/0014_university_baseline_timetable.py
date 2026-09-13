"""Add timetables and course_meetings tables for university baseline timetable

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. timetables table
    if "timetables" not in tables:
        op.create_table(
            "timetables",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("academic_term_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "academic_term_id", "name", name="uq_timetable_institution_term_name"),
        )

    # 2. course_meetings table
    if "course_meetings" not in tables:
        op.create_table(
            "course_meetings",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("timetable_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("section_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_sections.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("academic_term_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("day_of_week", sa.SmallInteger(), nullable=False, index=True),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("room_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("faculty_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("faculty_profiles.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("meeting_type", sa.String(length=32), server_default="lecture", nullable=False),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "course_meetings" in tables:
        op.drop_table("course_meetings")
    if "timetables" in tables:
        op.drop_table("timetables")
