"""Add academic resource tables: academic_courses, academic_sections, faculty_profiles, section_faculty_assignments, rooms

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. academic_courses table
    if "academic_courses" not in tables:
        op.create_table(
            "academic_courses",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("department_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("code", sa.String(length=32), nullable=False, index=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("credits", sa.Integer(), server_default="3", nullable=False),
            sa.Column("level", sa.String(length=32), server_default="undergraduate", nullable=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("min_room_capacity", sa.Integer(), nullable=True),
            sa.Column("required_room_type", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "code", name="uq_academic_course_institution_code"),
        )

    # 2. academic_sections table
    if "academic_sections" not in tables:
        op.create_table(
            "academic_sections",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("course_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_courses.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("academic_term_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("section_code", sa.String(length=32), nullable=False, index=True),
            sa.Column("capacity", sa.Integer(), server_default="30", nullable=False),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("course_id", "academic_term_id", "section_code", name="uq_academic_section_offering"),
        )

    # 3. faculty_profiles table
    if "faculty_profiles" not in tables:
        op.create_table(
            "faculty_profiles",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("department_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("employee_code", sa.String(length=64), nullable=True, index=True),
            sa.Column("title", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "user_id", name="uq_faculty_institution_user"),
        )

    # 4. section_faculty_assignments table
    if "section_faculty_assignments" not in tables:
        op.create_table(
            "section_faculty_assignments",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("section_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_sections.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("faculty_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("faculty_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("role", sa.String(length=32), server_default="instructor", nullable=False),
            sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("section_id", "faculty_id", name="uq_section_faculty_assignment"),
        )

    # 5. rooms table
    if "rooms" not in tables:
        op.create_table(
            "rooms",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("building", sa.String(length=100), nullable=False),
            sa.Column("room_number", sa.String(length=32), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=False),
            sa.Column("room_type", sa.String(length=32), server_default="classroom", nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("basic_features", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "building", "room_number", name="uq_room_institution_building_number"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "section_faculty_assignments" in tables:
        op.drop_table("section_faculty_assignments")
    if "faculty_profiles" in tables:
        op.drop_table("faculty_profiles")
    if "academic_sections" in tables:
        op.drop_table("academic_sections")
    if "rooms" in tables:
        op.drop_table("rooms")
    if "academic_courses" in tables:
        op.drop_table("academic_courses")
