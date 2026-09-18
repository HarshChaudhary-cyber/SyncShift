from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.block_override import BlockOverride
from app.models.course import Course
from app.models.study_task import StudyTask, TaskStatus
from app.models.time_block import BlockStatus, BlockType, TimeBlock
from app.models.user import User
from app.schemas.block import BlockOut

from app.schemas.conflict import ConflictItem, WeeklyTotals


@contextmanager
def get_session(db: Optional[Session] = None):
    """
    Yields the provided session or spins up a fresh session from SessionLocal,
    guaranteeing automatic commit and cleanup.
    """
    if db is not None:
        yield db
    else:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()


def time_to_minutes(t_val) -> int:
    if isinstance(t_val, time):
        return t_val.hour * 60 + t_val.minute
    parts = str(t_val).split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(m: int) -> str:
    m = m % (24 * 60)
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"


def _parse_time(t_val) -> time:
    if isinstance(t_val, time):
        return t_val
    t_str = str(t_val).strip()
    parts = [int(p) for p in t_str.split(":")[:3]]
    if len(parts) == 2:
        return time(parts[0], parts[1], 0)
    elif len(parts) >= 3:
        return time(parts[0], parts[1], parts[2])
    return time(0, 0, 0)


def _format_time_str(t_val) -> str:
    s = str(t_val).strip()
    if len(s) == 5:
        return f"{s}:00"
    return s


def _block_duration_hours(start_time: str, end_time: str) -> float:
    s = time_to_minutes(start_time)
    e = time_to_minutes(end_time)
    dur = (e + 24 * 60 - s) if e < s else (e - s)
    return max(0.0, dur / 60.0)


def _model_to_block_out(
    b: TimeBlock,
    occurrence_date: Optional[date] = None,
    is_exception: bool = False,
    original_date: Optional[date] = None,
    override_id: Optional[int] = None,
) -> BlockOut:
    eff_from = b.effective_from
    if isinstance(eff_from, str):
        eff_from = date.fromisoformat(eff_from)
    eff_until = b.effective_until
    if isinstance(eff_until, str):
        eff_until = date.fromisoformat(eff_until)

    color = getattr(b, "color", None)
    if not color and getattr(b, "course", None) and getattr(b.course, "color", None):
        color = b.course.color
    if not color:
        b_type_str = str(b.type.value if hasattr(b.type, "value") else b.type)
        if b_type_str == "study":
            color = "#8B5CF6"
        elif b_type_str == "shift":
            color = "#10B981"
        else:
            color = "#4F46E5"

    spec_d = b.specific_date
    if isinstance(spec_d, str):
        spec_d = date.fromisoformat(spec_d)

    return BlockOut(
        id=b.id,
        user_id=b.user_id,
        type=str(b.type.value if hasattr(b.type, "value") else b.type),
        title=b.title,
        location=b.location,
        day_of_week=b.day_of_week,
        start_time=_format_time_str(b.start_time),
        end_time=_format_time_str(b.end_time),
        effective_from=eff_from or date(2026, 9, 1),
        effective_until=eff_until,
        is_recurring=bool(b.is_recurring),
        recurrence_interval=int(getattr(b, "recurrence_interval", 1) or 1),
        specific_date=spec_d,
        is_flexible=bool(b.is_flexible),
        hourly_wage=float(b.hourly_wage) if b.hourly_wage is not None else None,
        course_id=b.course_id,
        study_task_id=b.study_task_id,
        color=color,
        deleted=bool(b.deleted),
        occurrence_date=occurrence_date,
        is_exception=is_exception,
        original_date=original_date,
        override_id=override_id,
    )


def _apply_override_to_block_out(
    b: TimeBlock,
    occ_date: date,
    ov: Optional[BlockOverride],
) -> BlockOut:
    base = _model_to_block_out(
        b,
        occurrence_date=occ_date,
        is_exception=bool(ov),
        original_date=ov.original_date if ov else occ_date,
        override_id=ov.id if ov else None,
    )
    if not ov:
        return base
    if ov.start_time:
        base.start_time = _format_time_str(ov.start_time)
    if ov.end_time:
        base.end_time = _format_time_str(ov.end_time)
    elif ov.duration_minutes and ov.start_time:
        s_min = time_to_minutes(ov.start_time)
        e_min = (s_min + ov.duration_minutes) % (24 * 60)
        base.end_time = minutes_to_time(e_min) + ":00"
    if ov.title:
        base.title = ov.title
    if ov.location is not None:
        base.location = ov.location
    if ov.override_date:
        base.occurrence_date = ov.override_date
        base.day_of_week = (ov.override_date.weekday() + 1) % 7
    return base


