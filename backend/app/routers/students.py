"""
Student Academics & Constraints Router
Prefix: /api/v1/students

Provides endpoints for:
- Student Institutional Profile (/me)
- Section Enrollments (/me/enrollments)
- Weekly Availability (/me/availability)
- Hard & Soft Constraints (/me/constraints)
- Optimizer Soft Preferences (/me/preferences)
"""
from datetime import datetime, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.institution import Institution, InstitutionMembership
from app.models.department import Department
from app.models.academic_term import AcademicTerm
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.course_meeting import CourseMeeting
from app.models.faculty import FacultyProfile
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint, StudentPreference
from app.models.student_profile import StudentProfile
from app.models.timetable import Timetable
from app.schemas.common import DataResponse, DeletedResponse, DeletedData
from app.schemas.student_academic import (
    StudentProfileOut,
    StudentProfileUpdate,
    SectionEnrollmentCreate,
    SectionEnrollmentOut,
    AvailableSectionOut,
    StudentAvailabilityItem,
    StudentAvailabilityPayload,
    StudentAvailabilityOut,
    StudentConstraintCreate,
    StudentConstraintUpdate,
    StudentConstraintOut,
    StudentPreferencePayload,
    StudentPreferenceOut,
)
from app.schemas.timetable import CourseMeetingOut, StudentAcademicScheduleOut

router = APIRouter(prefix="/students", tags=["Student Academics"])


def _get_active_student_membership(user_id: int, db: Session) -> InstitutionMembership:
    """Helper to retrieve active student institution membership."""
    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "not_institution_member", "message": "You must be an active member of an institution."},
        )
    return membership


# ── Student Profile Endpoints ────────────────────────────────────────────────

