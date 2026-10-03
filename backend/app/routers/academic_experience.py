from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.routers.classes import StrictBody, EventInput
from app.models.academic_experience import ProfessionalProfile, LectureRecord, SharedAppointment, AppointmentAudience
from app.models.user import User
from app.models.institution import InstitutionMembership, Institution
from app.models.faculty import FacultyProfile
from app.models.student_profile import StudentProfile
from app.models.class_workspace import ClassWorkspace, ClassEvent
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.department import Department
from app.models.section_enrollment import SectionEnrollment
from app.services.academic_access import membership, history, tenant
from app.services.class_workspaces import require_class, my_classes, legacy_events, role_for, members_for, notify_members

router = APIRouter(prefix="/academic", tags=["Role experiences"])


class ProfileInput(StrictBody):
    introduction: str = Field(default="", max_length=4000)
    specializations: str = Field(default="", max_length=1000)
    professional_phone: str = Field(default="", max_length=64)
    office_hours: str = Field(default="", max_length=500)
    office_location: str = Field(default="", max_length=255)


class RecordInput(StrictBody):
    event_key: str = Field(pattern=r"^(event|meeting):[1-9]\d*$")
    event_date: date
    status: Literal["delivered", "cancelled", "rescheduled", "scheduled"]
    replacement: EventInput | None = None


class AppointmentInput(EventInput):
    share_with_students: bool = False
    class_ids: list[int] = Field(default_factory=list, max_length=50)


def minutes(start, end):
    a, b = str(start)[:5], str(end)[:5]
    return int(b[:2])*60+int(b[3:])-int(a[:2])*60-int(a[3:])


def subject_data(db, workspace):
    course = db.get(AcademicCourse, workspace.course_id) if workspace.course_id else None
    section = db.get(AcademicSection, workspace.section_id) if workspace.section_id else None
    if not course and section:
        course = section.course
    sessions = []
    for event in db.query(ClassEvent).filter_by(class_id=workspace.id, status="published"):
        sessions.append({"event_key": f"event:{event.id}", "date": event.event_date, "start_time": event.start_time,
            "end_time": event.end_time, "title": event.title, "minutes": minutes(event.start_time, event.end_time)})
    for meeting, term in legacy_events(db, workspace):
        current = term.start_date
        while current and term.end_date and current <= term.end_date:
            if (current.weekday()+1)%7 == meeting.day_of_week:
                sessions.append({"event_key": f"meeting:{meeting.id}", "date": current, "start_time": str(meeting.start_time)[:5],
                    "end_time": str(meeting.end_time)[:5], "title": workspace.name, "minutes": minutes(meeting.start_time, meeting.end_time)})
            current += timedelta(days=1)
    records = {(r.event_key, r.event_date): r for r in db.query(LectureRecord).filter_by(class_id=workspace.id)}
    for s in sessions:
        record = records.get((s["event_key"], s["date"]))
        s["status"] = record.status if record else "scheduled"
    planned = [s for s in sessions if s["status"] not in ("cancelled", "rescheduled")]
    delivered = [r for r in records.values() if r.status == "delivered"]
    return {"subject": {"name": course.name if course else workspace.name, "code": course.code if course else None,
        "credits": course.credits if course else None, "department": course.department.name if course and course.department else None,
        "introduction": course.description if course else workspace.description,
        "term": section.term.name if section and section.term else None, "section": section.section_code if section else None},
        "professors": [m for m in members_for(db, workspace) if m["role"] == "instructor" and db.query(FacultyProfile).filter_by(user_id=m["user_id"], institution_id=tenant(db,workspace), status="active", deleted_at=None).first()],
        "progress": {"planned_lectures": len(planned), "planned_hours": round(sum(s["minutes"] for s in planned)/60,2),
            "delivered_lectures": len(delivered), "delivered_hours": round(sum(r.minutes for r in delivered)/60,2),
            "remaining_lectures": max(0,len(planned)-len(delivered)),
            "remaining_hours": round(max(0,sum(s["minutes"] for s in planned)-sum(r.minutes for r in delivered))/60,2)},
        "sessions": sorted(sessions, key=lambda s: (s["date"],s["start_time"]))}


@router.get("/classes/{class_id}")
def subject(class_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id)
    return {"data": subject_data(db, workspace)}


