"""University-scoped account operations. No private schedule access."""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.institution import InstitutionMembership, Institution
from app.models.user import User
from app.models.faculty import FacultyProfile
from app.models.student_profile import StudentProfile
from app.models.department import Department
from app.models.academic_section import AcademicSection
from app.models.section_enrollment import SectionEnrollment
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.academic_experience import AcademicInvitation, AcademicHistory
from app.services.academic_access import require_super, history

router = APIRouter(prefix="/academic-admin", tags=["Academic administration"])


def student_target(db, institution_id, user_id):
    m=db.query(InstitutionMembership).filter_by(user_id=user_id,institution_id=institution_id,role="student",status="active",deleted_at=None).first()
    target=db.get(User,user_id)
    if not m or not target or target.deleted_at:
        raise HTTPException(404,"Active student in this university required")
    return CurrentUser(user_id=target.id,email=target.email)


from app.schemas.student_academic import SectionEnrollmentCreate


@router.post("/{institution_id}/students/{student_id}/enrollments",status_code=201)
def enroll(institution_id:int,student_id:int,body:SectionEnrollmentCreate,user:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    require_super(db,user.user_id,institution_id)
    target=student_target(db,institution_id,student_id)
    section=db.query(AcademicSection).filter_by(id=body.section_id,institution_id=institution_id,deleted_at=None).first()
    if not section:
        raise HTTPException(404,detail={"code":"section_not_found","message":"Section not found in this university"})
    from app.routers.students import enroll_student_record
    result=enroll_student_record(body,target,db,institution_id)
    history(db,user.user_id,"enrollment_added",f"User {student_id}, section {body.section_id}",institution_id=institution_id);db.commit()
    return result


@router.delete("/{institution_id}/students/{student_id}/enrollments/{enrollment_id}")
def drop(institution_id:int,student_id:int,enrollment_id:int,user:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    require_super(db,user.user_id,institution_id)
    target=student_target(db,institution_id,student_id)
    row=db.query(SectionEnrollment).filter_by(id=enrollment_id,institution_id=institution_id,student_id=student_id).first()
    if not row:
        raise HTTPException(404,"Enrollment not found")
    from app.routers.students import drop_student_record
    result=drop_student_record(enrollment_id,target,db,institution_id)
    history(db,user.user_id,"enrollment_dropped",f"User {student_id}, enrollment {enrollment_id}",institution_id=institution_id);db.commit()
    return result


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvitationInput(Strict):
    email: EmailStr
    role: Literal["student", "professor"]


class AcceptInput(Strict):
    token: str = Field(min_length=20, max_length=200)


class MemberUpdate(Strict):
    role: Literal["student", "professor", "super_admin"]
    status: Literal["active", "inactive"]


class AcademicUpdate(Strict):
    department_id: int | None = None
    student_number: str | None = Field(default=None, max_length=64)
    program: str | None = Field(default=None, max_length=255)
    year_of_study: int | None = Field(default=None, ge=1, le=10)
    employee_code: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=64)


class AssignmentInput(Strict):
    user_id: int
    section_id: int
    active: bool = True


def ensure_profile(db, m):
    cls = FacultyProfile if m.role in ("professor", "faculty") else StudentProfile if m.role == "student" else None
    if cls:
        row = db.query(cls).filter_by(user_id=m.user_id, institution_id=m.institution_id).first()
        if not row:
            row = cls(user_id=m.user_id, institution_id=m.institution_id, status="active")
            db.add(row); db.flush()
        return row


@router.post("/accept")
def accept(body: AcceptInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    invitation = db.query(AcademicInvitation).filter_by(token_hash=hashlib.sha256(body.token.encode()).hexdigest()).with_for_update().first()
    if not invitation or invitation.accepted_at or invitation.expires_at <= datetime.utcnow() or invitation.email.lower() != user.email.lower():
        raise HTTPException(403, "Invalid, expired, used, or incorrectly addressed invitation")
    institution = db.get(Institution, invitation.institution_id)
    if not institution or institution.deleted_at or not institution.is_active:
        raise HTTPException(403, "University is unavailable")
    m = db.query(InstitutionMembership).filter_by(user_id=user.user_id, institution_id=institution.id).first()
    if m:
        raise HTTPException(409, "Membership already exists; an administrator must update it")
    m = InstitutionMembership(user_id=user.user_id, institution_id=institution.id, role=invitation.role, status="active")
    db.add(m); db.flush(); ensure_profile(db, m)
    invitation.accepted_at = datetime.utcnow()
    history(db, user.user_id, "invitation_accepted", f"Member {user.user_id}: {m.role}", institution_id=institution.id)
    db.commit()
    return {"data": {"institution_id": institution.id, "role": m.role}}


@router.get("/{institution_id}/users")
def users(institution_id: int, q: str = Query(default="", max_length=100), page: int = Query(default=1, ge=1),
          user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    query = db.query(InstitutionMembership, User).join(User).filter(InstitutionMembership.institution_id == institution_id,
        InstitutionMembership.deleted_at.is_(None), User.deleted_at.is_(None))
    if q:
        query = query.filter(or_(User.email.ilike(f"%{q}%"), User.display_name.ilike(f"%{q}%")))
    rows = query.order_by(User.id).offset((page-1)*20).limit(20).all()
    active = db.query(InstitutionMembership).filter_by(institution_id=institution_id, status="active", deleted_at=None)
    return {"data": {"total": query.count(), "page": page,
        "students": active.filter(InstitutionMembership.role == "student").count(),
        "professors": active.filter(InstitutionMembership.role.in_(["professor", "faculty"])).count(),
        "users": [{"id": m.user_id, "name": u.display_name or u.name, "email": u.email, "role": m.role, "status": m.status} for m,u in rows]}}


@router.post("/{institution_id}/invitations", status_code=201)
def invite(institution_id: int, body: InvitationInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    token = secrets.token_urlsafe(32)
    db.add(AcademicInvitation(institution_id=institution_id, email=str(body.email).lower(), role=body.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.utcnow()+timedelta(days=7)))
    history(db, user.user_id, "invitation_created", f"{body.email}: {body.role}", institution_id=institution_id)
    db.commit()
    return {"data": {"token": token, "expires_in_days": 7}}


@router.patch("/{institution_id}/users/{user_id}")
def update_member(institution_id: int, user_id: int, body: MemberUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    # Lock the tenant row to serialize last-admin changes on databases with row locks.
    db.query(Institution).filter_by(id=institution_id).with_for_update().one()
    m = db.query(InstitutionMembership).filter_by(user_id=user_id, institution_id=institution_id, deleted_at=None).first()
    if not m:
        raise HTTPException(404, "University member not found")
    if m.role == "super_admin" and m.status == "active" and (body.role != "super_admin" or body.status != "active"):
        if db.query(InstitutionMembership).filter_by(institution_id=institution_id, role="super_admin", status="active", deleted_at=None).count() <= 1:
            raise HTTPException(409, "A university must retain an active super admin")
    history(db, user.user_id, "membership_changed", f"User {user_id}: {m.role}/{m.status} → {body.role}/{body.status}", institution_id=institution_id)
    m.role, m.status = body.role, body.status
    ensure_profile(db, m)
    db.commit()
    return {"data": {"updated": True}}


@router.patch("/{institution_id}/users/{user_id}/academic")
def update_academic(institution_id: int, user_id: int, body: AcademicUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    m = db.query(InstitutionMembership).filter_by(user_id=user_id, institution_id=institution_id, deleted_at=None).first()
    if not m:
        raise HTTPException(404, "University member not found")
    if body.department_id and not db.query(Department).filter_by(id=body.department_id, institution_id=institution_id, deleted_at=None).first():
        raise HTTPException(422, "Department must belong to this university")
    profile = ensure_profile(db, m)
    if not profile:
        raise HTTPException(422, "Student or professor membership required")
    fields = {"department_id", "employee_code", "title"} if isinstance(profile, FacultyProfile) else {"department_id", "student_number", "program", "year_of_study"}
    values = body.model_dump(exclude_unset=True)
    if set(values) - fields:
        raise HTTPException(422, "Fields do not apply to this role")
    if values.get("student_number") and db.query(StudentProfile).filter(StudentProfile.institution_id == institution_id,
        StudentProfile.user_id != user_id,StudentProfile.student_number == values["student_number"],StudentProfile.deleted_at.is_(None)).first():
        raise HTTPException(409, detail={"code":"student_number_exists","message":"Enrollment number is already assigned"})
    for key, value in values.items():
        setattr(profile, key, value)
    history(db, user.user_id, "academic_profile_changed", f"User {user_id}: {', '.join(values)}", institution_id=institution_id)
    db.commit()
    return {"data": {"updated": True}}


@router.get("/{institution_id}/users/{user_id}/academic")
def get_academic(institution_id:int,user_id:int,user:CurrentUser=Depends(get_current_user),db:Session=Depends(get_db)):
    require_super(db,user.user_id,institution_id)
    m=db.query(InstitutionMembership).filter_by(user_id=user_id,institution_id=institution_id,deleted_at=None).first()
    if not m:
        raise HTTPException(404,"University member not found")
    cls=StudentProfile if m.role == "student" else FacultyProfile
    row=db.query(cls).filter_by(institution_id=institution_id,user_id=user_id,deleted_at=None).first()
    fields=("department_id","student_number","program","year_of_study") if cls is StudentProfile else ("department_id","employee_code","title")
    return {"data": {k:getattr(row,k) if row else None for k in fields}}


@router.post("/{institution_id}/assignments")
def assign(institution_id: int, body: AssignmentInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    m = db.query(InstitutionMembership).filter_by(user_id=body.user_id, institution_id=institution_id, status="active", deleted_at=None).first()
    section = db.query(AcademicSection).filter_by(id=body.section_id, institution_id=institution_id, deleted_at=None).first()
    if not m or not section:
        raise HTTPException(404, "Member and section must belong to this university")
    if body.active and (section.status != "active" or section.term.status in ("completed","archived")):
        raise HTTPException(422,"Assignments require an active section and academic term")
    profile = ensure_profile(db, m)
    if m.role == "student":
        db.query(AcademicSection).filter_by(id=section.id).with_for_update().one()
        row = db.query(SectionEnrollment).filter_by(student_id=m.user_id, section_id=section.id).first()
        if body.active and (not row or row.status != "active") and db.query(SectionEnrollment).filter(
            SectionEnrollment.section_id == section.id, SectionEnrollment.status.in_(["active","enrolled"]),SectionEnrollment.dropped_at.is_(None)).count() >= section.capacity:
            raise HTTPException(409,"Section capacity reached")
        if not row:
            row = SectionEnrollment(institution_id=institution_id, student_id=m.user_id, student_profile_id=profile.id, section_id=section.id)
            db.add(row)
        row.status = "active" if body.active else "dropped"
        row.dropped_at = None if body.active else datetime.utcnow()
    elif m.role in ("professor", "faculty"):
        row = db.query(SectionFacultyAssignment).filter_by(faculty_id=profile.id, section_id=section.id).first()
        if not row:
            row = SectionFacultyAssignment(institution_id=institution_id, faculty_id=profile.id, section_id=section.id, role="instructor")
            db.add(row)
        row.deleted_at = None if body.active else datetime.utcnow()
    else:
        raise HTTPException(422, "Assign a student or professor")
    history(db, user.user_id, "assignment_changed", f"User {m.user_id}, section {section.id}, active={body.active}", institution_id=institution_id)
    db.commit()
    return {"data": {"updated": True}}


@router.get("/{institution_id}/history")
def audit(institution_id: int, page: int = Query(default=1, ge=1), user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_super(db, user.user_id, institution_id)
    rows = db.query(AcademicHistory).filter_by(institution_id=institution_id).order_by(AcademicHistory.id.desc()).offset((page-1)*30).limit(30).all()
    return {"data": [{"id": r.id, "action": r.action, "detail": r.detail, "actor_id": r.actor_id, "created_at": r.created_at} for r in rows]}
