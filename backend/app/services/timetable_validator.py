from datetime import time
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.faculty import FacultyProfile
from app.models.room import Room
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.timetable import Timetable

DAY_NAMES = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


def time_to_minutes(t_val) -> int:
    """Converts a time object or 'HH:MM[:SS]' string to total minutes since midnight."""
    if isinstance(t_val, time):
        return t_val.hour * 60 + t_val.minute
    parts = str(t_val).strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def parse_time_obj(t_val) -> time:
    """Safely converts a string or time object to datetime.time."""
    if isinstance(t_val, time):
        return t_val
    t_str = str(t_val).strip()
    parts = [int(p) for p in t_str.split(":")[:3]]
    if len(parts) == 2:
        return time(parts[0], parts[1], 0)
    elif len(parts) >= 3:
        return time(parts[0], parts[1], parts[2])
    return time(0, 0, 0)


def format_time_str(t_val) -> str:
    """Formats time as HH:MM."""
    if isinstance(t_val, time):
        return t_val.strftime("%H:%M")
    s = str(t_val).strip()
    if len(s) >= 5:
        return s[:5]
    return s


def validate_course_meeting(
    db: Session,
    institution_id: int,
    timetable_id: int,
    section_id: int,
    day_of_week: int,
    start_time_val,
    end_time_val,
    room_id: Optional[int] = None,
    faculty_id: Optional[int] = None,
    existing_meeting_id: Optional[int] = None,
    version_id: Optional[int] = None,
) -> Tuple[time, time, AcademicSection, Timetable, Optional[Room], Optional[FacultyProfile]]:
    """
    Authoritative baseline timetable meeting validation:

    1. Temporal validation (start < end, valid day, 15-480 min duration).
    2. Timetable & Section existence, status, tenant isolation.
    3. Term consistency (section.academic_term_id == timetable.academic_term_id).
    4. Room validation: tenant isolation, active status, capacity (room.capacity >= section.capacity).
    5. Room overlap conflict check: interval overlap with any active meeting in the same room.
    6. Faculty resolution & overlap conflict check: interval overlap for the assigned faculty.
    7. Section overlap conflict check: section cannot have overlapping meetings.
    """
    start_time = parse_time_obj(start_time_val)
    end_time = parse_time_obj(end_time_val)
    s_mins = time_to_minutes(start_time)
    e_mins = time_to_minutes(end_time)

    # 1. Time range & duration
    if s_mins >= e_mins:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_time_range",
                "message": f"Start time ({format_time_str(start_time)}) must be strictly earlier than end time ({format_time_str(end_time)})",
            },
        )

    duration = e_mins - s_mins
    if duration < 15 or duration > 480:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_duration",
                "message": f"Meeting duration ({duration} mins) must be between 15 minutes and 8 hours",
            },
        )

    if day_of_week < 0 or day_of_week > 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_day_of_week", "message": "Day of week must be between 0 (Sunday) and 6 (Saturday)"},
        )

    # 2. Timetable existence & tenant isolation
    timetable = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not timetable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    # 3. Section existence, tenant isolation, and term alignment
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Academic section {section_id} not found in this institution"},
        )

    if section.academic_term_id != timetable.academic_term_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "term_mismatch",
                "message": f"Section term ({section.academic_term_id}) does not match timetable term ({timetable.academic_term_id})",
            },
        )

    # 4. Room validation (tenant isolation, active status, capacity)
    room: Optional[Room] = None
    if room_id is not None:
        room = (
            db.query(Room)
            .filter(
                Room.id == room_id,
                Room.institution_id == institution_id,
                Room.deleted_at.is_(None),
            )
            .first()
        )
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "room_not_found", "message": f"Room {room_id} not found in this institution"},
            )
        if room.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "room_inactive", "message": f"Room '{room.building} {room.room_number}' is inactive"},
            )

        # Capacity validation (Room capacity >= Section capacity)
        if room.capacity < section.capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "insufficient_room_capacity",
                    "message": f"Selected room '{room.building} {room.room_number}' capacity ({room.capacity}) is less than section capacity ({section.capacity})",
                },
            )

        # Resolve version_id if not explicitly provided
        if version_id is None and existing_meeting_id:
            ex_row = db.query(CourseMeeting.version_id).filter(CourseMeeting.id == existing_meeting_id).first()
            if ex_row and ex_row[0] is not None:
                version_id = ex_row[0]

        # 5. Room overlap conflict check
        room_query = (
            db.query(CourseMeeting)
            .filter(
                CourseMeeting.timetable_id == timetable.id,
                CourseMeeting.room_id == room.id,
                CourseMeeting.day_of_week == day_of_week,
                CourseMeeting.status == "active",
                CourseMeeting.deleted_at.is_(None),
            )
        )
        if version_id is not None:
            room_query = room_query.filter(CourseMeeting.version_id == version_id)
        if existing_meeting_id:
            room_query = room_query.filter(CourseMeeting.id != existing_meeting_id)

        for m in room_query.all():
            m_s = time_to_minutes(m.start_time)
            m_e = time_to_minutes(m.end_time)
            if s_mins < m_e and m_s < e_mins:
                sec_code = m.section.section_code if m.section else f"ID {m.section_id}"
                crs_code = m.section.course.code if m.section and m.section.course else ""
                label = f"{crs_code} {sec_code}".strip()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "room_conflict",
                        "message": f"Room '{room.building} {room.room_number}' is already occupied on {DAY_NAMES.get(day_of_week, 'this day')} from {format_time_str(m.start_time)} to {format_time_str(m.end_time)} by {label}",
                    },
                )

    # 6. Section overlap conflict check (same section cannot have overlapping meetings)
    if version_id is None and existing_meeting_id:
        ex_row = db.query(CourseMeeting.version_id).filter(CourseMeeting.id == existing_meeting_id).first()
        if ex_row and ex_row[0] is not None:
            version_id = ex_row[0]

    sec_query = (
        db.query(CourseMeeting)
        .filter(
            CourseMeeting.timetable_id == timetable.id,
            CourseMeeting.section_id == section.id,
            CourseMeeting.day_of_week == day_of_week,
            CourseMeeting.status == "active",
            CourseMeeting.deleted_at.is_(None),
        )
    )
    if version_id is not None:
        sec_query = sec_query.filter(CourseMeeting.version_id == version_id)
    if existing_meeting_id:
        sec_query = sec_query.filter(CourseMeeting.id != existing_meeting_id)


    for m in sec_query.all():
        m_s = time_to_minutes(m.start_time)
        m_e = time_to_minutes(m.end_time)
        if s_mins < m_e and m_s < e_mins:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "section_conflict",
                    "message": f"Section '{section.section_code}' already has another meeting scheduled on {DAY_NAMES.get(day_of_week, 'this day')} from {format_time_str(m.start_time)} to {format_time_str(m.end_time)}",
                },
            )

    # 7. Faculty validation and resolution
    faculty: Optional[FacultyProfile] = None
    resolved_faculty_id: Optional[int] = None
    faculty_name: str = "Faculty member"

    if faculty_id is not None:
        faculty = (
            db.query(FacultyProfile)
            .filter(
                FacultyProfile.id == faculty_id,
                FacultyProfile.institution_id == institution_id,
                FacultyProfile.deleted_at.is_(None),
            )
            .first()
        )
        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "faculty_not_found", "message": f"Faculty profile {faculty_id} not found in this institution"},
            )
        if faculty.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "faculty_inactive", "message": "Selected faculty profile is inactive"},
            )
        resolved_faculty_id = faculty.id
        if faculty.user:
            faculty_name = faculty.user.display_name or faculty.user.name or faculty.user.email
    else:
        # Resolve from section faculty assignments
        primary_assign = (
            db.query(SectionFacultyAssignment)
            .filter(
                SectionFacultyAssignment.section_id == section.id,
                SectionFacultyAssignment.is_primary == True,
            )
            .first()
        )
        if primary_assign and primary_assign.faculty:
            resolved_faculty_id = primary_assign.faculty_id
            faculty = primary_assign.faculty
            if faculty.user:
                faculty_name = faculty.user.display_name or faculty.user.name or faculty.user.email
        else:
            any_assign = (
                db.query(SectionFacultyAssignment)
                .filter(SectionFacultyAssignment.section_id == section.id)
                .first()
            )
            if any_assign and any_assign.faculty:
                resolved_faculty_id = any_assign.faculty_id
                faculty = any_assign.faculty
                if faculty.user:
                    faculty_name = faculty.user.display_name or faculty.user.name or faculty.user.email

    # Faculty overlap conflict check
    if resolved_faculty_id is not None:
        if version_id is None and existing_meeting_id:
            ex_row = db.query(CourseMeeting.version_id).filter(CourseMeeting.id == existing_meeting_id).first()
            if ex_row and ex_row[0] is not None:
                version_id = ex_row[0]

        fac_query = (
            db.query(CourseMeeting)
            .filter(
                CourseMeeting.timetable_id == timetable.id,
                CourseMeeting.day_of_week == day_of_week,
                CourseMeeting.status == "active",
                CourseMeeting.deleted_at.is_(None),
            )
        )
        if version_id is not None:
            fac_query = fac_query.filter(CourseMeeting.version_id == version_id)
        if existing_meeting_id:
            fac_query = fac_query.filter(CourseMeeting.id != existing_meeting_id)


        for m in fac_query.all():
            # Check if m is directly or indirectly assigned to this faculty
            m_fac_id = m.faculty_id
            if m_fac_id is None and m.section:
                # Resolve primary from m.section
                for fa in m.section.faculty_assignments:
                    if fa.faculty_id == resolved_faculty_id:
                        m_fac_id = resolved_faculty_id
                        break

            if m_fac_id == resolved_faculty_id:
                m_s = time_to_minutes(m.start_time)
                m_e = time_to_minutes(m.end_time)
                if s_mins < m_e and m_s < e_mins:
                    sec_code = m.section.section_code if m.section else ""
                    crs_code = m.section.course.code if m.section and m.section.course else ""
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "code": "faculty_conflict",
                            "message": f"Instructor '{faculty_name}' has another meeting scheduled on {DAY_NAMES.get(day_of_week, 'this day')} from {format_time_str(m.start_time)} to {format_time_str(m.end_time)} ({crs_code} {sec_code})",
                        },
                    )

    return start_time, end_time, section, timetable, room, faculty
