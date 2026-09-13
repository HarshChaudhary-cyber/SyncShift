"""
Impact Analysis Service for Task N6: University Timetable Editor + Impact Analysis.
Performs deterministic, pre-save timetable change validation, batched student conflict
calculations, room and faculty impact analysis, and privacy-sanitized impact reporting.
"""
from datetime import time
from typing import Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
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
from app.models.user import User
from app.schemas.timetable import (
    ImpactSummary,
    MeetingSnapshot,
    StudentImpactDetail,
    TimetableChangeProposal,
    TimetableImpactResponse,
)
from app.services.timetable_validator import (
    DAY_NAMES,
    format_time_str,
    parse_time_obj,
    time_to_minutes,
    validate_course_meeting,
)


def _format_time_hhmm(t_val) -> str:
    """Safely formats time into HH:MM."""
    if isinstance(t_val, time):
        return t_val.strftime("%H:%M")
    s = str(t_val).strip()
    return s[:5] if len(s) >= 5 else s


def _intervals_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    """Standard interval overlap: A.start < B.end AND B.start < A.end."""
    return s1 < e2 and s2 < e1


def analyze_timetable_change(
    db: Session,
    institution_id: int,
    timetable_id: int,
    proposal: TimetableChangeProposal,
) -> TimetableImpactResponse:
    """
    Computes a comprehensive, deterministic impact analysis for a proposed timetable change.
    STRICTLY READ-ONLY: performs zero mutations to the database.
    """
    # 1. Fetch existing CourseMeeting with joined relations
    meeting = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.timetable),
        )
        .filter(
            CourseMeeting.id == proposal.meeting_id,
            CourseMeeting.timetable_id == timetable_id,
            CourseMeeting.institution_id == institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {proposal.meeting_id} not found"},
        )

    sec = meeting.section
    crs = sec.course if sec else None
    rm_before = meeting.room
    fac_before = meeting.faculty
    fac_user_before = fac_before.user if fac_before else None

    # Resolve instructor name before
    fac_name_before = None
    if fac_user_before:
        fac_name_before = fac_user_before.display_name or fac_user_before.name or fac_user_before.email
    elif sec and sec.faculty_assignments:
        for fa in sec.faculty_assignments:
            if fa.is_primary and fa.faculty and fa.faculty.user:
                fac_name_before = fa.faculty.user.display_name or fa.faculty.user.name or fa.faculty.user.email
                break

    # Build BEFORE snapshot
    room_label_before = None
    if rm_before:
        room_label_before = f"{rm_before.building} {rm_before.room_number}".strip()

    snapshot_before = MeetingSnapshot(
        meeting_id=meeting.id,
        section_id=meeting.section_id,
        course_id=crs.id if crs else None,
        course_code=crs.code if crs else None,
        course_name=crs.name if crs else None,
        section_code=sec.section_code if sec else None,
        section_capacity=sec.capacity if sec else None,
        day_of_week=meeting.day_of_week,
        day_name=DAY_NAMES.get(meeting.day_of_week, "Unknown"),
        start_time=format_time_str(meeting.start_time),
        end_time=format_time_str(meeting.end_time),
        room_id=rm_before.id if rm_before else None,
        room_label=room_label_before,
        room_capacity=rm_before.capacity if rm_before else None,
        faculty_id=fac_before.id if fac_before else None,
        faculty_name=fac_name_before,
        updated_at=meeting.updated_at,
    )

    # 2. Determine target fields for proposed AFTER state
    target_day = proposal.day_of_week
    target_start_val = proposal.start_time
    target_end_val = proposal.end_time
    target_room_id = proposal.room_id if proposal.room_id is not None else meeting.room_id
    if proposal.room_id == 0:
        target_room_id = None
    target_faculty_id = proposal.faculty_id if proposal.faculty_id is not None else meeting.faculty_id
    if proposal.faculty_id == 0:
        target_faculty_id = None

    # 3. Pre-Save Validation (catch blocking violations gracefully for preview)
    is_blocked = False
    blocked_reasons: List[str] = []
    room_issues: List[str] = []
    faculty_issues: List[str] = []

    target_start_time = None
    target_end_time = None
    rm_after = None
    fac_after = None

    try:
        (
            target_start_time,
            target_end_time,
            val_sec,
            val_tt,
            rm_after,
            fac_after,
        ) = validate_course_meeting(
            db=db,
            institution_id=institution_id,
            timetable_id=timetable_id,
            section_id=meeting.section_id,
            day_of_week=target_day,
            start_time_val=target_start_val,
            end_time_val=target_end_val,
            room_id=target_room_id,
            faculty_id=target_faculty_id,
            existing_meeting_id=meeting.id,
        )
    except HTTPException as exc:
        is_blocked = True
        err_detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail), "code": "validation_error"}
        err_msg = err_detail.get("message", "Validation constraint violation")
        err_code = err_detail.get("code", "")
        blocked_reasons.append(err_msg)

        if "room" in err_code:
            room_issues.append(err_msg)
        elif "faculty" in err_code:
            faculty_issues.append(err_msg)

        # Fallback objects for AFTER snapshot rendering
        try:
            target_start_time = parse_time_obj(target_start_val)
            target_end_time = parse_time_obj(target_end_val)
        except Exception:
            target_start_time = meeting.start_time
            target_end_time = meeting.end_time

        if target_room_id is not None:
            rm_after = db.query(Room).filter(Room.id == target_room_id).first()
        if target_faculty_id is not None:
            fac_after = db.query(FacultyProfile).filter(FacultyProfile.id == target_faculty_id).first()

    # Resolve instructor name after
    fac_name_after = None
    if fac_after and fac_after.user:
        fac_name_after = fac_after.user.display_name or fac_after.user.name or fac_after.user.email
    else:
        fac_name_after = fac_name_before

    room_label_after = None
    if rm_after:
        room_label_after = f"{rm_after.building} {rm_after.room_number}".strip()

    # Build AFTER snapshot
    snapshot_after = MeetingSnapshot(
        meeting_id=meeting.id,
        section_id=meeting.section_id,
        course_id=crs.id if crs else None,
        course_code=crs.code if crs else None,
        course_name=crs.name if crs else None,
        section_code=sec.section_code if sec else None,
        section_capacity=sec.capacity if sec else None,
        day_of_week=target_day,
        day_name=DAY_NAMES.get(target_day, "Unknown"),
        start_time=_format_time_hhmm(target_start_time),
        end_time=_format_time_hhmm(target_end_time),
        room_id=rm_after.id if rm_after else None,
        room_label=room_label_after,
        room_capacity=rm_after.capacity if rm_after else None,
        faculty_id=fac_after.id if fac_after else None,
        faculty_name=fac_name_after,
        updated_at=meeting.updated_at,
    )

    # 4. Fetch Active Enrolled Students (authoritative real records, not capacity)
    enrollments = (
        db.query(SectionEnrollment)
        .filter(
            SectionEnrollment.section_id == meeting.section_id,
            SectionEnrollment.institution_id == institution_id,
            SectionEnrollment.status == "active",
            SectionEnrollment.dropped_at.is_(None),
        )
        .all()
    )
    student_ids: List[int] = [e.student_id for e in enrollments]
    students_affected_count = len(student_ids)

    # If no students enrolled, return early with validation status
    if not student_ids:
        severity = "BLOCKED" if is_blocked else "LOW"
        summary = ImpactSummary(
            severity=severity,
            students_affected=0,
            new_conflicts=0,
            resolved_conflicts=0,
            work_conflicts=0,
            personal_conflicts=0,
            class_conflicts=0,
            availability_conflicts=0,
            hard_constraint_conflicts=0,
            room_issues=room_issues,
            faculty_issues=faculty_issues,
            blocked_reasons=blocked_reasons,
        )
        return TimetableImpactResponse(
            is_blocked=is_blocked,
            summary=summary,
            before=snapshot_before,
            after=snapshot_after,
            student_impacts=[],
        )

    # 5. Batched In-Memory Schedule Context for Enrolled Students
    before_day = meeting.day_of_week
    after_day = target_day
    before_s_min = time_to_minutes(meeting.start_time)
    before_e_min = time_to_minutes(meeting.end_time)
    after_s_min = time_to_minutes(target_start_time)
    after_e_min = time_to_minutes(target_end_time)

    # Batch Query A: User objects for display names
    users = db.query(User).filter(User.id.in_(student_ids)).all()
    user_map = {u.id: u for u in users}

    # Batch Query B: Student TimeBlocks on relevant days
    relevant_days = list({before_day, after_day})
    blocks = (
        db.query(TimeBlock)
        .filter(
            TimeBlock.user_id.in_(student_ids),
            TimeBlock.deleted == False,
            TimeBlock.day_of_week.in_(relevant_days),
        )
        .all()
    )
    student_blocks: Dict[int, List[TimeBlock]] = {}
    for b in blocks:
        student_blocks.setdefault(b.user_id, []).append(b)

    # Batch Query C: Other active CourseMeetings for these students on relevant days
    other_enrollments = (
        db.query(SectionEnrollment.student_id, SectionEnrollment.section_id)
        .filter(
            SectionEnrollment.student_id.in_(student_ids),
            SectionEnrollment.section_id != meeting.section_id,
            SectionEnrollment.institution_id == institution_id,
            SectionEnrollment.status == "active",
            SectionEnrollment.dropped_at.is_(None),
        )
        .all()
    )
    other_section_ids = list({sec_id for _, sec_id in other_enrollments})
    student_other_sec_ids: Dict[int, Set[int]] = {}
    for stu_id, sec_id in other_enrollments:
        student_other_sec_ids.setdefault(stu_id, set()).add(sec_id)

    other_meetings: List[CourseMeeting] = []
    if other_section_ids:
        other_meetings = (
            db.query(CourseMeeting)
            .options(joinedload(CourseMeeting.section).joinedload(AcademicSection.course))
            .filter(
                CourseMeeting.section_id.in_(other_section_ids),
                CourseMeeting.timetable_id == timetable_id,
                CourseMeeting.day_of_week.in_(relevant_days),
                CourseMeeting.status == "active",
                CourseMeeting.deleted_at.is_(None),
            )
            .all()
        )
    sec_to_meetings: Dict[int, List[CourseMeeting]] = {}
    for om in other_meetings:
        sec_to_meetings.setdefault(om.section_id, []).append(om)

    # Batch Query D: Student Availability blackouts on relevant days
    availabilities = (
        db.query(StudentAvailability)
        .filter(
            StudentAvailability.user_id.in_(student_ids),
            StudentAvailability.day_of_week.in_(relevant_days),
            StudentAvailability.is_available == False,
        )
        .all()
    )
    student_avails: Dict[int, List[StudentAvailability]] = {}
    for av in availabilities:
        student_avails.setdefault(av.user_id, []).append(av)

    # Batch Query E: Hard student constraints
    constraints = (
        db.query(StudentConstraint)
        .filter(
            StudentConstraint.user_id.in_(student_ids),
            StudentConstraint.is_active == True,
            StudentConstraint.is_hard == True,
        )
        .all()
    )
    student_constraints: Dict[int, List[StudentConstraint]] = {}
    for c in constraints:
        student_constraints.setdefault(c.user_id, []).append(c)

    # 6. Evaluate Conflicts For Each Student
    work_conflicts = 0
    personal_conflicts = 0
    class_conflicts = 0
    availability_conflicts = 0
    hard_constraint_conflicts = 0
    resolved_conflicts = 0

    student_impact_details: List[StudentImpactDetail] = []

    for stu_id in student_ids:
        user = user_map.get(stu_id)
        stu_name = "Student"
        if user:
            stu_name = user.display_name or user.name or f"Student #{user.id}"

        # Helper to check slot conflicts for a given day and time range
        def _check_slot_conflicts(dow: int, s_min: int, e_min: int) -> List[Tuple[str, str, str]]:
            """Returns list of (conflict_type, description, overlap_time) for a given slot."""
            results: List[Tuple[str, str, str]] = []

            # A. Check TimeBlocks (work shifts, personal events, manual blocks)
            for b in student_blocks.get(stu_id, []):
                if b.day_of_week != dow:
                    continue
                b_s = time_to_minutes(b.start_time)
                b_e = time_to_minutes(b.end_time)
                if _intervals_overlap(s_min, e_min, b_s, b_e):
                    ov_s = max(s_min, b_s)
                    ov_e = min(e_min, b_e)
                    ov_time_str = f"{ov_s // 60:02d}:{ov_s % 60:02d}–{ov_e // 60:02d}:{ov_e % 60:02d}"
                    b_type_str = str(b.type.value if hasattr(b.type, "value") else b.type)
                    if b_type_str == "shift":
                        results.append(("work_shift", f"Work shift conflict on {DAY_NAMES.get(dow, '')}", ov_time_str))
                    elif b_type_str == "class":
                        results.append(("other_class", f"Class overlap on {DAY_NAMES.get(dow, '')}", ov_time_str))
                    else:
                        results.append(("personal", f"Personal commitment overlap on {DAY_NAMES.get(dow, '')}", ov_time_str))

            # B. Check Other Enrolled CourseMeetings
            for sec_id in student_other_sec_ids.get(stu_id, set()):
                for om in sec_to_meetings.get(sec_id, []):
                    if om.day_of_week != dow:
                        continue
                    om_s = time_to_minutes(om.start_time)
                    om_e = time_to_minutes(om.end_time)
                    if _intervals_overlap(s_min, e_min, om_s, om_e):
                        ov_s = max(s_min, om_s)
                        ov_e = min(e_min, om_e)
                        ov_time_str = f"{ov_s // 60:02d}:{ov_s % 60:02d}–{ov_e // 60:02d}:{ov_e % 60:02d}"
                        crs_label = om.section.course.code if om.section and om.section.course else f"Section {om.section_id}"
                        results.append(("other_class", f"Overlap with {crs_label}", ov_time_str))

            # C. Check Unavailable Blackout Periods
            for av in student_avails.get(stu_id, []):
                if av.day_of_week != dow:
                    continue
                av_s = time_to_minutes(av.start_time)
                av_e = time_to_minutes(av.end_time)
                if _intervals_overlap(s_min, e_min, av_s, av_e):
                    ov_s = max(s_min, av_s)
                    ov_e = min(e_min, av_e)
                    ov_time_str = f"{ov_s // 60:02d}:{ov_s % 60:02d}–{ov_e // 60:02d}:{ov_e % 60:02d}"
                    results.append(("unavailable", f"Unavailable period on {DAY_NAMES.get(dow, '')}", ov_time_str))

            # D. Check Hard Constraints
            for sc in student_constraints.get(stu_id, []):
                sc_dow = sc.day_of_week
                if sc_dow is not None and sc_dow != dow:
                    continue
                if sc.constraint_type == "day_off" and sc_dow == dow:
                    results.append(("hard_constraint", f"Day off constraint on {DAY_NAMES.get(dow, '')}", f"{s_min // 60:02d}:{s_min % 60:02d}–{e_min // 60:02d}:{e_min % 60:02d}"))
                elif sc.constraint_type == "earliest_start" and sc.time_value:
                    earliest_m = time_to_minutes(sc.time_value)
                    if s_min < earliest_m:
                        results.append(("hard_constraint", f"Starts before earliest allowed time ({_format_time_hhmm(sc.time_value)})", f"{s_min // 60:02d}:{s_min % 60:02d}"))
                elif sc.constraint_type == "latest_end" and sc.time_value:
                    latest_m = time_to_minutes(sc.time_value)
                    if e_min > latest_m:
                        results.append(("hard_constraint", f"Ends after latest allowed time ({_format_time_hhmm(sc.time_value)})", f"{e_min // 60:02d}:{e_min % 60:02d}"))

            return results

        before_conflicts = _check_slot_conflicts(before_day, before_s_min, before_e_min)
        after_conflicts = _check_slot_conflicts(after_day, after_s_min, after_e_min)

        # Before conflict signatures for diffing
        before_sigs = {(c_type, desc) for c_type, desc, _ in before_conflicts}
        after_sigs = {(c_type, desc) for c_type, desc, _ in after_conflicts}

        # Identify newly created conflicts
        new_for_stu = [c for c in after_conflicts if (c[0], c[1]) not in before_sigs]
        # Identify resolved conflicts
        resolved_for_stu = [c for c in before_conflicts if (c[0], c[1]) not in after_sigs]

        resolved_conflicts += len(resolved_for_stu)

        if new_for_stu:
            for c_type, c_desc, ov_time in new_for_stu:
                if c_type == "work_shift":
                    work_conflicts += 1
                elif c_type == "personal":
                    personal_conflicts += 1
                elif c_type == "other_class":
                    class_conflicts += 1
                elif c_type == "unavailable":
                    availability_conflicts += 1
                elif c_type == "hard_constraint":
                    hard_constraint_conflicts += 1

                student_impact_details.append(
                    StudentImpactDetail(
                        student_id=stu_id,
                        student_name=stu_name,
                        conflict_type=c_type,
                        conflict_description=c_desc,
                        overlap_time=ov_time,
                        is_new_conflict=True,
                        is_resolved_conflict=False,
                    )
                )
        elif resolved_for_stu:
            for c_type, c_desc, ov_time in resolved_for_stu:
                student_impact_details.append(
                    StudentImpactDetail(
                        student_id=stu_id,
                        student_name=stu_name,
                        conflict_type=c_type,
                        conflict_description=f"Resolved: {c_desc}",
                        overlap_time=ov_time,
                        is_new_conflict=False,
                        is_resolved_conflict=True,
                    )
                )
        else:
            # Student schedule shifted without conflict
            student_impact_details.append(
                StudentImpactDetail(
                    student_id=stu_id,
                    student_name=stu_name,
                    conflict_type="none",
                    conflict_description="Schedule shifted (no conflicts)",
                    overlap_time=None,
                    is_new_conflict=False,
                    is_resolved_conflict=False,
                )
            )

    new_conflicts_total = (
        work_conflicts
        + personal_conflicts
        + class_conflicts
        + availability_conflicts
        + hard_constraint_conflicts
    )

    # 7. Severity Determination
    if is_blocked:
        severity = "BLOCKED"
    elif new_conflicts_total >= 5 or students_affected_count > 50 or work_conflicts > 0 or availability_conflicts > 0:
        severity = "HIGH"
    elif new_conflicts_total > 0 or (students_affected_count > 10 and new_conflicts_total == 0):
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Add Room capacity note if changed
    if rm_after and sec and rm_after.capacity < sec.capacity:
        cap_msg = f"Room capacity ({rm_after.capacity}) is lower than section capacity ({sec.capacity})"
        if cap_msg not in room_issues:
            room_issues.append(cap_msg)

    summary = ImpactSummary(
        severity=severity,
        students_affected=students_affected_count,
        new_conflicts=new_conflicts_total,
        resolved_conflicts=resolved_conflicts,
        work_conflicts=work_conflicts,
        personal_conflicts=personal_conflicts,
        class_conflicts=class_conflicts,
        availability_conflicts=availability_conflicts,
        hard_constraint_conflicts=hard_constraint_conflicts,
        room_issues=room_issues,
        faculty_issues=faculty_issues,
        blocked_reasons=blocked_reasons,
    )

    return TimetableImpactResponse(
        is_blocked=is_blocked,
        summary=summary,
        before=snapshot_before,
        after=snapshot_after,
        student_impacts=student_impact_details,
    )
