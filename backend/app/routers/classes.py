import hashlib
import json
import secrets
from datetime import date, datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.class_workspace import ClassWorkspace, ClassMember, ClassEvent, ClassAnnouncement, ClassInvitation
from app.services.class_workspaces import require_class, my_classes, class_out, role_for, members_for, notify_members, legacy_events, workspace_available
from app.services.rate_limiter import rate_limit
from app.services.academic_access import course_allowed, membership, tenant, require_super, history

router = APIRouter(prefix="/classes", tags=["Classes"])


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ClassInput(StrictBody):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    institution_id: int | None = None
    course_id: int | None = None


class JoinInput(StrictBody):
    code: str = Field(min_length=8, max_length=100)


class InviteInput(StrictBody):
    email: EmailStr
    role: Literal["learner", "instructor"] = "learner"


class AcceptInput(StrictBody):
    token: str = Field(min_length=20, max_length=200)


class EventInput(StrictBody):
    title: str = Field(min_length=1, max_length=255)
    location: str = Field(default="", max_length=255)
    event_date: date
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def times(self):
        if self.start_time >= self.end_time:
            raise ValueError("Class events must end after they start on the same day")
        return self


class AnnouncementInput(StrictBody):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)


def event_out(event, instructor=False):
    data = {key: getattr(event, key) for key in ("id", "class_id", "title", "location", "event_date", "start_time", "end_time", "status")}
    if instructor:
        data["pending"] = json.loads(event.pending_json) if event.pending_json else None
    return data


