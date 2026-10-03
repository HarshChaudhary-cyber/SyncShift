"""Class authorization and compatibility. Never reads another user's private data."""
import secrets
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.class_workspace import ClassWorkspace, ClassMember, ClassEvent
from app.models.academic_section import AcademicSection
from app.models.academic_course import AcademicCourse
from app.models.academic_term import AcademicTerm
from app.models.section_enrollment import SectionEnrollment
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.faculty import FacultyProfile
from app.models.institution import Institution, InstitutionMembership
from app.models.course_meeting import CourseMeeting
from app.models.timetable import Timetable
from app.models.notification import NotificationLog
from app.models.user import User
from app.schemas.block import BlockOut


def legacy_role(db, workspace, user_id):
    if not workspace.section_id:
        return None
    section = db.get(AcademicSection, workspace.section_id)
    if not section or section.deleted_at:
        return None
    institution = db.get(Institution, section.institution_id)
    if not institution or institution.deleted_at or not institution.is_active:
        return None
    membership = db.query(InstitutionMembership).filter_by(user_id=user_id, institution_id=section.institution_id, status="active", deleted_at=None).first()
    if membership and membership.role in ("admin", "super_admin"):
        return "instructor"
    faculty = db.query(SectionFacultyAssignment).join(FacultyProfile, FacultyProfile.id == SectionFacultyAssignment.faculty_id).filter(
        SectionFacultyAssignment.section_id == section.id, SectionFacultyAssignment.deleted_at.is_(None),
        FacultyProfile.user_id == user_id, FacultyProfile.status == "active", FacultyProfile.deleted_at.is_(None)).first()
    if faculty and membership and membership.role in ("faculty", "professor"):
        return "instructor" if faculty.role in ("instructor", "co_instructor", "primary_instructor") else "learner"
    enrollment = db.query(SectionEnrollment).filter(SectionEnrollment.section_id == section.id,
        SectionEnrollment.student_id == user_id, SectionEnrollment.status.in_(["active", "enrolled"]), SectionEnrollment.dropped_at.is_(None)).first()
    return "learner" if enrollment else None


def workspace_available(db, workspace):
    if not workspace:
        return False
    if workspace.section_id:
        section = db.get(AcademicSection, workspace.section_id)
        if not section or section.deleted_at:
            return False
        inst = db.get(Institution, section.institution_id)
        if not inst or inst.deleted_at or not inst.is_active:
            return False
    return True


def role_for(db, workspace, user_id):
    if not workspace_available(db, workspace):
        return None
    from app.services.academic_access import membership, tenant, course_allowed
    institution_id = tenant(db, workspace)
    m = membership(db, user_id, institution_id) if institution_id else None
    if institution_id and not m:
        return None
    if m and m.role in ("admin", "super_admin"):
        return "instructor"
    member = db.query(ClassMember).filter_by(class_id=workspace.id, user_id=user_id).first()
    if member:
        if member.role == "removed":
            return None
        if member.role == "instructor":
            if workspace.section_id:
                return legacy_role(db, workspace, user_id)
            if m and m.role in ("professor", "faculty") and workspace.course_id:
                try:
                    course_allowed(db, user_id, institution_id, workspace.course_id)
                    return "instructor"
                except HTTPException:
                    pass
            # Preserve access to old standalone records, without retaining self-granted authority.
            return "learner"
        return "learner" if member.role == "learner" else None
    return legacy_role(db, workspace, user_id)


def require_class(db, class_id, user_id, instructor=False):
    workspace = db.get(ClassWorkspace, class_id)
    role = role_for(db, workspace, user_id) if workspace else None
    if not role:
        raise HTTPException(404, detail={"code": "class_not_found", "message": "Class not found or membership required"})
    if instructor and role != "instructor":
        raise HTTPException(403, detail={"code": "instructor_required", "message": "Only an instructor in this class can make this change"})
    return workspace, role


def ensure_legacy_workspaces(db):
    # Compatibility for sections created through retained administration after 0020.
    from sqlalchemy.exc import IntegrityError
    existing = {row[0] for row in db.query(ClassWorkspace.section_id).filter(ClassWorkspace.section_id.isnot(None))}
    for section, course in db.query(AcademicSection, AcademicCourse).join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id).filter(AcademicSection.deleted_at.is_(None), AcademicCourse.deleted_at.is_(None)):
        if section.id not in existing:
            try:
                with db.begin_nested():
                    db.add(ClassWorkspace(name=f"{course.code} · {course.name} ({section.section_code})"[:160],
                        description="", join_code=secrets.token_urlsafe(12), section_id=section.id,
                        institution_id=section.institution_id, course_id=section.course_id))
                    db.flush()
            except IntegrityError:
                pass  # Another request created the unique section wrapper.


