from datetime import date
from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.week import WeekViewData
from app.store import detect_conflicts_and_totals, get_all_blocks

router = APIRouter(prefix="/week", tags=["Week View"])


@router.get("", response_model=DataResponse[WeekViewData])
def get_week_schedule(
    start: date = Query(..., description="Start date of the target week (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Convenience endpoint returning everything the calendar UI needs in one call:
    - Active materialized time blocks from shared store
    - Detected conflicts
    - Weekly shift/class totals and visa work limit compliance
    """
    blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False)
    conflicts, totals = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=current_user.weekly_work_hour_limit or 20.0,
    )

    return DataResponse(
        data=WeekViewData(
            week_start=start,
            blocks=blocks,
            conflicts=conflicts,
            totals=totals,
        )
    )
