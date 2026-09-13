import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.faculty import FacultyProfile
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint
from app.models.time_block import TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.schemas.timetable import (
    TimetableVersionCreate,
    TimetableVersionOut,
    TimetableVersionUpdate,
    VersionChecklistItem,
    VersionChecklistOut,
    VersionComparisonOut,
    VersionMeetingDiff,
)
from app.services.audit import record_audit_log
from app.services.timetable_validator import DAY_NAMES, format_time_str, time_to_minutes

logger = logging.getLogger(__name__)


def _format_time_val(t) -> str:
    return format_time_str(t) if t else ""


def _resolve_faculty_for_meeting(m: CourseMeeting, sec: Optional[AcademicSection]) -> Tuple[Optional[FacultyProfile], Optional[str]]:
    fac = m.faculty
    if not fac and sec and sec.faculty_assignments:
        for fa in sec.faculty_assignments:
            if fa.is_primary and fa.faculty:
                fac = fa.faculty
                break
        if not fac and sec.faculty_assignments[0].faculty:
            fac = sec.faculty_assignments[0].faculty

    fac_name = None
    if fac:
        if fac.user:
            fac_name = fac.user.display_name or fac.user.name or fac.user.email
        elif fac.title:
            fac_name = fac.title
    return fac, fac_name


def _enrich_version_out(
    v: TimetableVersion,
    current_published_id: Optional[int] = None,
    meetings_count: Optional[int] = None,
    sections_count: Optional[int] = None,
) -> TimetableVersionOut:
    creator_name = None
    if v.creator:
        creator_name = v.creator.display_name or v.creator.name or v.creator.email

    return TimetableVersionOut(
        id=v.id,
        institution_id=v.institution_id,
        timetable_id=v.timetable_id,
        version_number=v.version_number,
        name=v.name,
        status=v.status,
        change_summary=v.change_summary,
        created_by_user_id=v.created_by_user_id,
        created_by_name=creator_name,
        created_at=v.created_at,
        updated_at=v.updated_at,
        published_at=v.published_at,
        archived_at=v.archived_at,
        meetings_count=meetings_count if meetings_count is not None else len(v.meetings or []),
        sections_count=sections_count if sections_count is not None else len(set(m.section_id for m in (v.meetings or []))),
        is_current_published=(v.id == current_published_id) if current_published_id else (v.status == "published"),
    )


def get_or_create_initial_version(db: Session, institution_id: int, timetable_id: int) -> TimetableVersion:
    """
    Ensures a timetable has at least an initial Version 1, and links any unversioned meetings to it.
    """
    tt = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found"},
        )

    # Check existing version
    existing_ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .order_by(TimetableVersion.version_number.asc())
        .first()
    )
    if existing_ver:
        return existing_ver

    # Create Version 1
    is_active = (tt.status == "active")
    ver_status = "published" if is_active else "draft"
    now_utc = datetime.now(timezone.utc)
    v1 = TimetableVersion(
        institution_id=institution_id,
        timetable_id=timetable_id,
        version_number=1,
        name="Version 1 — Baseline",
        status=ver_status,
        published_at=now_utc if is_active else None,
    )
    db.add(v1)
    db.flush()

    if is_active:
        tt.published_version_id = v1.id

    # Link unversioned meetings
    db.query(CourseMeeting).filter(
        CourseMeeting.timetable_id == timetable_id,
        CourseMeeting.version_id.is_(None),
    ).update({"version_id": v1.id}, synchronize_session=False)

    db.commit()
    db.refresh(v1)
    return v1


