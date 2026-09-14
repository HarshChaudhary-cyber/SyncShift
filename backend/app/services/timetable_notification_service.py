"""
Timetable Notification Service for Task N8.
Handles:
1. Diffing published timetable versions (N7 publication integration)
2. Identifying affected students via active SectionEnrollment records
3. Detecting student-specific impacts (real work shift and availability conflicts)
4. Generating targeted, human-readable notifications with appropriate priorities (INFO, IMPORTANT, URGENT)
5. Multi-channel delivery: in-app notification center, browser push, and email
6. Idempotent processing and failure isolation
7. University administrator delivery summaries and reporting
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.notification import NotificationLog, NotificationPrefs, PushSubscription
from app.models.section_enrollment import SectionEnrollment
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint
from app.models.student_profile import StudentProfile
from app.models.time_block import TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.services.reminders import send_email_alert, send_web_push

logger = logging.getLogger(__name__)

DAY_NAMES = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


def _time_to_minutes(t: Any) -> int:
    if not t:
        return 0
    if isinstance(t, str):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return t.hour * 60 + t.minute


def _format_time(t: Any) -> str:
    if not t:
        return ""
    if isinstance(t, str):
        return t[:5]
    return f"{t.hour:02d}:{t.minute:02d}"


class MeetingChangeDetail:
    def __init__(
        self,
        meeting_id: int,
        section_id: int,
        course_code: str,
        course_name: str,
        section_code: str,
        change_type: str,  # moved, room_changed, faculty_changed, added, removed, schedule_changed
        before_day: Optional[int] = None,
        before_start: Optional[str] = None,
        before_end: Optional[str] = None,
        before_room: Optional[str] = None,
        before_faculty: Optional[str] = None,
        after_day: Optional[int] = None,
        after_start: Optional[str] = None,
        after_end: Optional[str] = None,
        after_room: Optional[str] = None,
        after_faculty: Optional[str] = None,
    ):
        self.meeting_id = meeting_id
        self.section_id = section_id
        self.course_code = course_code
        self.course_name = course_name
        self.section_code = section_code
        self.change_type = change_type
        self.before_day = before_day
        self.before_start = before_start
        self.before_end = before_end
        self.before_room = before_room
        self.before_faculty = before_faculty
        self.after_day = after_day
        self.after_start = after_start
        self.after_end = after_end
        self.after_room = after_room
        self.after_faculty = after_faculty

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meeting_id": self.meeting_id,
            "section_id": self.section_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "section_code": self.section_code,
            "change_type": self.change_type,
            "before_day": self.before_day,
            "before_day_name": DAY_NAMES.get(self.before_day, "") if self.before_day is not None else "",
            "before_start": self.before_start,
            "before_end": self.before_end,
            "before_room": self.before_room,
            "before_faculty": self.before_faculty,
            "after_day": self.after_day,
            "after_day_name": DAY_NAMES.get(self.after_day, "") if self.after_day is not None else "",
            "after_start": self.after_start,
            "after_end": self.after_end,
            "after_room": self.after_room,
            "after_faculty": self.after_faculty,
        }


def detect_version_changes(
    db: Session,
    institution_id: int,
    timetable_id: int,
    published_version_id: int,
    previous_version_id: Optional[int] = None,
) -> Tuple[List[MeetingChangeDetail], Set[int]]:
    """
    Compares the newly published timetable version against the previous version.
    Returns:
      1. List of MeetingChangeDetail describing what changed per meeting/section.
      2. Set of section_ids that had meaningful changes.
    """
    new_meetings = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty),
        )
        .filter(
            CourseMeeting.version_id == published_version_id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .all()
    )

    old_meetings = []
    if previous_version_id:
        old_meetings = (
            db.query(CourseMeeting)
            .options(
                joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
                joinedload(CourseMeeting.room),
                joinedload(CourseMeeting.faculty),
            )
            .filter(
                CourseMeeting.version_id == previous_version_id,
                CourseMeeting.deleted_at.is_(None),
                CourseMeeting.status == "active",
            )
            .all()
        )

    changes: List[MeetingChangeDetail] = []
    changed_section_ids: Set[int] = set()

    # Case 1: First publication (no previous version)
    if not previous_version_id:
        for nm in new_meetings:
            sec = nm.section
            crs = sec.course if sec else None
            crs_code = crs.code if crs else f"Sec #{nm.section_id}"
            crs_name = crs.name if crs else "Course"
            sec_code = sec.section_code if sec else ""
            room_name = f"{nm.room.building} {nm.room.room_number}" if nm.room else "Unassigned"

            changes.append(
                MeetingChangeDetail(
                    meeting_id=nm.id,
                    section_id=nm.section_id,
                    course_code=crs_code,
                    course_name=crs_name,
                    section_code=sec_code,
                    change_type="added",
                    after_day=nm.day_of_week,
                    after_start=_format_time(nm.start_time),
                    after_end=_format_time(nm.end_time),
                    after_room=room_name,
                )
            )
            changed_section_ids.add(nm.section_id)
        return changes, changed_section_ids

    # Case 2: Compare against previous published version
    old_by_sec: Dict[int, List[CourseMeeting]] = {}
    for om in old_meetings:
        old_by_sec.setdefault(om.section_id, []).append(om)

    new_by_sec: Dict[int, List[CourseMeeting]] = {}
    for nm in new_meetings:
        new_by_sec.setdefault(nm.section_id, []).append(nm)

    all_secs = set(old_by_sec.keys()) | set(new_by_sec.keys())

    for sec_id in sorted(all_secs):
        o_list = old_by_sec.get(sec_id, [])
        n_list = new_by_sec.get(sec_id, [])

        sample_sec = (o_list[0].section if o_list else None) or (n_list[0].section if n_list else None)
        crs = sample_sec.course if sample_sec else None
        crs_code = crs.code if crs else f"Sec #{sec_id}"
        crs_name = crs.name if crs else "Course"
        sec_code = sample_sec.section_code if sample_sec else ""

        max_len = max(len(o_list), len(n_list))
        for i in range(max_len):
            om = o_list[i] if i < len(o_list) else None
            nm = n_list[i] if i < len(n_list) else None

            if om and not nm:
                # Removed
                b_room = f"{om.room.building} {om.room.room_number}" if om.room else "Unassigned"
                changes.append(
                    MeetingChangeDetail(
                        meeting_id=om.id,
                        section_id=sec_id,
                        course_code=crs_code,
                        course_name=crs_name,
                        section_code=sec_code,
                        change_type="removed",
                        before_day=om.day_of_week,
                        before_start=_format_time(om.start_time),
                        before_end=_format_time(om.end_time),
                        before_room=b_room,
                    )
                )
                changed_section_ids.add(sec_id)
            elif nm and not om:
                # Added
                a_room = f"{nm.room.building} {nm.room.room_number}" if nm.room else "Unassigned"
                changes.append(
                    MeetingChangeDetail(
                        meeting_id=nm.id,
                        section_id=sec_id,
                        course_code=crs_code,
                        course_name=crs_name,
                        section_code=sec_code,
                        change_type="added",
                        after_day=nm.day_of_week,
                        after_start=_format_time(nm.start_time),
                        after_end=_format_time(nm.end_time),
                        after_room=a_room,
                    )
                )
                changed_section_ids.add(sec_id)
            elif om and nm:
                day_changed = (om.day_of_week != nm.day_of_week)
                time_changed = (
                    _format_time(om.start_time) != _format_time(nm.start_time)
                    or _format_time(om.end_time) != _format_time(nm.end_time)
                )
                room_changed = (om.room_id != nm.room_id)
                fac_changed = (om.faculty_id != nm.faculty_id)

                if day_changed or time_changed or room_changed or fac_changed:
                    b_room = f"{om.room.building} {om.room.room_number}" if om.room else "Unassigned"
                    a_room = f"{nm.room.building} {nm.room.room_number}" if nm.room else "Unassigned"

                    ctype = "moved" if (day_changed or time_changed) else ("room_changed" if room_changed else "faculty_changed")

                    changes.append(
                        MeetingChangeDetail(
                            meeting_id=nm.id,
                            section_id=sec_id,
                            course_code=crs_code,
                            course_name=crs_name,
                            section_code=sec_code,
                            change_type=ctype,
                            before_day=om.day_of_week,
                            before_start=_format_time(om.start_time),
                            before_end=_format_time(om.end_time),
                            before_room=b_room,
                            after_day=nm.day_of_week,
                            after_start=_format_time(nm.start_time),
                            after_end=_format_time(nm.end_time),
                            after_room=a_room,
                        )
                    )
                    changed_section_ids.add(sec_id)

    return changes, changed_section_ids


def process_timetable_publication_notifications(
    db: Session,
    institution_id: int,
    timetable_id: int,
    published_version_id: int,
    previous_version_id: Optional[int] = None,
    actor_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orchestrates post-publish notification generation:
    1. Detects changes between previous version and newly published version.
    2. Identifies affected students through active SectionEnrollment records.
    3. Analyzes student-specific conflicts (work shifts, personal events).
    4. Generates targeted human-readable notifications with appropriate priority.
    5. Dispatches across in-app, push, and email according to preferences.
    6. Returns execution summary with delivery metrics.
    """
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == published_version_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        logger.error(f"Version {published_version_id} not found for notification processing")
        return {"error": "version_not_found"}

    # 1. Detect changes
    changes, changed_section_ids = detect_version_changes(
        db=db,
        institution_id=institution_id,
        timetable_id=timetable_id,
        published_version_id=published_version_id,
        previous_version_id=previous_version_id,
    )

    if not changed_section_ids:
        logger.info(f"Publication of Version {ver.version_number} has 0 changed sections. No notifications needed.")
        return {
            "students_affected": 0,
            "classes_changed": 0,
            "notifications_created": 0,
            "in_app_delivered": 0,
            "email_delivered": 0,
            "email_failed": 0,
            "push_delivered": 0,
            "push_failed": 0,
            "new_conflicts": 0,
            "resolved_conflicts": 0,
        }

    # 2. Identify affected students
    # Filter strictly by active enrollments and institution tenancy
    active_enrollments = (
        db.query(SectionEnrollment)
        .join(StudentProfile, SectionEnrollment.student_id == StudentProfile.user_id)
        .filter(
            SectionEnrollment.section_id.in_(list(changed_section_ids)),
            SectionEnrollment.status == "active",
            StudentProfile.institution_id == institution_id,
            StudentProfile.deleted_at.is_(None),
        )
        .all()
    )

    # Map student_id -> list of changed sections they are enrolled in
    student_to_sections: Dict[int, List[int]] = {}
    for enr in active_enrollments:
        student_to_sections.setdefault(enr.student_id, []).append(enr.section_id)

    affected_student_ids = list(student_to_sections.keys())
    if not affected_student_ids:
        logger.info("No active enrolled students affected by changed sections.")
        return {
            "students_affected": 0,
            "classes_changed": len(changes),
            "notifications_created": 0,
            "in_app_delivered": 0,
            "email_delivered": 0,
            "email_failed": 0,
            "push_delivered": 0,
            "push_failed": 0,
            "new_conflicts": 0,
            "resolved_conflicts": 0,
        }

    # Group changes by section_id
    changes_by_sec: Dict[int, List[MeetingChangeDetail]] = {}
    for ch in changes:
        changes_by_sec.setdefault(ch.section_id, []).append(ch)

    # 3. Preload student data in batched queries
    users = (
        db.query(User)
        .filter(User.id.in_(affected_student_ids), User.deleted_at.is_(None))
        .all()
    )
    user_map = {u.id: u for u in users}

    # Batched TimeBlocks (work shifts & personal events)
    timeblocks = (
        db.query(TimeBlock)
        .filter(
            TimeBlock.user_id.in_(affected_student_ids),
            TimeBlock.deleted == False,
        )
        .all()
    )
    blocks_by_student: Dict[int, List[TimeBlock]] = {}
    for tb in timeblocks:
        blocks_by_student.setdefault(tb.user_id, []).append(tb)

    # Batched Preferences
    prefs_list = (
        db.query(NotificationPrefs)
        .filter(NotificationPrefs.user_id.in_(affected_student_ids))
        .all()
    )
    prefs_map = {p.user_id: p for p in prefs_list}

    # Batched Push Subscriptions
    subs = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id.in_(affected_student_ids))
        .all()
    )
    subs_by_student: Dict[int, List[PushSubscription]] = {}
    for s in subs:
        subs_by_student.setdefault(s.user_id, []).append(s)

    # 4. Generate targeted notifications and deliver
    created_count = 0
    in_app_count = 0
    email_delivered_count = 0
    email_failed_count = 0
    push_delivered_count = 0
    push_failed_count = 0
    new_conflicts_total = 0
    now_utc = datetime.now(timezone.utc)

    for sid in affected_student_ids:
        try:
            student_user = user_map.get(sid)
            if not student_user:
                continue

            sec_ids = student_to_sections.get(sid, [])
            student_changes: List[MeetingChangeDetail] = []
            for s_id in sec_ids:
                student_changes.extend(changes_by_sec.get(s_id, []))

            if not student_changes:
                continue

            # Idempotency check: did we already process this version for this student?
            dedup_key = f"timetable_pub_{timetable_id}_v{ver.version_number}_user_{sid}"
            existing_notif = (
                db.query(NotificationLog)
                .filter(
                    NotificationLog.user_id == sid,
                    NotificationLog.dedup_key == dedup_key,
                )
                .first()
            )
            if existing_notif:
                logger.info(f"Skipping duplicate notification for student {sid} on version {ver.version_number}")
                continue

            # Check for conflict with student work shifts
            student_work_shifts = [
                tb for tb in blocks_by_student.get(sid, [])
                if tb.type == "shift"
            ]

            conflicting_shifts = []
            for ch in student_changes:
                if ch.after_day is not None and ch.after_start and ch.after_end:
                    a_s = _time_to_minutes(ch.after_start)
                    a_e = _time_to_minutes(ch.after_end)
                    for ws in student_work_shifts:
                        if ws.day_of_week == ch.after_day:
                            ws_s = _time_to_minutes(ws.start_time)
                            ws_e = _time_to_minutes(ws.end_time)
                            if a_s < ws_e and ws_s < a_e:
                                conflicting_shifts.append((ch, ws))

            has_work_conflict = (len(conflicting_shifts) > 0)
            if has_work_conflict:
                new_conflicts_total += len(conflicting_shifts)

            # Determine Title, Body, Priority, and Type
            priority = "INFO"
            notif_type = "TIMETABLE_UPDATE"
            action_url = "/calendar"

            if has_work_conflict:
                priority = "URGENT"
                notif_type = "SCHEDULE_CONFLICT"
                ch, ws = conflicting_shifts[0]
                ws_day = DAY_NAMES.get(ws.day_of_week, "")
                ws_time = f"{_format_time(ws.start_time)}–{_format_time(ws.end_time)}"
                c_time = f"{ch.after_start}–{ch.after_end}"
                title = f"Schedule Conflict — {ch.course_name}"
                body = (
                    f"Your {ch.course_name} class moved to {ws_day} {c_time}. "
                    f"This now overlaps with your work shift ({ws.title or 'Work'} {ws_time})."
                )
                action_url = "/calendar"
            elif len(student_changes) == 1:
                ch = student_changes[0]
                if ch.change_type == "moved":
                    priority = "IMPORTANT"
                    notif_type = "CLASS_MOVED"
                    b_day = DAY_NAMES.get(ch.before_day, "")
                    a_day = DAY_NAMES.get(ch.after_day, "")
                    title = f"Your {ch.course_name} class has moved"
                    body = (
                        f"{ch.course_name} ({ch.section_code}) moved from "
                        f"{b_day} {ch.before_start}–{ch.before_end} to {a_day} {ch.after_start}–{ch.after_end}."
                    )
                    action_url = "/calendar"
                elif ch.change_type == "added":
                    priority = "IMPORTANT"
                    notif_type = "CLASS_ADDED"
                    a_day = DAY_NAMES.get(ch.after_day, "")
                    title = f"New class scheduled — {ch.course_name}"
                    body = f"{ch.course_name} ({ch.section_code}) scheduled on {a_day} {ch.after_start}–{ch.after_end} in {ch.after_room}."
                    action_url = "/calendar"
                elif ch.change_type == "removed":
                    priority = "IMPORTANT"
                    notif_type = "CLASS_REMOVED"
                    b_day = DAY_NAMES.get(ch.before_day, "")
                    title = f"Class removed — {ch.course_name}"
                    body = f"{ch.course_name} ({ch.section_code}) on {b_day} {ch.before_start}–{ch.before_end} has been removed from the timetable."
                    action_url = "/calendar"
                elif ch.change_type == "room_changed":
                    priority = "INFO"
                    notif_type = "CLASS_ROOM_CHANGED"
                    title = f"Room changed — {ch.course_name}"
                    body = f"{ch.course_name} ({ch.section_code}) moved to Room {ch.after_room}."
                    action_url = "/student/academics"
                elif ch.change_type == "faculty_changed":
                    priority = "INFO"
                    notif_type = "CLASS_FACULTY_CHANGED"
                    title = f"Instructor update — {ch.course_name}"
                    body = f"Instructor assignment updated for {ch.course_name} ({ch.section_code})."
                    action_url = "/student/academics"
                else:
                    priority = "INFO"
                    notif_type = "TIMETABLE_UPDATE"
                    title = f"Timetable update — {ch.course_name}"
                    body = f"Your schedule for {ch.course_name} ({ch.section_code}) has been updated."
                    action_url = "/calendar"
            else:
                # Grouped Digest for multiple changes
                moved_count = sum(1 for c in student_changes if c.change_type in ("moved", "added", "removed"))
                if moved_count > 0:
                    priority = "IMPORTANT"
                    notif_type = "TIMETABLE_UPDATE"
                    title = "Your timetable was updated"
                    body = f"{len(student_changes)} classes in your schedule have been updated. Review your schedule."
                    action_url = "/calendar"
                else:
                    priority = "INFO"
                    notif_type = "TIMETABLE_UPDATE"
                    title = "Your timetable was updated"
                    body = f"{len(student_changes)} room or instructor updates for your classes."
                    action_url = "/student/academics"

            # Prepare structured metadata for progressive disclosure
            metadata_dict = {
                "timetable_version_id": published_version_id,
                "version_number": ver.version_number,
                "has_work_conflict": has_work_conflict,
                "total_changes": len(student_changes),
                "changes": [c.to_dict() for c in student_changes[:10]],  # Store first 10 diffs
            }
            if conflicting_shifts:
                c_ch, c_ws = conflicting_shifts[0]
                metadata_dict["conflict_details"] = {
                    "course_name": c_ch.course_name,
                    "shift_title": c_ws.title or "Work Shift",
                    "day_of_week": c_ws.day_of_week,
                    "shift_start": _format_time(c_ws.start_time),
                    "shift_end": _format_time(c_ws.end_time),
                }

            # 1. ALWAYS CREATE IN-APP NOTIFICATION
            in_app_log = NotificationLog(
                user_id=sid,
                type=notif_type,
                title=title,
                body=body,
                channel="in_app",
                priority=priority,
                action_url=action_url,
                institution_id=institution_id,
                timetable_version_id=published_version_id,
                delivery_status="delivered",
                metadata_json=json.dumps(metadata_dict),
                dedup_key=dedup_key,
                sent_at=now_utc,
            )
            db.add(in_app_log)
            created_count += 1
            in_app_count += 1

            # Check student preferences
            prefs = prefs_map.get(sid)
            push_enabled = prefs.push_enabled if prefs else True
            email_enabled = prefs.email_enabled if prefs else False
            timetable_changes_enabled = prefs.timetable_changes_enabled if prefs else True

            # If user disabled timetable changes entirely, skip push and email
            if not timetable_changes_enabled:
                continue

            # 2. BROWSER PUSH
            if push_enabled:
                student_subs = subs_by_student.get(sid, [])
                if student_subs:
                    short_push_body = body
                    if len(short_push_body) > 120:
                        short_push_body = short_push_body[:117] + "..."
                    push_payload = {
                        "title": f"SyncShift: {title}",
                        "body": short_push_body,
                        "url": action_url,
                    }
                    for sub in student_subs:
                        try:
                            ok = send_web_push(sub, push_payload, db=db)
                            if ok:
                                push_delivered_count += 1
                            else:
                                push_failed_count += 1
                        except Exception as push_err:
                            logger.warning(f"Push delivery failed for student {sid}: {push_err}")
                            push_failed_count += 1

            # 3. EMAIL NOTIFICATION
            if email_enabled and student_user.email:
                try:
                    email_subject = f"Your timetable changed — {student_changes[0].course_name if student_changes else 'SyncShift'}"
                    ok = send_email_alert(
                        to_email=student_user.email,
                        title=title,
                        body=body,
                        url=action_url,
                    )
                    if ok:
                        email_delivered_count += 1
                    else:
                        email_failed_count += 1
                except Exception as mail_err:
                    logger.warning(f"Email delivery failed for student {sid}: {mail_err}")
                    email_failed_count += 1

        except Exception as student_err:
            logger.error(f"Error processing notification for student {sid}: {student_err}", exc_info=True)
            # Failure for single student does NOT abort other students

    # Commit all created notification records
    try:
        db.commit()
    except Exception as commit_err:
        db.rollback()
        logger.error(f"Error committing notification batch: {commit_err}")
        return {"error": "database_error"}

    return {
        "students_affected": len(affected_student_ids),
        "classes_changed": len(changes),
        "notifications_created": created_count,
        "in_app_delivered": in_app_count,
        "email_delivered": email_delivered_count,
        "email_failed": email_failed_count,
        "push_delivered": push_delivered_count,
        "push_failed": push_failed_count,
        "new_conflicts": new_conflicts_total,
        "resolved_conflicts": 0,
    }


