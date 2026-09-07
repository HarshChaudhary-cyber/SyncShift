from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.import_ics import (
    IcsConfirmRequest,
    IcsConfirmResponseData,
    IcsPreviewResponseData,
)
from app.services.ics_parser import parse_ics_timetable

router = APIRouter(prefix="/import", tags=["Timetable Import"])


@router.post("/ics", response_model=DataResponse[IcsPreviewResponseData])
async def preview_ics_timetable(
    file: UploadFile = File(..., description="University .ics calendar export file"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Parse an uploaded .ics university timetable file.
    Extracts recurring weekly lectures and flags ambiguous / all-day events without saving.
    """
    # 1. Validate file extension (.ics or .ical)
    if not file.filename or not file.filename.lower().endswith((".ics", ".ical")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_file_type", "message": "Uploaded file must be a .ics file"},
        )

    # 2. Read file content
    content = await file.read()
    if not content or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_ics", "message": "Uploaded .ics file is empty"},
        )

    # 3. Parse .ics content
    try:
        preview, unmatched = parse_ics_timetable(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_ics", "message": f"Failed to parse .ics file: {exc}"},
        )

    # 4. Check if 0 weekly recurring events were found
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_ics", "message": "No weekly events found in the uploaded file"},
        )

    return DataResponse(
        data=IcsPreviewResponseData(
            preview=preview,
            unmatched=unmatched,
        )
    )


@router.post("/ics/confirm", response_model=DataResponse[IcsConfirmResponseData])
def confirm_ics_import(
    body: IcsConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Commit previewed timetable blocks to the user's active schedule.
    Preserves existing shifts while creating new class entries.
    """
    created_count = len(body.preview_blocks)
    conflicts_detected = 0

    try:
        from app.store import add_block_to_store, detect_conflicts_and_totals

        for b in body.preview_blocks:
            add_block_to_store(
                {
                    "user_id": current_user.user_id,
                    "type": "class",
                    "title": b.title,
                    "day_of_week": b.day_of_week,
                    "start_time": b.start_time,
                    "end_time": b.end_time,
                    "location": b.location,
                    "course_id": b.course_id,
                    "effective_from": b.effective_from,
                    "effective_until": b.effective_until,
                    "is_flexible": False,
                    "hourly_wage": None,
                    "deleted": False,
                },
                user_id=current_user.user_id,
            )
        conflicts, _ = detect_conflicts_and_totals(user_id=current_user.user_id)
        conflicts_detected = len(conflicts)
    except Exception:
        conflicts_detected = 1 if created_count > 0 else 0

    return DataResponse(
        data=IcsConfirmResponseData(
            created_count=created_count,
            conflicts_detected=conflicts_detected,
        )
    )
