from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.week import WeekViewData
from app.store import detect_conflicts_and_totals, get_occurrences_for_range
from sqlalchemy.orm import Session

router = APIRouter(prefix="/week", tags=["Week View"])


@router.get("", response_model=DataResponse[WeekViewData])
def get_week_schedule(
    start: date = Query(..., description="Start date of the target week (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Convenience endpoint returning everything the calendar UI needs in one call:
    - Active materialized occurrences for the requested week (including biweekly & single exceptions)
    - Detected conflicts for this week's active occurrences
    - Weekly shift/class totals and visa work limit compliance
    """
    end_date = start + timedelta(days=6)
    blocks = get_occurrences_for_range(
        user_id=current_user.user_id,
        start_date=start,
        end_date=end_date,
        db=db,
    )
    conflicts, totals = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=current_user.weekly_work_hour_limit or 20.0,
        week_start=start,
        db=db,
    )

    return DataResponse(
        data=WeekViewData(
            week_start=start,
            blocks=blocks,
            conflicts=conflicts,
            totals=totals,
        )
    )
