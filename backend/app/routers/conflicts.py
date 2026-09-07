from datetime import date
from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.conflict import ConflictsResponseData
from app.store import detect_conflicts_and_totals

router = APIRouter(prefix="/conflicts", tags=["Conflicts"])


@router.get("", response_model=DataResponse[ConflictsResponseData])
def get_conflicts(
    week_start: date = Query(..., description="Start of the week to analyze (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Run conflict detection sweep for the active week using the shared block store.
    """
    conflicts, totals = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=current_user.weekly_work_hour_limit or 20.0,
    )

    return DataResponse(
        data=ConflictsResponseData(
            conflicts=conflicts,
            weekly_totals=totals,
        )
    )
