from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    CurrentUser,
    InstitutionContext,
    get_current_user,
    get_institution_context,
    require_institution_admin,
)
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.department import Department
from app.models.faculty import FacultyProfile
from app.models.institution import Institution, InstitutionMembership
from app.models.room import Room
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.section_enrollment import SectionEnrollment
from app.models.user import User
from app.schemas.student_academic import AvailableSectionOut
from app.schemas.academic_resource import (
    AcademicCourseCreate,
    AcademicCourseOut,
    AcademicCourseUpdate,
    AcademicSectionCreate,
    AcademicSectionOut,
    AcademicSectionUpdate,
    FacultyAssignmentCreate,
    FacultyAssignmentOut,
    FacultyProfileCreate,
    FacultyProfileOut,
    FacultyProfileUpdate,
    RoomCreate,
    RoomOut,
    RoomUpdate,
)
from app.schemas.common import DataResponse, DeletedData
from app.schemas.institution import (
    AcademicTermCreate,
    AcademicTermOut,
    AcademicTermUpdate,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    InstitutionCreate,
    InstitutionOut,
    InstitutionUpdate,
    MembershipCreate,
    MembershipOut,
    UniversityDashboardOut,
    UserInstitutionStatus,
)

router = APIRouter(prefix="/institutions", tags=["Institutions"])


# ---------------------------------------------------------------------------
# Current User Institution Status & Onboarding
# ---------------------------------------------------------------------------

@router.get("/me", response_model=DataResponse[UserInstitutionStatus])
def get_my_institution_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the authenticated user's current institution association and role.
    If the user does not belong to any institution, returns has_institution=False.
    """
    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )

    if not membership:
        return DataResponse(
            data=UserInstitutionStatus(
                has_institution=False,
                institution=None,
                membership=None,
            )
        )

    institution = (
        db.query(Institution)
        .filter(
            Institution.id == membership.institution_id,
            Institution.deleted_at.is_(None),
            Institution.is_active.is_(True),
        )
        .first()
    )

    if not institution:
        return DataResponse(
            data=UserInstitutionStatus(
                has_institution=False,
                institution=None,
                membership=None,
            )
        )

    user = db.query(User).filter(User.id == current_user.user_id).first()
    user_email = user.email if user else current_user.email
    user_name = getattr(user, "display_name", None) or getattr(user, "name", None) if user else current_user.display_name

    membership_out = MembershipOut(
        id=membership.id,
        user_id=membership.user_id,
        institution_id=membership.institution_id,
        role=membership.role,
        status=membership.status,
        user_email=user_email,
        user_name=user_name,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )

    return DataResponse(
        data=UserInstitutionStatus(
            has_institution=True,
            institution=InstitutionOut.model_validate(institution),
            membership=membership_out,
        )
    )


@router.post("", response_model=DataResponse[InstitutionOut], status_code=status.HTTP_201_CREATED)
def create_institution(
    body: InstitutionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Onboard a new university/institution.
    The authenticated creator is automatically enrolled as the institution ADMIN.
    """
    # Verify code uniqueness
    existing = (
        db.query(Institution)
        .filter(
            func.lower(Institution.code) == body.code.lower(),
            Institution.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "institution_code_exists", "message": f"Institution with code '{body.code}' already exists"},
        )

    institution = Institution(
        name=body.name.strip(),
        code=body.code.strip().upper(),
        description=body.description,
        country=body.country,
        timezone=body.timezone,
        email_domain=body.email_domain,
        is_active=True,
    )
    db.add(institution)
    db.flush()

    # Assign creating user as ADMIN
    admin_membership = InstitutionMembership(
        user_id=current_user.user_id,
        institution_id=institution.id,
        role="admin",
        status="active",
    )
    db.add(admin_membership)
    db.commit()
    db.refresh(institution)

    return DataResponse(data=InstitutionOut.model_validate(institution))


# ---------------------------------------------------------------------------
# Institution Details & Administration
# ---------------------------------------------------------------------------

@router.get("/{institution_id}", response_model=DataResponse[InstitutionOut])
def get_institution(
    context: InstitutionContext = Depends(get_institution_context),
):
    """
    Retrieve institution details.
    Restricted to verified members of this institution.
    """
    return DataResponse(data=InstitutionOut.model_validate(context.institution))


@router.patch("/{institution_id}", response_model=DataResponse[InstitutionOut])
def update_institution(
    body: InstitutionUpdate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update institution settings.
    Restricted to institution ADMIN.
    """
    institution = context.institution

    if body.code is not None and body.code != institution.code:
        conflict = (
            db.query(Institution)
            .filter(
                func.lower(Institution.code) == body.code.lower(),
                Institution.id != institution.id,
                Institution.deleted_at.is_(None),
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "institution_code_exists", "message": f"Code '{body.code}' is already used by another institution"},
            )
        institution.code = body.code

    if body.name is not None:
        institution.name = body.name.strip()
    if body.description is not None:
        institution.description = body.description
    if body.country is not None:
        institution.country = body.country
    if body.timezone is not None:
        institution.timezone = body.timezone
    if body.email_domain is not None:
        institution.email_domain = body.email_domain
    if body.is_active is not None:
        institution.is_active = body.is_active

    db.commit()
    db.refresh(institution)

    return DataResponse(data=InstitutionOut.model_validate(institution))


# ---------------------------------------------------------------------------
# Dashboard Overview
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/dashboard", response_model=DataResponse[UniversityDashboardOut])
def get_university_dashboard(
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get university dashboard metrics: departments count, members count, and current active term.
    """
    dept_count = (
        db.query(Department)
        .filter(
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .count()
    )

    member_count = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.institution_id == context.institution_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .count()
    )

    course_count = (
        db.query(AcademicCourse)
        .filter(
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
        .count()
    )

    section_count = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .count()
    )

    faculty_count = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
        .count()
    )

    room_count = (
        db.query(Room)
        .filter(
            Room.institution_id == context.institution_id,
            Room.deleted_at.is_(None),
        )
        .count()
    )

    active_term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.status == "active",
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not active_term:
        active_term = (
            db.query(AcademicTerm)
            .filter(
                AcademicTerm.institution_id == context.institution_id,
                AcademicTerm.deleted_at.is_(None),
            )
            .order_by(AcademicTerm.start_date.desc())
            .first()
        )

    user = db.query(User).filter(User.id == context.user.user_id).first()
    membership_out = MembershipOut(
        id=context.membership.id,
        user_id=context.membership.user_id,
        institution_id=context.membership.institution_id,
        role=context.membership.role,
        status=context.membership.status,
        user_email=user.email if user else context.user.email,
        user_name=getattr(user, "display_name", None) or getattr(user, "name", None) if user else context.user.display_name,
        created_at=context.membership.created_at,
        updated_at=context.membership.updated_at,
    )

    return DataResponse(
        data=UniversityDashboardOut(
            institution=InstitutionOut.model_validate(context.institution),
            membership=membership_out,
            department_count=dept_count,
            member_count=member_count,
            course_count=course_count,
            section_count=section_count,
            faculty_count=faculty_count,
            room_count=room_count,
            active_term=AcademicTermOut.model_validate(active_term) if active_term else None,
        )
    )


