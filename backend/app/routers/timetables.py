from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import (
    CurrentUser,
    InstitutionContext,
    get_institution_context,
    require_institution_admin,
)
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.course_meeting import CourseMeeting
from app.models.faculty import FacultyProfile
from app.models.institution import Institution
from app.models.room import Room
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.schemas.common import DataResponse, DeletedData
from app.schemas.timetable import (
    ApproveVersionRequest,
    CourseMeetingCreate,
    CourseMeetingOut,
    CourseMeetingUpdate,
    PublishVersionRequest,
    PublishVersionResponse,
    SubmitReviewRequest,
    TimetableChangeApplyRequest,
    TimetableChangeApplyResponse,
    TimetableChangeProposal,
    TimetableCreate,
    TimetableImpactResponse,
    TimetableOut,
    TimetableUpdate,
    TimetableVersionCreate,
    TimetableVersionOut,
    TimetableVersionUpdate,
    VersionChecklistOut,
    VersionComparisonOut,
)
from app.services.audit import record_audit_log
from app.services.impact_analysis import analyze_timetable_change
from app.services.timetable_validator import (
    DAY_NAMES,
    format_time_str,
    parse_time_obj,
    validate_course_meeting,
)
from app.services.timetable_version_service import (
    _enrich_version_out,
    approve_version,
    compare_versions,
    create_version,
    get_or_create_initial_version,
    publish_version,
    run_version_checklist,
    submit_for_review,
)

router = APIRouter(prefix="/institutions", tags=["University Timetables"])


def _enrich_meeting_out(m: CourseMeeting) -> CourseMeetingOut:
    sec = m.section
    crs = sec.course if sec else None
    rm = m.room
    fac = m.faculty
    fac_user = fac.user if fac else None

    # If no meeting-specific faculty, resolve primary instructor from section
    if not fac and sec:
        for fa in sec.faculty_assignments:
            if fa.is_primary and fa.faculty:
                fac = fa.faculty
                fac_user = fac.user
                break
        if not fac and sec.faculty_assignments:
            first_fa = sec.faculty_assignments[0]
            if first_fa.faculty:
                fac = first_fa.faculty
                fac_user = fac.user

    fac_name = None
    if fac_user:
        fac_name = fac_user.display_name or fac_user.name or fac_user.email

    return CourseMeetingOut(
        id=m.id,
        institution_id=m.institution_id,
        timetable_id=m.timetable_id,
        version_id=m.version_id,
        section_id=m.section_id,
        academic_term_id=m.academic_term_id,
        day_of_week=m.day_of_week,
        start_time=format_time_str(m.start_time),
        end_time=format_time_str(m.end_time),

        room_id=m.room_id,
        faculty_id=m.faculty_id,
        meeting_type=m.meeting_type,
        status=m.status,
        created_at=m.created_at,
        updated_at=m.updated_at,
        course_id=crs.id if crs else None,
        course_code=crs.code if crs else None,
        course_name=crs.name if crs else None,
        section_code=sec.section_code if sec else None,
        section_capacity=sec.capacity if sec else None,
        room_building=rm.building if rm else None,
        room_number=rm.room_number if rm else None,
        room_name=rm.name if rm else None,
        room_capacity=rm.capacity if rm else None,
        faculty_name=fac_name,
        faculty_title=fac.title if fac else None,
    )


# ── Timetable Endpoints ───────────────────────────────────────────────────────

