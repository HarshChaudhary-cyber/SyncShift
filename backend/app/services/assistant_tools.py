"""
assistant_tools.py — Deterministic Tool Execution Engine for SyncShift AI Assistant (N9).

Provides a controlled, permission-enforced tool layer for both Student and University Administrator.
The AI assistant NEVER has direct database access; it selects tools which execute through
deterministic backend services with strict server-side authorization and tenant isolation.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.dependencies import CurrentUser
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.course_meeting import CourseMeeting
from app.models.faculty import FacultyProfile
from app.models.institution import Institution, InstitutionMembership
from app.models.notification import NotificationLog
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint, StudentPreference
from app.models.time_block import BlockStatus, TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.schemas.assistant import ActionCheckItem, ActionPreview
from app.services.impact_analysis import analyze_timetable_change
from app.services.smart_planner.service import SmartPlannerService
from app.services.timetable_validator import format_time_str, time_to_minutes
from app.services.timetable_version_service import (
    compare_versions,
    create_version,
    run_version_checklist,
    submit_for_review as submit_ver_review,
)

logger = logging.getLogger(__name__)

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_NAME_TO_INT = {name.lower(): i for i, name in enumerate(DAY_NAMES)}


def verify_institution_admin_access(db: Session, user_id: int, institution_id: Optional[int]) -> Institution:
    """Verifies that the user has admin or super_admin role in the requested institution."""
    if not institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "institution_required", "message": "University administration tools require an institution context."},
        )

    inst = db.query(Institution).filter(Institution.id == institution_id, Institution.deleted_at.is_(None)).first()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "institution_not_found", "message": f"Institution {institution_id} not found."},
        )

    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.institution_id == institution_id,
            InstitutionMembership.user_id == user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    if not membership or membership.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": "You do not have administrator privileges for this institution.",
            },
        )
    return inst


# =====================================================================
# STUDENT TOOLS
# =====================================================================

def tool_get_my_schedule(
    db: Session,
    current_user: CurrentUser,
    day_of_week: Optional[int] = None,
    target_date: Optional[str] = None,
    view: str = "today",
) -> dict[str, Any]:
    """
    Fetches the student's authoritative schedule (published classes, work shifts, personal events).
    """
    user_id = current_user.user_id
    today = date.today()
    if target_date:
        try:
            d_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
            target_dow = (d_obj.weekday() + 1) % 7
        except ValueError:
            target_dow = (today.weekday() + 1) % 7
    elif day_of_week is not None:
        target_dow = day_of_week
    else:
        target_dow = (today.weekday() + 1) % 7

    # 1. Fetch active enrollments -> published CourseMeetings
    meetings_q = (
        db.query(CourseMeeting, AcademicCourse, AcademicSection, Room)
        .join(AcademicSection, CourseMeeting.section_id == AcademicSection.id)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(SectionEnrollment, SectionEnrollment.section_id == AcademicSection.id)
        .join(Timetable, CourseMeeting.timetable_id == Timetable.id)
        .outerjoin(Room, CourseMeeting.room_id == Room.id)
        .filter(
            SectionEnrollment.student_id == user_id,
            SectionEnrollment.status.in_(["enrolled", "active"]),
            or_(
                (Timetable.published_version_id.isnot(None)) & (CourseMeeting.version_id == Timetable.published_version_id),
                (Timetable.published_version_id.is_(None)) & (Timetable.status.in_(["active", "draft"])) & (CourseMeeting.version_id.is_(None)),
            ),
        )
    )

    if view == "today":
        meetings_q = meetings_q.filter(CourseMeeting.day_of_week == target_dow)

    meetings = meetings_q.all()

    # 2. Fetch TimeBlocks (shifts, personal, study, classes)
    blocks_q = db.query(TimeBlock).filter(
        TimeBlock.user_id == user_id,
        TimeBlock.status != BlockStatus.DROPPED,
    )
    if view == "today":
        blocks_q = blocks_q.filter(TimeBlock.day_of_week == target_dow)
    blocks = blocks_q.all()

    items = []
    for m, c, s, r in meetings:
        st_str = format_time_str(m.start_time)
        et_str = format_time_str(m.end_time)
        items.append({
            "type": "class",
            "title": f"{c.code} - {c.name}",
            "section": s.section_code,
            "day_of_week": m.day_of_week,
            "day_name": DAY_NAMES[m.day_of_week],
            "start_time": st_str,
            "end_time": et_str,
            "start_mins": time_to_minutes(m.start_time),
            "end_mins": time_to_minutes(m.end_time),
            "location": f"Room {r.room_number}" if r else "TBD",
        })

    for b in blocks:
        st_str = b.start_time.strftime("%H:%M") if isinstance(b.start_time, dt_time) else str(b.start_time)[:5]
        et_str = b.end_time.strftime("%H:%M") if isinstance(b.end_time, dt_time) else str(b.end_time)[:5]
        items.append({
            "type": b.type.value if hasattr(b.type, "value") else str(b.type),
            "title": b.title,
            "day_of_week": b.day_of_week,
            "day_name": DAY_NAMES[b.day_of_week],
            "start_time": st_str,
            "end_time": et_str,
            "start_mins": time_to_minutes(b.start_time),
            "end_mins": time_to_minutes(b.end_time),
            "location": b.location or "",
        })

    items.sort(key=lambda x: (x["day_of_week"], x["start_mins"]))

    # Free intervals for today
    free_gaps = []
    if view == "today" and items:
        cur = 9 * 60  # start 09:00
        for ev in items:
            if ev["start_mins"] > cur:
                gap_len = ev["start_mins"] - cur
                if gap_len >= 30:
                    free_gaps.append(f"{cur // 60:02d}:{cur % 60:02d}–{ev['start_mins'] // 60:02d}:{ev['start_mins'] % 60:02d}")
            cur = max(cur, ev["end_mins"])
        if cur < 18 * 60:
            free_gaps.append(f"{cur // 60:02d}:{cur % 60:02d}–18:00")

    return {
        "view": view,
        "day_name": DAY_NAMES[target_dow],
        "events_count": len(items),
        "events": items,
        "free_gaps": free_gaps,
    }


def tool_get_my_courses(db: Session, current_user: CurrentUser) -> dict[str, Any]:
    """Fetches the student's enrolled university courses."""
    user_id = current_user.user_id
    enrollments = (
        db.query(SectionEnrollment, AcademicSection, AcademicCourse)
        .join(AcademicSection, SectionEnrollment.section_id == AcademicSection.id)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .filter(
            SectionEnrollment.student_id == user_id,
            SectionEnrollment.status.in_(["enrolled", "active"]),
        )
        .all()
    )

    results = []
    for enr, sec, crs in enrollments:
        meetings = (
            db.query(CourseMeeting, Room)
            .outerjoin(Room, CourseMeeting.room_id == Room.id)
            .filter(CourseMeeting.section_id == sec.id)
            .all()
        )
        sched = []
        for m, r in meetings:
            st = format_time_str(m.start_time)
            et = format_time_str(m.end_time)
            rm = f"Room {r.room_number}" if r else "TBD"
            sched.append(f"{DAY_NAMES[m.day_of_week]} {st}–{et} ({rm})")

        results.append({
            "course_id": crs.id,
            "code": crs.code,
            "name": crs.name,
            "credits": crs.credits,
            "section_code": sec.section_code,
            "schedule": sched,
        })

    return {"courses_count": len(results), "courses": results}