# ---------------------------------------------------------------------------
# Memberships Management
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/members", response_model=DataResponse[list[MembershipOut]])
def list_institution_members(
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    List members of the institution with roles and status.
    Restricted to institution ADMIN.
    """
    records = (
        db.query(InstitutionMembership, User)
        .join(User, InstitutionMembership.user_id == User.id)
        .filter(
            InstitutionMembership.institution_id == context.institution_id,
            InstitutionMembership.deleted_at.is_(None),
        )
        .order_by(InstitutionMembership.created_at.desc())
        .all()
    )

    items = [
        MembershipOut(
            id=m.id,
            user_id=m.user_id,
            institution_id=m.institution_id,
            role=m.role,
            status=m.status,
            user_email=u.email,
            user_name=u.display_name or u.name,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m, u in records
    ]

    return DataResponse(data=items)


@router.get("/{institution_id}/members/me", response_model=DataResponse[MembershipOut])
def get_my_institution_membership(
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Retrieve the current user's membership details in this institution.
    """
    user = db.query(User).filter(User.id == context.user.user_id).first()
    return DataResponse(
        data=MembershipOut(
            id=context.membership.id,
            user_id=context.membership.user_id,
            institution_id=context.membership.institution_id,
            role=context.membership.role,
            status=context.membership.status,
            user_email=user.email if user else context.user.email,
            user_name=getattr(user, "display_name", None) or getattr(user, "name", None) if user else context.user.display_name,
            created_at=context.membership.created_at,
            updated_at=context.membership.updated_at,
        )
    )


@router.post("/{institution_id}/members", response_model=DataResponse[MembershipOut], status_code=status.HTTP_201_CREATED)
def add_institution_member(
    body: MembershipCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Add or invite a user to the institution with a specified role.
    Restricted to institution ADMIN.
    """
    target_user = None
    if body.user_id:
        target_user = db.query(User).filter(User.id == body.user_id, User.deleted_at.is_(None)).first()
    elif body.email:
        target_user = db.query(User).filter(User.email == body.email.strip().lower(), User.deleted_at.is_(None)).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "The specified user does not exist"},
        )

    # Prevent duplicate membership
    existing = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == target_user.id,
            InstitutionMembership.institution_id == context.institution_id,
            InstitutionMembership.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_membership", "message": "User is already a member of this institution"},
        )

    membership = InstitutionMembership(
        user_id=target_user.id,
        institution_id=context.institution_id,
        role=body.role,
        status=body.status,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return DataResponse(
        data=MembershipOut(
            id=membership.id,
            user_id=membership.user_id,
            institution_id=membership.institution_id,
            role=membership.role,
            status=membership.status,
            user_email=target_user.email,
            user_name=target_user.display_name or target_user.name,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )
    )


# ---------------------------------------------------------------------------
# Department Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/departments", response_model=DataResponse[list[DepartmentOut]])
def list_departments(
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List all active departments belonging to this institution.
    Tenant-isolated.
    """
    departments = (
        db.query(Department)
        .filter(
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .order_by(Department.code)
        .all()
    )
    return DataResponse(data=[DepartmentOut.model_validate(d) for d in departments])


@router.post("/{institution_id}/departments", response_model=DataResponse[DepartmentOut], status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new department in this institution.
    Code must be unique within this institution.
    Restricted to institution ADMIN.
    """
    code_upper = body.code.strip().upper()
    conflict = (
        db.query(Department)
        .filter(
            Department.institution_id == context.institution_id,
            func.lower(Department.code) == code_upper.lower(),
            Department.deleted_at.is_(None),
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_department_code",
                "message": f"Department code '{code_upper}' already exists in this institution",
            },
        )

    dept = Department(
        institution_id=context.institution_id,
        name=body.name.strip(),
        code=code_upper,
        description=body.description,
        is_active=True,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    return DataResponse(data=DepartmentOut.model_validate(dept))


@router.get("/{institution_id}/departments/{department_id}", response_model=DataResponse[DepartmentOut])
def get_department(
    department_id: int = Path(..., description="ID of the department"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of a specific department.
    Guaranteed tenant isolation.
    """
    dept = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .first()
    )
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "department_not_found", "message": f"Department {department_id} not found in this institution"},
        )

    return DataResponse(data=DepartmentOut.model_validate(dept))


@router.patch("/{institution_id}/departments/{department_id}", response_model=DataResponse[DepartmentOut])
def update_department(
    body: DepartmentUpdate,
    department_id: int = Path(..., description="ID of the department to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update department details.
    Restricted to institution ADMIN.
    """
    dept = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .first()
    )
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "department_not_found", "message": f"Department {department_id} not found in this institution"},
        )

    if body.code is not None and body.code.strip().upper() != dept.code:
        code_upper = body.code.strip().upper()
        conflict = (
            db.query(Department)
            .filter(
                Department.institution_id == context.institution_id,
                func.lower(Department.code) == code_upper.lower(),
                Department.id != dept.id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "duplicate_department_code",
                    "message": f"Department code '{code_upper}' already exists in this institution",
                },
            )
        dept.code = code_upper

    if body.name is not None:
        dept.name = body.name.strip()
    if body.description is not None:
        dept.description = body.description
    if body.is_active is not None:
        dept.is_active = body.is_active

    db.commit()
    db.refresh(dept)

    return DataResponse(data=DepartmentOut.model_validate(dept))


@router.delete("/{institution_id}/departments/{department_id}", response_model=DataResponse[DeletedData])
def delete_department(
    department_id: int = Path(..., description="ID of the department to delete"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a department.
    Restricted to institution ADMIN.
    """
    dept = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .first()
    )
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "department_not_found", "message": f"Department {department_id} not found in this institution"},
        )

    dept.deleted_at = func.now()
    dept.is_active = False
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Academic Terms Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/terms", response_model=DataResponse[list[AcademicTermOut]])
def list_academic_terms(
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List academic terms belonging to this institution.
    Tenant-isolated.
    """
    terms = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .order_by(AcademicTerm.start_date.desc())
        .all()
    )
    return DataResponse(data=[AcademicTermOut.model_validate(t) for t in terms])


@router.post("/{institution_id}/terms", response_model=DataResponse[AcademicTermOut], status_code=status.HTTP_201_CREATED)
def create_academic_term(
    body: AcademicTermCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new academic term.
    Validates that end_date > start_date.
    Restricted to institution ADMIN.
    """
    if body.end_date <= body.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_date_range", "message": "Academic term end_date must be strictly after start_date"},
        )

    term = AcademicTerm(
        institution_id=context.institution_id,
        name=body.name.strip(),
        academic_year=body.academic_year.strip(),
        term_type=body.term_type,
        start_date=body.start_date,
        end_date=body.end_date,
        status=body.status,
    )
    db.add(term)
    db.commit()
    db.refresh(term)

    return DataResponse(data=AcademicTermOut.model_validate(term))


