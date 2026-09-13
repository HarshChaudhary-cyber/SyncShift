"""
Analytics & Schedule Health Router
Endpoints:
- GET /api/v1/analytics/week
- GET /api/v1/analytics
- GET /api/v1/analytics/health
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.analytics import AnalyticsData, ScheduleHealthData
from app.schemas.common import DataResponse
from app.services.analytics import compute_week_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics & Health"])


@router.get("", response_model=DataResponse[AnalyticsData])
@router.get("/week", response_model=DataResponse[AnalyticsData])
def get_week_analytics(
    start_date: Optional[date] = Query(
        None,
        description="Optional start date of target week (YYYY-MM-DD), defaults to Monday of current week",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns comprehensive schedule analytics for the student:
    - Weekly hours breakdown (Class, Work, Study, Total, Free)
    - Work-hour utilization against configured limit
    - Shift earnings (using student's profile currency)
    - Monday–Sunday daily workload breakdown & heavy day warnings
    - Deterministic Schedule Health Score & factor breakdown
    """
    analytics = compute_week_analytics(
        current_user=current_user,
        week_start=start_date,
        db=db,
    )
    return DataResponse(data=analytics)


@router.get("/health", response_model=DataResponse[ScheduleHealthData])
def get_schedule_health(
    start_date: Optional[date] = Query(
        None,
        description="Optional start date of target week (YYYY-MM-DD)",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the deterministic Schedule Health Score and breakdown for the requested week.
    """
    analytics = compute_week_analytics(
        current_user=current_user,
        week_start=start_date,
        db=db,
    )
    return DataResponse(data=analytics.health)