def tool_get_my_conflicts(db: Session, current_user: CurrentUser) -> dict[str, Any]:
    """Detects any schedule conflicts between student classes and personal/work blocks."""
    sched = tool_get_my_schedule(db, current_user, view="week")
    events = sched["events"]

    conflicts = []
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            a, b = events[i], events[j]
            if a["day_of_week"] == b["day_of_week"]:
                # Interval overlap: A.start < B.end and B.start < A.end
                if a["start_mins"] < b["end_mins"] and b["start_mins"] < a["end_mins"]:
                    conflicts.append({
                        "day": a["day_name"],
                        "event_a": f"{a['title']} ({a['start_time']}–{a['end_time']})",
                        "event_b": f"{b['title']} ({b['start_time']}–{b['end_time']})",
                        "overlap_minutes": min(a["end_mins"], b["end_mins"]) - max(a["start_mins"], b["start_mins"]),
                    })

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def tool_get_my_notifications(db: Session, current_user: CurrentUser, unread_only: bool = True) -> dict[str, Any]:
    """Retrieves the student's recent schedule and timetable notifications."""
    q = db.query(NotificationLog).filter(NotificationLog.user_id == current_user.user_id)
    if unread_only:
        q = q.filter(NotificationLog.read_at.is_(None))
    q = q.order_by(NotificationLog.created_at.desc()).limit(10)
    notifs = q.all()

    return {
        "count": len(notifs),
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.body,
                "type": n.notification_type,
                "priority": getattr(n, "priority", "INFO"),
                "read": n.read_at is not None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
    }