def create_version(
    db: Session,
    institution_id: int,
    timetable_id: int,
    user_id: int,
    data: TimetableVersionCreate,
) -> TimetableVersion:
    """
    Creates a new sequential TimetableVersion (always in 'draft' status).
    Clones all meetings from source_version_id (or the published version).
    Draft isolation: the new version gets cloned, completely independent meeting rows.
    """
    tt = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found"},
        )

    # Determine highest version number
    max_num = (
        db.query(func.max(TimetableVersion.version_number))
        .filter(
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .scalar()
        or 0
    )
    next_ver_num = max_num + 1

    # Determine source version to clone meetings from
    source_ver = None
    if data.source_version_id:
        source_ver = (
            db.query(TimetableVersion)
            .filter(
                TimetableVersion.id == data.source_version_id,
                TimetableVersion.timetable_id == timetable_id,
                TimetableVersion.institution_id == institution_id,
            )
            .first()
        )
        if not source_ver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "source_version_not_found", "message": f"Source version {data.source_version_id} not found"},
            )
    else:
        if tt.published_version_id:
            source_ver = (
                db.query(TimetableVersion)
                .filter(TimetableVersion.id == tt.published_version_id)
                .first()
            )
        if not source_ver:
            # Fall back to latest version
            source_ver = (
                db.query(TimetableVersion)
                .filter(
                    TimetableVersion.timetable_id == timetable_id,
                    TimetableVersion.institution_id == institution_id,
                )
                .order_by(TimetableVersion.version_number.desc())
                .first()
            )

    ver_name = data.name.strip() if data.name and data.name.strip() else f"Version {next_ver_num}"

    new_ver = TimetableVersion(
        institution_id=institution_id,
        timetable_id=timetable_id,
        version_number=next_ver_num,
        name=ver_name,
        status="draft",
        change_summary=data.change_summary.strip() if data.change_summary else None,
        created_by_user_id=user_id,
    )
    db.add(new_ver)
    db.flush()

    # Clone meetings from source version if available
    if source_ver:
        source_meetings = (
            db.query(CourseMeeting)
            .filter(
                CourseMeeting.version_id == source_ver.id,
                CourseMeeting.deleted_at.is_(None),
            )
            .all()
        )
        for sm in source_meetings:
            cloned = CourseMeeting(
                institution_id=institution_id,
                timetable_id=timetable_id,
                version_id=new_ver.id,
                section_id=sm.section_id,
                academic_term_id=sm.academic_term_id,
                day_of_week=sm.day_of_week,
                start_time=sm.start_time,
                end_time=sm.end_time,
                room_id=sm.room_id,
                faculty_id=sm.faculty_id,
                meeting_type=sm.meeting_type,
                status=sm.status,
            )
            db.add(cloned)

    db.commit()
    db.refresh(new_ver)
    return new_ver


