"""Add student profile, section enrollments, availability, constraints, and preferences tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. student_profiles table
    if "student_profiles" not in tables:
        op.create_table(
            "student_profiles",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("department_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("student_number", sa.String(length=64), nullable=True, index=True),
            sa.Column("program", sa.String(length=255), nullable=True),
            sa.Column("year_of_study", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "user_id", name="uq_student_profile_inst_user"),
        )

    # 2. section_enrollments table
    if "section_enrollments" not in tables:
        op.create_table(
            "section_enrollments",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("student_profile_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("student_profiles.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("section_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("academic_sections.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("enrollment_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("dropped_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("section_id", "student_id", name="uq_section_enrollment_student_section"),
        )

    # 3. student_availabilities table
    if "student_availabilities" not in tables:
        op.create_table(
            "student_availabilities",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("is_available", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_student_avail_day"),
            sa.CheckConstraint("start_time < end_time", name="ck_student_avail_times"),
        )

    # 4. student_constraints table
    if "student_constraints" not in tables:
        op.create_table(
            "student_constraints",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("constraint_type", sa.String(length=64), nullable=False),
            sa.Column("is_hard", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("day_of_week", sa.SmallInteger(), nullable=True),
            sa.Column("time_value", sa.Time(), nullable=True),
            sa.Column("int_value", sa.Integer(), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)", name="ck_student_constraint_day"),
        )

    # 5. student_preferences table
    if "student_preferences" not in tables:
        op.create_table(
            "student_preferences",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("preferred_time_of_day", sa.String(length=32), server_default="any", nullable=False),
            sa.Column("schedule_density", sa.String(length=32), server_default="balanced", nullable=False),
            sa.Column("preferred_break_duration_minutes", sa.Integer(), server_default="30", nullable=False),
            sa.Column("max_campus_days_per_week", sa.Integer(), nullable=True),
            sa.Column("preferred_days_off", sa.String(length=32), nullable=True),
            sa.Column("work_study_balance_weight", sa.Integer(), server_default="3", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "student_preferences" in tables:
        op.drop_table("student_preferences")
    if "student_constraints" in tables:
        op.drop_table("student_constraints")
    if "student_availabilities" in tables:
        op.drop_table("student_availabilities")
    if "section_enrollments" in tables:
        op.drop_table("section_enrollments")
    if "student_profiles" in tables:
        op.drop_table("student_profiles")