def tool_get_my_preferences(db: Session, current_user: CurrentUser) -> dict[str, Any]:
    """Retrieves the student's work hours, availability preferences, and hard constraints."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    pref = db.query(StudentPreference).filter(StudentPreference.user_id == current_user.user_id).first()
    constraints = db.query(StudentConstraint).filter(StudentConstraint.user_id == current_user.user_id).all()

    return {
        "weekly_work_hour_limit": float(user.weekly_work_hour_limit or 20.0) if user else 20.0,
        "preferred_time_of_day": pref.preferred_time_of_day if pref else "any",
        "schedule_density": pref.schedule_density if pref else "balanced",
        "constraints": [
            {"type": c.constraint_type, "is_hard": c.is_hard, "day_of_week": c.day_of_week}
            for c in constraints
        ],
    }


def tool_get_my_availability(db: Session, current_user: CurrentUser) -> dict[str, Any]:
    """Retrieves the student's blackout and availability intervals."""
    avails = (
        db.query(StudentAvailability)
        .filter(StudentAvailability.user_id == current_user.user_id)
        .all()
    )
    return {
        "count": len(avails),
        "blackouts": [
            {
                "id": a.id,
                "day_of_week": a.day_of_week,
                "day_name": DAY_NAMES[a.day_of_week] if 0 <= a.day_of_week < 7 else "Unknown",
                "start_time": format_time_str(a.start_time),
                "end_time": format_time_str(a.end_time),
                "is_available": a.is_available,
                "title": a.title or "Unavailable",
            }
            for a in avails
        ],
    }


def tool_preview_my_plan(db: Session, current_user: CurrentUser, strategy: str = "balanced") -> dict[str, Any]:
    """Executes N5 Smart Planner in strictly read-only preview mode."""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    user = db.query(User).filter(User.id == current_user.user_id).first()

    try:
        preview_res = SmartPlannerService.preview_weekly_plan(
            db=db,
            user=user,
            week_start=start_of_week,
            strategies=[strategy],
        )
        return {
            "success": True,
            "week_start": start_of_week.isoformat(),
            "selected_strategy": strategy,
            "options": [
                {
                    "strategy": opt.strategy,
                    "score": opt.score,
                    "total_study_minutes": opt.total_study_minutes,
                    "planned_sessions_count": len(opt.planned_sessions),
                    "reasons": opt.reasons,
                    "trade_offs": opt.trade_offs,
                    "sessions": [
                        {
                            "task_title": s.task_title,
                            "day_name": DAY_NAMES[s.day_of_week],
                            "start_time": s.start_time,
                            "end_time": s.end_time,
                            "duration_minutes": s.duration_minutes,
                        }
                        for s in opt.planned_sessions
                    ],
                }
                for opt in preview_res.options
            ],
        }
    except Exception as exc:
        logger.warning(f"Planner preview failed: {exc}")
        return {"success": False, "message": str(exc), "options": []}