def run_version_checklist(
    db: Session,
    institution_id: int,
    timetable_id: int,
    version_id: int,
) -> VersionChecklistOut:
    """
    Runs authoritative pre-approval and pre-publishing validation for a timetable version:
    1. Room collision check (same room double-booked on same day)
    2. Faculty collision check (same faculty double-booked on same day)
    3. Section collision check (same section scheduled with overlapping meetings)
    4. Room capacity check (room capacity vs section enrolled students & capacity)
    5. Time boundary validity (start_time < end_time)
    6. Unassigned rooms & faculty warnings
    """
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )

    meetings = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.version_id == ver.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .all()
    )

    checklist_items: List[VersionChecklistItem] = []
    blocking_issues: List[str] = []
    warnings: List[str] = []

    # 1. Time boundary check
    time_issues = []
    for m in meetings:
        s_min = time_to_minutes(m.start_time)
        e_min = time_to_minutes(m.end_time)
        if s_min >= e_min:
            crs_code = m.section.course.code if m.section and m.section.course else f"Sec #{m.section_id}"
            time_issues.append(f"{crs_code}: start time {format_time_str(m.start_time)} must be before end time {format_time_str(m.end_time)}")

    if time_issues:
        blocking_issues.extend(time_issues)
        checklist_items.append(
            VersionChecklistItem(
                code="time_boundaries",
                title="Class Meeting Times",
                description="All class meetings must have valid start and end times",
                status="failed",
                details=time_issues,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="time_boundaries",
                title="Class Meeting Times",
                description="All class meetings have valid time ranges",
                status="passed",
                details=[],
            )
        )

    # 2. Section overlaps check
    section_issues = []
    by_section: Dict[int, List[CourseMeeting]] = {}
    for m in meetings:
        by_section.setdefault(m.section_id, []).append(m)

    for sec_id, sec_meetings in by_section.items():
        by_day: Dict[int, List[CourseMeeting]] = {}
        for m in sec_meetings:
            by_day.setdefault(m.day_of_week, []).append(m)

        for dow, day_ms in by_day.items():
            for i in range(len(day_ms)):
                for j in range(i + 1, len(day_ms)):
                    m1, m2 = day_ms[i], day_ms[j]
                    s1, e1 = time_to_minutes(m1.start_time), time_to_minutes(m1.end_time)
                    s2, e2 = time_to_minutes(m2.start_time), time_to_minutes(m2.end_time)
                    if s1 < e2 and s2 < e1:
                        sec_code = m1.section.section_code if m1.section else f"#{sec_id}"
                        crs_code = m1.section.course.code if m1.section and m1.section.course else ""
                        msg = f"Section {crs_code} ({sec_code}) has overlapping meetings on {DAY_NAMES.get(dow, 'Day ' + str(dow))} ({format_time_str(m1.start_time)}–{format_time_str(m1.end_time)} and {format_time_str(m2.start_time)}–{format_time_str(m2.end_time)})"
                        section_issues.append(msg)

    if section_issues:
        blocking_issues.extend(section_issues)
        checklist_items.append(
            VersionChecklistItem(
                code="section_conflicts",
                title="Section Schedule Conflicts",
                description="A class section cannot have overlapping meetings",
                status="failed",
                details=section_issues,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="section_conflicts",
                title="Section Schedule Conflicts",
                description="Zero overlapping meetings within sections",
                status="passed",
                details=[],
            )
        )

    # 3. Room collisions check
    room_issues = []
    by_room: Dict[int, List[CourseMeeting]] = {}
    for m in meetings:
        if m.room_id:
            by_room.setdefault(m.room_id, []).append(m)

    for r_id, r_meetings in by_room.items():
        by_day: Dict[int, List[CourseMeeting]] = {}
        for m in r_meetings:
            by_day.setdefault(m.day_of_week, []).append(m)

        for dow, day_ms in by_day.items():
            for i in range(len(day_ms)):
                for j in range(i + 1, len(day_ms)):
                    m1, m2 = day_ms[i], day_ms[j]
                    s1, e1 = time_to_minutes(m1.start_time), time_to_minutes(m1.end_time)
                    s2, e2 = time_to_minutes(m2.start_time), time_to_minutes(m2.end_time)
                    if s1 < e2 and s2 < e1:
                        rm_name = f"{m1.room.building} {m1.room.room_number}" if m1.room else f"Room #{r_id}"
                        crs1 = m1.section.course.code if m1.section and m1.section.course else f"Sec {m1.section_id}"
                        crs2 = m2.section.course.code if m2.section and m2.section.course else f"Sec {m2.section_id}"
                        msg = f"{rm_name} is double-booked on {DAY_NAMES.get(dow, '')} between {crs1} and {crs2}"
                        room_issues.append(msg)

    if room_issues:
        blocking_issues.extend(room_issues)
        checklist_items.append(
            VersionChecklistItem(
                code="room_collisions",
                title="Room Availability & Collisions",
                description="Classrooms cannot be scheduled for two classes at the same time",
                status="failed",
                details=room_issues,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="room_collisions",
                title="Room Availability & Collisions",
                description="Zero classroom double-bookings detected",
                status="passed",
                details=[],
            )
        )

    # 4. Faculty double-booking check
    faculty_issues = []
    faculty_meeting_pairs = []
    for m in meetings:
        fac, fac_name = _resolve_faculty_for_meeting(m, m.section)
        if fac:
            faculty_meeting_pairs.append((fac.id, fac_name, m))

    by_fac: Dict[int, List[Tuple[str, CourseMeeting]]] = {}
    for fid, fname, m in faculty_meeting_pairs:
        by_fac.setdefault(fid, []).append((fname, m))

    for fid, f_list in by_fac.items():
        by_day: Dict[int, List[Tuple[str, CourseMeeting]]] = {}
        for fname, m in f_list:
            by_day.setdefault(m.day_of_week, []).append((fname, m))

        for dow, day_items in by_day.items():
            for i in range(len(day_items)):
                for j in range(i + 1, len(day_items)):
                    fn1, m1 = day_items[i]
                    fn2, m2 = day_items[j]
                    s1, e1 = time_to_minutes(m1.start_time), time_to_minutes(m1.end_time)
                    s2, e2 = time_to_minutes(m2.start_time), time_to_minutes(m2.end_time)
                    if s1 < e2 and s2 < e1:
                        crs1 = m1.section.course.code if m1.section and m1.section.course else f"Sec {m1.section_id}"
                        crs2 = m2.section.course.code if m2.section and m2.section.course else f"Sec {m2.section_id}"
                        inst_name = fn1 or f"Faculty #{fid}"
                        msg = f"{inst_name} is scheduled for overlapping classes on {DAY_NAMES.get(dow, '')}: {crs1} and {crs2}"
                        faculty_issues.append(msg)

    if faculty_issues:
        blocking_issues.extend(faculty_issues)
        checklist_items.append(
            VersionChecklistItem(
                code="faculty_collisions",
                title="Faculty Schedule Collisions",
                description="Instructors cannot teach two classes simultaneously",
                status="failed",
                details=faculty_issues,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="faculty_collisions",
                title="Faculty Schedule Collisions",
                description="Zero instructor double-bookings detected",
                status="passed",
                details=[],
            )
        )

    # 5. Room capacity check (vs enrolled students)
    capacity_issues = []
    # Batch query enrolled counts
    sec_ids = list(by_section.keys())
    enrolled_counts: Dict[int, int] = {}
    if sec_ids:
        enr_rows = (
            db.query(SectionEnrollment.section_id, func.count(SectionEnrollment.id))
            .filter(
                SectionEnrollment.section_id.in_(sec_ids),
                SectionEnrollment.status == "active",
            )
            .group_by(SectionEnrollment.section_id)
            .all()
        )
        enrolled_counts = {r[0]: r[1] for r in enr_rows}

    for m in meetings:
        if m.room and m.section:
            enrolled = enrolled_counts.get(m.section_id, 0)
            if enrolled > 0 and m.room.capacity < enrolled:
                crs_code = m.section.course.code if m.section.course else f"Sec {m.section_id}"
                rm_name = f"{m.room.building} {m.room.room_number}"
                msg = f"{crs_code} has {enrolled} enrolled students but assigned room {rm_name} holds only {m.room.capacity} seats"
                capacity_issues.append(msg)

    if capacity_issues:
        blocking_issues.extend(capacity_issues)
        checklist_items.append(
            VersionChecklistItem(
                code="room_capacity",
                title="Room Capacity vs Enrolled Students",
                description="Assigned classrooms must have enough seats for enrolled students",
                status="failed",
                details=capacity_issues,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="room_capacity",
                title="Room Capacity vs Enrolled Students",
                description="All assigned classrooms meet or exceed enrolled student requirements",
                status="passed",
                details=[],
            )
        )

    # 6. Unassigned rooms & faculty (Informational Warnings)
    unassigned_rooms = [m.section.course.code for m in meetings if not m.room_id and m.section and m.section.course]
    unassigned_faculty = [m.section.course.code for m in meetings if not m.faculty_id and m.section and m.section.course and not m.section.faculty_assignments]

    if unassigned_rooms or unassigned_faculty:
        warn_details = []
        if unassigned_rooms:
            warn_details.append(f"{len(unassigned_rooms)} classes have no room assigned ({', '.join(unassigned_rooms[:3])}{'...' if len(unassigned_rooms) > 3 else ''})")
        if unassigned_faculty:
            warn_details.append(f"{len(unassigned_faculty)} classes have no instructor assigned ({', '.join(unassigned_faculty[:3])}{'...' if len(unassigned_faculty) > 3 else ''})")
        warnings.extend(warn_details)
        checklist_items.append(
            VersionChecklistItem(
                code="assignments",
                title="Resource Assignment Coverage",
                description="Rooms and instructors should be assigned to classes",
                status="warning",
                details=warn_details,
            )
        )
    else:
        checklist_items.append(
            VersionChecklistItem(
                code="assignments",
                title="Resource Assignment Coverage",
                description="All scheduled classes have rooms and instructors assigned",
                status="passed",
                details=[],
            )
        )

    is_publishable = (len(blocking_issues) == 0)
    can_submit_review = is_publishable and (ver.status in ("draft", "rejected"))
    can_approve = is_publishable and (ver.status == "in_review")

    summary_text = (
        "Timetable is valid and ready for publishing"
        if is_publishable
        else f"{len(blocking_issues)} blocking issue(s) must be resolved before approval or publishing"
    )

    return VersionChecklistOut(
        version_id=ver.id,
        version_number=ver.version_number,
        version_status=ver.status,
        is_publishable=is_publishable,
        can_submit_review=can_submit_review,
        can_approve=can_approve,
        blocking_issues=blocking_issues,
        warnings=warnings,
        checklist_items=checklist_items,
        summary=summary_text,
    )