def my_classes(db, user_id):
    ensure_legacy_workspaces(db)
    result = []
    institution_ids=db.query(InstitutionMembership.institution_id).filter_by(user_id=user_id,status="active",deleted_at=None)
    explicit_ids=db.query(ClassMember.class_id).filter_by(user_id=user_id)
    sections=db.query(AcademicSection.id).filter(AcademicSection.institution_id.in_(institution_ids))
    for workspace in db.query(ClassWorkspace).filter(or_(ClassWorkspace.institution_id.in_(institution_ids),
            ClassWorkspace.id.in_(explicit_ids),ClassWorkspace.section_id.in_(sections))).order_by(ClassWorkspace.name):
        role = role_for(db, workspace, user_id)
        if role:
            result.append(class_out(workspace, role))
    return result


def class_out(workspace, role):
    return {"id": workspace.id, "name": workspace.name, "description": workspace.description,
        "role": role, "section_id": workspace.section_id, "institution_id": workspace.institution_id, "course_id": workspace.course_id,
        "join_code": workspace.join_code if role == "instructor" else None}


def members_for(db, workspace):
    ids = {r[0] for r in db.query(ClassMember.user_id).filter_by(class_id=workspace.id)}
    if workspace.section_id:
        ids.update(r[0] for r in db.query(SectionEnrollment.student_id).filter_by(section_id=workspace.section_id))
        ids.update(r[0] for r in db.query(FacultyProfile.user_id).join(SectionFacultyAssignment, SectionFacultyAssignment.faculty_id == FacultyProfile.id).filter(SectionFacultyAssignment.section_id == workspace.section_id))
        section = db.get(AcademicSection, workspace.section_id)
        ids.update(r[0] for r in db.query(InstitutionMembership.user_id).filter(InstitutionMembership.institution_id == section.institution_id, InstitutionMembership.role.in_(["admin", "super_admin"])))
    result = []
    for user_id in sorted(ids):
        user = db.get(User, user_id)
        role = role_for(db, workspace, user_id)
        if user and not user.deleted_at and role:
            result.append({"user_id": user_id, "name": user.display_name or user.name or "Member", "role": role})
    return result


def notify_members(db, workspace, title, body):
    for member in members_for(db, workspace):
        db.add(NotificationLog(user_id=member["user_id"], type="CLASS_UPDATE", title=title[:255],
            body=body[:500], channel="in_app", action_url=f"/classes/{workspace.id}", delivery_status="delivered"))


def legacy_events(db, workspace):
    if not workspace.section_id:
        return []
    return db.query(CourseMeeting, AcademicTerm).join(Timetable, CourseMeeting.timetable_id == Timetable.id).join(
        AcademicSection, CourseMeeting.section_id == AcademicSection.id).join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id).filter(
        CourseMeeting.section_id == workspace.section_id, CourseMeeting.deleted_at.is_(None),
        CourseMeeting.status.in_(["active", "scheduled"]), Timetable.deleted_at.is_(None),
        or_((Timetable.published_version_id.isnot(None)) & (CourseMeeting.version_id == Timetable.published_version_id),
            (Timetable.published_version_id.is_(None)) & (Timetable.status == "active") & (CourseMeeting.version_id.is_(None)))).all()


def shared_occurrences(db, user_id, start_date, end_date):
    """Read-through calendar overlay; no private event copies are created."""
    result = []
    requested_start, requested_end = start_date, end_date
    start_date, end_date = start_date-timedelta(days=2), end_date+timedelta(days=2)
    from app.services.academic_events import suppressed, appointment_occurrences
    for entry in my_classes(db, user_id):
        workspace = db.get(ClassWorkspace, entry["id"])
        for event in db.query(ClassEvent).filter(ClassEvent.class_id == workspace.id, ClassEvent.status == "published",
                ClassEvent.event_date >= start_date, ClassEvent.event_date <= end_date):
            if suppressed(db,workspace.id,f"event:{event.id}",event.event_date):
                continue
            result.append(BlockOut(id=-(1_000_000_000 + event.id), user_id=user_id, type="class", title=event.title,
                location=event.location, day_of_week=(event.event_date.weekday()+1)%7,
                start_time=event.start_time, end_time=event.end_time, is_recurring=False,
                occurrence_date=event.event_date, specific_date=event.event_date,
                source="shared_class", class_id=workspace.id, class_name=workspace.name))
        for meeting, term in legacy_events(db, workspace):
            current = max(start_date, term.start_date or start_date)
            until = min(end_date, term.end_date or end_date)
            while current <= until:
                if (current.weekday()+1)%7 == meeting.day_of_week and not suppressed(db,workspace.id,f"meeting:{meeting.id}",current):
                    result.append(BlockOut(id=-meeting.id, user_id=user_id, type="class", title=workspace.name,
                        location=f"{meeting.room.building} {meeting.room.room_number}" if meeting.room else "",
                        day_of_week=meeting.day_of_week, start_time=meeting.start_time.strftime("%H:%M"),
                        end_time=meeting.end_time.strftime("%H:%M"), occurrence_date=current,
                        source="shared_class", class_id=workspace.id, class_name=workspace.name))
                current += timedelta(days=1)
    from app.services.academic_events import localize_occurrences
    return localize_occurrences(db,user_id,result+appointment_occurrences(db,user_id,start_date,end_date),requested_start,requested_end)
