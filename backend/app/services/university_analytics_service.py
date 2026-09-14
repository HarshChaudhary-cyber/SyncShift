"""
University Analytics Service for Task N10 — University Analytics & Decision Dashboard.

Provides deterministic, term-aware, tenant-isolated calculations for:
1. Overview KPIs
2. Enrollment Demand & Capacity Utilization (high demand vs low utilization)
3. Room Scheduled Utilization (honest weekly scheduled hours, never physical occupancy)
4. Faculty Teaching Schedules & Hours (neutral operational wording)
5. Timetable Health & Conflict Analytics (room, faculty, student class & work conflicts)
6. Timetable Publication History & Student Impact
7. Departmental Operations Comparison
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.course_meeting import CourseMeeting
from app.models.department import Department
from app.models.faculty import FacultyProfile
from app.models.institution import Institution
from app.models.notification import NotificationLog
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.student_profile import StudentProfile
from app.models.time_block import TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User

from app.schemas.university_analytics import (
    AnalyticsOverviewKPIs,
    AnalyticsTermOption,
    DailyRoomUtilization,
    DepartmentComparisonItem,
    EnrollmentAnalyticsData,
    FacultyAnalyticsData,
    FacultyScheduleItem,
    RoomAnalyticsData,
    RoomUtilizationItem,
    SectionDemandItem,
    TimetableChangeHistoryItem,
    TimetableConflictSummary,
    TimetableHealthAnalyticsData,
    UniversityDashboardAnalyticsResponse,
)


def _time_to_minutes(t) -> int:
    if t is None:
        return 0
    return t.hour * 60 + t.minute


def _calc_hours(start_time, end_time) -> float:
    s = _time_to_minutes(start_time)
    e = _time_to_minutes(end_time)
    if e > s:
        return (e - s) / 60.0
    return 0.0


def _intervals_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    return s1 < e2 and s2 < e1


def resolve_term(
    db: Session, institution_id: int, term_id: Optional[int] = None
) -> Tuple[Optional[AcademicTerm], List[AnalyticsTermOption]]:
    """Resolves the requested or active term for an institution and lists available terms."""
    terms_query = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.institution_id == institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .order_by((AcademicTerm.status == "active").desc(), AcademicTerm.start_date.desc())
        .all()
    )
    available_terms = [
        AnalyticsTermOption(
            id=t.id,
            name=t.name,
            academic_year=t.academic_year,
            status=t.status,
            is_active=(t.status == "active"),
            start_date=t.start_date,
            end_date=t.end_date,
        )
        for t in terms_query
    ]

    selected_term: Optional[AcademicTerm] = None
    if term_id is not None:
        selected_term = next((t for t in terms_query if t.id == term_id), None)
    
    if selected_term is None:
        # Pick active term or most recent
        selected_term = next((t for t in terms_query if t.status == "active"), None)
        if selected_term is None and terms_query:
            selected_term = terms_query[0]

    return selected_term, available_terms


def get_active_timetable_and_meetings(
    db: Session, institution_id: int, term_id: Optional[int]
) -> Tuple[Optional[Timetable], List[CourseMeeting]]:
    """
    Finds the active or published timetable for the term and returns its active meetings.
    If published version exists, official published meetings are used.
    Otherwise, active draft meetings of the current timetable are used.
    """
    if term_id is None:
        return None, []

    timetable = (
        db.query(Timetable)
        .filter(
            Timetable.institution_id == institution_id,
            Timetable.academic_term_id == term_id,
            Timetable.deleted_at.is_(None),
        )
        .order_by(Timetable.published_version_id.isnot(None).desc(), Timetable.id.desc())
        .first()
    )

    if not timetable:
        return None, []

    meetings_query = (
        db.query(CourseMeeting)
        .filter(
            CourseMeeting.institution_id == institution_id,
            CourseMeeting.status == "active",
            CourseMeeting.deleted_at.is_(None),
        )
    )

    if timetable.published_version_id:
        meetings = meetings_query.filter(CourseMeeting.version_id == timetable.published_version_id).all()
    else:
        meetings = meetings_query.filter(CourseMeeting.timetable_id == timetable.id).all()

    return timetable, meetings


# =========================================================================
# 1. ENROLLMENT DEMAND & CAPACITY ANALYTICS
# =========================================================================

def get_enrollment_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> EnrollmentAnalyticsData:
    """
    Calculates real section capacity utilization and identifies high-demand and low-utilization sections.
    """
    term, _ = resolve_term(db, institution_id, term_id)
    if not term:
        return EnrollmentAnalyticsData()

    query = (
        db.query(AcademicSection)
        .join(AcademicCourse, AcademicCourse.id == AcademicSection.course_id)
        .filter(
            AcademicSection.institution_id == institution_id,
            AcademicSection.academic_term_id == term.id,
            AcademicSection.status == "active",
            AcademicSection.deleted_at.is_(None),
            AcademicCourse.deleted_at.is_(None),
        )
    )

    if department_id is not None:
        query = query.filter(AcademicCourse.department_id == department_id)

    sections = query.all()
    if not sections:
        return EnrollmentAnalyticsData()

    section_ids = [s.id for s in sections]

    # Count active enrollments grouped by section_id
    enrollment_counts = dict(
        db.query(SectionEnrollment.section_id, func.count(SectionEnrollment.id))
        .filter(
            SectionEnrollment.institution_id == institution_id,
            SectionEnrollment.section_id.in_(section_ids),
            SectionEnrollment.status.in_(["active", "enrolled"]),
        )
        .group_by(SectionEnrollment.section_id)
        .all()
    )

    items: List[SectionDemandItem] = []
    total_capacity = 0
    total_enrolled = 0

    for s in sections:
        cap = s.capacity or 0
        enr = enrollment_counts.get(s.id, 0)
        rem = max(0, cap - enr)
        util_pct = round((enr / cap * 100.0), 1) if cap > 0 else 0.0

        if enr > cap:
            demand_status = "over_capacity"
        elif enr == cap and cap > 0:
            demand_status = "full"
        elif util_pct >= 90.0:
            demand_status = "high_demand"
        elif util_pct <= 30.0:
            demand_status = "low_utilization"
        else:
            demand_status = "moderate"

        dept_name = s.course.department.name if (s.course and s.course.department) else None

        items.append(
            SectionDemandItem(
                section_id=s.id,
                section_code=s.section_code,
                course_code=s.course.code if s.course else "",
                course_name=s.course.name if s.course else "",
                department_name=dept_name,
                capacity=cap,
                enrolled_count=enr,
                remaining_seats=rem,
                utilization_pct=util_pct,
                demand_status=demand_status,
            )
        )
        total_capacity += cap
        total_enrolled += enr

    # Sort all sections by utilization descending
    items.sort(key=lambda x: x.utilization_pct, reverse=True)

    high_demand = [item for item in items if item.demand_status in ("high_demand", "full", "over_capacity")]
    low_util = [item for item in items if item.demand_status == "low_utilization"]

    overall_util = round((total_enrolled / total_capacity * 100.0), 1) if total_capacity > 0 else 0.0

    return EnrollmentAnalyticsData(
        total_capacity=total_capacity,
        total_enrolled=total_enrolled,
        overall_capacity_utilization_pct=overall_util,
        high_demand_sections=high_demand,
        low_utilization_sections=low_util,
        all_sections=items,
    )


# =========================================================================
# 2. ROOM SCHEDULED UTILIZATION ANALYTICS
# =========================================================================

def get_room_utilization_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> RoomAnalyticsData:
    """
    Calculates scheduled weekly hours and scheduled room utilization percentage.
    Honest reporting: based strictly on scheduled meetings.
    Operating baseline: 45 scheduled hours / week (Mon-Fri standard university schedule).
    """
    term, _ = resolve_term(db, institution_id, term_id)
    if not term:
        return RoomAnalyticsData()

    rooms = (
        db.query(Room)
        .filter(
            Room.institution_id == institution_id,
            Room.deleted_at.is_(None),
        )
        .order_by(Room.building.asc(), Room.room_number.asc())
        .all()
    )

    if not rooms:
        return RoomAnalyticsData()

    _, meetings = get_active_timetable_and_meetings(db, institution_id, term.id)

    # If department filter is active, filter meetings by section course department
    if department_id is not None:
        meetings = [
            m for m in meetings
            if m.section and m.section.course and m.section.course.department_id == department_id
        ]

    # Map meetings by room_id and day_of_week
    meetings_by_room: Dict[int, List[CourseMeeting]] = {}
    daily_hours: Dict[int, float] = {d: 0.0 for d in range(7)}
    daily_counts: Dict[int, int] = {d: 0 for d in range(7)}

    for m in meetings:
        if m.room_id is not None:
            meetings_by_room.setdefault(m.room_id, []).append(m)
            hrs = _calc_hours(m.start_time, m.end_time)
            d = m.day_of_week if 0 <= m.day_of_week <= 6 else 1
            daily_hours[d] += hrs
            daily_counts[d] += 1

    room_items: List[RoomUtilizationItem] = []
    total_weekly_capacity_hours = len(rooms) * 45.0
    total_weekly_scheduled_hours = 0.0

    for r in rooms:
        r_meetings = meetings_by_room.get(r.id, [])
        sched_hours = sum(_calc_hours(m.start_time, m.end_time) for m in r_meetings)
        util_pct = round(min(100.0, (sched_hours / 45.0) * 100.0), 1)

        total_weekly_scheduled_hours += sched_hours

        room_items.append(
            RoomUtilizationItem(
                room_id=r.id,
                room_number=r.room_number,
                building=r.building,
                room_type=r.room_type,
                capacity=r.capacity,
                weekly_scheduled_hours=round(sched_hours, 1),
                scheduled_utilization_pct=util_pct,
                meetings_count=len(r_meetings),
                status=r.status,
            )
        )

    # Sort by scheduled utilization
    room_items.sort(key=lambda x: x.weekly_scheduled_hours, reverse=True)
    most_used = room_items[:10]
    least_used = sorted(room_items, key=lambda x: x.weekly_scheduled_hours)[:10]

    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    # Standard academic week: Monday through Friday, plus Sat/Sun if used
    ordered_days = [1, 2, 3, 4, 5, 6, 0]
    daily_dist = [
        DailyRoomUtilization(
            day_of_week=d,
            day_name=day_names[d],
            scheduled_hours=round(daily_hours[d], 1),
            meeting_count=daily_counts[d],
        )
        for d in ordered_days
    ]

    active_rooms_count = sum(1 for r in rooms if r.status == "active")
    avg_util = round((total_weekly_scheduled_hours / total_weekly_capacity_hours * 100.0), 1) if total_weekly_capacity_hours > 0 else 0.0

    return RoomAnalyticsData(
        total_rooms=len(rooms),
        active_rooms=active_rooms_count,
        total_weekly_capacity_hours=total_weekly_capacity_hours,
        total_weekly_scheduled_hours=round(total_weekly_scheduled_hours, 1),
        average_utilization_pct=avg_util,
        most_used_rooms=most_used,
        least_used_rooms=least_used,
        daily_distribution=daily_dist,
        rooms=room_items,
    )


# =========================================================================
# 3. FACULTY SCHEDULE & TEACHING LOAD INSIGHTS
# =========================================================================

def get_faculty_schedule_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> FacultyAnalyticsData:
    """
    Provides neutral operational insights into teaching schedules, scheduled hours, and overlap conflicts.
    Avoids judgmental ratings or performance assumptions.
    """
    term, _ = resolve_term(db, institution_id, term_id)
    if not term:
        return FacultyAnalyticsData()

    query = (
        db.query(FacultyProfile)
        .join(User, User.id == FacultyProfile.user_id)
        .filter(
            FacultyProfile.institution_id == institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
    )

    if department_id is not None:
        query = query.filter(FacultyProfile.department_id == department_id)

    faculty_list = query.all()
    if not faculty_list:
        return FacultyAnalyticsData()

    _, meetings = get_active_timetable_and_meetings(db, institution_id, term.id)

    meetings_by_faculty: Dict[int, List[CourseMeeting]] = {}
    for m in meetings:
        if m.faculty_id is not None:
            meetings_by_faculty.setdefault(m.faculty_id, []).append(m)

    items: List[FacultyScheduleItem] = []
    total_hours = 0.0
    teaching_faculty_count = 0

    for f in faculty_list:
        f_meetings = meetings_by_faculty.get(f.id, [])
        hours = sum(_calc_hours(m.start_time, m.end_time) for m in f_meetings)
        unique_sections = len(set(m.section_id for m in f_meetings))

        # Check for schedule conflicts (same day overlap)
        has_conflict = False
        day_meetings: Dict[int, List[CourseMeeting]] = {}
        for m in f_meetings:
            day_meetings.setdefault(m.day_of_week, []).append(m)

        for d, d_list in day_meetings.items():
            if len(d_list) > 1:
                for i in range(len(d_list)):
                    for j in range(i + 1, len(d_list)):
                        s1 = _time_to_minutes(d_list[i].start_time)
                        e1 = _time_to_minutes(d_list[i].end_time)
                        s2 = _time_to_minutes(d_list[j].start_time)
                        e2 = _time_to_minutes(d_list[j].end_time)
                        if _intervals_overlap(s1, e1, s2, e2):
                            has_conflict = True
                            break
                    if has_conflict:
                        break
            if has_conflict:
                break

        if hours > 0:
            teaching_faculty_count += 1
            total_hours += hours

        dept_name = f.department.name if f.department else None
        user_name = f.user.name or f.user.email.split("@")[0] if f.user else "Faculty Member"

        items.append(
            FacultyScheduleItem(
                faculty_id=f.id,
                user_id=f.user_id,
                name=user_name,
                email=f.user.email if f.user else "",
                department_name=dept_name,
                title=f.title,
                sections_count=unique_sections,
                weekly_teaching_hours=round(hours, 1),
                has_schedule_conflicts=has_conflict,
            )
        )

    items.sort(key=lambda x: x.weekly_teaching_hours, reverse=True)
    avg_hours = round(total_hours / teaching_faculty_count, 1) if teaching_faculty_count > 0 else 0.0

    return FacultyAnalyticsData(
        total_faculty=len(faculty_list),
        teaching_faculty_count=teaching_faculty_count,
        average_teaching_hours=avg_hours,
        faculty_list=items,
    )


# =========================================================================
# 4. TIMETABLE HEALTH, CONFLICTS & PUBLICATION IMPACT
# =========================================================================

def get_timetable_health_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
) -> TimetableHealthAnalyticsData:
    """
    Computes real collision counts (rooms, faculty, student class collisions, work-shift clashes)
    and lists timetable version publication history and affected students.
    """
    term, _ = resolve_term(db, institution_id, term_id)
    if not term:
        return TimetableHealthAnalyticsData(conflicts=TimetableConflictSummary())

    timetable, meetings = get_active_timetable_and_meetings(db, institution_id, term.id)

    if not timetable:
        return TimetableHealthAnalyticsData(conflicts=TimetableConflictSummary())

    # Sections in term
    term_sections = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.institution_id == institution_id,
            AcademicSection.academic_term_id == term.id,
            AcademicSection.status == "active",
            AcademicSection.deleted_at.is_(None),
        )
        .all()
    )
    scheduled_sec_ids = set(m.section_id for m in meetings)
    scheduled_sections_count = len(scheduled_sec_ids)
    unscheduled_sections_count = max(0, len(term_sections) - scheduled_sections_count)

    # 1. Room double-bookings
    room_conflicts = 0
    room_days: Dict[Tuple[int, int], List[CourseMeeting]] = {}
    for m in meetings:
        if m.room_id is not None:
            room_days.setdefault((m.room_id, m.day_of_week), []).append(m)

    for (rid, d), d_meetings in room_days.items():
        if len(d_meetings) > 1:
            for i in range(len(d_meetings)):
                for j in range(i + 1, len(d_meetings)):
                    s1 = _time_to_minutes(d_meetings[i].start_time)
                    e1 = _time_to_minutes(d_meetings[i].end_time)
                    s2 = _time_to_minutes(d_meetings[j].start_time)
                    e2 = _time_to_minutes(d_meetings[j].end_time)
                    if _intervals_overlap(s1, e1, s2, e2):
                        room_conflicts += 1

    # 2. Faculty double-bookings
    faculty_conflicts = 0
    faculty_days: Dict[Tuple[int, int], List[CourseMeeting]] = {}
    for m in meetings:
        if m.faculty_id is not None:
            faculty_days.setdefault((m.faculty_id, m.day_of_week), []).append(m)

    for (fid, d), d_meetings in faculty_days.items():
        if len(d_meetings) > 1:
            for i in range(len(d_meetings)):
                for j in range(i + 1, len(d_meetings)):
                    s1 = _time_to_minutes(d_meetings[i].start_time)
                    e1 = _time_to_minutes(d_meetings[i].end_time)
                    s2 = _time_to_minutes(d_meetings[j].start_time)
                    e2 = _time_to_minutes(d_meetings[j].end_time)
                    if _intervals_overlap(s1, e1, s2, e2):
                        faculty_conflicts += 1

    # 3. Student class conflicts & work-shift clashes
    student_class_conflicts = 0
    student_work_shift_clashes = 0

    # Map section meetings by section_id
    sec_meetings_map: Dict[int, List[CourseMeeting]] = {}
    for m in meetings:
        sec_meetings_map.setdefault(m.section_id, []).append(m)

    # Active enrollments for term sections
    if scheduled_sec_ids:
        enrollments = (
            db.query(SectionEnrollment.student_id, SectionEnrollment.section_id)
            .filter(
                SectionEnrollment.institution_id == institution_id,
                SectionEnrollment.section_id.in_(list(scheduled_sec_ids)),
                SectionEnrollment.status.in_(["active", "enrolled"]),
            )
            .all()
        )

        student_sections: Dict[int, List[int]] = {}
        for sid, sec_id in enrollments:
            student_sections.setdefault(sid, []).append(sec_id)

        # Preload student work shifts for enrolled students
        enrolled_student_ids = list(student_sections.keys())
        student_work_shifts: Dict[int, List[TimeBlock]] = {}
        if enrolled_student_ids:
            work_blocks = (
                db.query(TimeBlock)
                .filter(
                    TimeBlock.user_id.in_(enrolled_student_ids),
                    TimeBlock.type == "shift",
                    TimeBlock.deleted == False,
                )
                .all()
            )
            for wb in work_blocks:
                student_work_shifts.setdefault(wb.user_id, []).append(wb)

        # Check collisions per student
        for sid, sec_list in student_sections.items():
            st_meetings: List[CourseMeeting] = []
            for sec_id in sec_list:
                st_meetings.extend(sec_meetings_map.get(sec_id, []))

            # Pairwise class collision check
            if len(st_meetings) > 1:
                has_student_conflict = False
                for i in range(len(st_meetings)):
                    for j in range(i + 1, len(st_meetings)):
                        m1 = st_meetings[i]
                        m2 = st_meetings[j]
                        if m1.day_of_week == m2.day_of_week and m1.section_id != m2.section_id:
                            s1 = _time_to_minutes(m1.start_time)
                            e1 = _time_to_minutes(m1.end_time)
                            s2 = _time_to_minutes(m2.start_time)
                            e2 = _time_to_minutes(m2.end_time)
                            if _intervals_overlap(s1, e1, s2, e2):
                                student_class_conflicts += 1
                                has_student_conflict = True
                                break
                    if has_student_conflict:
                        break

            # Work shift clash check
            shifts = student_work_shifts.get(sid, [])
            if shifts and st_meetings:
                clash_found = False
                for m in st_meetings:
                    for sh in shifts:
                        if sh.day_of_week == m.day_of_week:
                            s1 = _time_to_minutes(m.start_time)
                            e1 = _time_to_minutes(m.end_time)
                            s2 = _time_to_minutes(sh.start_time)
                            e2 = _time_to_minutes(sh.end_time)
                            if _intervals_overlap(s1, e1, s2, e2):
                                student_work_shift_clashes += 1
                                clash_found = True
                                break
                    if clash_found:
                        break

    total_conflicts = (
        room_conflicts
        + faculty_conflicts
        + student_class_conflicts
        + student_work_shift_clashes
    )

    conflict_summary = TimetableConflictSummary(
        room_double_bookings=room_conflicts,
        faculty_double_bookings=faculty_conflicts,
        student_class_conflicts=student_class_conflicts,
        student_work_shift_clashes=student_work_shift_clashes,
        total_conflicts=total_conflicts,
    )

    # 4. Version publication & notification impact history
    versions = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.institution_id == institution_id,
            TimetableVersion.timetable_id == timetable.id,
            TimetableVersion.deleted_at.is_(None),
        )
        .order_by(TimetableVersion.version_number.desc())
        .all()
    )

    draft_versions_count = sum(1 for v in versions if v.status == "draft")
    pub_version_number = (
        timetable.published_version.version_number if timetable.published_version else None
    )

    history_items: List[TimetableChangeHistoryItem] = []
    version_ids = [v.id for v in versions]

    if version_ids:
        # Query notification logs for these versions
        notif_logs = (
            db.query(
                NotificationLog.timetable_version_id,
                NotificationLog.user_id,
                NotificationLog.type,
                NotificationLog.priority,
            )
            .filter(
                NotificationLog.institution_id == institution_id,
                NotificationLog.timetable_version_id.in_(version_ids),
            )
            .all()
        )

        users_by_version: Dict[int, Set[int]] = {}
        urgent_by_version: Dict[int, int] = {}

        for log in notif_logs:
            vid = log.timetable_version_id
            if vid:
                users_by_version.setdefault(vid, set()).add(log.user_id)
                if log.type == "SCHEDULE_CONFLICT" or log.priority == "URGENT":
                    urgent_by_version[vid] = urgent_by_version.get(vid, 0) + 1

        for v in versions:
            creator_name = (
                v.creator.name or v.creator.email.split("@")[0] if v.creator else None
            )
            notified_students = len(users_by_version.get(v.id, set()))
            urgent_cnt = urgent_by_version.get(v.id, 0)

            history_items.append(
                TimetableChangeHistoryItem(
                    version_id=v.id,
                    version_number=v.version_number,
                    version_name=v.name,
                    change_summary=v.change_summary,
                    published_at=v.published_at,
                    published_by_name=creator_name,
                    students_notified_count=notified_students,
                    urgent_conflicts_count=urgent_cnt,
                )
            )

    return TimetableHealthAnalyticsData(
        timetable_id=timetable.id,
        timetable_name=timetable.name,
        published_version_number=pub_version_number,
        draft_versions_count=draft_versions_count,
        scheduled_sections_count=scheduled_sections_count,
        unscheduled_sections_count=unscheduled_sections_count,
        total_meetings_count=len(meetings),
        conflicts=conflict_summary,
        recent_history=history_items,
    )


# =========================================================================
# 5. DEPARTMENTAL COMPARISON INSIGHTS
# =========================================================================

def get_department_comparison_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
) -> List[DepartmentComparisonItem]:
    """
    Summarizes course counts, section counts, capacity utilization, and scheduled hours per department.
    """
    term, _ = resolve_term(db, institution_id, term_id)
    if not term:
        return []

    departments = (
        db.query(Department)
        .filter(
            Department.institution_id == institution_id,
            Department.deleted_at.is_(None),
        )
        .order_by(Department.name.asc())
        .all()
    )

    if not departments:
        return []

    dept_ids = [d.id for d in departments]

    # Courses count per department
    course_counts = dict(
        db.query(AcademicCourse.department_id, func.count(AcademicCourse.id))
        .filter(
            AcademicCourse.institution_id == institution_id,
            AcademicCourse.department_id.in_(dept_ids),
            AcademicCourse.status == "active",
            AcademicCourse.deleted_at.is_(None),
        )
        .group_by(AcademicCourse.department_id)
        .all()
    )

    # Sections in term
    sections = (
        db.query(
            AcademicSection.id,
            AcademicSection.capacity,
            AcademicCourse.department_id,
        )
        .join(AcademicCourse, AcademicCourse.id == AcademicSection.course_id)
        .filter(
            AcademicSection.institution_id == institution_id,
            AcademicSection.academic_term_id == term.id,
            AcademicSection.status == "active",
            AcademicSection.deleted_at.is_(None),
            AcademicCourse.department_id.in_(dept_ids),
            AcademicCourse.deleted_at.is_(None),
        )
        .all()
    )

    sec_ids_by_dept: Dict[int, List[int]] = {}
    capacity_by_dept: Dict[int, int] = {}
    sec_count_by_dept: Dict[int, int] = {}

    all_sec_ids = []
    for s_id, s_cap, d_id in sections:
        all_sec_ids.append(s_id)
        sec_ids_by_dept.setdefault(d_id, []).append(s_id)
        capacity_by_dept[d_id] = capacity_by_dept.get(d_id, 0) + (s_cap or 0)
        sec_count_by_dept[d_id] = sec_count_by_dept.get(d_id, 0) + 1

    # Enrollments
    enrolled_by_dept: Dict[int, int] = {}
    if all_sec_ids:
        enr_rows = (
            db.query(SectionEnrollment.section_id, func.count(SectionEnrollment.id))
            .filter(
                SectionEnrollment.institution_id == institution_id,
                SectionEnrollment.section_id.in_(all_sec_ids),
                SectionEnrollment.status.in_(["active", "enrolled"]),
            )
            .group_by(SectionEnrollment.section_id)
            .all()
        )
        enr_by_sec = dict(enr_rows)
        for d_id, s_list in sec_ids_by_dept.items():
            enrolled_by_dept[d_id] = sum(enr_by_sec.get(sid, 0) for sid in s_list)

    # Scheduled hours
    hours_by_dept: Dict[int, float] = {}
    _, meetings = get_active_timetable_and_meetings(db, institution_id, term.id)
    sec_to_dept = {s_id: d_id for s_id, _, d_id in sections}

    for m in meetings:
        d_id = sec_to_dept.get(m.section_id)
        if d_id:
            hrs = _calc_hours(m.start_time, m.end_time)
            hours_by_dept[d_id] = hours_by_dept.get(d_id, 0.0) + hrs

    items: List[DepartmentComparisonItem] = []
    for d in departments:
        c_cnt = course_counts.get(d.id, 0)
        s_cnt = sec_count_by_dept.get(d.id, 0)
        tot_cap = capacity_by_dept.get(d.id, 0)
        tot_enr = enrolled_by_dept.get(d.id, 0)
        util_pct = round((tot_enr / tot_cap * 100.0), 1) if tot_cap > 0 else 0.0
        hrs = round(hours_by_dept.get(d.id, 0.0), 1)

        items.append(
            DepartmentComparisonItem(
                department_id=d.id,
                name=d.name,
                code=d.code,
                courses_count=c_cnt,
                sections_count=s_cnt,
                total_capacity=tot_cap,
                total_enrolled=tot_enr,
                capacity_utilization_pct=util_pct,
                weekly_scheduled_hours=hrs,
            )
        )

    return items


# =========================================================================
# 6. OVERVIEW KPIS & UNIFIED DASHBOARD
# =========================================================================

def get_university_overview_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
) -> AnalyticsOverviewKPIs:
    """
    Computes top-level high-value metrics for the university dashboard.
    """
    term, _ = resolve_term(db, institution_id, term_id)
    term_id_val = term.id if term else None

    # Active students count
    active_students = (
        db.query(func.count(StudentProfile.id))
        .filter(
            StudentProfile.institution_id == institution_id,
            StudentProfile.status == "active",
            StudentProfile.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    # Active courses count
    active_courses = (
        db.query(func.count(AcademicCourse.id))
        .filter(
            AcademicCourse.institution_id == institution_id,
            AcademicCourse.status == "active",
            AcademicCourse.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    # Active faculty count
    active_faculty = (
        db.query(func.count(FacultyProfile.id))
        .filter(
            FacultyProfile.institution_id == institution_id,
            FacultyProfile.status == "active",
            FacultyProfile.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    # Term-scoped counts
    enrolled_students = 0
    total_enrollments = 0
    active_sections = 0
    scheduled_classes = 0
    unscheduled_sections = 0
    published_ver_num: Optional[int] = None

    if term_id_val is not None:
        # Sections in this term
        sections = (
            db.query(AcademicSection.id)
            .filter(
                AcademicSection.institution_id == institution_id,
                AcademicSection.academic_term_id == term_id_val,
                AcademicSection.status == "active",
                AcademicSection.deleted_at.is_(None),
            )
            .all()
        )
        sec_ids = [s[0] for s in sections]
        active_sections = len(sec_ids)

        if sec_ids:
            # Enrolled unique students
            enrolled_students = (
                db.query(func.count(distinct(SectionEnrollment.student_id)))
                .filter(
                    SectionEnrollment.institution_id == institution_id,
                    SectionEnrollment.section_id.in_(sec_ids),
                    SectionEnrollment.status.in_(["active", "enrolled"]),
                )
                .scalar()
                or 0
            )

            # Total enrollment seats
            total_enrollments = (
                db.query(func.count(SectionEnrollment.id))
                .filter(
                    SectionEnrollment.institution_id == institution_id,
                    SectionEnrollment.section_id.in_(sec_ids),
                    SectionEnrollment.status.in_(["active", "enrolled"]),
                )
                .scalar()
                or 0
            )

        # Timetable meetings
        timetable, meetings = get_active_timetable_and_meetings(db, institution_id, term_id_val)
        if timetable:
            scheduled_classes = len(meetings)
            scheduled_sec_ids = set(m.section_id for m in meetings)
            unscheduled_sections = max(0, active_sections - len(scheduled_sec_ids))
            if timetable.published_version:
                published_ver_num = timetable.published_version.version_number

    # Rooms & Utilization
    room_analytics = get_room_utilization_analytics(db, institution_id, term_id_val)
    avg_room_util = room_analytics.average_utilization_pct
    active_rooms = room_analytics.active_rooms

    # Timetable health conflicts
    tt_health = get_timetable_health_analytics(db, institution_id, term_id_val)
    total_conflicts = tt_health.conflicts.total_conflicts

    return AnalyticsOverviewKPIs(
        active_students_count=active_students,
        enrolled_students_count=enrolled_students,
        total_enrollments_count=total_enrollments,
        active_courses_count=active_courses,
        active_sections_count=active_sections,
        scheduled_classes_count=scheduled_classes,
        unscheduled_sections_count=unscheduled_sections,
        active_rooms_count=active_rooms,
        average_room_utilization_pct=avg_room_util,
        active_faculty_count=active_faculty,
        total_conflicts_count=total_conflicts,
        published_timetable_version=published_ver_num,
    )


def get_full_university_analytics(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> UniversityDashboardAnalyticsResponse:
    """
    Returns the complete aggregated analytics response for the university decision dashboard.
    """
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    inst_name = inst.name if inst else "University"

    term, available_terms = resolve_term(db, institution_id, term_id)
    term_option = AnalyticsTermOption.model_validate(term) if term else None
    term_id_val = term.id if term else None

    overview = get_university_overview_analytics(db, institution_id, term_id_val)
    enrollment = get_enrollment_analytics(db, institution_id, term_id_val, department_id)
    rooms = get_room_utilization_analytics(db, institution_id, term_id_val, department_id)
    faculty = get_faculty_schedule_analytics(db, institution_id, term_id_val, department_id)
    timetable = get_timetable_health_analytics(db, institution_id, term_id_val)
    departments = get_department_comparison_analytics(db, institution_id, term_id_val)

    return UniversityDashboardAnalyticsResponse(
        institution_id=institution_id,
        institution_name=inst_name,
        generated_at=datetime.now(timezone.utc),
        active_term=term_option,
        available_terms=available_terms,
        overview=overview,
        enrollment=enrollment,
        rooms=rooms,
        faculty=faculty,
        timetable=timetable,
        departments=departments,
    )