def submit_for_review(
    db: Session,
    institution_id: int,
    timetable_id: int,
    version_id: int,
    user_id: int,
    notes: Optional[str] = None,
    request = None,
) -> TimetableVersion:
    """
    Submits a draft version for review: DRAFT -> IN_REVIEW.
    Rejects invalid state shortcuts or blocked versions.
    """
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )

    if ver.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_state_transition", "message": f"Cannot submit version in '{ver.status}' status for review. Must be 'draft'."},
        )

    # Validate checklist
    checklist = run_version_checklist(db, institution_id, timetable_id, version_id)
    if not checklist.is_publishable:
        reasons = "; ".join(checklist.blocking_issues)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "version_blocked", "message": f"Cannot submit for review with blocking timetable problems: {reasons}"},
        )

    ver.status = "in_review"
    if notes:
        ver.change_summary = (ver.change_summary or "") + f"\n[Review Note]: {notes}"

    record_audit_log(
        db=db,
        user_id=user_id,
        action="timetable_version_review_submit",
        entity_type="timetable_version",
        entity_id=ver.id,
        description=f"Submitted Version {ver.version_number} for review",
        metadata={"version_number": ver.version_number, "notes": notes},
        request=request,
    )

    db.commit()
    db.refresh(ver)
    return ver