@router.get("/{institution_id}/timetables", response_model=DataResponse[List[TimetableOut]])
def list_timetables(
    institution_id: int = Path(...),
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: draft, active, archived"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """List all timetables for this institution with summary metrics."""
    query = (
        db.query(Timetable)
        .filter(
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
    )
    if term_id is not None:
        query = query.filter(Timetable.academic_term_id == term_id)
    if status_filter is not None:
        query = query.filter(Timetable.status == status_filter)

    timetables = query.order_by(Timetable.created_at.desc()).all()

    results: List[TimetableOut] = []
    for t in timetables:
        term = db.query(AcademicTerm).filter(AcademicTerm.id == t.academic_term_id).first()
        # Count meetings
        m_count = (
            db.query(func.count(CourseMeeting.id))
            .filter(
                CourseMeeting.timetable_id == t.id,
                CourseMeeting.deleted_at.is_(None),
                CourseMeeting.status == "active",
            )
            .scalar()
            or 0
        )
        # Distinct sections
        sec_count = (
            db.query(func.count(func.distinct(CourseMeeting.section_id)))
            .filter(
                CourseMeeting.timetable_id == t.id,
                CourseMeeting.deleted_at.is_(None),
                CourseMeeting.status == "active",
            )
            .scalar()
            or 0
        )

        pub_ver_num = None
        if t.published_version:
            pub_ver_num = t.published_version.version_number
        elif t.published_version_id:
            pv = db.query(TimetableVersion.version_number).filter(TimetableVersion.id == t.published_version_id).first()
            if pv:
                pub_ver_num = pv[0]
        v_count = db.query(func.count(TimetableVersion.id)).filter(TimetableVersion.timetable_id == t.id).scalar() or 0

        results.append(
            TimetableOut(
                id=t.id,
                institution_id=t.institution_id,
                academic_term_id=t.academic_term_id,
                name=t.name,
                status=t.status,
                description=t.description,
                created_at=t.created_at,
                updated_at=t.updated_at,
                term_name=term.name if term else None,
                academic_year=term.academic_year if term else None,
                meetings_count=m_count,
                sections_count=sec_count,
                published_version_id=t.published_version_id,
                published_version_number=pub_ver_num,
                versions_count=v_count,
            )
        )

    return DataResponse(data=results)


@router.post("/{institution_id}/timetables", response_model=DataResponse[TimetableOut], status_code=status.HTTP_201_CREATED)
def create_timetable(
    body: TimetableCreate,
    institution_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Create a new university baseline timetable. Restricted to ADMIN."""
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

    name_clean = body.name.strip()
    if not name_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_name", "message": "Timetable name cannot be empty"},
        )

    # Check unique constraint (institution_id, academic_term_id, name)
    existing = (
        db.query(Timetable)
        .filter(
            Timetable.institution_id == context.institution_id,
            Timetable.academic_term_id == body.academic_term_id,
            func.lower(Timetable.name) == name_clean.lower(),
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "timetable_exists", "message": f"A timetable named '{name_clean}' already exists for this term"},
        )

    new_status = body.status or "draft"
    if new_status == "active":
        # Deactivate any other active timetable for this term
        db.query(Timetable).filter(
            Timetable.institution_id == context.institution_id,
            Timetable.academic_term_id == body.academic_term_id,
            Timetable.status == "active",
        ).update({"status": "draft"})

    timetable = Timetable(
        institution_id=context.institution_id,
        academic_term_id=body.academic_term_id,
        name=name_clean,
        description=body.description.strip() if body.description else None,
        status=new_status,
    )
    db.add(timetable)
    db.commit()
    db.refresh(timetable)

    # Automatically create initial Version 1 for the new timetable
    v1 = get_or_create_initial_version(db, context.institution_id, timetable.id)
    db.refresh(timetable)

    return DataResponse(
        data=TimetableOut(
            id=timetable.id,
            institution_id=timetable.institution_id,
            academic_term_id=timetable.academic_term_id,
            name=timetable.name,
            status=timetable.status,
            description=timetable.description,
            created_at=timetable.created_at,
            updated_at=timetable.updated_at,
            term_name=term.name,
            academic_year=term.academic_year,
            meetings_count=0,
            sections_count=0,
            published_version_id=timetable.published_version_id,
            published_version_number=1 if timetable.published_version_id else None,
            versions_count=1,
        )
    )