def tool_prepare_create_study_block(
    db: Session,
    current_user: CurrentUser,
    title: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
) -> ActionPreview:
    """Prepares a study block creation action card with pre-validation."""
    start_m = time_to_minutes(start_time)
    end_m = time_to_minutes(end_time)

    # Check overlaps with student's schedule
    sched = tool_get_my_schedule(db, current_user, day_of_week=day_of_week, view="today")
    has_conflict = False
    conflict_name = ""
    for ev in sched["events"]:
        if start_m < ev["end_mins"] and end_m > ev["start_mins"]:
            has_conflict = True
            conflict_name = ev["title"]
            break

    checks = [
        ActionCheckItem(label="Time slot is valid", passed=start_m < end_m),
        ActionCheckItem(
            label=f"Zero conflict with classes/shifts (overlaps with {conflict_name})" if has_conflict else "Zero conflicts detected",
            passed=not has_conflict,
            warning=has_conflict,
        ),
        ActionCheckItem(label="Student-owned personal commitment", passed=True),
    ]

    return ActionPreview(
        action_type="create_study_block",
        title=f"Create Study Block: {title}",
        parameters={
            "title": title,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
        },
        original=None,
        target={
            "day": DAY_NAMES[day_of_week],
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
            "time": f"{start_time}–{end_time}",
            "title": title,
        },
        checks=checks,
    )


# =====================================================================
# UNIVERSITY ADMINISTRATOR TOOLS
# =====================================================================

def tool_get_university_timetable(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
) -> dict[str, Any]:
    """Fetches the official university timetables and published status."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    timetables = (
        db.query(Timetable, AcademicTerm)
        .join(AcademicTerm, Timetable.academic_term_id == AcademicTerm.id)
        .filter(Timetable.institution_id == institution_id, Timetable.deleted_at.is_(None))
        .all()
    )

    out = []
    for tt, term in timetables:
        meetings_count = (
            db.query(func.count(CourseMeeting.id))
            .filter(CourseMeeting.timetable_id == tt.id)
            .scalar()
        )
        pub_ver = None
        if tt.published_version_id:
            pv = db.query(TimetableVersion).filter(TimetableVersion.id == tt.published_version_id).first()
            if pv:
                pub_ver = f"Version {pv.version_number} ({pv.status})"

        out.append({
            "id": tt.id,
            "name": tt.name,
            "term_name": term.name,
            "status": tt.status,
            "published_version": pub_ver,
            "meetings_count": meetings_count,
        })

    return {"timetables_count": len(out), "timetables": out}


def tool_get_rooms(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    day_of_week: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> dict[str, Any]:
    """Fetches rooms and checks availability at a specific interval if provided."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    rooms = db.query(Room).filter(Room.institution_id == institution_id, Room.deleted_at.is_(None)).all()

    target_start_m = time_to_minutes(start_time) if start_time else None
    target_end_m = time_to_minutes(end_time) if end_time else None

    # If checking interval availability, find occupied rooms
    occupied_room_ids = set()
    if day_of_week is not None and target_start_m is not None and target_end_m is not None:
        meetings = (
            db.query(CourseMeeting)
            .filter(
                CourseMeeting.institution_id == institution_id,
                CourseMeeting.day_of_week == day_of_week,
                CourseMeeting.room_id.isnot(None),
            )
            .all()
        )
        for m in meetings:
            st = time_to_minutes(m.start_time)
            et = time_to_minutes(m.end_time)
            if target_start_m < et and target_end_m > st:
                occupied_room_ids.add(m.room_id)

    room_items = []
    for r in rooms:
        is_free = r.id not in occupied_room_ids if occupied_room_ids or day_of_week is not None else True
        room_items.append({
            "id": r.id,
            "room_number": r.room_number,
            "name": r.name or r.room_number,
            "building": r.building or "Main Campus",
            "capacity": r.capacity,
            "is_available": is_free,
        })

    return {
        "rooms_count": len(room_items),
        "time_slot_checked": f"{DAY_NAMES[day_of_week]} {start_time}–{end_time}" if day_of_week is not None and start_time else None,
        "available_rooms": [r for r in room_items if r["is_available"]],
        "rooms": room_items,
    }