def approve_version(
    db: Session,
    institution_id: int,
    timetable_id: int,
    version_id: int,
    user_id: int,
    notes: Optional[str] = None,
    request = None,
) -> TimetableVersion:
    """
    Approves a timetable version: IN_REVIEW -> APPROVED.
    Verifies 0 blocking issues. Rejects invalid shortcuts (e.g. DRAFT -> APPROVED).
    """
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )

    if ver.status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_state_transition", "message": f"Cannot approve version in '{ver.status}' status. Version must be 'in_review'."},
        )

    # Verify checklist
    checklist = run_version_checklist(db, institution_id, timetable_id, version_id)
    if not checklist.is_publishable:
        reasons = "; ".join(checklist.blocking_issues)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "version_blocked", "message": f"Cannot approve timetable with blocking problems: {reasons}"},
        )

    ver.status = "approved"
    if notes:
        ver.change_summary = (ver.change_summary or "") + f"\n[Approval Note]: {notes}"

    record_audit_log(
        db=db,
        user_id=user_id,
        action="timetable_version_approve",
        entity_type="timetable_version",
        entity_id=ver.id,
        description=f"Approved Version {ver.version_number}",
        metadata={"version_number": ver.version_number, "notes": notes},
        request=request,
    )

    db.commit()
    db.refresh(ver)
    return ver


def publish_version(
    db: Session,
    institution_id: int,
    timetable_id: int,
    version_id: int,
    user_id: int,
    expected_updated_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    request = None,
) -> Tuple[TimetableVersion, Optional[int]]:
    """
    Atomically publishes a version:
    1. Verify status is 'approved'.
    2. Concurrency check against expected_updated_at.
    3. Revalidate checklist (0 blocking issues).
    4. Atomically archive previous published version.
    5. Mark target version as 'published' (published_at = now).
    6. Update timetable.published_version_id and timetable.status = 'active'.
    7. Record immutable audit log.
    If publication fails, previous state remains completely intact.
    """
    tt = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found"},
        )

    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )

    # Valid state transition: must be 'approved'
    if ver.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_state_transition", "message": f"Cannot publish version in '{ver.status}' status. Version must be 'approved' before publication."},
        )

    # Concurrency / Stale Check
    if expected_updated_at is not None and ver.updated_at is not None:
        dt_ver = ver.updated_at
        dt_exp = expected_updated_at
        if dt_ver.tzinfo is None:
            dt_ver = dt_ver.replace(tzinfo=timezone.utc)
        if dt_exp.tzinfo is None:
            dt_exp = dt_exp.replace(tzinfo=timezone.utc)
        if abs((dt_ver - dt_exp).total_seconds()) > 1.0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "stale_version",
                    "message": "This timetable changed after your review. Please review the latest version.",
                },
            )

    # Revalidate checklist
    checklist = run_version_checklist(db, institution_id, timetable_id, version_id)
    if not checklist.is_publishable:
        reasons = "; ".join(checklist.blocking_issues)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "version_blocked", "message": f"Cannot publish timetable with blocking problems: {reasons}"},
        )

    now_utc = datetime.now(timezone.utc)

    # 1. Archive current published version
    prev_published = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
            TimetableVersion.status == "published",
        )
        .all()
    )
    archived_id = None
    for p in prev_published:
        if p.id != ver.id:
            p.status = "archived"
            p.archived_at = now_utc
            archived_id = p.id

    # 2. Publish target version
    ver.status = "published"
    ver.published_at = now_utc

    # 3. Update Timetable root
    tt.published_version_id = ver.id
    tt.status = "active"

    # 4. Audit logging
    record_audit_log(
        db=db,
        user_id=user_id,
        action="timetable_version_publish",
        entity_type="timetable_version",
        entity_id=ver.id,
        description=f"Published official Timetable Version {ver.version_number}",
        metadata={
            "version_number": ver.version_number,
            "archived_version_id": archived_id,
            "notes": notes,
        },
        request=request,
    )

    db.commit()
    db.refresh(ver)
    return ver, archived_id


