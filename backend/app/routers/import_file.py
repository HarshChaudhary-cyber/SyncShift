"""
import_file.py – router for the multi-format timetable import endpoints.

POST /api/v1/import/file         → parse any supported file, return preview
POST /api/v1/import/file/confirm → save approved blocks (reuses ICS confirm logic)
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.file_import import FilePreviewItem, FilePreviewResponseData
from app.schemas.import_ics import (
    IcsConfirmRequest,
    IcsConfirmResponseData,
)
from app.services.file_extractor import (
    SUPPORTED_READABLE,
    LEGACY_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    _ext,
    extract_text,
)
from app.services.text_extractor import text_to_blocks
from app.services.ics_parser import parse_ics_timetable

router = APIRouter(prefix="/import", tags=["File Import"])

_EMPTY_MESSAGE = (
    "Couldn't find a timetable in this file. "
    "Try a clearer export or enter classes manually."
)


@router.post("/file", response_model=DataResponse[FilePreviewResponseData])
async def preview_file_timetable(
    file: UploadFile = File(..., description="Timetable file (.ics, .pdf, .docx, .pptx, .txt, .csv, .jpg, .png)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Parse an uploaded timetable file of any supported type.

    - **.ics / .ical** – uses the existing iCalendar parser (recurring events only).
    - **.pdf** – extracts text and tables via pdfplumber.
    - **.docx** – extracts paragraphs and tables via python-docx.
    - **.pptx** – extracts text from all slides via python-pptx.
    - **.txt / .csv** – reads raw text.
    - **.jpg / .png** – runs OCR via pytesseract (best-effort; results flagged low-confidence).

    All paths return the same preview JSON shape. Nothing is saved here.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "missing_filename", "message": "Uploaded file has no filename"},
        )

    ext = _ext(file.filename)

    # ── Reject legacy formats ────────────────────────────────────────────────
    if ext in LEGACY_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "legacy_format",
                "message": (
                    f"Please save the file as .docx / .pptx and re-upload. "
                    f"Old binary formats ({ext}) cannot be parsed."
                ),
            },
        )

    # ── Reject unknown formats ───────────────────────────────────────────────
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_format",
                "message": f"Unsupported file type '{ext}'. Supported: {SUPPORTED_READABLE}",
            },
        )

    # ── Read file bytes ──────────────────────────────────────────────────────
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_file", "message": "Uploaded file is empty"},
        )

    # ── ICS: delegate to existing parser ────────────────────────────────────
    if ext in (".ics", ".ical"):
        try:
            ics_preview, _unmatched = parse_ics_timetable(content)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_ics", "message": f"Failed to parse .ics file: {exc}"},
            )

        if not ics_preview:
            return DataResponse(
                data=FilePreviewResponseData(
                    preview=[],
                    message="No weekly recurring events found in the uploaded .ics file.",
                )
            )

        # Wrap IcsPreviewItem → FilePreviewItem (confidence always high for ICS)
        wrapped: list[FilePreviewItem] = [
            FilePreviewItem(
                temp_id=item.temp_id,
                title=item.title,
                day_of_week=item.day_of_week,
                start_time=item.start_time,
                end_time=item.end_time,
                location=item.location,
                confidence="high",
                source_line="",
                course_code=item.course_code,
                notes=item.notes or "",
            )
            for item in ics_preview
        ]
        return DataResponse(data=FilePreviewResponseData(preview=wrapped))

    # ── All other file types ─────────────────────────────────────────────────
    try:
        raw_text, is_ocr = extract_text(content, file.filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "extraction_failed", "message": str(exc)},
        )

    # OCR returned empty (Tesseract not installed or image unreadable)
    if is_ocr and not raw_text.strip():
        return DataResponse(
            data=FilePreviewResponseData(
                preview=[],
                message=(
                    "OCR could not extract text from this image. "
                    "Make sure the image is clear and Tesseract OCR is installed, "
                    "or try a PDF / DOCX export instead."
                ),
            )
        )

    if not raw_text.strip():
        return DataResponse(
            data=FilePreviewResponseData(preview=[], message=_EMPTY_MESSAGE)
        )

    items = text_to_blocks(raw_text, is_ocr=is_ocr)

    message: str | None = None
    if not items:
        message = _EMPTY_MESSAGE

    return DataResponse(data=FilePreviewResponseData(preview=items, message=message))


@router.post("/file/confirm", response_model=DataResponse[IcsConfirmResponseData])
def confirm_file_import(
    body: IcsConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Commit previewed timetable blocks (from any file type) to the user's schedule.
    Identical logic to /import/ics/confirm — reuses the same store functions.
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
