"""
University Analytics Router for Task N10 — University Analytics & Decision Dashboard.

Provides secure, tenant-isolated, term-aware analytics endpoints for university administrators.
Enforces institutional role-based access control (only institution admins / super admins).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import InstitutionContext, require_institution_admin
from app.models.academic_term import AcademicTerm
from app.models.department import Department
from app.schemas.university_analytics import (
    AnalyticsOverviewKPIs,
    DepartmentComparisonItem,
    EnrollmentAnalyticsData,
    FacultyAnalyticsData,
    RoomAnalyticsData,
    TimetableHealthAnalyticsData,
    UniversityDashboardAnalyticsResponse,
)
from app.services import university_analytics_service

router = APIRouter(
    prefix="/institutions/{institution_id}/analytics",
    tags=["University Analytics"],
)


def _validate_filters(
    db: Session,
    institution_id: int,
    term_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> None:
    """Validates that term_id and department_id belong to the requested institution (tenant isolation)."""
    if term_id is not None:
        term = (
            db.query(AcademicTerm)
            .filter(
                AcademicTerm.id == term_id,
                AcademicTerm.institution_id == institution_id,
                AcademicTerm.deleted_at.is_(None),
            )
            .first()
        )
        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "term_not_found", "message": f"Academic term {term_id} not found in this institution"},
            )

    if department_id is not None:
        dept = (
            db.query(Department)
            .filter(
                Department.id == department_id,
                Department.institution_id == institution_id,
                Department.deleted_at.is_(None),
            )
            .first()
        )
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "department_not_found", "message": f"Department {department_id} not found in this institution"},
            )


@router.get(
    "/dashboard",
    response_model=UniversityDashboardAnalyticsResponse,
    summary="Get unified university analytics dashboard",
)
def get_dashboard_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID (defaults to active term)"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """
    Returns the comprehensive university decision dashboard analytics for the institution.
    Provides overview KPIs, enrollment demand, scheduled room usage, faculty schedules,
    timetable health/conflicts, and departmental comparisons.
    """
    _validate_filters(db, context.institution_id, term_id, department_id)
    return university_analytics_service.get_full_university_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
        department_id=department_id,
    )


@router.get(
    "/overview",
    response_model=AnalyticsOverviewKPIs,
    summary="Get overview KPI analytics",
)
def get_overview_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns top-level KPI metrics for the institution."""
    _validate_filters(db, context.institution_id, term_id=term_id)
    return university_analytics_service.get_university_overview_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
    )


@router.get(
    "/enrollment",
    response_model=EnrollmentAnalyticsData,
    summary="Get enrollment demand and capacity analytics",
)
def get_enrollment_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns section capacity utilization and identifies high-demand and low-utilization sections."""
    _validate_filters(db, context.institution_id, term_id, department_id)
    return university_analytics_service.get_enrollment_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
        department_id=department_id,
    )


@router.get(
    "/rooms",
    response_model=RoomAnalyticsData,
    summary="Get scheduled room utilization analytics",
)
def get_rooms_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns scheduled room utilization based strictly on timetable meetings."""
    _validate_filters(db, context.institution_id, term_id, department_id)
    return university_analytics_service.get_room_utilization_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
        department_id=department_id,
    )


@router.get(
    "/faculty",
    response_model=FacultyAnalyticsData,
    summary="Get faculty teaching load and schedule analytics",
)
def get_faculty_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns neutral operational teaching load and schedule conflict analytics for faculty."""
    _validate_filters(db, context.institution_id, term_id, department_id)
    return university_analytics_service.get_faculty_schedule_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
        department_id=department_id,
    )


@router.get(
    "/timetable",
    response_model=TimetableHealthAnalyticsData,
    summary="Get timetable health and conflict analytics",
)
def get_timetable_health_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns collision counts (room, faculty, student class, work shifts) and version change history."""
    _validate_filters(db, context.institution_id, term_id=term_id)
    return university_analytics_service.get_timetable_health_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
    )


@router.get(
    "/departments",
    response_model=List[DepartmentComparisonItem],
    summary="Get departmental comparison analytics",
)
def get_departments_analytics(
    institution_id: int,
    term_id: Optional[int] = Query(None, description="Filter by academic term ID"),
    context: InstitutionContext = Depends(require_institution_admin),
    db: Session = Depends(get_db),
):
    """Returns operational metric comparisons across departments."""
    _validate_filters(db, context.institution_id, term_id=term_id)
    return university_analytics_service.get_department_comparison_analytics(
        db=db,
        institution_id=context.institution_id,
        term_id=term_id,
    )