@router.get("/{institution_id}/terms/{term_id}", response_model=DataResponse[AcademicTermOut])
def get_academic_term(
    term_id: int = Path(..., description="ID of the academic term"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of an academic term.
    Tenant-isolated.
    """
    term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.id == term_id,
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "term_not_found", "message": f"Academic term {term_id} not found in this institution"},
        )

    return DataResponse(data=AcademicTermOut.model_validate(term))


@router.patch("/{institution_id}/terms/{term_id}", response_model=DataResponse[AcademicTermOut])
def update_academic_term(
    body: AcademicTermUpdate,
    term_id: int = Path(..., description="ID of the academic term to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update an academic term.
    Validates start_date and end_date logically.
    Restricted to institution ADMIN.
    """
    term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.id == term_id,
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "term_not_found", "message": f"Academic term {term_id} not found in this institution"},
        )

    new_start = body.start_date if body.start_date is not None else term.start_date
    new_end = body.end_date if body.end_date is not None else term.end_date
    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_date_range", "message": "Academic term end_date must be strictly after start_date"},
        )

    if body.name is not None:
        term.name = body.name.strip()
    if body.academic_year is not None:
        term.academic_year = body.academic_year.strip()
    if body.term_type is not None:
        term.term_type = body.term_type
    if body.start_date is not None:
        term.start_date = body.start_date
    if body.end_date is not None:
        term.end_date = body.end_date
    if body.status is not None:
        term.status = body.status

    db.commit()
    db.refresh(term)

    return DataResponse(data=AcademicTermOut.model_validate(term))