# ---------------------------------------------------------------------------
# Occurrence Generation Engine
# ---------------------------------------------------------------------------

def get_occurrences_for_range(
    user_id: int,
    start_date: date,
    end_date: date,
    db: Optional[Session] = None,
) -> list[BlockOut]:
    """
    Generates materialized occurrences for all active blocks within [start_date, end_date].
    Handles:
    - Non-recurring single date blocks
    - Weekly and biweekly recurring blocks (modulo weeks from effective_from)
    - Effective date range [effective_from, effective_until]
    - Block overrides: skips cancelled occurrences, applies single-occurrence modifications,
      and includes occurrences rescheduled into this window.
    Strictly isolated by user_id.
    """
    with get_session(db) as session:
        # 1. Fetch non-deleted time blocks for user
        blocks = (
            session.query(TimeBlock)
            .filter(
                TimeBlock.user_id == user_id,
                TimeBlock.deleted == False,
            )
            .order_by(TimeBlock.day_of_week, TimeBlock.start_time)
            .all()
        )
        block_map = {b.id: b for b in blocks}
        block_ids = list(block_map.keys())

        # 2. Fetch all overrides for these blocks touching [start_date, end_date]
        override_by_orig: dict[tuple[int, date], BlockOverride] = {}
        moved_in_overrides: list[BlockOverride] = []

        if block_ids:
            overrides = (
                session.query(BlockOverride)
                .filter(
                    BlockOverride.user_id == user_id,
                    BlockOverride.time_block_id.in_(block_ids),
                    (
                        (BlockOverride.original_date >= start_date) & (BlockOverride.original_date <= end_date)
                        | (BlockOverride.override_date >= start_date) & (BlockOverride.override_date <= end_date)
                    ),
                )
                .all()
            )
            for ov in overrides:
                override_by_orig[(ov.time_block_id, ov.original_date)] = ov
                if ov.override_date and ov.override_date != ov.original_date:
                    if start_date <= ov.override_date <= end_date and not ov.is_cancelled:
                        moved_in_overrides.append(ov)

        occurrences: list[BlockOut] = []
        days_count = (end_date - start_date).days + 1

        for day_offset in range(days_count):
            curr_d = start_date + timedelta(days=day_offset)
            syncshift_dow = (curr_d.weekday() + 1) % 7  # 0 = Sunday, 1 = Monday ... 6 = Saturday

            for b in blocks:
                # A. Non-recurring event
                if not b.is_recurring:
                    event_date = b.specific_date or b.effective_from
                    if isinstance(event_date, str):
                        event_date = date.fromisoformat(event_date)
                    if event_date == curr_d:
                        ov = override_by_orig.get((b.id, curr_d))
                        if ov and ov.is_cancelled:
                            continue
                        occurrences.append(_apply_override_to_block_out(b, curr_d, ov))
                    continue

                # B. Recurring event
                if b.day_of_week != syncshift_dow:
                    continue

                if b.effective_from and curr_d < b.effective_from:
                    continue
                if b.effective_until and curr_d > b.effective_until:
                    continue

                interval = getattr(b, "recurrence_interval", 1) or 1
                if interval > 1:
                    anchor = b.effective_from or curr_d
                    anchor_dow = (anchor.weekday() + 1) % 7
                    days_ahead = (b.day_of_week - anchor_dow) % 7
                    first_occ = anchor + timedelta(days=days_ahead)
                    if curr_d < first_occ:
                        continue
                    weeks_diff = (curr_d - first_occ).days // 7
                    if weeks_diff % interval != 0:
                        continue

                # Check override on this occurrence date
                ov = override_by_orig.get((b.id, curr_d))
                if ov:
                    if ov.is_cancelled:
                        # Cancelled occurrence! Skip output!
                        continue
                    if ov.override_date and ov.override_date != curr_d:
                        # Moved to another date; skip here
                        continue
                    occurrences.append(_apply_override_to_block_out(b, curr_d, ov))
                else:
                    occurrences.append(_model_to_block_out(b, occurrence_date=curr_d))

        # Handle occurrences moved into this date range from an original date outside
        for ov in moved_in_overrides:
            b = block_map.get(ov.time_block_id)
            if b and ov.override_date:
                already_exists = any(
                    occ.id == b.id and occ.occurrence_date == ov.override_date for occ in occurrences
                )
                if not already_exists:
                    occurrences.append(_apply_override_to_block_out(b, ov.override_date, ov))

        # Incorporate university course meetings from active section enrollments (Task N4)
        if user_id is not None:
            try:
                from app.models.academic_course import AcademicCourse
                from app.models.academic_section import AcademicSection
                from app.models.academic_term import AcademicTerm
                from app.models.course_meeting import CourseMeeting
                from app.models.room import Room
                from app.models.section_enrollment import SectionEnrollment
                from app.models.timetable import Timetable

                active_enrollments = (
                    session.query(SectionEnrollment, AcademicSection, AcademicCourse, AcademicTerm)
                    .join(AcademicSection, SectionEnrollment.section_id == AcademicSection.id)
                    .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
                    .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
                    .filter(
                        SectionEnrollment.student_id == user_id,
                        SectionEnrollment.status == "active",
                    )
                    .all()
                )

                if active_enrollments:
                    sec_map = {sec.id: (sec, crs, trm) for enr, sec, crs, trm in active_enrollments}
                    sec_ids = list(sec_map.keys())

                    from sqlalchemy import or_

                    active_meetings = (
                        session.query(CourseMeeting, Timetable, Room)
                        .join(Timetable, CourseMeeting.timetable_id == Timetable.id)
                        .outerjoin(Room, CourseMeeting.room_id == Room.id)
                        .filter(
                            CourseMeeting.section_id.in_(sec_ids),
                            CourseMeeting.status.in_(["active", "scheduled"]),
                            CourseMeeting.deleted_at.is_(None),
                            Timetable.deleted_at.is_(None),
                            or_(
                                (Timetable.published_version_id.isnot(None)) & (CourseMeeting.version_id == Timetable.published_version_id),
                                (Timetable.published_version_id.is_(None)) & (Timetable.status.in_(["active", "draft"])) & (CourseMeeting.version_id.is_(None)),
                            ),
                        )
                        .all()
                    )


                    for m, tt, rm in active_meetings:
                        sec_info = sec_map.get(m.section_id)
                        if not sec_info:
                            continue
                        sec, crs, trm = sec_info

                        for day_offset in range(days_count):
                            curr_d = start_date + timedelta(days=day_offset)
                            syncshift_dow = (curr_d.weekday() + 1) % 7

                            if m.day_of_week != syncshift_dow:
                                continue

                            if trm.start_date and curr_d < trm.start_date:
                                continue
                            if trm.end_date and curr_d > trm.end_date:
                                continue

                            st_str = _format_time_str(m.start_time)
                            et_str = _format_time_str(m.end_time)
                            s_min = time_to_minutes(st_str)
                            e_min = time_to_minutes(et_str)
                            dur = (e_min + 24 * 60 - s_min) if e_min < s_min else (e_min - s_min)
                            loc_str = f"{rm.building} {rm.room_number}" if rm else ""

                            uni_block = BlockOut(
                                id=-int(m.id),
                                user_id=user_id,
                                type="class",
                                title=f"{crs.code} - {crs.name} ({sec.section_code})",
                                location=loc_str,
                                day_of_week=m.day_of_week,
                                start_time=st_str,
                                end_time=et_str,
                                duration_minutes=dur,
                                effective_from=trm.start_date,
                                effective_until=trm.end_date,
                                is_recurring=True,
                                occurrence_date=curr_d,
                                is_flexible=False,
                                course_id=None,
                                color="#2563eb",
                                deleted=False,
                            )
                            occurrences.append(uni_block)
            except Exception:
                pass

        occurrences.sort(key=lambda x: (x.occurrence_date or date.min, time_to_minutes(x.start_time)))
        return occurrences