@router.get("/me", response_model=DataResponse[StudentProfileOut])
def get_my_student_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve current student's institutional academic profile."""
    membership = _get_active_student_membership(current_user.user_id, db)
    institution = db.query(Institution).filter(Institution.id == membership.institution_id).first()

    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id == current_user.user_id,
            StudentProfile.institution_id == membership.institution_id,
            StudentProfile.deleted_at.is_(None),
        )
        .first()
    )

    if not profile:
        # Lazily initialize default profile for student
        profile = StudentProfile(
            institution_id=membership.institution_id,
            user_id=current_user.user_id,
            status="active",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    dept = None
    if profile.department_id:
        dept = db.query(Department).filter(Department.id == profile.department_id).first()

    return DataResponse(
        data=StudentProfileOut(
            id=profile.id,
            institution_id=profile.institution_id,
            institution_name=institution.name if institution else None,
            institution_code=institution.code if institution else None,
            user_id=profile.user_id,
            user_name=current_user.display_name or current_user.email,
            user_email=current_user.email,
            department_id=profile.department_id,
            department_name=dept.name if dept else None,
            department_code=dept.code if dept else None,
            student_number=profile.student_number,
            program=profile.program,
            year_of_study=profile.year_of_study,
            status=profile.status,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    )


@router.patch("/me", response_model=DataResponse[StudentProfileOut])
def update_my_student_profile(
    body: StudentProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current student's academic profile (department, student number, program, year)."""
    membership = _get_active_student_membership(current_user.user_id, db)
    institution = db.query(Institution).filter(Institution.id == membership.institution_id).first()

    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id == current_user.user_id,
            StudentProfile.institution_id == membership.institution_id,
            StudentProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not profile:
        profile = StudentProfile(
            institution_id=membership.institution_id,
            user_id=current_user.user_id,
            status="active",
        )
        db.add(profile)

    if body.department_id is not None:
        if body.department_id == 0:
            profile.department_id = None
        else:
            dept = (
                db.query(Department)
                .filter(
                    Department.id == body.department_id,
                    Department.institution_id == membership.institution_id,
                    Department.deleted_at.is_(None),
                )
                .first()
            )
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "department_not_found", "message": "Department not found in your institution"},
                )
            profile.department_id = dept.id

    if body.student_number is not None:
        trimmed = body.student_number.strip()
        if trimmed:
            # Check unique within institution
            existing = (
                db.query(StudentProfile)
                .filter(
                    StudentProfile.institution_id == membership.institution_id,
                    StudentProfile.student_number == trimmed,
                    StudentProfile.user_id != current_user.user_id,
                    StudentProfile.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "student_number_exists", "message": "Student ID number already in use by another student"},
                )
            profile.student_number = trimmed
        else:
            profile.student_number = None

    if body.program is not None:
        profile.program = body.program.strip() or None

    if body.year_of_study is not None:
        if body.year_of_study < 1 or body.year_of_study > 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_year", "message": "Year of study must be between 1 and 10"},
            )
        profile.year_of_study = body.year_of_study

    if body.status is not None:
        profile.status = body.status

    db.commit()
    db.refresh(profile)

    dept = None
    if profile.department_id:
        dept = db.query(Department).filter(Department.id == profile.department_id).first()

    return DataResponse(
        data=StudentProfileOut(
            id=profile.id,
            institution_id=profile.institution_id,
            institution_name=institution.name if institution else None,
            institution_code=institution.code if institution else None,
            user_id=profile.user_id,
            user_name=current_user.display_name or current_user.email,
            user_email=current_user.email,
            department_id=profile.department_id,
            department_name=dept.name if dept else None,
            department_code=dept.code if dept else None,
            student_number=profile.student_number,
            program=profile.program,
            year_of_study=profile.year_of_study,
            status=profile.status,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    )


# ── Section Enrollment Endpoints ─────────────────────────────────────────────

@router.get("/me/enrollments", response_model=DataResponse[List[SectionEnrollmentOut]])
def get_my_enrollments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status e.g. active, dropped"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List section enrollments for the authenticated student."""
    membership = _get_active_student_membership(current_user.user_id, db)

    query = (
        db.query(SectionEnrollment, AcademicSection, AcademicCourse, AcademicTerm)
        .join(AcademicSection, SectionEnrollment.section_id == AcademicSection.id)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
        .filter(
            SectionEnrollment.student_id == current_user.user_id,
            SectionEnrollment.institution_id == membership.institution_id,
        )
    )

    if status_filter:
        query = query.filter(SectionEnrollment.status == status_filter)
    else:
        # Default to active enrollments unless explicitly requested
        query = query.filter(SectionEnrollment.status == "active")

    query = query.order_by(SectionEnrollment.enrollment_date.desc())
    records = query.all()

    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id == current_user.user_id,
            StudentProfile.institution_id == membership.institution_id,
        )
        .first()
    )

    items = []
    for enr, sec, crs, trm in records:
        # Fetch instructor names
        instructors = [
            a.faculty.user.display_name or a.faculty.user.name or a.faculty.user.email
            for a in sec.faculty_assignments
            if a.faculty and a.faculty.user
        ]
        items.append(
            SectionEnrollmentOut(
                id=enr.id,
                institution_id=enr.institution_id,
                student_id=enr.student_id,
                student_name=current_user.display_name or current_user.email,
                student_email=current_user.email,
                student_number=profile.student_number if profile else None,
                section_id=sec.id,
                section_code=sec.section_code,
                course_id=crs.id,
                course_code=crs.code,
                course_name=crs.name,
                credits=crs.credits,
                academic_term_id=trm.id,
                term_name=trm.name,
                instructors=instructors,
                status=enr.status,
                enrollment_date=enr.enrollment_date,
                dropped_at=enr.dropped_at,
                created_at=enr.created_at,
            )
        )

    return DataResponse(data=items)


