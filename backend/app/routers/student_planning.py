"""
Student Smart Planning Router
Prefix: /api/v1/students/me/planning

Endpoints for:
- POST /preview: Read-only smart planning generation (multi-option: balanced, focused, compact)
- POST /apply: Safe application of approved student-owned flexible items
- DELETE /revert: Reverting applied study blocks for a week window
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.planning import (
    PlanApplyRequest,
    PlanApplyResponse,
    PlanPreviewRequest,
    PlanPreviewResponse,
)
from app.services.smart_planner import SmartPlannerService

router = APIRouter(prefix="/students/me/planning", tags=["Student Smart Planning"])


@router.post("/preview", response_model=DataResponse[PlanPreviewResponse])
def preview_smart_plan(
    body: Optional[PlanPreviewRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyzes student's weekly commitments, authoritative university timetable meetings,
    work shifts, personal constraints, availability, and study goals.
    Returns up to 3 strategic, transparent planning options (Balanced Week, Deep Focus, Compact Schedule).
    Strictly read-only: mutates ZERO database records.
    """
    req = body or PlanPreviewRequest()
    preview = SmartPlannerService.preview_plan(
        user_id=current_user.user_id,
        request=req,
        db=db,
    )
    return DataResponse(data=preview)


@router.post("/apply", response_model=DataResponse[PlanApplyResponse])
def apply_smart_plan(
    body: PlanApplyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Applies the student's selected smart planning option:
    - Inserts approved study blocks into TimeBlock.
    - Updates associated StudyTask status to 'scheduled'.
    - Leaves official university class meetings and fixed commitments completely untouched.
    - Runs conflict engine post-application to verify clean zero-conflict schedule.
    """
    if not body.approved_new_blocks and not body.approved_moved_shifts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_plan", "message": "No approved blocks provided to apply."},
        )

    res = SmartPlannerService.apply_plan(
        user_id=current_user.user_id,
        request=body,
        db=db,
    )
    return DataResponse(data=res)


@router.delete("/revert", response_model=DataResponse[dict])
def revert_smart_plan(
    week_start: date = Query(..., description="Monday of the week to revert planned study blocks"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reverts planned study blocks for the target week.
    Restores study tasks to 'pending' if all blocks are removed.
    """
    res = SmartPlannerService.revert_plan(
        user_id=current_user.user_id,
        week_start=week_start,
        db=db,
    )
    return DataResponse(data=res)