def get_version_notification_summary(
    db: Session,
    institution_id: int,
    timetable_id: int,
    version_id: int,
) -> Dict[str, Any]:
    """
    Returns the university administrator's summary of notifications sent for this timetable version.
    Includes delivery statistics across channels and privacy-preserving student delivery list.
    """
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.institution_id == institution_id,
        )
        .first()
    )
    if not ver:
        return {"error": "version_not_found"}

    # Query all notification logs for this version
    logs = (
        db.query(NotificationLog)
        .options(joinedload(NotificationLog.user))
        .filter(
            NotificationLog.timetable_version_id == version_id,
            NotificationLog.institution_id == institution_id,
        )
        .order_by(NotificationLog.sent_at.desc())
        .all()
    )

    in_app_count = sum(1 for log in logs if log.channel == "in_app")
    email_delivered = sum(1 for log in logs if log.channel == "email" and log.delivery_status == "delivered")
    email_failed = sum(1 for log in logs if log.channel == "email" and log.delivery_status == "failed")
    push_delivered = sum(1 for log in logs if log.channel == "push" and log.delivery_status == "delivered")
    push_failed = sum(1 for log in logs if log.channel == "push" and log.delivery_status == "failed")
    conflict_count = sum(1 for log in logs if log.type == "SCHEDULE_CONFLICT")

    unique_students = set(log.user_id for log in logs)

    summary_status = "all_delivered"
    if email_failed > 0 or push_failed > 0:
        summary_status = "partially_delivered"
    elif len(logs) == 0:
        summary_status = "none_sent"

    log_items = []
    for log in logs[:100]:
        st_name = "Student"
        if log.user:
            st_name = log.user.name or (log.user.email.split("@")[0] if log.user.email else "Student")
        log_items.append({
            "id": log.id,
            "student_id": log.user_id,
            "student_name": st_name,
            "type": log.type,
            "priority": log.priority or "INFO",
            "channel": log.channel,
            "delivery_status": log.delivery_status,
            "title": log.title,
            "sent_at": log.sent_at,
            "read_at": log.read_at,
        })

    return {
        "version_id": ver.id,
        "version_number": ver.version_number,
        "students_affected": len(unique_students),
        "total_notifications": len(logs),
        "in_app_count": in_app_count,
        "email_delivered_count": email_delivered,
        "email_failed_count": email_failed,
        "push_delivered_count": push_delivered,
        "push_failed_count": push_failed,
        "conflict_alerts_count": conflict_count,
        "summary_status": summary_status,
        "logs": log_items,
    }
