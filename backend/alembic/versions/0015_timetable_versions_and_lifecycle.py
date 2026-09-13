"""Add timetable_versions table and version relationships

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Create timetable_versions table
    if "timetable_versions" not in tables:
        op.create_table(
            "timetable_versions",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True, index=True),
            sa.Column("institution_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("timetable_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("timetables.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
            sa.Column("change_summary", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("timetable_id", "version_number", name="uq_timetable_version_number"),
        )

    is_sqlite = bind.dialect.name == "sqlite"

    # 2. Add published_version_id to timetables
    tt_columns = [col["name"] for col in insp.get_columns("timetables")]
    if "published_version_id" not in tt_columns:
        if is_sqlite:
            op.add_column(
                "timetables",
                sa.Column("published_version_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
            )
        else:
            op.add_column(
                "timetables",
                sa.Column(
                    "published_version_id",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                    sa.ForeignKey("timetable_versions.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )

    # 3. Add version_id to course_meetings
    cm_columns = [col["name"] for col in insp.get_columns("course_meetings")]
    if "version_id" not in cm_columns:
        if is_sqlite:
            op.add_column(
                "course_meetings",
                sa.Column("version_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
            )
        else:
            op.add_column(
                "course_meetings",
                sa.Column(
                    "version_id",
                    sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                    sa.ForeignKey("timetable_versions.id", ondelete="CASCADE"),
                    nullable=True,
                ),
            )
        op.create_index("ix_course_meetings_version_id", "course_meetings", ["version_id"])



    # 4. Data backfill: Ensure every existing timetable has at least Version 1
    # and existing course_meetings are linked to it.
    conn = bind
    tt_tbl = table(
        "timetables",
        column("id", sa.BigInteger),
        column("institution_id", sa.BigInteger),
        column("status", sa.String),
        column("published_version_id", sa.BigInteger),
    )
    tv_tbl = table(
        "timetable_versions",
        column("id", sa.BigInteger),
        column("institution_id", sa.BigInteger),
        column("timetable_id", sa.BigInteger),
        column("version_number", sa.Integer),
        column("name", sa.String),
        column("status", sa.String),
    )
    cm_tbl = table(
        "course_meetings",
        column("id", sa.BigInteger),
        column("timetable_id", sa.BigInteger),
        column("version_id", sa.BigInteger),
    )

    existing_timetables = conn.execute(select(tt_tbl.c.id, tt_tbl.c.institution_id, tt_tbl.c.status, tt_tbl.c.published_version_id)).fetchall()
    for row in existing_timetables:
        tt_id, inst_id, tt_status, pub_ver_id = row[0], row[1], row[2], row[3]
        ver_count = conn.execute(select(sa.func.count(tv_tbl.c.id)).where(tv_tbl.c.timetable_id == tt_id)).scalar() or 0
        if ver_count == 0:
            is_active = (tt_status == "active")
            ver_status = "published" if is_active else "draft"
            res = conn.execute(
                tv_tbl.insert().values(
                    institution_id=inst_id,
                    timetable_id=tt_id,
                    version_number=1,
                    name="Version 1 — Baseline",
                    status=ver_status,
                )
            )
            v1_id = None
            if hasattr(res, "inserted_primary_key") and res.inserted_primary_key:
                v1_id = res.inserted_primary_key[0]
            if not v1_id:
                v1_id = conn.execute(select(tv_tbl.c.id).where(tv_tbl.c.timetable_id == tt_id, tv_tbl.c.version_number == 1)).scalar()

            if is_active and v1_id:
                conn.execute(
                    tt_tbl.update().where(tt_tbl.c.id == tt_id).values(published_version_id=v1_id)
                )
            if v1_id:
                conn.execute(
                    cm_tbl.update().where(cm_tbl.c.timetable_id == tt_id, cm_tbl.c.version_id.is_(None)).values(version_id=v1_id)
                )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "course_meetings" in tables:
        cm_columns = [col["name"] for col in insp.get_columns("course_meetings")]
        if "version_id" in cm_columns:
            try:
                op.drop_index("ix_course_meetings_version_id", table_name="course_meetings")
            except Exception:
                pass
            op.drop_column("course_meetings", "version_id")

    if "timetables" in tables:
        tt_columns = [col["name"] for col in insp.get_columns("timetables")]
        if "published_version_id" in tt_columns:
            op.drop_column("timetables", "published_version_id")

    if "timetable_versions" in tables:
        op.drop_table("timetable_versions")