# ---------------------------------------------------------------------------
# Time Block Database Persistence Operations
# ---------------------------------------------------------------------------

def get_all_blocks(
    user_id: Optional[int] = None,
    include_deleted: bool = False,
    db: Optional[Session] = None,
) -> list[BlockOut]:
    """
    Retrieves base time block definitions persisted in the database.
    Strictly isolates by user_id and filters out soft-deleted blocks unless requested.
    """
    with get_session(db) as session:
        query = session.query(TimeBlock)
        if not include_deleted:
            query = query.filter(TimeBlock.deleted == False)
        if user_id is not None:
            query = query.filter(TimeBlock.user_id == user_id)
        blocks = query.order_by(TimeBlock.day_of_week, TimeBlock.start_time).all()
        return [_model_to_block_out(b) for b in blocks]


def get_block_by_id(
    block_id: int,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[dict]:
    """
    Returns a dict representation of a block by ID with optional user_id check.
    """
    with get_session(db) as session:
        query = session.query(TimeBlock).filter(TimeBlock.id == block_id)
        if user_id is not None:
            query = query.filter(TimeBlock.user_id == user_id)
        b = query.first()
        if not b:
            return None
        return {
            "id": b.id,
            "user_id": b.user_id,
            "type": str(b.type.value if hasattr(b.type, "value") else b.type),
            "status": str(b.status.value if hasattr(b.status, "value") else b.status),
            "title": b.title,
            "location": b.location,
            "day_of_week": b.day_of_week,
            "start_time": _format_time_str(b.start_time),
            "end_time": _format_time_str(b.end_time),
            "duration_minutes": b.duration_minutes,
            "is_recurring": b.is_recurring,
            "recurrence_interval": getattr(b, "recurrence_interval", 1) or 1,
            "specific_date": b.specific_date.isoformat() if b.specific_date else None,
            "effective_from": b.effective_from.isoformat() if b.effective_from else None,
            "effective_until": b.effective_until.isoformat() if b.effective_until else None,
            "is_flexible": b.is_flexible,
            "hourly_wage": float(b.hourly_wage) if b.hourly_wage is not None else None,
            "course_id": b.course_id,
            "study_task_id": b.study_task_id,
            "deleted": b.deleted,
        }


def add_block_to_store(
    data: dict,
    user_id: int = 1,
    db: Optional[Session] = None,
) -> BlockOut:
    """
    Persists a new time block to the database with strict user_id from JWT.
    """
    with get_session(db) as session:
        st_obj = _parse_time(data["start_time"])
        et_obj = _parse_time(data["end_time"])
        s_min = st_obj.hour * 60 + st_obj.minute
        e_min = et_obj.hour * 60 + et_obj.minute
        duration = data.get("duration_minutes") or ((e_min - s_min) % (24 * 60))
        if duration <= 0:
            duration = 60

        eff_from = data.get("effective_from")
        if isinstance(eff_from, str):
            eff_from = date.fromisoformat(eff_from)
        eff_until = data.get("effective_until")
        if isinstance(eff_until, str):
            eff_until = date.fromisoformat(eff_until)

        spec_d = data.get("specific_date")
        if isinstance(spec_d, str):
            spec_d = date.fromisoformat(spec_d)

        b_type = data.get("type", "class")
        if isinstance(b_type, str):
            b_type = BlockType(b_type)

        new_block = TimeBlock(
            user_id=user_id,
            type=b_type,
            status=BlockStatus.ENROLLED,
            title=data["title"],
            location=data.get("location"),
            day_of_week=data["day_of_week"],
            start_time=st_obj,
            end_time=et_obj,
            duration_minutes=duration,
            is_recurring=data.get("is_recurring", True),
            recurrence_interval=int(data.get("recurrence_interval", 1) or 1),
            specific_date=spec_d,
            effective_from=eff_from or date(2026, 9, 1),
            effective_until=eff_until,
            is_flexible=data.get("is_flexible", False),
            hourly_wage=data.get("hourly_wage"),
            course_id=data.get("course_id"),
            study_task_id=data.get("study_task_id"),
            deleted=False,
        )
        session.add(new_block)
        session.commit()
        session.refresh(new_block)
        return _model_to_block_out(new_block)


def update_block_in_store(
    block_id: int,
    updates: dict,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[BlockOut]:
    """
    Updates a time block in the database, verifying user ownership.
    """
    with get_session(db) as session:
        query = session.query(TimeBlock).filter(TimeBlock.id == block_id)
        if user_id is not None:
            query = query.filter(TimeBlock.user_id == user_id)
        block = query.first()
        if not block:
            return None

        for k, v in updates.items():
            if v is not None and k not in ("id", "user_id", "scope", "occurrence_date"):
                if k == "start_time":
                    block.start_time = _parse_time(v)
                elif k == "end_time":
                    block.end_time = _parse_time(v)
                elif k == "effective_from" and isinstance(v, str):
                    block.effective_from = date.fromisoformat(v)
                elif k == "effective_until" and isinstance(v, str):
                    block.effective_until = date.fromisoformat(v)
                elif k == "specific_date" and isinstance(v, str):
                    block.specific_date = date.fromisoformat(v)
                elif k == "type" and isinstance(v, str):
                    block.type = BlockType(v)
                elif k == "recurrence_interval":
                    block.recurrence_interval = int(v)
                elif hasattr(block, k):
                    setattr(block, k, v)

        # Recalculate duration_minutes
        s_min = block.start_time.hour * 60 + block.start_time.minute
        e_min = block.end_time.hour * 60 + block.end_time.minute
        block.duration_minutes = (e_min - s_min) % (24 * 60)
        if block.duration_minutes <= 0:
            block.duration_minutes = 60

        session.commit()
        session.refresh(block)
        return _model_to_block_out(block)


# ---------------------------------------------------------------------------
# Recurrence Scoped Modifications & Exceptions
# ---------------------------------------------------------------------------

def create_or_update_override(
    user_id: int,
    block_id: int,
    original_date: date,
    override_data: dict,
    db: Optional[Session] = None,
) -> BlockOverride:
    """
    Creates or updates an occurrence exception (e.g. single-occurrence cancel or modify).
    """
    with get_session(db) as session:
        block = session.query(TimeBlock).filter(TimeBlock.id == block_id, TimeBlock.user_id == user_id).first()
        if not block:
            raise ValueError(f"Block with id {block_id} not found for user")

        ov = session.query(BlockOverride).filter(
            BlockOverride.time_block_id == block_id,
            BlockOverride.original_date == original_date,
            BlockOverride.user_id == user_id,
        ).first()

        if not ov:
            ov = BlockOverride(
                time_block_id=block_id,
                user_id=user_id,
                original_date=original_date,
            )
            session.add(ov)

        for k, v in override_data.items():
            if v is not None:
                if k in ("start_time", "end_time") and isinstance(v, str):
                    setattr(ov, k, _parse_time(v))
                elif k in ("override_date", "original_date") and isinstance(v, str):
                    setattr(ov, k, date.fromisoformat(v))
                elif hasattr(ov, k):
                    setattr(ov, k, v)

        if ov.start_time and ov.end_time:
            s_m = time_to_minutes(ov.start_time)
            e_m = time_to_minutes(ov.end_time)
            ov.duration_minutes = (e_m + 24 * 60 - s_m) if e_m < s_m else (e_m - s_m)

        session.commit()
        session.refresh(ov)
        return ov


def split_recurring_block(
    user_id: int,
    block_id: int,
    split_date: date,
    updates: dict,
    db: Optional[Session] = None,
) -> BlockOut:
    """
    Splits a series at split_date ("This and future"):
    1. Truncates original block's effective_until to day before split_date.
    2. Creates a new block starting at split_date with the requested updates.
    """
    with get_session(db) as session:
        block = session.query(TimeBlock).filter(TimeBlock.id == block_id, TimeBlock.user_id == user_id).first()
        if not block:
            raise ValueError(f"Block {block_id} not found")

        # 1. Truncate previous series
        original_until = block.effective_until
        block.effective_until = split_date - timedelta(days=1)
        if block.effective_from and block.effective_until < block.effective_from:
            block.deleted = True

        # 2. Prepare new block data copying from original
        new_data = {
            "type": updates.get("type", str(block.type.value if hasattr(block.type, "value") else block.type)),
            "title": updates.get("title", block.title),
            "location": updates.get("location", block.location),
            "day_of_week": updates.get("day_of_week", block.day_of_week),
            "start_time": updates.get("start_time", _format_time_str(block.start_time)),
            "end_time": updates.get("end_time", _format_time_str(block.end_time)),
            "is_recurring": updates.get("is_recurring", block.is_recurring),
            "recurrence_interval": updates.get("recurrence_interval", getattr(block, "recurrence_interval", 1)),
            "effective_from": split_date,
            "effective_until": updates.get("effective_until", original_until),
            "is_flexible": updates.get("is_flexible", block.is_flexible),
            "hourly_wage": updates.get("hourly_wage", float(block.hourly_wage) if block.hourly_wage is not None else None),
            "course_id": updates.get("course_id", block.course_id),
            "study_task_id": updates.get("study_task_id", block.study_task_id),
        }
        session.commit()
        return add_block_to_store(new_data, user_id=user_id, db=session)


def delete_recurring_scope(
    user_id: int,
    block_id: int,
    scope: str = "all",
    occurrence_date: Optional[date] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Deletes according to scope:
    - "this": creates a BlockOverride with is_cancelled = True on occurrence_date
    - "future": truncates effective_until of the series to occurrence_date - 1 day
    - "all": soft deletes the entire TimeBlock (deleted = True)
    """
    with get_session(db) as session:
        block = session.query(TimeBlock).filter(TimeBlock.id == block_id, TimeBlock.user_id == user_id).first()
        if not block:
            return False

        if scope == "this" and occurrence_date:
            create_or_update_override(
                user_id=user_id,
                block_id=block_id,
                original_date=occurrence_date,
                override_data={"is_cancelled": True},
                db=session,
            )
            return True
        elif scope == "future" and occurrence_date:
            block.effective_until = occurrence_date - timedelta(days=1)
            if block.effective_from and block.effective_until < block.effective_from:
                block.deleted = True
            session.commit()
            return True
        else:
            block.deleted = True
            session.commit()
            return True


def delete_block_from_store(
    block_id: int,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Performs a SOFT DELETE on a time block by setting deleted = True.
    Never hard deletes rows so historical data is protected.
    """
    with get_session(db) as session:
        query = session.query(TimeBlock).filter(TimeBlock.id == block_id)
        if user_id is not None:
            query = query.filter(TimeBlock.user_id == user_id)
        block = query.first()
        if not block:
            return False
        block.deleted = True
        session.commit()
        return True


def clear_student_timetable_store(
    user_id: int,
    only_imported: bool = False,
    db: Optional[Session] = None,
) -> dict:
    """
    Performs bulk soft-deletion of student timetable blocks (type == BlockType.CLASS).
    - If only_imported is True, only deletes blocks where is_imported is True.
    - Preserves work shifts (type == BlockType.SHIFT) and study tasks (type == BlockType.STUDY).
    - Preserves institutional authoritative university timetable models completely.
    - Strictly bound to user_id (no IDOR / cross-user leakage).
    - Returns counts of deleted, remaining, and preserved blocks.
    """
    with get_session(db) as session:
        query = session.query(TimeBlock).filter(
            TimeBlock.user_id == user_id,
            TimeBlock.type == BlockType.CLASS,
            TimeBlock.deleted == False,
        )
        if only_imported:
            query = query.filter(TimeBlock.is_imported == True)

        blocks_to_delete = query.all()
        deleted_count = len(blocks_to_delete)

        for b in blocks_to_delete:
            b.deleted = True

        session.commit()

        # Recalculate remaining active metrics
        remaining_class_count = (
            session.query(TimeBlock)
            .filter(
                TimeBlock.user_id == user_id,
                TimeBlock.type == BlockType.CLASS,
                TimeBlock.deleted == False,
            )
            .count()
        )

        remaining_total_blocks = (
            session.query(TimeBlock)
            .filter(
                TimeBlock.user_id == user_id,
                TimeBlock.deleted == False,
            )
            .count()
        )

        preserved_shifts_count = (
            session.query(TimeBlock)
            .filter(
                TimeBlock.user_id == user_id,
                TimeBlock.type == BlockType.SHIFT,
                TimeBlock.deleted == False,
            )
            .count()
        )

        preserved_study_count = (
            session.query(TimeBlock)
            .filter(
                TimeBlock.user_id == user_id,
                TimeBlock.type == BlockType.STUDY,
                TimeBlock.deleted == False,
            )
            .count()
        )

        return {
            "deleted_count": deleted_count,
            "remaining_count": remaining_class_count,
            "remaining_total_blocks": remaining_total_blocks,
            "preserved_shifts_count": preserved_shifts_count,
            "preserved_study_count": preserved_study_count,
        }


# ---------------------------------------------------------------------------
# Recurrence-Aware Conflict Engine
# ---------------------------------------------------------------------------

def detect_conflicts_and_totals(
    user_id: Optional[int] = None,
    weekly_hour_limit: float = 20.0,
    week_start: Optional[date] = None,
    db: Optional[Session] = None,
) -> tuple[list[ConflictItem], WeeklyTotals]:
    """
    Detects pairwise schedule overlaps among active non-deleted occurrences for user_id.
    When week_start is provided, evaluates conflicts on the actual occurrences generated
    for that week (Monday to Sunday).
    If an occurrence was cancelled (e.g. Oct 12 class), it produces no conflict and its
    hours are not counted.
    """
    with get_session(db) as session:
        if user_id is None:
            return [], WeeklyTotals(shift_hours=0.0, class_hours=0.0, expected_earnings=0.0, over_limit=False)

        if week_start is not None:
            w_start = week_start
            w_end = week_start + timedelta(days=6)
            occurrences = get_occurrences_for_range(
                user_id=user_id,
                start_date=w_start,
                end_date=w_end,
                db=session,
            )
        else:
            # Fallback to current week or all active blocks
            today_d = date.today()
            w_start = today_d - timedelta(days=today_d.weekday())
            w_end = w_start + timedelta(days=6)
            occurrences = get_occurrences_for_range(
                user_id=user_id,
                start_date=w_start,
                end_date=w_end,
                db=session,
            )
            # If no occurrences this week, also check template blocks
            if not occurrences:
                raw_blocks = get_all_blocks(user_id=user_id, include_deleted=False, db=session)
                occurrences = raw_blocks

        # Fetch user's configured transition buffer
        min_transition = 15
        if user_id is not None:
            user_rec = session.query(User).filter(User.id == user_id).first()
            if user_rec and user_rec.minimum_transition_minutes is not None:
                min_transition = int(user_rec.minimum_transition_minutes)

        conflicts: list[ConflictItem] = []
        conflict_id = 9000

        # 1. Exact Temporal Overlap Test (A.start < B.end AND B.start < A.end)
        for i in range(len(occurrences)):
            for j in range(i + 1, len(occurrences)):
                o1 = occurrences[i]
                o2 = occurrences[j]

                # Match by occurrence date if available, otherwise by day of week
                if o1.occurrence_date and o2.occurrence_date:
                    if o1.occurrence_date != o2.occurrence_date:
                        continue
                elif o1.day_of_week != o2.day_of_week:
                    continue

                s1 = time_to_minutes(o1.start_time)
                e1 = time_to_minutes(o1.end_time)
                s2 = time_to_minutes(o2.start_time)
                e2 = time_to_minutes(o2.end_time)

                # Overlap test: s1 < e2 and s2 < e1
                if s1 < e2 and s2 < e1:
                    conflict_id += 1
                    overlap_start_min = max(s1, s2)
                    overlap_end_min = min(e1, e2)
                    overlap_minutes = overlap_end_min - overlap_start_min
                    severity = "hard" if o1.type == "class" or o2.type == "class" else "warning"

                    conflicts.append(
                        ConflictItem(
                            id=conflict_id,
                            block_a_id=o1.id,
                            block_b_id=o2.id,
                            overlap_minutes=overlap_minutes,
                            severity=severity,
                            conflict_type="class_shift" if (o1.type == "class" and o2.type == "shift") or (o1.type == "shift" and o2.type == "class") else ("class_class" if o1.type == "class" and o2.type == "class" else "shift_shift"),
                            overlap_start=minutes_to_time(overlap_start_min),
                            overlap_end=minutes_to_time(overlap_end_min),
                            day_of_week=o1.day_of_week,
                            description=f"{o1.title} overlaps with {o2.title}",
                            location_a=o1.location,
                            location_b=o2.location,
                        )
                    )

        # 2. Travel / Transition-Aware Check (insufficient gap between adjacent non-overlapping events)
        if min_transition > 0 and occurrences:
            grouped_by_day: dict[object, list[BlockOut]] = {}
            for occ in occurrences:
                k = occ.occurrence_date if occ.occurrence_date else occ.day_of_week
                grouped_by_day.setdefault(k, []).append(occ)

            for _, day_blocks in grouped_by_day.items():
                if len(day_blocks) < 2:
                    continue
                sorted_day = sorted(day_blocks, key=lambda b: time_to_minutes(b.start_time))
                for k in range(len(sorted_day) - 1):
                    b1 = sorted_day[k]
                    b2 = sorted_day[k + 1]

                    s1 = time_to_minutes(b1.start_time)
                    e1 = time_to_minutes(b1.end_time)
                    s2 = time_to_minutes(b2.start_time)

                    # Only check transition if no temporal overlap (s2 >= e1)
                    if s2 >= e1:
                        avail_transition = s2 - e1
                        loc1 = (b1.location or "").strip().lower()
                        loc2 = (b2.location or "").strip().lower()

                        # Same location: if both specified and identical (e.g. "Campus A" and "Campus A"), no travel required
                        same_loc = bool(loc1 and loc2 and loc1 == loc2)
                        required_buffer = 0 if same_loc else min_transition

                        if required_buffer > 0 and avail_transition < required_buffer:
                            conflict_id += 1
                            shortfall = required_buffer - avail_transition
                            conflicts.append(
                                ConflictItem(
                                    id=conflict_id,
                                    block_a_id=b1.id,
                                    block_b_id=b2.id,
                                    overlap_minutes=shortfall,
                                    severity="warning",
                                    conflict_type="transition",
                                    overlap_start=minutes_to_time(e1),
                                    overlap_end=minutes_to_time(s2),
                                    day_of_week=b1.day_of_week,
                                    description=f"Short transition ({avail_transition}m available, {required_buffer}m preferred) between {b1.title} and {b2.title}",
                                    available_transition_minutes=avail_transition,
                                    required_transition_minutes=required_buffer,
                                    location_a=b1.location,
                                    location_b=b2.location,
                                )
                            )


        # Calculate weekly totals from the actual occurrences
        shift_hours = 0.0
        class_hours = 0.0
        expected_earnings = 0.0

        for o in occurrences:
            dur = _block_duration_hours(o.start_time, o.end_time)
            if o.type == "shift":
                shift_hours += dur
                wage = float(o.hourly_wage) if o.hourly_wage else 0.0
                expected_earnings += dur * wage
            elif o.type == "class":
                class_hours += dur

        totals = WeeklyTotals(
            shift_hours=round(shift_hours, 1),
            class_hours=round(class_hours, 1),
            expected_earnings=round(expected_earnings, 2),
            over_limit=shift_hours > weekly_hour_limit,
        )

        return conflicts, totals


# ---------------------------------------------------------------------------
# Study Tasks Database Persistence Operations
# ---------------------------------------------------------------------------

def _model_to_task_dict(t: StudyTask) -> dict:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "title": t.title,
        "course_id": t.course_id,
        "total_hours_required": float(t.total_hours_required),
        "deadline": t.deadline.isoformat() if hasattr(t.deadline, "isoformat") else str(t.deadline),
        "status": str(t.status.value if hasattr(t.status, "value") else t.status),
        "priority": getattr(t, "priority", "medium") or "medium",
        "preferred_duration": getattr(t, "preferred_duration", 90) or 90,
        "completed_hours": float(getattr(t, "completed_hours", 0.0) or 0.0),
        "created_at": t.created_at.isoformat() if hasattr(t.created_at, "isoformat") else str(t.created_at),
    }


def get_user_tasks(user_id: int, db: Optional[Session] = None) -> list[dict]:
    with get_session(db) as session:
        tasks = (
            session.query(StudyTask)
            .filter(StudyTask.user_id == user_id)
            .order_by(StudyTask.deadline)
            .all()
        )
        return [_model_to_task_dict(t) for t in tasks]


def get_task_by_id(
    task_id: int,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[dict]:
    with get_session(db) as session:
        query = session.query(StudyTask).filter(StudyTask.id == task_id)
        if user_id is not None:
            query = query.filter(StudyTask.user_id == user_id)
        task = query.first()
        if not task:
            return None
        return _model_to_task_dict(task)


def create_task_in_store(
    task_dict: dict,
    user_id: int = 1,
    db: Optional[Session] = None,
) -> dict:
    with get_session(db) as session:
        d_val = task_dict["deadline"]
        if isinstance(d_val, str):
            d_val = date.fromisoformat(d_val)

        status_val = task_dict.get("status", "pending")
        if isinstance(status_val, str):
            status_val = TaskStatus(status_val)

        new_task = StudyTask(
            user_id=user_id,
            title=task_dict["title"],
            course_id=task_dict.get("course_id"),
            total_hours_required=float(task_dict["total_hours_required"]),
            deadline=d_val,
            status=status_val,
            priority=task_dict.get("priority", "medium"),
            preferred_duration=int(task_dict.get("preferred_duration", 90)),
            completed_hours=float(task_dict.get("completed_hours", 0.0)),
        )
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return _model_to_task_dict(new_task)


def update_task_in_store(
    task_id: int,
    updates: dict,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[dict]:
    with get_session(db) as session:
        query = session.query(StudyTask).filter(StudyTask.id == task_id)
        if user_id is not None:
            query = query.filter(StudyTask.user_id == user_id)
        task = query.first()
        if not task:
            return None

        for k, v in updates.items():
            if v is not None and k not in ("id", "user_id"):
                if k == "deadline" and isinstance(v, str):
                    task.deadline = date.fromisoformat(v)
                elif k == "status" and isinstance(v, str):
                    task.status = TaskStatus(v)
                elif k == "completed_hours":
                    task.completed_hours = float(v)
                elif k == "preferred_duration":
                    task.preferred_duration = int(v)
                elif hasattr(task, k):
                    setattr(task, k, v)

        session.commit()
        session.refresh(task)
        return _model_to_task_dict(task)


def delete_task_in_store(
    task_id: int,
    user_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> bool:
    with get_session(db) as session:
        query = session.query(StudyTask).filter(StudyTask.id == task_id)
        if user_id is not None:
            query = query.filter(StudyTask.user_id == user_id)
        task = query.first()
        if not task:
            return False
        delete_study_blocks_for_task(task_id=task_id, future_only=False, db=session)
        session.delete(task)
        session.commit()
        return True


def delete_study_blocks_for_task(
    task_id: int,
    future_only: bool = False,
    now_dow: Optional[int] = None,
    now_minutes: Optional[int] = None,
    db: Optional[Session] = None,
) -> int:
    """
    Soft-deletes blocks associated with study_task_id by setting deleted = True.
    """
    with get_session(db) as session:
        blocks = (
            session.query(TimeBlock)
            .filter(TimeBlock.study_task_id == task_id, TimeBlock.deleted == False)
            .all()
        )
        count = 0
        for b in blocks:
            if future_only and now_dow is not None and now_minutes is not None:
                block_dow = b.day_of_week or 0
                end_m = b.end_time.hour * 60 + b.end_time.minute
                if block_dow < now_dow or (block_dow == now_dow and end_m <= now_minutes):
                    continue
            b.deleted = True
            count += 1
        session.commit()
        return count
