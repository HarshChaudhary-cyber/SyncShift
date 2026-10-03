from fastapi import HTTPException
from app.models.institution import Institution, InstitutionMembership
from app.models.academic_section import AcademicSection
from app.models.academic_course import AcademicCourse
from app.models.faculty import FacultyProfile
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.academic_experience import AcademicHistory


def membership(db, user_id, institution_id):
    return db.query(InstitutionMembership).join(Institution).filter(
        InstitutionMembership.user_id == user_id, InstitutionMembership.institution_id == institution_id,
        InstitutionMembership.status == "active", InstitutionMembership.deleted_at.is_(None),
        Institution.is_active.is_(True), Institution.deleted_at.is_(None)).first()


def require_super(db, user_id, institution_id):
    m = membership(db, user_id, institution_id)
    if not m or m.role != "super_admin":
        raise HTTPException(403, "University super admin access required")
    return m


def tenant(db, workspace):
    section = db.get(AcademicSection, workspace.section_id) if workspace.section_id else None
    return section.institution_id if section else workspace.institution_id


def course_allowed(db, user_id, institution_id, course_id):
    m = membership(db, user_id, institution_id)
    course = db.query(AcademicCourse).filter_by(id=course_id, institution_id=institution_id, deleted_at=None).first()
    if not m or not course:
        raise HTTPException(403, "An active university membership and subject in that university are required")
    if m.role in ("admin", "super_admin"):
        return course
    assigned = db.query(SectionFacultyAssignment).join(FacultyProfile).join(AcademicSection, AcademicSection.id == SectionFacultyAssignment.section_id).filter(
        FacultyProfile.user_id == user_id, FacultyProfile.status == "active", FacultyProfile.deleted_at.is_(None),
        SectionFacultyAssignment.deleted_at.is_(None), SectionFacultyAssignment.role.in_(["instructor", "co_instructor", "primary_instructor"]),
        AcademicSection.course_id == course_id, AcademicSection.deleted_at.is_(None)).first()
    if m.role not in ("professor", "faculty") or not assigned:
        raise HTTPException(403, "Only assigned professors can create classes for this subject")
    return course


def history(db, user_id, action, detail, workspace=None, institution_id=None):
    db.add(AcademicHistory(actor_id=user_id, action=action, detail=detail,
        class_id=workspace.id if workspace else None,
        institution_id=tenant(db, workspace) if workspace else institution_id))
