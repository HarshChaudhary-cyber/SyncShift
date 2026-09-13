"""Add university foundation tables: institutions, institution_memberships, departments, academic_terms

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. institutions table
    if "institutions" not in tables:
        op.create_table(
            "institutions",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False, unique=True, index=True),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("timezone", sa.String(length=64), server_default="Europe/London", nullable=False),
            sa.Column("email_domain", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # 2. institution_memberships table
    if "institution_memberships" not in tables:
        op.create_table(
            "institution_memberships",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("role", sa.String(length=32), server_default="student", nullable=False),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("user_id", "institution_id", name="uq_user_institution_membership"),
        )

    # 3. departments table
    if "departments" not in tables:
        op.create_table(
            "departments",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("code", sa.String(length=32), nullable=False, index=True),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("institution_id", "code", name="uq_department_institution_code"),
        )

    # 4. academic_terms table
    if "academic_terms" not in tables:
        op.create_table(
            "academic_terms",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("academic_year", sa.String(length=32), nullable=False),
            sa.Column("term_type", sa.String(length=32), server_default="semester", nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="upcoming", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "academic_terms" in tables:
        op.drop_table("academic_terms")
    if "departments" in tables:
        op.drop_table("departments")
    if "institution_memberships" in tables:
        op.drop_table("institution_memberships")
    if "institutions" in tables:
        op.drop_table("institutions")