@router.get("/{institution_id}/timetables/{timetable_id}", response_model=DataResponse[TimetableOut])
def get_timetable(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """Get timetable details with metrics."""
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    term = db.query(AcademicTerm).filter(AcademicTerm.id == t.academic_term_id).first()
    m_count = (
        db.query(func.count(CourseMeeting.id))
        .filter(
            CourseMeeting.timetable_id == t.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )
    sec_count = (
        db.query(func.count(func.distinct(CourseMeeting.section_id)))
        .filter(
            CourseMeeting.timetable_id == t.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )

    pub_ver_num = None
    if t.published_version:
        pub_ver_num = t.published_version.version_number
    elif t.published_version_id:
        pv = db.query(TimetableVersion.version_number).filter(TimetableVersion.id == t.published_version_id).first()
        if pv:
            pub_ver_num = pv[0]
    v_count = db.query(func.count(TimetableVersion.id)).filter(TimetableVersion.timetable_id == t.id).scalar() or 0

    return DataResponse(
        data=TimetableOut(
            id=t.id,
            institution_id=t.institution_id,
            academic_term_id=t.academic_term_id,
            name=t.name,
            status=t.status,
            description=t.description,
            created_at=t.created_at,
            updated_at=t.updated_at,
            term_name=term.name if term else None,
            academic_year=term.academic_year if term else None,
            meetings_count=m_count,
            sections_count=sec_count,
            published_version_id=t.published_version_id,
            published_version_number=pub_ver_num,
            versions_count=v_count,
        )
    )


@router.patch("/{institution_id}/timetables/{timetable_id}", response_model=DataResponse[TimetableOut])
def update_timetable(
    body: TimetableUpdate,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Update timetable metadata or status. Restricted to ADMIN."""
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    if body.name is not None:
        name_clean = body.name.strip()
        if not name_clean:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_name", "message": "Timetable name cannot be empty"},
            )
        # Check unique constraint
        existing = (
            db.query(Timetable)
            .filter(
                Timetable.institution_id == context.institution_id,
                Timetable.academic_term_id == t.academic_term_id,
                func.lower(Timetable.name) == name_clean.lower(),
                Timetable.id != t.id,
                Timetable.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "timetable_exists", "message": f"A timetable named '{name_clean}' already exists for this term"},
            )
        t.name = name_clean

    if body.description is not None:
        t.description = body.description.strip() or None

    if body.status is not None:
        if body.status == "active":
            # Demote any other active timetables for this term to draft
            db.query(Timetable).filter(
                Timetable.institution_id == context.institution_id,
                Timetable.academic_term_id == t.academic_term_id,
                Timetable.id != t.id,
                Timetable.status == "active",
            ).update({"status": "draft"})
        t.status = body.status

    db.commit()
    db.refresh(t)

    term = db.query(AcademicTerm).filter(AcademicTerm.id == t.academic_term_id).first()
    m_count = (
        db.query(func.count(CourseMeeting.id))
        .filter(
            CourseMeeting.timetable_id == t.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )
    sec_count = (
        db.query(func.count(func.distinct(CourseMeeting.section_id)))
        .filter(
            CourseMeeting.timetable_id == t.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )

    pub_ver_num = None
    if t.published_version:
        pub_ver_num = t.published_version.version_number
    elif t.published_version_id:
        pv = db.query(TimetableVersion.version_number).filter(TimetableVersion.id == t.published_version_id).first()
        if pv:
            pub_ver_num = pv[0]
    v_count = db.query(func.count(TimetableVersion.id)).filter(TimetableVersion.timetable_id == t.id).scalar() or 0

    return DataResponse(
        data=TimetableOut(
            id=t.id,
            institution_id=t.institution_id,
            academic_term_id=t.academic_term_id,
            name=t.name,
            status=t.status,
            description=t.description,
            created_at=t.created_at,
            updated_at=t.updated_at,
            term_name=term.name if term else None,
            academic_year=term.academic_year if term else None,
            meetings_count=m_count,
            sections_count=sec_count,
            published_version_id=t.published_version_id,
            published_version_number=pub_ver_num,
            versions_count=v_count,
        )
    )


@router.delete("/{institution_id}/timetables/{timetable_id}", response_model=DataResponse[DeletedData])
def delete_timetable(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete / archive a baseline timetable. Restricted to ADMIN."""
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    t.deleted_at = func.now()
    t.status = "archived"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ── Timetable Version Endpoints (Task N7) ─────────────────────────────────────

@router.get("/{institution_id}/timetables/{timetable_id}/versions", response_model=DataResponse[List[TimetableVersionOut]])
def list_versions(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """List all versions for this timetable."""
    tt = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    # Ensure baseline initial version exists
    get_or_create_initial_version(db, context.institution_id, timetable_id)

    versions = (
        db.query(TimetableVersion)
        .options(joinedload(TimetableVersion.creator))
        .filter(
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == context.institution_id,
            TimetableVersion.deleted_at.is_(None),
        )
        .order_by(TimetableVersion.version_number.desc())
        .all()
    )

    results: List[TimetableVersionOut] = []
    for v in versions:
        m_count = (
            db.query(func.count(CourseMeeting.id))
            .filter(
                CourseMeeting.version_id == v.id,
                CourseMeeting.deleted_at.is_(None),
                CourseMeeting.status == "active",
            )
            .scalar()
            or 0
        )
        s_count = (
            db.query(func.count(func.distinct(CourseMeeting.section_id)))
            .filter(
                CourseMeeting.version_id == v.id,
                CourseMeeting.deleted_at.is_(None),
                CourseMeeting.status == "active",
            )
            .scalar()
            or 0
        )
        results.append(_enrich_version_out(v, tt.published_version_id, m_count, s_count))

    return DataResponse(data=results)


@router.post("/{institution_id}/timetables/{timetable_id}/versions", response_model=DataResponse[TimetableVersionOut], status_code=status.HTTP_201_CREATED)
def create_new_version(
    body: TimetableVersionCreate,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Create a new timetable version (draft). Clones meetings from source/published version."""
    new_ver = create_version(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        user_id=context.user_id,
        data=body,
    )
    m_count = (
        db.query(func.count(CourseMeeting.id))
        .filter(
            CourseMeeting.version_id == new_ver.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )
    s_count = (
        db.query(func.count(func.distinct(CourseMeeting.section_id)))
        .filter(
            CourseMeeting.version_id == new_ver.id,
            CourseMeeting.deleted_at.is_(None),
            CourseMeeting.status == "active",
        )
        .scalar()
        or 0
    )
    return DataResponse(data=_enrich_version_out(new_ver, None, m_count, s_count))


@router.get("/{institution_id}/timetables/{timetable_id}/versions/compare", response_model=DataResponse[VersionComparisonOut])
def compare_timetable_versions(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    base_version_id: int = Query(..., description="Base version ID (e.g. V1)"),
    target_version_id: int = Query(..., description="Target version ID (e.g. V2)"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """Compare two versions: returns human-readable changes and N6 student ripple effects."""
    comparison = compare_versions(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        base_version_id=base_version_id,
        target_version_id=target_version_id,
    )
    return DataResponse(data=comparison)


@router.get("/{institution_id}/timetables/{timetable_id}/versions/{version_id}", response_model=DataResponse[TimetableVersionOut])
def get_version(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """Get details of a specific timetable version."""
    tt = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not tt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found"},
        )
    v = (
        db.query(TimetableVersion)
        .options(joinedload(TimetableVersion.creator))
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == context.institution_id,
            TimetableVersion.deleted_at.is_(None),
        )
        .first()
    )
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )
    m_count = (
        db.query(func.count(CourseMeeting.id))
        .filter(CourseMeeting.version_id == v.id, CourseMeeting.deleted_at.is_(None), CourseMeeting.status == "active")
        .scalar()
        or 0
    )
    s_count = (
        db.query(func.count(func.distinct(CourseMeeting.section_id)))
        .filter(CourseMeeting.version_id == v.id, CourseMeeting.deleted_at.is_(None), CourseMeeting.status == "active")
        .scalar()
        or 0
    )
    return DataResponse(data=_enrich_version_out(v, tt.published_version_id, m_count, s_count))


@router.patch("/{institution_id}/timetables/{timetable_id}/versions/{version_id}", response_model=DataResponse[TimetableVersionOut])
def update_version(
    body: TimetableVersionUpdate,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Update version name or change summary. Restricted to ADMIN."""
    v = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == context.institution_id,
            TimetableVersion.deleted_at.is_(None),
        )
        .first()
    )
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )
    if body.name is not None:
        v.name = body.name.strip()
    if body.change_summary is not None:
        v.change_summary = body.change_summary.strip()
    db.commit()
    db.refresh(v)
    return DataResponse(data=_enrich_version_out(v))


@router.get("/{institution_id}/timetables/{timetable_id}/versions/{version_id}/checklist", response_model=DataResponse[VersionChecklistOut])
def get_version_checklist(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """Runs safety checklist for this version (blocking issues, warnings, room & faculty checks)."""
    checklist = run_version_checklist(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        version_id=version_id,
    )
    return DataResponse(data=checklist)


@router.post("/{institution_id}/timetables/{timetable_id}/versions/{version_id}/review", response_model=DataResponse[TimetableVersionOut])
def submit_version_for_review(
    body: Optional[SubmitReviewRequest] = None,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Submits draft version for review: DRAFT -> IN_REVIEW. Verifies 0 blocking issues."""
    notes = body.notes if body else None
    ver = submit_for_review(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        version_id=version_id,
        user_id=context.user_id,
        notes=notes,
        request=request,
    )
    return DataResponse(data=_enrich_version_out(ver))


@router.post("/{institution_id}/timetables/{timetable_id}/versions/{version_id}/approve", response_model=DataResponse[TimetableVersionOut])
def approve_timetable_version(
    body: Optional[ApproveVersionRequest] = None,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Approves timetable version: IN_REVIEW -> APPROVED. Verifies 0 blocking issues."""
    notes = body.notes if body else None
    ver = approve_version(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        version_id=version_id,
        user_id=context.user_id,
        notes=notes,
        request=request,
    )
    return DataResponse(data=_enrich_version_out(ver))


@router.post("/{institution_id}/timetables/{timetable_id}/versions/{version_id}/publish", response_model=DataResponse[PublishVersionResponse])
def publish_timetable_version(
    body: Optional[PublishVersionRequest] = None,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Atomically publishes timetable version: APPROVED -> PUBLISHED. Archives previous published version."""
    expected_updated_at = body.expected_updated_at if body else None
    notes = body.notes if body else None
    ver, archived_id = publish_version(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        version_id=version_id,
        user_id=context.user_id,
        expected_updated_at=expected_updated_at,
        notes=notes,
        request=request,
    )
    from datetime import datetime, timezone
    return DataResponse(
        data=PublishVersionResponse(
            success=True,
            message=f"Successfully published Version {ver.version_number}",
            published_version=_enrich_version_out(ver, ver.id),
            archived_version_id=archived_id,
            published_at=ver.published_at or datetime.now(timezone.utc),
        )
    )


@router.post("/{institution_id}/timetables/{timetable_id}/versions/{version_id}/archive", response_model=DataResponse[TimetableVersionOut])
def archive_timetable_version(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Archives an older or unused timetable version."""
    ver = (
        db.query(TimetableVersion)
        .filter(
            TimetableVersion.id == version_id,
            TimetableVersion.timetable_id == timetable_id,
            TimetableVersion.institution_id == context.institution_id,
            TimetableVersion.deleted_at.is_(None),
        )
        .first()
    )
    if not ver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": f"Version {version_id} not found"},
        )
    if ver.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "cannot_archive_published", "message": "Cannot manually archive the currently published version directly without publishing another version."},
        )
    from datetime import datetime, timezone
    ver.status = "archived"
    ver.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ver)
    return DataResponse(data=_enrich_version_out(ver))


# ── Course Meeting Endpoints ──────────────────────────────────────────────────

@router.get("/{institution_id}/timetables/{timetable_id}/meetings", response_model=DataResponse[List[CourseMeetingOut]])
def list_meetings(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    version_id: Optional[int] = Query(None, description="Filter by version ID"),
    section_id: Optional[int] = Query(None, description="Filter by section ID"),
    day_of_week: Optional[int] = Query(None, ge=0, le=6, description="Filter by day of week"),
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """List all course meetings for the given timetable with enriched details."""
    # Verify timetable exists and belongs to institution
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    query = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.timetable_id == t.id,
            CourseMeeting.institution_id == context.institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
    )

    if version_id is not None:
        query = query.filter(CourseMeeting.version_id == version_id)
    elif t.published_version_id is not None:
        query = query.filter((CourseMeeting.version_id == t.published_version_id) | (CourseMeeting.version_id.is_(None)))


    if section_id is not None:
        query = query.filter(CourseMeeting.section_id == section_id)
    if day_of_week is not None:
        query = query.filter(CourseMeeting.day_of_week == day_of_week)
    if room_id is not None:
        query = query.filter(CourseMeeting.room_id == room_id)

    meetings = query.order_by(CourseMeeting.day_of_week, CourseMeeting.start_time).all()
    return DataResponse(data=[_enrich_meeting_out(m) for m in meetings])


@router.post("/{institution_id}/timetables/{timetable_id}/meetings", response_model=DataResponse[CourseMeetingOut], status_code=status.HTTP_201_CREATED)
def create_meeting(
    body: CourseMeetingCreate,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Create a new course meeting in the baseline timetable with full conflict/capacity validation. Restricted to ADMIN."""
    target_version_id = body.version_id
    if target_version_id is None:
        tt_obj = db.query(Timetable).filter(Timetable.id == timetable_id, Timetable.institution_id == context.institution_id, Timetable.deleted_at.is_(None)).first()
        if tt_obj and tt_obj.published_version_id:
            target_version_id = tt_obj.published_version_id
        else:
            v_init = get_or_create_initial_version(db, context.institution_id, timetable_id)
            target_version_id = v_init.id


    start_time, end_time, section, timetable, room, faculty = validate_course_meeting(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        section_id=body.section_id,
        day_of_week=body.day_of_week,
        start_time_val=body.start_time,
        end_time_val=body.end_time,
        room_id=body.room_id,
        faculty_id=body.faculty_id,
        version_id=target_version_id,
    )

    meeting = CourseMeeting(
        institution_id=context.institution_id,
        timetable_id=timetable.id,
        version_id=target_version_id,
        section_id=section.id,
        academic_term_id=timetable.academic_term_id,
        day_of_week=body.day_of_week,
        start_time=start_time,
        end_time=end_time,
        room_id=room.id if room else None,
        faculty_id=faculty.id if faculty else None,
        meeting_type=body.meeting_type or "lecture",
        status=body.status or "active",
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)


    # Re-query with eager relationships for output
    meeting_loaded = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(CourseMeeting.id == meeting.id)
        .first()
    )

    return DataResponse(data=_enrich_meeting_out(meeting_loaded))


@router.get("/{institution_id}/timetables/{timetable_id}/meetings/{meeting_id}", response_model=DataResponse[CourseMeetingOut])
def get_meeting(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    meeting_id: int = Path(...),
    context: InstitutionContext = Depends(get_institution_context),
    db: Session = Depends(get_db),
):
    """Get details for a specific course meeting."""
    meeting = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.id == meeting_id,
            CourseMeeting.timetable_id == timetable_id,
            CourseMeeting.institution_id == context.institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {meeting_id} not found"},
        )

    return DataResponse(data=_enrich_meeting_out(meeting))


@router.patch("/{institution_id}/timetables/{timetable_id}/meetings/{meeting_id}", response_model=DataResponse[CourseMeetingOut])
def update_meeting(
    body: CourseMeetingUpdate,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    meeting_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Update a course meeting with full revalidation. Restricted to ADMIN."""
    meeting = (
        db.query(CourseMeeting)
        .filter(
            CourseMeeting.id == meeting_id,
            CourseMeeting.timetable_id == timetable_id,
            CourseMeeting.institution_id == context.institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {meeting_id} not found"},
        )

    target_day = body.day_of_week if body.day_of_week is not None else meeting.day_of_week
    target_start = body.start_time if body.start_time is not None else meeting.start_time
    target_end = body.end_time if body.end_time is not None else meeting.end_time
    target_room_id = body.room_id if body.room_id is not None else meeting.room_id
    if body.room_id == 0:
        target_room_id = None
    target_faculty_id = body.faculty_id if body.faculty_id is not None else meeting.faculty_id
    if body.faculty_id == 0:
        target_faculty_id = None

    start_time, end_time, section, timetable, room, faculty = validate_course_meeting(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        section_id=meeting.section_id,
        day_of_week=target_day,
        start_time_val=target_start,
        end_time_val=target_end,
        room_id=target_room_id,
        faculty_id=target_faculty_id,
        existing_meeting_id=meeting.id,
    )

    meeting.day_of_week = target_day
    meeting.start_time = start_time
    meeting.end_time = end_time
    meeting.room_id = room.id if room else None
    meeting.faculty_id = faculty.id if faculty else None
    if body.meeting_type is not None:
        meeting.meeting_type = body.meeting_type
    if body.status is not None:
        meeting.status = body.status

    db.commit()
    db.refresh(meeting)

    meeting_loaded = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(CourseMeeting.id == meeting.id)
        .first()
    )

    return DataResponse(data=_enrich_meeting_out(meeting_loaded))


@router.delete("/{institution_id}/timetables/{timetable_id}/meetings/{meeting_id}", response_model=DataResponse[DeletedData])
def delete_meeting(
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    meeting_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Soft-delete / remove a course meeting from the baseline timetable. Restricted to ADMIN."""
    meeting = (
        db.query(CourseMeeting)
        .filter(
            CourseMeeting.id == meeting_id,
            CourseMeeting.timetable_id == timetable_id,
            CourseMeeting.institution_id == context.institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {meeting_id} not found"},
        )

    meeting.deleted_at = func.now()
    meeting.status = "cancelled"
    db.commit()

    return DataResponse(data=DeletedData(deleted=True))


# ── Task N6 University Timetable Editor & Impact Analysis Endpoints ─────────

@router.post(
    "/{institution_id}/timetables/{timetable_id}/changes/preview",
    response_model=DataResponse[TimetableImpactResponse],
)
def preview_timetable_change(
    body: TimetableChangeProposal,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Validates a proposed course meeting change and calculates deterministic impact
    on enrolled students, room, and faculty. Strictly read-only. Restricted to ADMIN.
    """
    # Verify timetable exists and belongs to this institution
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    impact = analyze_timetable_change(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        proposal=body,
    )
    return DataResponse(data=impact)


@router.post(
    "/{institution_id}/timetables/{timetable_id}/changes/apply",
    response_model=DataResponse[TimetableChangeApplyResponse],
)
def apply_timetable_change(
    body: TimetableChangeApplyRequest,
    institution_id: int = Path(...),
    timetable_id: int = Path(...),
    request: Request = None,
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Safely applies an explicitly confirmed timetable change.
    - Re-validates current timetable and meeting state.
    - Protects against stale concurrent updates via expected_updated_at.
    - Applies atomically in database transaction.
    - Records audit log entry with before/after and impact summary metadata.
    Restricted to ADMIN.
    """
    # 1. Verify timetable
    t = (
        db.query(Timetable)
        .filter(
            Timetable.id == timetable_id,
            Timetable.institution_id == context.institution_id,
            Timetable.deleted_at.is_(None),
        )
        .first()
    )
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "timetable_not_found", "message": f"Timetable {timetable_id} not found in this institution"},
        )

    # 2. Fetch existing meeting
    meeting = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(
            CourseMeeting.id == body.meeting_id,
            CourseMeeting.timetable_id == timetable_id,
            CourseMeeting.institution_id == context.institution_id,
            CourseMeeting.deleted_at.is_(None),
        )
        .first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "meeting_not_found", "message": f"Course meeting {body.meeting_id} not found in this timetable"},
        )

    # 3. Concurrency Protection (Check expected_updated_at if provided)
    if body.expected_updated_at is not None and meeting.updated_at is not None:
        # Compare timestamps (allow tolerance < 1 second for datetime formatting differences)
        from datetime import timezone
        dt_meeting = meeting.updated_at
        dt_expected = body.expected_updated_at
        if dt_meeting.tzinfo is None:
            dt_meeting = dt_meeting.replace(tzinfo=timezone.utc)
        if dt_expected.tzinfo is None:
            dt_expected = dt_expected.replace(tzinfo=timezone.utc)

        time_diff = abs((dt_meeting - dt_expected).total_seconds())
        if time_diff > 1.0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "stale_preview",
                    "message": "This timetable changed since you reviewed it. Please review the new version before applying your change.",
                },
            )

    # 4. Calculate final impact before mutating
    proposal = TimetableChangeProposal(
        meeting_id=body.meeting_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        room_id=body.room_id,
        faculty_id=body.faculty_id,
        meeting_type=body.meeting_type,
    )
    impact = analyze_timetable_change(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        proposal=proposal,
    )

    if impact.is_blocked:
        reason_msg = "; ".join(impact.summary.blocked_reasons) if impact.summary.blocked_reasons else "Hard constraint violation"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "change_blocked", "message": f"Cannot apply blocked change: {reason_msg}"},
        )

    # 5. Full authoritative revalidation
    target_room_id = body.room_id if body.room_id is not None else meeting.room_id
    if body.room_id == 0:
        target_room_id = None
    target_faculty_id = body.faculty_id if body.faculty_id is not None else meeting.faculty_id
    if body.faculty_id == 0:
        target_faculty_id = None

    start_time, end_time, section, timetable, room, faculty = validate_course_meeting(
        db=db,
        institution_id=context.institution_id,
        timetable_id=timetable_id,
        section_id=meeting.section_id,
        day_of_week=body.day_of_week,
        start_time_val=body.start_time,
        end_time_val=body.end_time,
        room_id=target_room_id,
        faculty_id=target_faculty_id,
        existing_meeting_id=meeting.id,
    )

    # 6. Apply change atomically
    before_day = meeting.day_of_week
    before_start = format_time_str(meeting.start_time)
    before_end = format_time_str(meeting.end_time)

    meeting.day_of_week = body.day_of_week
    meeting.start_time = start_time
    meeting.end_time = end_time
    meeting.room_id = room.id if room else None
    meeting.faculty_id = faculty.id if faculty else None
    if body.meeting_type is not None:
        meeting.meeting_type = body.meeting_type

    db.commit()
    db.refresh(meeting)

    # 7. Record Audit Log Foundation for N7
    sec_code = section.section_code if section else ""
    crs_code = section.course.code if section and section.course else ""
    audit_desc = (
        f"Modified class meeting {crs_code} {sec_code}: "
        f"{DAY_NAMES.get(before_day, '')} {before_start}–{before_end} → "
        f"{DAY_NAMES.get(body.day_of_week, '')} {format_time_str(start_time)}–{format_time_str(end_time)}"
    )
    audit_meta = {
        "institution_id": context.institution_id,
        "timetable_id": timetable_id,
        "section_id": section.id if section else None,
        "course_code": crs_code,
        "before": {
            "day_of_week": before_day,
            "start_time": before_start,
            "end_time": before_end,
            "room_id": impact.before.room_id,
            "faculty_id": impact.before.faculty_id,
        },
        "after": {
            "day_of_week": body.day_of_week,
            "start_time": format_time_str(start_time),
            "end_time": format_time_str(end_time),
            "room_id": impact.after.room_id,
            "faculty_id": impact.after.faculty_id,
        },
        "impact": {
            "severity": impact.summary.severity,
            "students_affected": impact.summary.students_affected,
            "new_conflicts": impact.summary.new_conflicts,
            "resolved_conflicts": impact.summary.resolved_conflicts,
        },
    }
    record_audit_log(
        db=db,
        user_id=context.user_id,
        action="timetable_meeting_change",
        entity_type="course_meeting",
        entity_id=meeting.id,
        description=audit_desc,
        metadata=audit_meta,
        request=request,
    )

    # 8. Reload meeting for output
    meeting_loaded = (
        db.query(CourseMeeting)
        .options(
            joinedload(CourseMeeting.section).joinedload(AcademicSection.course),
            joinedload(CourseMeeting.section).joinedload(AcademicSection.faculty_assignments).joinedload(SectionFacultyAssignment.faculty).joinedload(FacultyProfile.user),
            joinedload(CourseMeeting.room),
            joinedload(CourseMeeting.faculty).joinedload(FacultyProfile.user),
        )
        .filter(CourseMeeting.id == meeting.id)
        .first()
    )

    meeting_out = _enrich_meeting_out(meeting_loaded)
    from datetime import datetime, timezone
    applied_time = datetime.now(timezone.utc)

    return DataResponse(
        data=TimetableChangeApplyResponse(
            success=True,
            message=f"Successfully updated meeting for {crs_code} ({sec_code})",
            meeting=meeting_out,
            impact_summary=impact.summary,
            applied_at=applied_time,
        )
    )
