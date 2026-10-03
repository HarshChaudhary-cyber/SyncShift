from fastapi import HTTPException
from app.models.class_workspace import ClassWorkspace, ClassEvent, ClassMember
from app.models.academic_experience import LectureRecord, SharedAppointment, AppointmentAudience
from app.services.class_workspaces import members_for, role_for, legacy_events
from app.services.academic_access import tenant, membership
from app.schemas.block import BlockOut
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from app.models.user import User
from app.models.institution import Institution


def suppressed(db, class_id, key, day):
    return db.query(LectureRecord).filter(LectureRecord.class_id == class_id, LectureRecord.event_key == key,
        LectureRecord.event_date == day, LectureRecord.status.in_(["cancelled", "rescheduled"])).first() is not None


def validate_official_event(db, workspace, event, exclude_key=None, exclude_date=None):
    """Compare only official schedules, never student or professor private tasks."""
    def teachers_for(w):
        from app.models.faculty import FacultyProfile
        from app.models.section_faculty_assignment import SectionFacultyAssignment
        ids={r[0] for r in db.query(ClassMember.user_id).filter_by(class_id=w.id,role="instructor")}
        if w.section_id:
            ids.update(r[0] for r in db.query(FacultyProfile.user_id).join(SectionFacultyAssignment).filter(SectionFacultyAssignment.section_id==w.section_id))
        return {uid for uid in ids if role_for(db,w,uid)=="instructor" and membership(db,uid,tenant(db,w)).role in ("faculty","professor")}
    teachers = teachers_for(workspace)
    for other in db.query(ClassWorkspace).filter(ClassWorkspace.institution_id==tenant(db,workspace)):
        if tenant(db,other) != tenant(db,workspace):
            continue
        other_teachers = teachers_for(other)
        same_class = workspace.id == other.id or bool(workspace.section_id and workspace.section_id == other.section_id)
        for existing in db.query(ClassEvent).filter_by(class_id=other.id,status="published",event_date=event.event_date):
            key = f"event:{existing.id}"
            if key == exclude_key or suppressed(db,other.id,key,event.event_date):
                continue
            overlap = existing.start_time < event.end_time and existing.end_time > event.start_time
            room = bool(event.location and existing.location and event.location.strip().casefold() == existing.location.strip().casefold())
            if overlap and (same_class or teachers & other_teachers or room):
                raise HTTPException(409,"Official class, professor, or room conflict. Choose another time or location.")
        for meeting,term in legacy_events(db,other):
            key = f"meeting:{meeting.id}"
            if key == exclude_key and (exclude_date is None or exclude_date == event.event_date):
                continue
            if not term.start_date <= event.event_date <= term.end_date or (event.event_date.weekday()+1)%7 != meeting.day_of_week or suppressed(db,other.id,key,event.event_date):
                continue
            location = f"{meeting.room.building} {meeting.room.room_number}" if meeting.room else ""
            room = bool(event.location and location and event.location.strip().casefold() == location.strip().casefold())
            if str(meeting.start_time)[:5] < event.end_time and str(meeting.end_time)[:5] > event.start_time and (same_class or teachers & other_teachers or room):
                raise HTTPException(409,"Official class, professor, or room conflict. Choose another time or location.")


def appointment_occurrences(db,user_id,start_date,end_date):
    result = []
    for row in db.query(SharedAppointment).filter(SharedAppointment.event_date >= start_date,SharedAppointment.event_date <= end_date):
        audiences = []
        for a in db.query(AppointmentAudience).filter_by(appointment_id=row.id):
            w = db.get(ClassWorkspace,a.class_id)
            # Revoked teaching authority revokes exposure immediately.
            if w and role_for(db,w,row.owner_id) == "instructor" and role_for(db,w,user_id):
                audiences.append(w)
        if row.owner_id != user_id and not audiences:
            continue
        result.append(BlockOut(id=-(2_000_000_000+row.id),user_id=user_id,type="class",title=row.title,
            appointment_id=row.id,can_manage_appointment=row.owner_id==user_id,
            location=row.location,start_time=row.start_time,end_time=row.end_time,day_of_week=(row.event_date.weekday()+1)%7,
            occurrence_date=row.event_date,specific_date=row.event_date,is_recurring=False,
            source="shared_class" if audiences else "private",class_id=audiences[0].id if audiences else None,
            class_name="Shared appointment" if audiences else "Personal appointment"))
    return result


def localize_occurrences(db,user_id,blocks,start_date,end_date):
    """Store class times in university time; present all calendar days in viewer time."""
    viewer=db.get(User,user_id) if user_id else None
    viewer_tz=(viewer.timezone if viewer else None) or "Europe/London"
    zone=ZoneInfo(viewer_tz)
    result=[]
    for b in blocks:
        source_zone=zone
        if b.appointment_id:
            row=db.get(SharedAppointment,b.appointment_id)
            owner=db.get(User,row.owner_id) if row else None
            source_zone=ZoneInfo((owner.timezone if owner else None) or "Europe/London")
        elif b.class_id:
            w=db.get(ClassWorkspace,b.class_id)
            inst_id=tenant(db,w) if w else None
            institution=db.get(Institution,inst_id) if inst_id else None
            if institution and institution.timezone:
                source_zone=ZoneInfo(institution.timezone or "Europe/London")
        start=datetime.combine(b.occurrence_date,time.fromisoformat(b.start_time)).replace(tzinfo=source_zone).astimezone(zone)
        end=datetime.combine(b.occurrence_date,time.fromisoformat(b.end_time)).replace(tzinfo=source_zone).astimezone(zone)
        while start < end:
            midnight=datetime.combine(start.date()+timedelta(days=1),time.min,tzinfo=zone)
            segment_end=min(end,midnight)
            if start_date <= start.date() <= end_date:
                result.append(b.model_copy(update={"occurrence_date":start.date(),"specific_date":start.date(),
                    "day_of_week":(start.weekday()+1)%7,"start_time":start.strftime("%H:%M"),
                    "end_time":"24:00" if segment_end==midnight else segment_end.strftime("%H:%M")}))
            start=segment_end
    return result