@router.get("")
def list_classes(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    result = my_classes(db, user.user_id)
    db.commit()
    return {"data": result}


@router.post("", status_code=201)
def create_class(body: ClassInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
        _limit=Depends(rate_limit(10, 60, "create_class"))):
    course_allowed(db, user.user_id, body.institution_id, body.course_id)
    workspace = ClassWorkspace(**body.model_dump(), join_code=secrets.token_urlsafe(12), created_by=user.user_id)
    db.add(workspace); db.flush()
    db.add(ClassMember(class_id=workspace.id, user_id=user.user_id, role="instructor"))
    history(db, user.user_id, "class_created", workspace.name, workspace)
    db.commit()
    return {"data": class_out(workspace, "instructor")}


@router.post("/join")
def join_class(body: JoinInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
        _limit=Depends(rate_limit(10, 60, "join_class"))):
    workspace = db.query(ClassWorkspace).filter_by(join_code=body.code).first()
    if not workspace_available(db, workspace):
        raise HTTPException(404, "Class code not found")
    institution_id = tenant(db, workspace)
    if institution_id and not membership(db, user.user_id, institution_id):
        raise HTTPException(403, "Join your university through an administrator invitation first")
    member = db.query(ClassMember).filter_by(class_id=workspace.id, user_id=user.user_id).first()
    if member and member.role == "removed":
        raise HTTPException(403, "Your membership was removed. Ask an instructor for a new invitation.")
    role = role_for(db, workspace, user.user_id)
    if workspace.section_id and not role:
        raise HTTPException(403,"Official section enrollment must be assigned by a university administrator")
    if not role:
        db.add(ClassMember(class_id=workspace.id, user_id=user.user_id, role="learner"))
        db.commit()
        role = "learner"
    return {"data": class_out(workspace, role)}


@router.post("/invitations/accept")
def accept_invitation(body: AcceptInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
        _limit=Depends(rate_limit(10, 60, "class_invitation"))):
    invitation = db.query(ClassInvitation).filter_by(token_hash=hashlib.sha256(body.token.encode()).hexdigest()).with_for_update().first()
    if not invitation or invitation.accepted_at or invitation.expires_at < datetime.utcnow() or invitation.email.lower() != user.email.lower():
        raise HTTPException(403, "Invitation is invalid, expired, already used, or addressed to another account")
    workspace = db.get(ClassWorkspace, invitation.class_id)
    if not workspace_available(db, workspace):
        raise HTTPException(404, "Class is no longer available")
    institution_id = tenant(db, workspace)
    if institution_id and not membership(db, user.user_id, institution_id):
        raise HTTPException(403, "Active university membership required")
    if invitation.role == "instructor":
        course_allowed(db, user.user_id, institution_id, workspace.course_id)
    if workspace.section_id and not role_for(db,workspace,user.user_id):
        raise HTTPException(403,"An administrator must assign your official section first")
    member = db.query(ClassMember).filter_by(class_id=workspace.id, user_id=user.user_id).first()
    # A learner invite cannot demote an existing instructor.
    role = "instructor" if role_for(db, workspace, user.user_id) == "instructor" else invitation.role
    if member:
        member.role = role
    else:
        db.add(ClassMember(class_id=workspace.id, user_id=user.user_id, role=role))
    invitation.accepted_at = datetime.utcnow()
    db.commit()
    return {"data": class_out(workspace, role)}


@router.get("/{class_id}")
def get_class(class_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, role = require_class(db, class_id, user.user_id)
    events = db.query(ClassEvent).filter_by(class_id=class_id).filter(ClassEvent.status != "archived").order_by(ClassEvent.event_date, ClassEvent.start_time).all()
    announcements = db.query(ClassAnnouncement).filter_by(class_id=class_id).order_by(ClassAnnouncement.created_at.desc(), ClassAnnouncement.id.desc()).all()
    return {"data": {**class_out(workspace, role),
        "events": [event_out(e, role == "instructor") for e in events if role == "instructor" or e.status == "published"],
        "legacy_events": [{"id": m.id, "day_of_week": m.day_of_week, "start_time": str(m.start_time), "end_time": str(m.end_time),
            "start_date": term.start_date, "end_date": term.end_date, "timetable_id": m.timetable_id} for m, term in legacy_events(db, workspace)],
        "announcements": [{"id": a.id, "title": a.title, "body": a.body, "created_at": a.created_at} for a in announcements],
        "members": members_for(db, workspace)}}


@router.patch("/{class_id}")
def edit_class(class_id: int, body: ClassInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, role = require_class(db, class_id, user.user_id, True)
    workspace.name, workspace.description = body.name, body.description
    db.commit()
    return {"data": class_out(workspace, role)}


@router.post("/{class_id}/invitations", status_code=201)
def invite(class_id: int, body: InviteInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    if body.role == "instructor":
        require_super(db, user.user_id, tenant(db, workspace))
    token = secrets.token_urlsafe(32)
    db.add(ClassInvitation(class_id=class_id, email=str(body.email).lower(), role=body.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.utcnow()+timedelta(days=7)))
    db.commit()
    return {"data": {"token": token, "role": body.role, "email": body.email, "expires_in_days": 7}}


@router.delete("/{class_id}/members/{member_id}")
def remove_member(class_id: int, member_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    if workspace.section_id:
        require_super(db,user.user_id,tenant(db,workspace))
    if role_for(db, workspace, member_id) == "instructor" and sum(m["role"] == "instructor" for m in members_for(db, workspace)) <= 1:
        raise HTTPException(409, "A class must retain at least one instructor")
    member = db.query(ClassMember).filter_by(class_id=class_id, user_id=member_id).first()
    if member:
        member.role = "removed"
    else:
        db.add(ClassMember(class_id=class_id, user_id=member_id, role="removed"))
    db.commit()
    return {"data": {"removed": True}}


@router.post("/{class_id}/events", status_code=201)
def create_event(class_id: int, body: EventInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_class(db, class_id, user.user_id, True)
    event = ClassEvent(class_id=class_id, **body.model_dump(), status="draft")
    db.add(event); db.commit()
    return {"data": event_out(event, True)}


def owned_event(db, class_id, event_id):
    event = db.query(ClassEvent).filter_by(id=event_id, class_id=class_id).filter(ClassEvent.status != "archived").first()
    if not event:
        raise HTTPException(404, "Class event not found")
    return event


@router.patch("/{class_id}/events/{event_id}")
def edit_event(class_id: int, event_id: int, body: EventInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_class(db, class_id, user.user_id, True)
    event = owned_event(db, class_id, event_id)
    event.pending_json = body.model_dump_json()
    db.commit()
    return {"data": event_out(event, True)}


@router.post("/{class_id}/events/{event_id}/publish")
def publish_event(class_id: int, event_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    event = owned_event(db, class_id, event_id)
    if event.status == "published" and not event.pending_json:
        return {"data": event_out(event, True)}
    from app.services.academic_events import validate_official_event
    candidate = EventInput.model_validate_json(event.pending_json) if event.pending_json else event
    validate_official_event(db, workspace, candidate, exclude_key=f"event:{event.id}")
    if event.pending_json:
        history(db, user.user_id, "event_rescheduled", json.dumps(event_out(event), default=str), workspace)
        for key, value in EventInput.model_validate_json(event.pending_json).model_dump().items():
            setattr(event, key, value)
    event.pending_json = None
    event.status = "published"
    history(db, user.user_id, "event_published", json.dumps(event_out(event), default=str), workspace)
    notify_members(db, workspace, f"{workspace.name}: timetable updated", f"{event.title} — {event.event_date} at {event.start_time}. Open your calendar to review conflicts.")
    db.commit()
    return {"data": event_out(event, True)}


@router.delete("/{class_id}/events/{event_id}")
def cancel_event(class_id: int, event_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    event = owned_event(db, class_id, event_id)
    if event.status == "published":
        notify_members(db, workspace, f"{workspace.name}: event cancelled", event.title)
    event.status = "archived"
    history(db, user.user_id, "event_cancelled", json.dumps(event_out(event), default=str), workspace)
    db.commit()
    return {"data": {"cancelled": True}}


@router.post("/{class_id}/announcements", status_code=201)
def announce(class_id: int, body: AnnouncementInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace, _ = require_class(db, class_id, user.user_id, True)
    announcement = ClassAnnouncement(class_id=class_id, author_id=user.user_id, **body.model_dump())
    db.add(announcement)
    notify_members(db, workspace, body.title, f"New announcement in {workspace.name}")
    db.commit()
    return {"data": {"id": announcement.id}}