@router.delete("/{institution_id}/terms/{term_id}", response_model=DataResponse[DeletedData])
def delete_academic_term(
    term_id: int = Path(..., description="ID of the academic term to delete"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete / archive an academic term.
    Restricted to institution ADMIN.
    """
    term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.id == term_id,
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "term_not_found", "message": f"Academic term {term_id} not found in this institution"},
        )

    term.deleted_at = func.now()
    term.status = "archived"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Academic Courses Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/courses", response_model=DataResponse[list[AcademicCourseOut]])
def list_courses(
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List academic courses for this institution.
    Tenant-isolated.
    Supports filtering by department_id, status, and search query.
    """
    query = (
        db.query(AcademicCourse, Department)
        .join(Department, AcademicCourse.department_id == Department.id)
        .filter(
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
    )

    if department_id is not None:
        query = query.filter(AcademicCourse.department_id == department_id)
    if status:
        query = query.filter(AcademicCourse.status == status)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(AcademicCourse.code).like(s) | func.lower(AcademicCourse.name).like(s)
        )

    results = query.order_by(AcademicCourse.code).all()
    courses_out = []
    for course, dept in results:
        out = AcademicCourseOut(
            id=course.id,
            institution_id=course.institution_id,
            department_id=course.department_id,
            department_name=dept.name if dept else None,
            department_code=dept.code if dept else None,
            code=course.code,
            name=course.name,
            description=course.description,
            credits=course.credits,
            level=course.level,
            status=course.status,
            min_room_capacity=course.min_room_capacity,
            required_room_type=course.required_room_type,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
        courses_out.append(out)

    return DataResponse(data=courses_out)


@router.post("/{institution_id}/courses", response_model=DataResponse[AcademicCourseOut], status_code=status.HTTP_201_CREATED)
def create_course(
    body: AcademicCourseCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new course in the institution catalog.
    Validates that the department belongs to this institution and course code is unique.
    Restricted to institution ADMIN.
    """
    # 1. Validate department belongs to same institution
    dept = (
        db.query(Department)
        .filter(
            Department.id == body.department_id,
            Department.institution_id == context.institution_id,
            Department.deleted_at.is_(None),
        )
        .first()
    )
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "department_not_found", "message": f"Department {body.department_id} not found in this institution"},
        )

    # 2. Validate course code uniqueness within institution
    existing = (
        db.query(AcademicCourse)
        .filter(
            AcademicCourse.institution_id == context.institution_id,
            func.lower(AcademicCourse.code) == body.code.strip().lower(),
            AcademicCourse.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "course_code_exists", "message": f"Course with code '{body.code}' already exists in this institution"},
        )

    course = AcademicCourse(
        institution_id=context.institution_id,
        department_id=dept.id,
        code=body.code.strip().upper(),
        name=body.name.strip(),
        description=body.description.strip() if body.description else None,
        credits=body.credits,
        level=body.level or "undergraduate",
        status=body.status or "active",
        min_room_capacity=body.min_room_capacity,
        required_room_type=body.required_room_type,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    out = AcademicCourseOut(
        id=course.id,
        institution_id=course.institution_id,
        department_id=course.department_id,
        department_name=dept.name,
        department_code=dept.code,
        code=course.code,
        name=course.name,
        description=course.description,
        credits=course.credits,
        level=course.level,
        status=course.status,
        min_room_capacity=course.min_room_capacity,
        required_room_type=course.required_room_type,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )
    return DataResponse(data=out)


@router.get("/{institution_id}/courses/{course_id}", response_model=DataResponse[AcademicCourseOut])
def get_course(
    course_id: int = Path(..., description="ID of the course"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of an academic course.
    Tenant-isolated.
    """
    res = (
        db.query(AcademicCourse, Department)
        .join(Department, AcademicCourse.department_id == Department.id)
        .filter(
            AcademicCourse.id == course_id,
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "course_not_found", "message": f"Course {course_id} not found in this institution"},
        )
    course, dept = res
    out = AcademicCourseOut(
        id=course.id,
        institution_id=course.institution_id,
        department_id=course.department_id,
        department_name=dept.name if dept else None,
        department_code=dept.code if dept else None,
        code=course.code,
        name=course.name,
        description=course.description,
        credits=course.credits,
        level=course.level,
        status=course.status,
        min_room_capacity=course.min_room_capacity,
        required_room_type=course.required_room_type,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )
    return DataResponse(data=out)


@router.patch("/{institution_id}/courses/{course_id}", response_model=DataResponse[AcademicCourseOut])
def update_course(
    body: AcademicCourseUpdate,
    course_id: int = Path(..., description="ID of the course to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update an academic course.
    Restricted to institution ADMIN.
    """
    course = (
        db.query(AcademicCourse)
        .filter(
            AcademicCourse.id == course_id,
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "course_not_found", "message": f"Course {course_id} not found in this institution"},
        )

    if body.department_id is not None:
        dept = (
            db.query(Department)
            .filter(
                Department.id == body.department_id,
                Department.institution_id == context.institution_id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "department_not_found", "message": f"Department {body.department_id} not found in this institution"},
            )
        course.department_id = dept.id

    if body.code is not None:
        normalized_code = body.code.strip().upper()
        if normalized_code != course.code:
            existing = (
                db.query(AcademicCourse)
                .filter(
                    AcademicCourse.institution_id == context.institution_id,
                    AcademicCourse.id != course.id,
                    func.lower(AcademicCourse.code) == normalized_code.lower(),
                    AcademicCourse.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "course_code_exists", "message": f"Course with code '{body.code}' already exists in this institution"},
                )
            course.code = normalized_code

    if body.name is not None:
        course.name = body.name.strip()
    if body.description is not None:
        course.description = body.description.strip() or None
    if body.credits is not None:
        course.credits = body.credits
    if body.level is not None:
        course.level = body.level
    if body.status is not None:
        course.status = body.status
    if body.min_room_capacity is not None:
        course.min_room_capacity = body.min_room_capacity
    if body.required_room_type is not None:
        course.required_room_type = body.required_room_type

    db.commit()
    db.refresh(course)

    dept = db.query(Department).filter(Department.id == course.department_id).first()
    out = AcademicCourseOut(
        id=course.id,
        institution_id=course.institution_id,
        department_id=course.department_id,
        department_name=dept.name if dept else None,
        department_code=dept.code if dept else None,
        code=course.code,
        name=course.name,
        description=course.description,
        credits=course.credits,
        level=course.level,
        status=course.status,
        min_room_capacity=course.min_room_capacity,
        required_room_type=course.required_room_type,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )
    return DataResponse(data=out)


@router.delete("/{institution_id}/courses/{course_id}", response_model=DataResponse[DeletedData])
def delete_course(
    course_id: int = Path(..., description="ID of the course to archive"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete / archive an academic course.
    Restricted to institution ADMIN.
    """
    course = (
        db.query(AcademicCourse)
        .filter(
            AcademicCourse.id == course_id,
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "course_not_found", "message": f"Course {course_id} not found in this institution"},
        )

    course.deleted_at = func.now()
    course.status = "archived"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Academic Sections Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

def _get_section_instructors(section_id: int, institution_id: int, db: Session) -> list[FacultyAssignmentOut]:
    assignments = (
        db.query(SectionFacultyAssignment, FacultyProfile, User)
        .join(FacultyProfile, SectionFacultyAssignment.faculty_id == FacultyProfile.id)
        .join(User, FacultyProfile.user_id == User.id)
        .filter(
            SectionFacultyAssignment.section_id == section_id,
            SectionFacultyAssignment.institution_id == institution_id,
            SectionFacultyAssignment.deleted_at.is_(None),
        )
        .order_by(SectionFacultyAssignment.is_primary.desc(), SectionFacultyAssignment.created_at)
        .all()
    )
    instructors = []
    for a, f, u in assignments:
        instructors.append(
            FacultyAssignmentOut(
                id=a.id,
                institution_id=a.institution_id,
                section_id=a.section_id,
                faculty_id=a.faculty_id,
                user_id=f.user_id,
                faculty_name=getattr(u, "display_name", None) or getattr(u, "name", None) or u.email,
                faculty_email=u.email,
                faculty_title=f.title,
                role=a.role,
                is_primary=a.is_primary,
                created_at=a.created_at,
            )
        )
    return instructors


@router.get("/{institution_id}/sections", response_model=DataResponse[list[AcademicSectionOut]])
def list_sections(
    course_id: Optional[int] = None,
    academic_term_id: Optional[int] = None,
    status: Optional[str] = None,
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List academic sections for this institution.
    Tenant-isolated.
    Supports filtering by course_id, academic_term_id, and status.
    """
    query = (
        db.query(AcademicSection, AcademicCourse, AcademicTerm)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
        .filter(
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
    )

    if course_id is not None:
        query = query.filter(AcademicSection.course_id == course_id)
    if academic_term_id is not None:
        query = query.filter(AcademicSection.academic_term_id == academic_term_id)
    if status:
        query = query.filter(AcademicSection.status == status)

    records = query.order_by(AcademicCourse.code, AcademicSection.section_code).all()
    sections_out = []
    for sec, crs, trm in records:
        instructors = _get_section_instructors(sec.id, context.institution_id, db)
        sections_out.append(
            AcademicSectionOut(
                id=sec.id,
                institution_id=sec.institution_id,
                course_id=sec.course_id,
                course_code=crs.code if crs else None,
                course_name=crs.name if crs else None,
                academic_term_id=sec.academic_term_id,
                term_name=trm.name if trm else None,
                section_code=sec.section_code,
                capacity=sec.capacity,
                status=sec.status,
                description=sec.description,
                instructors=instructors,
                created_at=sec.created_at,
                updated_at=sec.updated_at,
            )
        )

    return DataResponse(data=sections_out)


@router.get("/{institution_id}/sections/available", response_model=DataResponse[list[AvailableSectionOut]])
def list_available_sections(
    academic_term_id: Optional[int] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    only_open: Optional[bool] = None,
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List available sections for student enrollment in this institution.
    Accessible to institution members. Tenant-isolated.
    Includes capacity, enrolled count, remaining seats, and user enrollment status.
    """
    query = (
        db.query(AcademicSection, AcademicCourse, AcademicTerm, Department)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
        .join(Department, AcademicCourse.department_id == Department.id)
        .filter(
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
            AcademicSection.status == "active",
            AcademicCourse.deleted_at.is_(None),
            AcademicTerm.deleted_at.is_(None),
            AcademicTerm.status.notin_(["completed", "archived"]),
        )
    )

    if academic_term_id is not None:
        query = query.filter(AcademicSection.academic_term_id == academic_term_id)
    if department_id is not None:
        query = query.filter(AcademicCourse.department_id == department_id)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(AcademicCourse.code).like(s),
                func.lower(AcademicCourse.name).like(s),
                func.lower(AcademicSection.section_code).like(s),
            )
        )

    records = query.order_by(AcademicCourse.code, AcademicSection.section_code).all()

    # Pre-fetch current user's active enrollments in this institution
    user_enrolled_section_ids = set(
        db.query(SectionEnrollment.section_id)
        .filter(
            SectionEnrollment.student_id == context.user.user_id,
            SectionEnrollment.institution_id == context.institution_id,
            SectionEnrollment.status == "active",
        )
        .all()
    )
    user_enrolled_section_ids = {r[0] for r in user_enrolled_section_ids}

    # Pre-fetch enrollment counts for all sections in this institution
    counts_map = dict(
        db.query(SectionEnrollment.section_id, func.count(SectionEnrollment.id))
        .filter(
            SectionEnrollment.institution_id == context.institution_id,
            SectionEnrollment.status == "active",
        )
        .group_by(SectionEnrollment.section_id)
        .all()
    )

    results = []
    for sec, crs, trm, dept in records:
        enrolled_count = counts_map.get(sec.id, 0)
        remaining = max(0, sec.capacity - enrolled_count)
        if only_open and remaining <= 0:
            continue

        instructors = _get_section_instructors(sec.id, context.institution_id, db)
        instructor_names = [inst.faculty_name or inst.faculty_email or "Instructor" for inst in instructors]

        results.append(
            AvailableSectionOut(
                section_id=sec.id,
                section_code=sec.section_code,
                course_id=crs.id,
                course_code=crs.code,
                course_name=crs.name,
                credits=crs.credits,
                level=crs.level,
                department_id=dept.id,
                department_name=dept.name,
                academic_term_id=trm.id,
                term_name=trm.name,
                capacity=sec.capacity,
                enrolled_count=enrolled_count,
                remaining_seats=remaining,
                status=sec.status,
                instructors=instructor_names,
                is_enrolled_by_me=(sec.id in user_enrolled_section_ids),
            )
        )

    return DataResponse(data=results)


@router.post("/{institution_id}/sections", response_model=DataResponse[AcademicSectionOut], status_code=status.HTTP_201_CREATED)
def create_section(
    body: AcademicSectionCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new course section offering for an academic term.
    Validates that both course and term belong to this institution.
    Restricted to institution ADMIN.
    """
    # 1. Validate course belongs to institution
    course = (
        db.query(AcademicCourse)
        .filter(
            AcademicCourse.id == body.course_id,
            AcademicCourse.institution_id == context.institution_id,
            AcademicCourse.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "course_not_found", "message": f"Course {body.course_id} not found in this institution"},
        )

    # 2. Validate term belongs to institution
    term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.id == body.academic_term_id,
            AcademicTerm.institution_id == context.institution_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "term_not_found", "message": f"Academic term {body.academic_term_id} not found in this institution"},
        )

    # 3. Validate unique section code within course and term
    normalized_section_code = body.section_code.strip().upper()
    existing = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.course_id == course.id,
            AcademicSection.academic_term_id == term.id,
            func.lower(AcademicSection.section_code) == normalized_section_code.lower(),
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "section_code_exists", "message": f"Section '{body.section_code}' already exists for this course and term"},
        )

    section = AcademicSection(
        institution_id=context.institution_id,
        course_id=course.id,
        academic_term_id=term.id,
        section_code=normalized_section_code,
        capacity=body.capacity,
        status=body.status or "active",
        description=body.description.strip() if body.description else None,
    )
    db.add(section)
    db.commit()
    db.refresh(section)

    out = AcademicSectionOut(
        id=section.id,
        institution_id=section.institution_id,
        course_id=section.course_id,
        course_code=course.code,
        course_name=course.name,
        academic_term_id=section.academic_term_id,
        term_name=term.name,
        section_code=section.section_code,
        capacity=section.capacity,
        status=section.status,
        description=section.description,
        instructors=[],
        created_at=section.created_at,
        updated_at=section.updated_at,
    )
    return DataResponse(data=out)


@router.get("/{institution_id}/sections/{section_id}", response_model=DataResponse[AcademicSectionOut])
def get_section(
    section_id: int = Path(..., description="ID of the section"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of an academic section including assigned instructors.
    Tenant-isolated.
    """
    res = (
        db.query(AcademicSection, AcademicCourse, AcademicTerm)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found in this institution"},
        )
    sec, crs, trm = res
    instructors = _get_section_instructors(sec.id, context.institution_id, db)
    out = AcademicSectionOut(
        id=sec.id,
        institution_id=sec.institution_id,
        course_id=sec.course_id,
        course_code=crs.code if crs else None,
        course_name=crs.name if crs else None,
        academic_term_id=sec.academic_term_id,
        term_name=trm.name if trm else None,
        section_code=sec.section_code,
        capacity=sec.capacity,
        status=sec.status,
        description=sec.description,
        instructors=instructors,
        created_at=sec.created_at,
        updated_at=sec.updated_at,
    )
    return DataResponse(data=out)


@router.patch("/{institution_id}/sections/{section_id}", response_model=DataResponse[AcademicSectionOut])
def update_section(
    body: AcademicSectionUpdate,
    section_id: int = Path(..., description="ID of the section to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update an academic section.
    Restricted to institution ADMIN.
    """
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found in this institution"},
        )

    if body.section_code is not None:
        normalized_code = body.section_code.strip().upper()
        if normalized_code != section.section_code:
            existing = (
                db.query(AcademicSection)
                .filter(
                    AcademicSection.course_id == section.course_id,
                    AcademicSection.academic_term_id == section.academic_term_id,
                    AcademicSection.id != section.id,
                    func.lower(AcademicSection.section_code) == normalized_code.lower(),
                    AcademicSection.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "section_code_exists", "message": f"Section '{body.section_code}' already exists for this course and term"},
                )
            section.section_code = normalized_code

    if body.capacity is not None:
        section.capacity = body.capacity
    if body.status is not None:
        section.status = body.status
    if body.description is not None:
        section.description = body.description.strip() or None

    db.commit()
    db.refresh(section)

    course = db.query(AcademicCourse).filter(AcademicCourse.id == section.course_id).first()
    term = db.query(AcademicTerm).filter(AcademicTerm.id == section.academic_term_id).first()
    instructors = _get_section_instructors(section.id, context.institution_id, db)

    out = AcademicSectionOut(
        id=section.id,
        institution_id=section.institution_id,
        course_id=section.course_id,
        course_code=course.code if course else None,
        course_name=course.name if course else None,
        academic_term_id=section.academic_term_id,
        term_name=term.name if term else None,
        section_code=section.section_code,
        capacity=section.capacity,
        status=section.status,
        description=section.description,
        instructors=instructors,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )
    return DataResponse(data=out)


@router.delete("/{institution_id}/sections/{section_id}", response_model=DataResponse[DeletedData])
def delete_section(
    section_id: int = Path(..., description="ID of the section to delete"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete / cancel an academic section.
    Restricted to institution ADMIN.
    """
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found in this institution"},
        )

    section.deleted_at = func.now()
    section.status = "cancelled"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Faculty Profiles Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/faculty", response_model=DataResponse[list[FacultyProfileOut]])
def list_faculty(
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List faculty profiles for this institution.
    Tenant-isolated.
    """
    query = (
        db.query(FacultyProfile, User, Department)
        .join(User, FacultyProfile.user_id == User.id)
        .outerjoin(Department, FacultyProfile.department_id == Department.id)
        .filter(
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
    )

    if department_id is not None:
        query = query.filter(FacultyProfile.department_id == department_id)
    if status:
        query = query.filter(FacultyProfile.status == status)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(User.name).like(s)
            | func.lower(User.display_name).like(s)
            | func.lower(User.email).like(s)
            | func.lower(FacultyProfile.employee_code).like(s)
        )

    records = query.order_by(User.name, User.email).all()
    faculty_out = []
    for f, u, d in records:
        faculty_out.append(
            FacultyProfileOut(
                id=f.id,
                institution_id=f.institution_id,
                user_id=f.user_id,
                user_name=getattr(u, "display_name", None) or getattr(u, "name", None) or u.email,
                user_email=u.email,
                department_id=f.department_id,
                department_name=d.name if d else None,
                department_code=d.code if d else None,
                employee_code=f.employee_code,
                title=f.title,
                status=f.status,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
        )

    return DataResponse(data=faculty_out)


@router.post("/{institution_id}/faculty", response_model=DataResponse[FacultyProfileOut], status_code=status.HTTP_201_CREATED)
def create_faculty_profile(
    body: FacultyProfileCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a faculty profile for an institution member.
    Validates user is an active member with professor or admin role.
    Restricted to institution ADMIN.
    """
    user = None
    if body.user_id:
        user = db.query(User).filter(User.id == body.user_id, User.deleted_at.is_(None)).first()
    elif body.email:
        user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower(), User.deleted_at.is_(None)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "The specified user does not exist"},
        )

    # Validate active membership in this institution
    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == user.id,
            InstitutionMembership.institution_id == context.institution_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "user_not_member", "message": "User is not an active member of this institution"},
        )

    # Promote to professor if adding as faculty member and not already admin/professor
    if membership.role not in ("professor", "admin", "super_admin"):
        membership.role = "professor"

    # Validate unique faculty profile per user in institution
    existing = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.user_id == user.id,
            FacultyProfile.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "faculty_profile_exists", "message": "Faculty profile already exists for this user in this institution"},
        )

    # Validate department if provided
    dept = None
    if body.department_id:
        dept = (
            db.query(Department)
            .filter(
                Department.id == body.department_id,
                Department.institution_id == context.institution_id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "department_not_found", "message": f"Department {body.department_id} not found in this institution"},
            )

    faculty = FacultyProfile(
        institution_id=context.institution_id,
        user_id=user.id,
        department_id=dept.id if dept else None,
        employee_code=body.employee_code.strip() if body.employee_code else None,
        title=body.title.strip() if body.title else "Professor",
        status=body.status or "active",
    )
    db.add(faculty)
    db.commit()
    db.refresh(faculty)

    out = FacultyProfileOut(
        id=faculty.id,
        institution_id=faculty.institution_id,
        user_id=faculty.user_id,
        user_name=getattr(user, "display_name", None) or getattr(user, "name", None) or user.email,
        user_email=user.email,
        department_id=faculty.department_id,
        department_name=dept.name if dept else None,
        department_code=dept.code if dept else None,
        employee_code=faculty.employee_code,
        title=faculty.title,
        status=faculty.status,
        created_at=faculty.created_at,
        updated_at=faculty.updated_at,
    )
    return DataResponse(data=out)


@router.get("/{institution_id}/faculty/{faculty_id}", response_model=DataResponse[FacultyProfileOut])
def get_faculty_profile(
    faculty_id: int = Path(..., description="ID of the faculty profile"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of a faculty profile.
    Tenant-isolated.
    """
    res = (
        db.query(FacultyProfile, User, Department)
        .join(User, FacultyProfile.user_id == User.id)
        .outerjoin(Department, FacultyProfile.department_id == Department.id)
        .filter(
            FacultyProfile.id == faculty_id,
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "faculty_not_found", "message": f"Faculty profile {faculty_id} not found in this institution"},
        )
    f, u, d = res
    out = FacultyProfileOut(
        id=f.id,
        institution_id=f.institution_id,
        user_id=f.user_id,
        user_name=getattr(u, "display_name", None) or getattr(u, "name", None) or u.email,
        user_email=u.email,
        department_id=f.department_id,
        department_name=d.name if d else None,
        department_code=d.code if d else None,
        employee_code=f.employee_code,
        title=f.title,
        status=f.status,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )
    return DataResponse(data=out)


@router.patch("/{institution_id}/faculty/{faculty_id}", response_model=DataResponse[FacultyProfileOut])
def update_faculty_profile(
    body: FacultyProfileUpdate,
    faculty_id: int = Path(..., description="ID of the faculty profile to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update a faculty profile.
    Restricted to institution ADMIN.
    """
    faculty = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.id == faculty_id,
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "faculty_not_found", "message": f"Faculty profile {faculty_id} not found in this institution"},
        )

    if body.department_id is not None:
        dept = (
            db.query(Department)
            .filter(
                Department.id == body.department_id,
                Department.institution_id == context.institution_id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "department_not_found", "message": f"Department {body.department_id} not found in this institution"},
            )
        faculty.department_id = dept.id

    if body.employee_code is not None:
        faculty.employee_code = body.employee_code.strip() or None
    if body.title is not None:
        faculty.title = body.title.strip() or None
    if body.status is not None:
        faculty.status = body.status

    db.commit()
    db.refresh(faculty)

    user = db.query(User).filter(User.id == faculty.user_id).first()
    dept = db.query(Department).filter(Department.id == faculty.department_id).first() if faculty.department_id else None

    out = FacultyProfileOut(
        id=faculty.id,
        institution_id=faculty.institution_id,
        user_id=faculty.user_id,
        user_name=getattr(user, "display_name", None) or getattr(user, "name", None) or user.email if user else None,
        user_email=user.email if user else None,
        department_id=faculty.department_id,
        department_name=dept.name if dept else None,
        department_code=dept.code if dept else None,
        employee_code=faculty.employee_code,
        title=faculty.title,
        status=faculty.status,
        created_at=faculty.created_at,
        updated_at=faculty.updated_at,
    )
    return DataResponse(data=out)


@router.delete("/{institution_id}/faculty/{faculty_id}", response_model=DataResponse[DeletedData])
def delete_faculty_profile(
    faculty_id: int = Path(..., description="ID of the faculty profile to deactivate"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete / deactivate a faculty profile.
    Restricted to institution ADMIN.
    """
    faculty = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.id == faculty_id,
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "faculty_not_found", "message": f"Faculty profile {faculty_id} not found in this institution"},
        )

    faculty.deleted_at = func.now()
    faculty.status = "inactive"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Section Faculty Assignments (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/sections/{section_id}/faculty", response_model=DataResponse[list[FacultyAssignmentOut]])
def list_section_faculty(
    section_id: int = Path(..., description="ID of the section"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List faculty instructors assigned to this section.
    Tenant-isolated.
    """
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found in this institution"},
        )

    instructors = _get_section_instructors(section.id, context.institution_id, db)
    return DataResponse(data=instructors)


@router.post("/{institution_id}/sections/{section_id}/faculty", response_model=DataResponse[FacultyAssignmentOut], status_code=status.HTTP_201_CREATED)
def assign_faculty_to_section(
    body: FacultyAssignmentCreate,
    section_id: int = Path(..., description="ID of the section"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Assign a faculty instructor to a section.
    Validates that both section and faculty belong to this institution.
    Restricted to institution ADMIN.
    """
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == section_id,
            AcademicSection.institution_id == context.institution_id,
            AcademicSection.deleted_at.is_(None),
        )
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": f"Section {section_id} not found in this institution"},
        )

    faculty = (
        db.query(FacultyProfile)
        .filter(
            FacultyProfile.id == body.faculty_id,
            FacultyProfile.institution_id == context.institution_id,
            FacultyProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "faculty_not_found", "message": f"Faculty profile {body.faculty_id} not found in this institution"},
        )

    # Check for duplicate assignment
    existing = (
        db.query(SectionFacultyAssignment)
        .filter(
            SectionFacultyAssignment.section_id == section.id,
            SectionFacultyAssignment.faculty_id == faculty.id,
            SectionFacultyAssignment.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_faculty_assignment", "message": "Faculty member is already assigned to this section"},
        )

    assignment = SectionFacultyAssignment(
        institution_id=context.institution_id,
        section_id=section.id,
        faculty_id=faculty.id,
        role=body.role or "instructor",
        is_primary=bool(body.is_primary),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    user = db.query(User).filter(User.id == faculty.user_id).first()
    out = FacultyAssignmentOut(
        id=assignment.id,
        institution_id=assignment.institution_id,
        section_id=assignment.section_id,
        faculty_id=assignment.faculty_id,
        user_id=faculty.user_id,
        faculty_name=getattr(user, "display_name", None) or getattr(user, "name", None) or user.email if user else None,
        faculty_email=user.email if user else None,
        faculty_title=faculty.title,
        role=assignment.role,
        is_primary=assignment.is_primary,
        created_at=assignment.created_at,
    )
    return DataResponse(data=out)


@router.delete("/{institution_id}/sections/{section_id}/faculty/{assignment_id}", response_model=DataResponse[DeletedData])
def remove_faculty_from_section(
    section_id: int = Path(..., description="ID of the section"),
    assignment_id: int = Path(..., description="ID of the faculty assignment to remove"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Remove a faculty instructor from a section.
    Restricted to institution ADMIN.
    """
    assignment = (
        db.query(SectionFacultyAssignment)
        .filter(
            SectionFacultyAssignment.id == assignment_id,
            SectionFacultyAssignment.section_id == section_id,
            SectionFacultyAssignment.institution_id == context.institution_id,
            SectionFacultyAssignment.deleted_at.is_(None),
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "assignment_not_found", "message": f"Faculty assignment {assignment_id} not found for section {section_id}"},
        )

    assignment.deleted_at = func.now()
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ---------------------------------------------------------------------------
# Rooms / Resources Management (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/rooms", response_model=DataResponse[list[RoomOut]])
def list_rooms(
    building: Optional[str] = None,
    room_type: Optional[str] = None,
    status: Optional[str] = None,
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    List physical rooms and resources for this institution.
    Tenant-isolated.
    """
    query = (
        db.query(Room)
        .filter(
            Room.institution_id == context.institution_id,
            Room.deleted_at.is_(None),
        )
    )

    if building:
        query = query.filter(func.lower(Room.building) == building.strip().lower())
    if room_type:
        query = query.filter(Room.room_type == room_type)
    if status:
        query = query.filter(Room.status == status)

    rooms = query.order_by(Room.building, Room.room_number).all()
    return DataResponse(data=[RoomOut.model_validate(r) for r in rooms])


@router.post("/{institution_id}/rooms", response_model=DataResponse[RoomOut], status_code=status.HTTP_201_CREATED)
def create_room(
    body: RoomCreate,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Create a room / resource in this institution.
    Validates capacity > 0 and building + room_number uniqueness.
    Restricted to institution ADMIN.
    """
    if body.capacity <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_capacity", "message": "Room capacity must be greater than zero"},
        )

    existing = (
        db.query(Room)
        .filter(
            Room.institution_id == context.institution_id,
            func.lower(Room.building) == body.building.strip().lower(),
            func.lower(Room.room_number) == body.room_number.strip().lower(),
            Room.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "room_exists", "message": f"Room '{body.room_number}' in building '{body.building}' already exists in this institution"},
        )

    room = Room(
        institution_id=context.institution_id,
        building=body.building.strip(),
        room_number=body.room_number.strip(),
        name=body.name.strip() if body.name else f"{body.building.strip()} {body.room_number.strip()}",
        capacity=body.capacity,
        room_type=body.room_type or "classroom",
        description=body.description.strip() if body.description else None,
        basic_features=body.basic_features.strip() if body.basic_features else None,
        status=body.status or "active",
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return DataResponse(data=RoomOut.model_validate(room))


@router.get("/{institution_id}/rooms/{room_id}", response_model=DataResponse[RoomOut])
def get_room(
    room_id: int = Path(..., description="ID of the room"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """
    Get details of a room.
    Tenant-isolated.
    """
    room = (
        db.query(Room)
        .filter(
            Room.id == room_id,
            Room.institution_id == context.institution_id,
            Room.deleted_at.is_(None),
        )
        .first()
    )
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "room_not_found", "message": f"Room {room_id} not found in this institution"},
        )

    return DataResponse(data=RoomOut.model_validate(room))


@router.patch("/{institution_id}/rooms/{room_id}", response_model=DataResponse[RoomOut])
def update_room(
    body: RoomUpdate,
    room_id: int = Path(..., description="ID of the room to update"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Update a room.
    Restricted to institution ADMIN.
    """
    room = (
        db.query(Room)
        .filter(
            Room.id == room_id,
            Room.institution_id == context.institution_id,
            Room.deleted_at.is_(None),
        )
        .first()
    )
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "room_not_found", "message": f"Room {room_id} not found in this institution"},
        )

    target_bldg = body.building.strip() if body.building is not None else room.building
    target_num = body.room_number.strip() if body.room_number is not None else room.room_number

    if (body.building is not None and body.building.strip().lower() != room.building.lower()) or \
       (body.room_number is not None and body.room_number.strip().lower() != room.room_number.lower()):
        existing = (
            db.query(Room)
            .filter(
                Room.institution_id == context.institution_id,
                Room.id != room.id,
                func.lower(Room.building) == target_bldg.lower(),
                func.lower(Room.room_number) == target_num.lower(),
                Room.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "room_exists", "message": f"Room '{target_num}' in building '{target_bldg}' already exists in this institution"},
            )
        room.building = target_bldg
        room.room_number = target_num

    if body.capacity is not None:
        if body.capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_capacity", "message": "Room capacity must be greater than zero"},
            )
        room.capacity = body.capacity

    if body.name is not None:
        room.name = body.name.strip() or None
    if body.room_type is not None:
        room.room_type = body.room_type
    if body.description is not None:
        room.description = body.description.strip() or None
    if body.basic_features is not None:
        room.basic_features = body.basic_features.strip() or None
    if body.status is not None:
        room.status = body.status

    db.commit()
    db.refresh(room)

    return DataResponse(data=RoomOut.model_validate(room))


@router.delete("/{institution_id}/rooms/{room_id}", response_model=DataResponse[DeletedData])
def delete_room(
    room_id: int = Path(..., description="ID of the room to delete"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Soft-delete / deactivate a room.
    Restricted to institution ADMIN.
    """
    room = (
        db.query(Room)
        .filter(
            Room.id == room_id,
            Room.institution_id == context.institution_id,
            Room.deleted_at.is_(None),
        )
        .first()
    )
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "room_not_found", "message": f"Room {room_id} not found in this institution"},
        )

    room.deleted_at = func.now()
    room.status = "inactive"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))