def compare_versions(
    db: Session,
    institution_id: int,
    timetable_id: int,
    base_version_id: int,
    target_version_id: int,
) -> VersionComparisonOut:
    """
    Computes a human-readable comparison between two timetable versions (e.g. V1 -> V2).
    Integrates with N6 impact analysis: detects moved classes, changed rooms, faculty reassignments,
    and calculates real student ripple effects using active section enrollments.
    """
    base_ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == base_version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    target_ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == target_version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not base_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "base_version_not_found", "message": f"Base version {base_version_id} not found"},
        )
    if not target_ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "target_version_not_found", "message": f"Target version {target_version_id} not found"},
        )

    base_meetings = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.version_id == base_ver.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .all()
    )

    target_meetings = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.version_id == target_ver.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .all()
    )

    # Group by section_id
    base_by_sec: Dict[int, List[CourseMeeting]] = {}
    for m in base_meetings:
        base_by_sec.setdefault(m.section_id, []).append(m)

    target_by_sec: Dict[int, List[CourseMeeting]] = {}
    for m in target_meetings:
        target_by_sec.setdefault(m.section_id, []).append(m)

    all_sec_ids = set(base_by_sec.keys()) | set(target_by_sec.keys())

    diffs: List[VersionMeetingDiff] = []
    time_changes = 0
    room_changes = 0
    fac_changes = 0
    added_classes = 0
    removed_classes = 0
    changed_section_ids: Set[int] = set()

    for sec_id in sorted(all_sec_ids):
        b_list = base_by_sec.get(sec_id, [])
        t_list = target_by_sec.get(sec_id, [])

        sample_sec = (b_list[0].section if b_list else None) or (t_list[0].section if t_list else None)
        crs_code = sample_sec.course.code if sample_sec and sample_sec.course else f"Sec #{sec_id}"
        crs_name = sample_sec.course.name if sample_sec and sample_sec.course else ""
        sec_code = sample_sec.section_code if sample_sec else ""

        # Match meetings sequentially
        max_len = max(len(b_list), len(t_list))
        for idx in range(max_len):
            bm = b_list[idx] if idx < len(b_list) else None
            tm = t_list[idx] if idx < len(t_list) else None

            if bm and not tm:
                # Removed
                removed_classes += 1
                changed_section_ids.add(sec_id)
                diffs.append(
                    VersionMeetingDiff(
                        section_id=sec_id,
                        course_code=crs_code,
                        course_name=crs_name,
                        section_code=sec_code,
                        change_type="removed",
                        before_day=bm.day_of_week,
                        before_day_name=DAY_NAMES.get(bm.day_of_week, ""),
                        before_start_time=format_time_str(bm.start_time),
                        before_end_time=format_time_str(bm.end_time),
                        before_room=f"{bm.room.building} {bm.room.room_number}" if bm.room else "Unassigned",
                        before_faculty=_resolve_faculty_for_meeting(bm, bm.section)[1] or "Unassigned",
                        human_summary=f"Class removed: {DAY_NAMES.get(bm.day_of_week, '')} {format_time_str(bm.start_time)}–{format_time_str(bm.end_time)}",
                    )
                )
            elif tm and not bm:
                # Added
                added_classes += 1
                changed_section_ids.add(sec_id)
                diffs.append(
                    VersionMeetingDiff(
                        section_id=sec_id,
                        course_code=crs_code,
                        course_name=crs_name,
                        section_code=sec_code,
                        change_type="added",
                        after_day=tm.day_of_week,
                        after_day_name=DAY_NAMES.get(tm.day_of_week, ""),
                        after_start_time=format_time_str(tm.start_time),
                        after_end_time=format_time_str(tm.end_time),
                        after_room=f"{tm.room.building} {tm.room.room_number}" if tm.room else "Unassigned",
                        after_faculty=_resolve_faculty_for_meeting(tm, tm.section)[1] or "Unassigned",
                        human_summary=f"New class added: {DAY_NAMES.get(tm.day_of_week, '')} {format_time_str(tm.start_time)}–{format_time_str(tm.end_time)}",
                    )
                )
            elif bm and tm:
                # Compare fields
                day_changed = (bm.day_of_week != tm.day_of_week)
                time_changed = (format_time_str(bm.start_time) != format_time_str(tm.start_time) or format_time_str(bm.end_time) != format_time_str(tm.end_time))
                room_changed = (bm.room_id != tm.room_id)
                b_fac, b_fname = _resolve_faculty_for_meeting(bm, bm.section)
                t_fac, t_fname = _resolve_faculty_for_meeting(tm, tm.section)
                fac_changed = (b_fname != t_fname)

                if day_changed or time_changed or room_changed or fac_changed:
                    changed_section_ids.add(sec_id)
                    change_parts = []
                    change_type = "modified"
                    if day_changed or time_changed:
                        time_changes += 1
                        change_type = "moved"
                        change_parts.append(
                            f"{DAY_NAMES.get(bm.day_of_week, '')} {format_time_str(bm.start_time)}–{format_time_str(bm.end_time)} → "
                            f"{DAY_NAMES.get(tm.day_of_week, '')} {format_time_str(tm.start_time)}–{format_time_str(tm.end_time)}"
                        )
                    if room_changed:
                        room_changes += 1
                        b_r = f"{bm.room.building} {bm.room.room_number}" if bm.room else "Unassigned"
                        t_r = f"{tm.room.building} {tm.room.room_number}" if tm.room else "Unassigned"
                        change_parts.append(f"Room: {b_r} → {t_r}")
                    if fac_changed:
                        fac_changes += 1
                        change_parts.append(f"Faculty: {b_fname or 'Unassigned'} → {t_fname or 'Unassigned'}")

                    diffs.append(
                        VersionMeetingDiff(
                            section_id=sec_id,
                            course_code=crs_code,
                            course_name=crs_name,
                            section_code=sec_code,
                            change_type=change_type,
                            before_day=bm.day_of_week,
                            before_day_name=DAY_NAMES.get(bm.day_of_week, ""),
                            before_start_time=format_time_str(bm.start_time),
                            before_end_time=format_time_str(bm.end_time),
                            before_room=f"{bm.room.building} {bm.room.room_number}" if bm.room else "Unassigned",
                            before_faculty=b_fname or "Unassigned",
                            after_day=tm.day_of_week,
                            after_day_name=DAY_NAMES.get(tm.day_of_week, ""),
                            after_start_time=format_time_str(tm.start_time),
                            after_end_time=format_time_str(tm.end_time),
                            after_room=f"{tm.room.building} {tm.room.room_number}" if tm.room else "Unassigned",
                            after_faculty=t_fname or "Unassigned",
                            human_summary="; ".join(change_parts),
                        )
                    )

    # ── N6 Impact Integration: Real Student Ripple Effects ───────────────────
    students_affected_set: Set[int] = set()
    new_conflicts_count = 0
    resolved_conflicts_count = 0

    if changed_section_ids:
        # 1. Fetch active enrollments for changed sections
        enrollments = (
            db.query(SectionEnrollment)
            .filter(
                SectionEnrollment.section_id.in_(list(changed_section_ids)),
                SectionEnrollment.status == "active",
            )
            .all()
        )
        enrolled_student_ids = list(set(e.student_id for e in enrollments))
        sec_to_students: Dict[int, List[int]] = {}
        for e in enrollments:
            sec_to_students.setdefault(e.section_id, []).append(e.student_id)

        if enrolled_student_ids:
            # Preload student commitments in a single batched query
            timeblocks = (
                db.query(TimeBlock)
                .filter(
                    TimeBlock.user_id.in_(enrolled_student_ids),
                    TimeBlock.deleted == False,
                )
                .all()
            )
            blocks_by_student: Dict[int, List[TimeBlock]] = {}
            for tb in timeblocks:
                blocks_by_student.setdefault(tb.user_id, []).append(tb)

            # Preload student availability blackouts
            availabilities = (
                db.query(StudentAvailability)
                .filter(
                    StudentAvailability.student_id.in_(enrolled_student_ids),
                    StudentAvailability.is_available == False,
                )
                .all()
            )
            avail_by_student: Dict[int, List[StudentAvailability]] = {}
            for av in availabilities:
                avail_by_student.setdefault(av.student_id, []).append(av)

            # Preload student hard constraints
            constraints = (
                db.query(StudentConstraint)
                .filter(
                    StudentConstraint.student_id.in_(enrolled_student_ids),
                    StudentConstraint.is_hard == True,
                )
                .all()
            )
            const_by_student: Dict[int, List[StudentConstraint]] = {}
            for sc in constraints:
                const_by_student.setdefault(sc.student_id, []).append(sc)

            # Calculate conflict delta for each diff
            for diff in diffs:
                st_ids = sec_to_students.get(diff.section_id, [])
                for sid in st_ids:
                    has_change_impact = False

                    # Check before slot conflicts
                    b_conflicts = 0
                    if diff.before_day is not None and diff.before_start_time and diff.before_end_time:
                        b_s = time_to_minutes(diff.before_start_time)
                        b_e = time_to_minutes(diff.before_end_time)
                        for tb in blocks_by_student.get(sid, []):
                            if tb.day_of_week == diff.before_day:
                                ts, te = time_to_minutes(tb.start_time), time_to_minutes(tb.end_time)
                                if b_s < te and ts < b_e:
                                    b_conflicts += 1

                    # Check after slot conflicts
                    a_conflicts = 0
                    if diff.after_day is not None and diff.after_start_time and diff.after_end_time:
                        a_s = time_to_minutes(diff.after_start_time)
                        a_e = time_to_minutes(diff.after_end_time)
                        for tb in blocks_by_student.get(sid, []):
                            if tb.day_of_week == diff.after_day:
                                ts, te = time_to_minutes(tb.start_time), time_to_minutes(tb.end_time)
                                if a_s < te and ts < a_e:
                                    a_conflicts += 1
                        for av in avail_by_student.get(sid, []):
                            if av.day_of_week == diff.after_day:
                                as_, ae_ = time_to_minutes(av.start_time), time_to_minutes(av.end_time)
                                if a_s < ae_ and as_ < a_e:
                                    a_conflicts += 1

                    if a_conflicts > b_conflicts:
                        new_conflicts_count += (a_conflicts - b_conflicts)
                        has_change_impact = True
                    elif b_conflicts > a_conflicts:
                        resolved_conflicts_count += (b_conflicts - a_conflicts)
                        has_change_impact = True

                    if (diff.before_day != diff.after_day or diff.before_start_time != diff.after_start_time):
                        students_affected_set.add(sid)
                    elif has_change_impact:
                        students_affected_set.add(sid)

    return VersionComparisonOut(
        base_version_id=base_ver.id,
        base_version_number=base_ver.version_number,
        base_version_name=base_ver.name,
        target_version_id=target_ver.id,
        target_version_number=target_ver.version_number,
        target_version_name=target_ver.name,
        total_classes_changed=len(diffs),
        time_changes_count=time_changes,
        room_changes_count=room_changes,
        faculty_changes_count=fac_changes,
        added_classes_count=added_classes,
        removed_classes_count=removed_classes,
        students_affected=len(students_affected_set),
        new_conflicts=new_conflicts_count,
        resolved_conflicts=resolved_conflicts_count,
        diffs=diffs,
    )