@router.post("/classes/{class_id}/records")
def record(class_id: int, body: RecordInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    session = next((s for s in subject_data(db, workspace)["sessions"] if s["event_key"] == body.event_key and s["date"] == body.event_date), None)
    if not session:
        raise HTTPException(404, "Published lecture occurrence not found")
    institution=db.get(Institution,tenant(db,workspace)) if tenant(db,workspace) else None
    if body.status == "delivered" and body.event_date > datetime.now(ZoneInfo(institution.timezone if institution else user.timezone)).date():
        raise HTTPException(422, "Future lectures cannot be recorded as delivered")
    if (body.status == "rescheduled") != (body.replacement is not None):
        raise HTTPException(422, "Rescheduling requires a replacement lecture")
    row = db.query(LectureRecord).filter_by(class_id=class_id, event_key=body.event_key, event_date=body.event_date).first()
    if row and row.status == "rescheduled":
        raise HTTPException(409, "This occurrence was already rescheduled; edit its replacement")
    if not row:
        row = LectureRecord(class_id=class_id, event_key=body.event_key, event_date=body.event_date)
        db.add(row)
    if body.replacement:
        from app.services.academic_events import validate_official_event
        validate_official_event(db, workspace, body.replacement, exclude_key=body.event_key, exclude_date=body.event_date)
        replacement = ClassEvent(class_id=class_id, status="published", **body.replacement.model_dump())
        db.add(replacement); db.flush()
        history(db, user.user_id, "lecture_replacement", f"{body.event_key} on {body.event_date} → event:{replacement.id}", workspace)
    row.status, row.minutes, row.recorded_by = body.status, session["minutes"], user.user_id
    history(db, user.user_id, "lecture_recorded", f"{body.event_key} on {body.event_date}: {body.status}", workspace)
    if body.status in ("cancelled", "rescheduled", "scheduled"):
        notify_members(db, workspace, "Lecture updated", f"{session['title']} on {body.event_date}: {body.status}. Review your calendar for conflicts.")
    db.commit()
    return {"data": subject_data(db, workspace)}


@router.get("/teaching")
def teaching(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.now(ZoneInfo(user.timezone)).date()
    classes = []
    for c in my_classes(db, user.user_id):
        if c["role"] == "instructor":
            classes.append({**c, **subject_data(db, db.get(ClassWorkspace,c["id"]))})
    sessions = []
    for c in classes:
        institution=db.get(Institution,c["institution_id"]) if c["institution_id"] else None
        source_zone=ZoneInfo(institution.timezone if institution else user.timezone)
        for s in c["sessions"]:
            start=datetime.fromisoformat(f"{s['date']}T{s['start_time']}").replace(tzinfo=source_zone).astimezone(ZoneInfo(user.timezone))
            end=datetime.fromisoformat(f"{s['date']}T{s['end_time']}").replace(tzinfo=source_zone).astimezone(ZoneInfo(user.timezone))
            sessions.append({**s,"date":start.date(),"start_time":start.strftime("%H:%M"),"end_time":end.strftime("%H:%M"),"class_id":c["id"],"class_name":c["name"]})
    today_sessions = sorted([s for s in sessions if s["date"] == today], key=lambda s:s["start_time"])
    db.commit()
    return {"data": {"today": today, "timezone": user.timezone, "classes": classes, "today_sessions": today_sessions,
        "upcoming": sorted([s for s in sessions if s["date"] > today and s["status"] == "scheduled"],key=lambda s:(s["date"],s["start_time"]))[:10],
        "completed_today": sum(s["status"] == "delivered" for s in today_sessions),
        "remaining_today": sum(s["status"] == "scheduled" for s in today_sessions)}}


def profile_data(db, user_id, viewer_id):
    target = db.query(User).filter_by(id=user_id, deleted_at=None).first()
    if not target:
        raise HTTPException(404, "Profile not found")
    memberships = db.query(InstitutionMembership).filter_by(user_id=user_id, status="active", deleted_at=None).all()
    visible = [m for m in memberships if membership(db, viewer_id, m.institution_id)]
    faculty = db.query(FacultyProfile).filter(FacultyProfile.user_id == user_id, FacultyProfile.status == "active", FacultyProfile.deleted_at.is_(None),
        FacultyProfile.institution_id.in_([m.institution_id for m in visible if m.role in ("professor", "faculty")])).all()
    own = viewer_id == user_id
    if not own and not faculty:
        raise HTTPException(404, "Professional profile not available in your university")
    professional = db.get(ProfessionalProfile, user_id)
    result = {"user_id": user_id, "name": target.display_name or target.name, "avatar_url": target.avatar_url,
        "introduction": professional.introduction if professional else "",
        "affiliations": [{"institution": f.institution.name, "institution_id": f.institution_id,
            "department": f.department.name if f.department else None, "designation": f.title,
            **({"staff_identifier": f.employee_code} if own else {})} for f in faculty],
        "subjects": [], "professional": {}}
    if faculty:
        # Only an institutional email domain is presented as university email.
        result["university_email"] = target.email if any(f.institution.email_domain and target.email.lower().endswith('@'+f.institution.email_domain.lower()) for f in faculty) else None
        result["professional"] = {k: getattr(professional,k) if professional else "" for k in ("specializations","professional_phone","office_hours","office_location")}
        result["subjects"] = [{"id":c["id"],"name":c["name"]} for c in my_classes(db,user_id) if c["role"] == "instructor" and c["institution_id"] in [f.institution_id for f in faculty]]
    if own:
        result["email"], result["timezone"] = target.email, target.timezone
        result["academic"] = []
        for m in visible:
            if m.role != "student":
                continue
            p=db.query(StudentProfile).filter_by(user_id=user_id,institution_id=m.institution_id,deleted_at=None).first()
            result["academic"].append({"university":m.institution.name,"department":p.department.name if p and p.department else None,
                "enrollment_number":p.student_number if p else None,"program":p.program if p else None,"year":p.year_of_study if p else None})
        result["enrollments"] = [{"subject": e.section.course.name, "section": e.section.section_code, "term": e.section.term.name}
            for e in db.query(SectionEnrollment).filter(SectionEnrollment.student_id == user_id,
                SectionEnrollment.status.in_(["active","enrolled"]),SectionEnrollment.dropped_at.is_(None))
            if membership(db,user_id,e.institution_id) and e.section and not e.section.deleted_at]
    return result


@router.get("/profile/me")
def my_profile(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"data": profile_data(db, user.user_id, user.user_id)}


@router.get("/profile/{user_id}")
def professor_profile(user_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"data": profile_data(db, user_id, user.user_id)}


@router.patch("/profile/me")
def save_profile(body: ProfileInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    faculty = db.query(InstitutionMembership).filter(InstitutionMembership.user_id == user.user_id,
        InstitutionMembership.status == "active", InstitutionMembership.deleted_at.is_(None), InstitutionMembership.role.in_(["faculty","professor"])).first()
    if not faculty and any(getattr(body,k) for k in ("specializations","professional_phone","office_hours","office_location")):
        raise HTTPException(403,"Professional fields require professor membership")
    profile = db.get(ProfessionalProfile,user.user_id)
    if not profile:
        profile = ProfessionalProfile(user_id=user.user_id); db.add(profile)
    for key,value in body.model_dump().items():
        setattr(profile,key,value)
    db.commit()
    return {"data": profile_data(db,user.user_id,user.user_id)}


def appointment_out(db, row):
    return {**{k:getattr(row,k) for k in ("id","title","location","event_date","start_time","end_time")},
        "class_ids": [a.class_id for a in db.query(AppointmentAudience).filter_by(appointment_id=row.id)]}


@router.get("/appointments")
def appointments(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"data": [appointment_out(db,r) for r in db.query(SharedAppointment).filter_by(owner_id=user.user_id).order_by(SharedAppointment.event_date)]}


@router.post("/appointments")
@router.put("/appointments/{appointment_id}")
def save_appointment(body: AppointmentInput, appointment_id: int | None = None, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    audiences = set(body.class_ids) if body.share_with_students else set()
    if body.share_with_students and not audiences:
        raise HTTPException(422,"Select at least one class when sharing")
    for class_id in audiences:
        require_class(db,class_id,user.user_id,True)
    row = db.query(SharedAppointment).filter_by(id=appointment_id,owner_id=user.user_id).first() if appointment_id else SharedAppointment(owner_id=user.user_id)
    if row is None:
        raise HTTPException(404,"Appointment not found")
    old = {a.class_id for a in db.query(AppointmentAudience).filter_by(appointment_id=row.id)} if row.id else set()
    for key,value in body.model_dump(exclude={"share_with_students","class_ids"}).items():
        setattr(row,key,value)
    db.add(row); db.flush()
    db.query(AppointmentAudience).filter_by(appointment_id=row.id).delete()
    for class_id in audiences:
        db.add(AppointmentAudience(appointment_id=row.id,class_id=class_id))
    for class_id in old | audiences:
        workspace = db.get(ClassWorkspace,class_id)
        notify_members(db, workspace,"Shared event updated" if class_id in audiences else "Event no longer shared",
            "A shared event changed. Open your calendar to review the current schedule.")
    db.commit()
    return {"data": appointment_out(db,row)}


@router.delete("/appointments/{appointment_id}")
def delete_appointment(appointment_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SharedAppointment).filter_by(id=appointment_id,owner_id=user.user_id).first()
    if not row:
        raise HTTPException(404,"Appointment not found")
    for a in db.query(AppointmentAudience).filter_by(appointment_id=row.id):
        notify_members(db,db.get(ClassWorkspace,a.class_id),"Shared event cancelled","Review your calendar for the current schedule.")
        db.delete(a)
    db.delete(row); db.commit()
    return {"data": {"deleted":True}}