def tool_get_students_affected(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    meeting_id: Optional[int] = None,
    section_id: Optional[int] = None,
) -> dict[str, Any]:
    """Retrieves active student enrollments affected by a course meeting or section."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    if not section_id and meeting_id:
        m = db.query(CourseMeeting).filter(
            CourseMeeting.id == meeting_id,
            CourseMeeting.institution_id == institution_id,
            CourseMeeting.deleted_at.is_(None),
        ).first()
        if not m:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "meeting_not_found", "message": f"Course meeting {meeting_id} not found for this institution."},
            )
        section_id = m.section_id

    if not section_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "section_or_meeting_required", "message": "A meeting_id or section_id is required."},
        )

    # Multi-tenant hardening: verify the section strictly belongs to this institution
    sec = db.query(AcademicSection).filter(
        AcademicSection.id == section_id,
        AcademicSection.institution_id == institution_id,
        AcademicSection.deleted_at.is_(None),
    ).first()
    if not sec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found for this institution."},
        )

    enrollments = (
        db.query(SectionEnrollment, User)
        .join(User, SectionEnrollment.student_id == User.id)
        .filter(
            SectionEnrollment.section_id == section_id,
            SectionEnrollment.status.in_(["enrolled", "active"]),
        )
        .all()
    )

    return {
        "section_id": section_id,
        "affected_students_count": len(enrollments),
        "students": [{"id": u.id, "name": u.name or u.email} for _, u in enrollments],
    }


def tool_preview_timetable_change(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    timetable_id: int,
    meeting_id: int,
    proposed_day: int,
    proposed_start: str,
    proposed_end: str,
    room_id: Optional[int] = None,
) -> ActionPreview:
    """
    Integrates N6 Impact Engine to preview timetable move without mutating database.
    Returns structured ActionPreview card with student conflict stats.
    """
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    # Multi-tenant hardening: verify timetable belongs to this institution
    tt = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == institution_id,
        Timetable.deleted_at.is_(None),
    ).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found for this institution."},
        )

    meeting = db.query(CourseMeeting).filter(
        CourseMeeting.id == meeting_id,
        CourseMeeting.timetable_id == timetable_id,
        CourseMeeting.institution_id == institution_id,
        CourseMeeting.deleted_at.is_(None),
    ).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {meeting_id} not found."},
        )

    from app.schemas.timetable import TimetableChangeProposal
    proposal = TimetableChangeProposal(
        meeting_id=meeting_id,
        day_of_week=proposed_day,
        start_time=proposed_start,
        end_time=proposed_end,
        room_id=room_id or meeting.room_id,
        faculty_id=meeting.faculty_id,
    )

    impact_res = analyze_timetable_change(
        db=db,
        institution_id=institution_id,
        timetable_id=timetable_id,
        proposal=proposal,
    )

    sm = impact_res.summary
    severity = sm.severity
    students_affected = sm.students_affected
    new_conflicts = sm.new_conflicts
    work_conflicts = sm.work_conflicts
    blocked_reasons = sm.blocked_reasons

    checks = [
        ActionCheckItem(
            label=f"Room & Faculty available ({severity})",
            passed=not impact_res.is_blocked,
            warning=severity in ("HIGH", "MEDIUM"),
        ),
        ActionCheckItem(
            label=f"{students_affected} students affected",
            passed=True,
        ),
        ActionCheckItem(
            label=f"{new_conflicts} new student conflicts created",
            passed=new_conflicts == 0,
            warning=new_conflicts > 0,
        ),
        ActionCheckItem(
            label=f"{work_conflicts} work-shift clashes",
            passed=work_conflicts == 0,
            warning=work_conflicts > 0,
        ),
    ]

    return ActionPreview(
        action_type="timetable_change",
        title=f"Move Meeting #{meeting_id} to {DAY_NAMES[proposed_day]} {proposed_start}–{proposed_end}",
        block_id=meeting_id,
        parameters={
            "institution_id": institution_id,
            "timetable_id": timetable_id,
            "meeting_id": meeting_id,
            "day_of_week": proposed_day,
            "start_time": proposed_start,
            "end_time": proposed_end,
            "room_id": room_id or meeting.room_id,
            "expected_updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
        },
        original={
            "day": DAY_NAMES[meeting.day_of_week],
            "time": f"{format_time_str(meeting.start_time)}–{format_time_str(meeting.end_time)}",
        },
        target={
            "day": DAY_NAMES[proposed_day],
            "time": f"{proposed_start}–{proposed_end}",
            "severity": severity,
        },
        checks=checks,
        impact_summary={
            "severity": severity,
            "is_blocked": impact_res.is_blocked,
            "blocking_reasons": blocked_reasons,
            "students_affected_count": students_affected,
            "new_conflicts_count": new_conflicts,
            "work_shift_conflicts_count": work_conflicts,
        },
    )


def tool_get_version_history(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    timetable_id: int,
) -> dict[str, Any]:
    """Fetches N7 Timetable Versions and change summaries."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    tt = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == institution_id,
        Timetable.deleted_at.is_(None),
    ).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found for this institution."},
        )

    versions = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == institution_id,
            TimetableVersion.deleted_at.is_(None),
        )
        .order_by(TimetableVersion.version_number.desc())
        .all()
    )

    return {
        "timetable_id": timetable_id,
        "current_published_version_id": tt.published_version_id if tt else None,
        "versions_count": len(versions),
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "name": v.name,
                "status": v.status,
                "change_summary": v.change_summary,
                "is_published": tt.published_version_id == v.id if tt else False,
                "published_at": v.published_at.isoformat() if v.published_at else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


def tool_prepare_create_draft(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    timetable_id: int,
    name: str,
) -> ActionPreview:
    """Prepares an action card for N7 draft version creation."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)

    tt = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == institution_id,
        Timetable.deleted_at.is_(None),
    ).first()
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found for this institution."},
        )

    checks = [
        ActionCheckItem(label="Admin privileges verified", passed=True),
        ActionCheckItem(label="Clones meetings from currently published version", passed=True),
        ActionCheckItem(label="Draft status is isolated from students", passed=True),
    ]

    return ActionPreview(
        action_type="create_timetable_draft",
        title=f"Create New Timetable Draft: {name}",
        parameters={
            "institution_id": institution_id,
            "timetable_id": timetable_id,
            "name": name,
        },
        original=None,
        target={"name": name, "status": "draft"},
        checks=checks,
    )


# =====================================================================
# N10 UNIVERSITY ANALYTICS DETERMINISTIC TOOLS
# =====================================================================

def tool_get_university_analytics_overview(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    term_id: Optional[int] = None,
) -> dict[str, Any]:
    """Fetches high-level university KPIs (enrolled students, room utilization, conflicts, courses)."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)
    from app.services.university_analytics_service import get_university_overview_analytics
    kpis = get_university_overview_analytics(db=db, institution_id=institution_id, term_id=term_id)
    return kpis.model_dump()


def tool_get_enrollment_analytics(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict[str, Any]:
    """Fetches section capacity demand, highlighting sections near capacity or under-utilized."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)
    from app.services.university_analytics_service import get_enrollment_analytics
    data = get_enrollment_analytics(db=db, institution_id=institution_id, term_id=term_id, department_id=department_id)
    return data.model_dump()


def tool_get_room_utilization_analytics(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict[str, Any]:
    """Fetches scheduled room utilization metrics based on real timetable meetings."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)
    from app.services.university_analytics_service import get_room_utilization_analytics
    data = get_room_utilization_analytics(db=db, institution_id=institution_id, term_id=term_id, department_id=department_id)
    return data.model_dump()


def tool_get_faculty_schedule_analytics(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict[str, Any]:
    """Fetches neutral teaching schedule loads and collision metrics for faculty."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)
    from app.services.university_analytics_service import get_faculty_schedule_analytics
    data = get_faculty_schedule_analytics(db=db, institution_id=institution_id, term_id=term_id, department_id=department_id)
    return data.model_dump()


def tool_get_timetable_health_analytics(
    db: Session,
    current_user: CurrentUser,
    institution_id: int,
    term_id: Optional[int] = None,
) -> dict[str, Any]:
    """Fetches real timetable conflict counts and version change impact history."""
    verify_institution_admin_access(db, current_user.user_id, institution_id)
    from app.services.university_analytics_service import get_timetable_health_analytics
    data = get_timetable_health_analytics(db=db, institution_id=institution_id, term_id=term_id)
    return data.model_dump()