@router.post("/me/enrollments", response_model=DataResponse[SectionEnrollmentOut], status_code=status.HTTP_201_CREATED)
def enroll_in_section(
    body: SectionEnrollmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enroll student in an academic section.
    Enforces concurrency lock (FOR UPDATE), section capacity, and multi-tenant isolation.
    """
    membership = _get_active_student_membership(current_user.user_id, db)

    # 1. Acquire row lock on section to prevent race conditions during capacity evaluation
    section = (
        db.query(AcademicSection)
        .filter(
            AcademicSection.id == body.section_id,
            AcademicSection.deleted_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": "Section not found"},
        )

    # 2. Multi-tenant validation: section must belong to student's institution
    if section.institution_id != membership.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "section_not_found", "message": "Section not found in your institution"},
        )

    # 3. Validate Section status
    if section.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "section_not_active", "message": f"Cannot enroll: section status is {section.status}"},
        )

    # 4. Validate Academic Term
    term = (
        db.query(AcademicTerm)
        .filter(
            AcademicTerm.id == section.academic_term_id,
            AcademicTerm.deleted_at.is_(None),
        )
        .first()
    )
    if not term or term.status in ("completed", "archived"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "term_not_active", "message": "Cannot enroll in a section from a completed or archived term"},
        )

    # 5. Check if already actively enrolled
    existing = (
        db.query(SectionEnrollment)
        .filter(
            SectionEnrollment.section_id == section.id,
            SectionEnrollment.student_id == current_user.user_id,
        )
        .first()
    )
    if existing and existing.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "already_enrolled", "message": "You are already actively enrolled in this section"},
        )

    # 6. Check Capacity
    active_count = (
        db.query(func.count(SectionEnrollment.id))
        .filter(
            SectionEnrollment.section_id == section.id,
            SectionEnrollment.status == "active",
        )
        .scalar()
    ) or 0

    if active_count >= section.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "section_capacity_reached", "message": "Section has reached maximum student capacity"},
        )

    # 7. Get or create StudentProfile
    profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id == current_user.user_id,
            StudentProfile.institution_id == membership.institution_id,
            StudentProfile.deleted_at.is_(None),
        )
        .first()
    )
    if not profile:
        profile = StudentProfile(
            institution_id=membership.institution_id,
            user_id=current_user.user_id,
            status="active",
        )
        db.add(profile)
        db.flush()

    # 8. Create or reactivate enrollment record
    if existing:
        existing.status = "active"
        existing.dropped_at = None
        existing.enrollment_date = datetime.now()
        existing.student_profile_id = profile.id
        enrollment = existing
    else:
        enrollment = SectionEnrollment(
            institution_id=membership.institution_id,
            student_id=current_user.user_id,
            student_profile_id=profile.id,
            section_id=section.id,
            status="active",
        )
        db.add(enrollment)

    db.commit()
    db.refresh(enrollment)

    # Build response
    crs = db.query(AcademicCourse).filter(AcademicCourse.id == section.course_id).first()
    instructors = [
        a.faculty.user.display_name or a.faculty.user.name or a.faculty.user.email
        for a in section.faculty_assignments
        if a.faculty and a.faculty.user
    ]

    return DataResponse(
        data=SectionEnrollmentOut(
            id=enrollment.id,
            institution_id=enrollment.institution_id,
            student_id=enrollment.student_id,
            student_name=current_user.display_name or current_user.email,
            student_email=current_user.email,
            student_number=profile.student_number if profile else None,
            section_id=section.id,
            section_code=section.section_code,
            course_id=crs.id if crs else None,
            course_code=crs.code if crs else None,
            course_name=crs.name if crs else None,
            credits=crs.credits if crs else None,
            academic_term_id=term.id,
            term_name=term.name,
            instructors=instructors,
            status=enrollment.status,
            enrollment_date=enrollment.enrollment_date,
            dropped_at=enrollment.dropped_at,
            created_at=enrollment.created_at,
        )
    )


@router.delete("/me/enrollments/{enrollment_id}", response_model=DataResponse[dict])
def drop_enrollment(
    enrollment_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Drop an active section enrollment."""
    membership = _get_active_student_membership(current_user.user_id, db)

    enrollment = (
        db.query(SectionEnrollment)
        .filter(
            SectionEnrollment.id == enrollment_id,
            SectionEnrollment.student_id == current_user.user_id,
            SectionEnrollment.institution_id == membership.institution_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "enrollment_not_found", "message": "Enrollment record not found"},
        )

    enrollment.status = "dropped"
    enrollment.dropped_at = datetime.now()
    db.commit()

    return DataResponse(data={"dropped": True, "enrollment_id": enrollment.id})


# ── Student Academic Schedule Read API (N4) ─────────────────────────────────

@router.get("/me/schedule", response_model=DataResponse[StudentAcademicScheduleOut])
def get_my_academic_schedule(
    term_id: Optional[int] = Query(None, description="Optional academic term filter"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authoritative student academic schedule read API.
    Retrieves course meetings derived from the student's active section enrollments
    in the institution's active baseline timetable.
    """
    membership = _get_active_student_membership(current_user.user_id, db)
    institution = db.query(Institution).filter(Institution.id == membership.institution_id).first()

    # 1. Fetch active enrollments for this student
    enr_query = (
        db.query(SectionEnrollment, AcademicSection, AcademicCourse, AcademicTerm)
        .join(AcademicSection, SectionEnrollment.section_id == AcademicSection.id)
        .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
        .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
        .filter(
            SectionEnrollment.student_id == current_user.user_id,
            SectionEnrollment.institution_id == membership.institution_id,
            SectionEnrollment.status == "active",
        )
    )
    if term_id is not None:
        enr_query = enr_query.filter(AcademicTerm.id == term_id)

    enrollments = enr_query.all()
    if not enrollments:
        return DataResponse(
            data=StudentAcademicScheduleOut(
                institution_id=membership.institution_id,
                institution_name=institution.name if institution else None,
                academic_term_id=term_id,
                academic_term_name=None,
                enrolled_sections_count=0,
                meetings=[],
            )
        )

    section_ids = [sec.id for enr, sec, crs, trm in enrollments]
    first_term = enrollments[0][3]

    # 2. Find active timetable(s) in this institution
    tt_query = (
        db.query(Timetable)
        .filter(
            Timetable.institution_id == membership.institution_id,
            Timetable.status == "active",
            Timetable.deleted_at.is_(None),
        )
    )
    if term_id is not None:
        tt_query = tt_query.filter(Timetable.academic_term_id == term_id)
    else:
        tt_query = tt_query.filter(Timetable.academic_term_id == first_term.id)

    active_timetables = tt_query.all()

    # Fallback: if no active timetable explicitly marked yet, check draft timetable
    if not active_timetables:
        fallback_tt = (
            db.query(Timetable)
            .filter(
                Timetable.institution_id == membership.institution_id,
                Timetable.academic_term_id == (term_id if term_id is not None else first_term.id),
                Timetable.deleted_at.is_(None),
            )
            .order_by(Timetable.created_at.desc())
            .first()
        )
        if fallback_tt:
            active_timetables = [fallback_tt]

    if not active_timetables:
        return DataResponse(
            data=StudentAcademicScheduleOut(
                institution_id=membership.institution_id,
                institution_name=institution.name if institution else None,
                academic_term_id=first_term.id,
                academic_term_name=first_term.name,
                enrolled_sections_count=len(section_ids),
                meetings=[],
            )
        )

    # 3. Query CourseMeeting records respecting strict version isolation
    from sqlalchemy import or_

    version_conditions = []
    for tt in active_timetables:
        if tt.published_version_id:
            version_conditions.append(
                (CourseMeeting.timetable_id == tt.id) & (CourseMeeting.version_id == tt.published_version_id)
            )
        else:
            version_conditions.append(
                (CourseMeeting.timetable_id == tt.id) & (CourseMeeting.version_id.is_(None))
            )

    meetings = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.section_id.in_(section_ids),
            CourseMeeting.status == "active",
            CourseMeeting.deleted_at.is_(None),
            or_(*version_conditions) if version_conditions else False,
        )
        .order_by(CourseMeeting.day_of_week, CourseMeeting.start_time)
        .all()
    )


    from app.routers.timetables import _enrich_meeting_out
    enriched_meetings = [_enrich_meeting_out(m) for m in meetings]

    return DataResponse(
        data=StudentAcademicScheduleOut(
            institution_id=membership.institution_id,
            institution_name=institution.name if institution else None,
            academic_term_id=first_term.id,
            academic_term_name=first_term.name,
            enrolled_sections_count=len(section_ids),
            meetings=enriched_meetings,
        )
    )


# ── Student Weekly Availability Endpoints ────────────────────────────────────

def _parse_time_str(t_str: str) -> time:
    """Parse HH:MM:SS or HH:MM string into datetime.time."""
    parts = t_str.strip().split(":")
    if len(parts) == 2:
        return time(hour=int(parts[0]), minute=int(parts[1]))
    elif len(parts) == 3:
        return time(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2].split(".")[0]))
    raise ValueError(f"Invalid time format: {t_str}")


@router.get("/me/availability", response_model=DataResponse[List[StudentAvailabilityOut]])
def get_my_availability(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recurring weekly availability slots for the current student."""
    slots = (
        db.query(StudentAvailability)
        .filter(StudentAvailability.user_id == current_user.user_id)
        .order_by(StudentAvailability.day_of_week.asc(), StudentAvailability.start_time.asc())
        .all()
    )

    items = [
        StudentAvailabilityOut(
            id=s.id,
            user_id=s.user_id,
            institution_id=s.institution_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time.isoformat() if hasattr(s.start_time, "isoformat") else str(s.start_time),
            end_time=s.end_time.isoformat() if hasattr(s.end_time, "isoformat") else str(s.end_time),
            is_available=s.is_available,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in slots
    ]
    return DataResponse(data=items)


@router.put("/me/availability", response_model=DataResponse[List[StudentAvailabilityOut]])
def save_my_availability(
    body: StudentAvailabilityPayload,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save or replace the full recurring weekly availability schedule.
    Validates day ranges (0-6), start_time < end_time, and non-overlapping intervals per day.
    """
    # Check optional institution membership context
    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    inst_id = membership.institution_id if membership else None

    # Validate slots and check for overlaps per day
    day_slots: dict[int, list[tuple[time, time, StudentAvailabilityItem]]] = {d: [] for d in range(7)}

    for s in body.slots:
        if s.day_of_week < 0 or s.day_of_week > 6:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_day", "message": "Day of week must be between 0 (Sunday) and 6 (Saturday)"},
            )
        try:
            st = _parse_time_str(s.start_time)
            et = _parse_time_str(s.end_time)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_time_format", "message": "Time must be in HH:MM or HH:MM:SS format"},
            )

        if st >= et:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_time_range", "message": f"start_time ({s.start_time}) must be strictly before end_time ({s.end_time})"},
            )
        day_slots[s.day_of_week].append((st, et, s))

    # Verify no overlaps on same day
    for d, intervals in day_slots.items():
        intervals.sort(key=lambda x: x[0])
        for i in range(len(intervals) - 1):
            curr_end = intervals[i][1]
            next_start = intervals[i + 1][0]
            if curr_end > next_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "overlapping_availability",
                        "message": f"Availability intervals overlap on day {d}: {intervals[i][0]}-{curr_end} and {next_start}-{intervals[i+1][1]}",
                    },
                )

    # In a transaction, remove existing slots and replace with new set
    db.query(StudentAvailability).filter(StudentAvailability.user_id == current_user.user_id).delete()

    created_records = []
    for d, intervals in day_slots.items():
        for st, et, item in intervals:
            rec = StudentAvailability(
                user_id=current_user.user_id,
                institution_id=inst_id,
                day_of_week=d,
                start_time=st,
                end_time=et,
                is_available=item.is_available,
                title=item.title.strip() if item.title else None,
            )
            db.add(rec)
            created_records.append(rec)

    db.commit()

    # Re-fetch in order
    slots = (
        db.query(StudentAvailability)
        .filter(StudentAvailability.user_id == current_user.user_id)
        .order_by(StudentAvailability.day_of_week.asc(), StudentAvailability.start_time.asc())
        .all()
    )

    items = [
        StudentAvailabilityOut(
            id=s.id,
            user_id=s.user_id,
            institution_id=s.institution_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time.isoformat() if hasattr(s.start_time, "isoformat") else str(s.start_time),
            end_time=s.end_time.isoformat() if hasattr(s.end_time, "isoformat") else str(s.end_time),
            is_available=s.is_available,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in slots
    ]
    return DataResponse(data=items)


# ── Student Constraints Endpoints ────────────────────────────────────────────

VALID_CONSTRAINT_TYPES = {
    "earliest_start",
    "latest_end",
    "max_hours_per_day",
    "max_consecutive_hours",
    "day_off",
    "protect_work_shifts",
    "custom",
}


@router.get("/me/constraints", response_model=DataResponse[List[StudentConstraintOut]])
def get_my_constraints(
    is_hard: Optional[bool] = Query(None, description="Filter hard vs soft constraints"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List constraints defined by the student."""
    query = db.query(StudentConstraint).filter(StudentConstraint.user_id == current_user.user_id)
    if is_hard is not None:
        query = query.filter(StudentConstraint.is_hard == is_hard)

    query = query.order_by(StudentConstraint.is_hard.desc(), StudentConstraint.created_at.desc())
    records = query.all()

    items = [
        StudentConstraintOut(
            id=c.id,
            user_id=c.user_id,
            institution_id=c.institution_id,
            constraint_type=c.constraint_type,
            is_hard=c.is_hard,
            day_of_week=c.day_of_week,
            time_value=c.time_value.isoformat() if c.time_value and hasattr(c.time_value, "isoformat") else (str(c.time_value) if c.time_value else None),
            int_value=c.int_value,
            description=c.description,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in records
    ]
    return DataResponse(data=items)


@router.post("/me/constraints", response_model=DataResponse[StudentConstraintOut], status_code=status.HTTP_201_CREATED)
def create_student_constraint(
    body: StudentConstraintCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new hard constraint or soft limit."""
    c_type = body.constraint_type.strip().lower()
    if c_type not in VALID_CONSTRAINT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_constraint_type", "message": f"Valid types are: {', '.join(sorted(VALID_CONSTRAINT_TYPES))}"},
        )

    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    inst_id = membership.institution_id if membership else None

    parsed_time = None
    if body.time_value:
        try:
            parsed_time = _parse_time_str(body.time_value)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_time_format", "message": "time_value must be in HH:MM or HH:MM:SS format"},
            )

    constraint = StudentConstraint(
        user_id=current_user.user_id,
        institution_id=inst_id,
        constraint_type=c_type,
        is_hard=body.is_hard,
        day_of_week=body.day_of_week,
        time_value=parsed_time,
        int_value=body.int_value,
        description=body.description.strip() if body.description else None,
        is_active=body.is_active,
    )
    db.add(constraint)
    db.commit()
    db.refresh(constraint)

    return DataResponse(
        data=StudentConstraintOut(
            id=constraint.id,
            user_id=constraint.user_id,
            institution_id=constraint.institution_id,
            constraint_type=constraint.constraint_type,
            is_hard=constraint.is_hard,
            day_of_week=constraint.day_of_week,
            time_value=constraint.time_value.isoformat() if constraint.time_value and hasattr(constraint.time_value, "isoformat") else (str(constraint.time_value) if constraint.time_value else None),
            int_value=constraint.int_value,
            description=constraint.description,
            is_active=constraint.is_active,
            created_at=constraint.created_at,
            updated_at=constraint.updated_at,
        )
    )


@router.patch("/me/constraints/{constraint_id}", response_model=DataResponse[StudentConstraintOut])
def update_student_constraint(
    constraint_id: int,
    body: StudentConstraintUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing student constraint."""
    constraint = (
        db.query(StudentConstraint)
        .filter(
            StudentConstraint.id == constraint_id,
            StudentConstraint.user_id == current_user.user_id,
        )
        .first()
    )
    if not constraint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "constraint_not_found", "message": "Constraint not found"},
        )

    if body.constraint_type is not None:
        c_type = body.constraint_type.strip().lower()
        if c_type not in VALID_CONSTRAINT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_constraint_type", "message": f"Valid types: {', '.join(sorted(VALID_CONSTRAINT_TYPES))}"},
            )
        constraint.constraint_type = c_type

    if body.is_hard is not None:
        constraint.is_hard = body.is_hard

    if body.day_of_week is not None:
        constraint.day_of_week = body.day_of_week

    if body.time_value is not None:
        if body.time_value.strip() == "":
            constraint.time_value = None
        else:
            try:
                constraint.time_value = _parse_time_str(body.time_value)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "invalid_time_format", "message": "time_value must be in HH:MM or HH:MM:SS format"},
                )

    if body.int_value is not None:
        constraint.int_value = body.int_value

    if body.description is not None:
        constraint.description = body.description.strip() or None

    if body.is_active is not None:
        constraint.is_active = body.is_active

    db.commit()
    db.refresh(constraint)

    return DataResponse(
        data=StudentConstraintOut(
            id=constraint.id,
            user_id=constraint.user_id,
            institution_id=constraint.institution_id,
            constraint_type=constraint.constraint_type,
            is_hard=constraint.is_hard,
            day_of_week=constraint.day_of_week,
            time_value=constraint.time_value.isoformat() if constraint.time_value and hasattr(constraint.time_value, "isoformat") else (str(constraint.time_value) if constraint.time_value else None),
            int_value=constraint.int_value,
            description=constraint.description,
            is_active=constraint.is_active,
            created_at=constraint.created_at,
            updated_at=constraint.updated_at,
        )
    )


@router.delete("/me/constraints/{constraint_id}", response_model=DeletedResponse)
def delete_student_constraint(
    constraint_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a student constraint."""
    constraint = (
        db.query(StudentConstraint)
        .filter(
            StudentConstraint.id == constraint_id,
            StudentConstraint.user_id == current_user.user_id,
        )
        .first()
    )
    if not constraint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "constraint_not_found", "message": "Constraint not found"},
        )

    db.delete(constraint)
    db.commit()
    return DeletedResponse(data=DeletedData(deleted=True, id=constraint_id))


# ── Student Optimizer Soft Preferences Endpoints ─────────────────────────────

VALID_TIMES_OF_DAY = {"morning", "afternoon", "evening", "any"}
VALID_DENSITIES = {"compact", "balanced", "spread"}


@router.get("/me/preferences", response_model=DataResponse[StudentPreferenceOut])
def get_my_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the student's soft optimization preferences."""
    pref = db.query(StudentPreference).filter(StudentPreference.user_id == current_user.user_id).first()
    if not pref:
        # Default initialization
        pref = StudentPreference(
            user_id=current_user.user_id,
            preferred_time_of_day="any",
            schedule_density="balanced",
            preferred_break_duration_minutes=30,
            work_study_balance_weight=3,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return DataResponse(
        data=StudentPreferenceOut(
            id=pref.id,
            user_id=pref.user_id,
            institution_id=pref.institution_id,
            preferred_time_of_day=pref.preferred_time_of_day,
            schedule_density=pref.schedule_density,
            preferred_break_duration_minutes=pref.preferred_break_duration_minutes,
            max_campus_days_per_week=pref.max_campus_days_per_week,
            preferred_days_off=pref.preferred_days_off,
            work_study_balance_weight=pref.work_study_balance_weight,
            created_at=pref.created_at,
            updated_at=pref.updated_at,
        )
    )


@router.put("/me/preferences", response_model=DataResponse[StudentPreferenceOut])
def update_my_preferences(
    body: StudentPreferencePayload,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the student's soft optimization preferences."""
    time_pref = (body.preferred_time_of_day or "any").strip().lower()
    if time_pref not in VALID_TIMES_OF_DAY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_time_pref", "message": f"Allowed: {', '.join(sorted(VALID_TIMES_OF_DAY))}"},
        )

    density_pref = (body.schedule_density or "balanced").strip().lower()
    if density_pref not in VALID_DENSITIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_density_pref", "message": f"Allowed: {', '.join(sorted(VALID_DENSITIES))}"},
        )

    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    inst_id = membership.institution_id if membership else None

    pref = db.query(StudentPreference).filter(StudentPreference.user_id == current_user.user_id).first()
    if not pref:
        pref = StudentPreference(
            user_id=current_user.user_id,
            institution_id=inst_id,
            preferred_time_of_day=time_pref,
            schedule_density=density_pref,
            preferred_break_duration_minutes=body.preferred_break_duration_minutes or 30,
            max_campus_days_per_week=body.max_campus_days_per_week,
            preferred_days_off=body.preferred_days_off.strip() if body.preferred_days_off else None,
            work_study_balance_weight=body.work_study_balance_weight or 3,
        )
        db.add(pref)
    else:
        pref.institution_id = inst_id
        pref.preferred_time_of_day = time_pref
        pref.schedule_density = density_pref
        pref.preferred_break_duration_minutes = body.preferred_break_duration_minutes or 30
        pref.max_campus_days_per_week = body.max_campus_days_per_week
        pref.preferred_days_off = body.preferred_days_off.strip() if body.preferred_days_off else None
        pref.work_study_balance_weight = body.work_study_balance_weight or 3

    db.commit()
    db.refresh(pref)

    return DataResponse(
        data=StudentPreferenceOut(
            id=pref.id,
            user_id=pref.user_id,
            institution_id=pref.institution_id,
            preferred_time_of_day=pref.preferred_time_of_day,
            schedule_density=pref.schedule_density,
            preferred_break_duration_minutes=pref.preferred_break_duration_minutes,
            max_campus_days_per_week=pref.max_campus_days_per_week,
            preferred_days_off=pref.preferred_days_off,
            work_study_balance_weight=pref.work_study_balance_weight,
            created_at=pref.created_at,
            updated_at=pref.updated_at,
        )
    )
