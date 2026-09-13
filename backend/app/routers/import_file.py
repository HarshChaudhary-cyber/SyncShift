"""
import_file.py – router for the multi-format timetable import endpoints.

POST /api/v1/import/file         → parse any supported file using Gemini 1.5 Flash, return preview
POST /api/v1/import/file/confirm → save approved blocks (reuses database confirm logic)
"""
import logging
import os
import re
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse
from app.schemas.file_import import FilePreviewItem, FilePreviewResponseData
from app.schemas.import_ics import (
    IcsConfirmRequest,
    IcsConfirmResponseData,
)
from app.services.audit import record_audit_log
from app.services.file_extractor import _ext
from app.services.gemini_timetable import (
    MAX_FILE_SIZE_BYTES,
    extract_timetable_with_gemini,
)
from app.services.ics_parser import parse_ics_timetable
from app.services.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

DANGEROUS_EXTENSIONS = {
    "exe", "sh", "bat", "cmd", "py", "js", "vbs", "ps1", "php", "bin", "dll",
    ".exe", ".sh", ".bat", ".cmd", ".py", ".js", ".vbs", ".ps1", ".php", ".bin", ".dll",
}


router = APIRouter(prefix="/import", tags=["File Import"])

# Allowed extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".ics",
    ".ical",
}

from datetime import date, time as dt_time
from app.database import get_db
from app.models.time_block import BlockStatus, BlockType, TimeBlock
from sqlalchemy.orm import Session

DAY_NAME_MAP = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def enrich_preview_items(
    preview_items: list[FilePreviewItem],
    user_id: int,
    db: Session,
) -> tuple[list[FilePreviewItem], int, int, int, int]:
    """
    Enriches candidate timetable entries with:
    - human-readable day_name
    - duplicate detection against existing user blocks
    - conflict detection against existing user shifts/classes
    - validation & review issue flags
    """
    existing_blocks = db.query(TimeBlock).filter(
        TimeBlock.user_id == user_id,
        TimeBlock.deleted == False,
    ).all()

    valid_count = 0
    review_count = 0
    duplicate_count = 0
    conflict_count = 0

    for item in preview_items:
        issues: list[str] = []
        if 0 <= item.day_of_week <= 6:
            item.day_name = DAY_NAME_MAP.get(item.day_of_week, "Monday")
        else:
            item.day_name = "Unknown"
            issues.append("Unknown day of week")

        # Parse candidate times to minutes
        s_parts = item.start_time.split(":") if item.start_time else []
        e_parts = item.end_time.split(":") if item.end_time else []
        if len(s_parts) == 2 and len(e_parts) == 2:
            try:
                cand_s = int(s_parts[0]) * 60 + int(s_parts[1])
                cand_e = int(e_parts[0]) * 60 + int(e_parts[1])
            except ValueError:
                cand_s, cand_e = -1, -1
                issues.append("Invalid time values")
        else:
            cand_s, cand_e = -1, -1
            issues.append("Missing time information")

        # SyncShift standard day index for TimeBlock comparison (1=Mon ... 0=Sun)
        sync_dow = (item.day_of_week + 1) % 7 if item.day_of_week >= 0 else -1

        is_dup = False
        dup_reason = None
        has_conf = False
        conf_desc = None

        if cand_s >= 0 and cand_e >= 0 and sync_dow >= 0:
            for b in existing_blocks:
                # Compare against both sync_dow and direct day_of_week
                if b.day_of_week not in (sync_dow, item.day_of_week):
                    continue

                b_s = b.start_time.hour * 60 + b.start_time.minute
                b_e = b.end_time.hour * 60 + b.end_time.minute
                b_type_str = str(b.type.value if hasattr(b.type, "value") else b.type)
                b_start_str = b.start_time.strftime("%H:%M")
                b_end_str = b.end_time.strftime("%H:%M")

                # Duplicate test: identical or near identical times and title/course
                if b_s == cand_s and b_e == cand_e:
                    title_norm = b.title.lower().strip()
                    cand_title_norm = item.title.lower().strip()
                    code_match = item.course_code and item.course_code.lower() in title_norm
                    if title_norm == cand_title_norm or code_match:
                        is_dup = True
                        dup_reason = f"Matches existing {b_type_str} '{b.title}' ({b_start_str}–{b_end_str})"
                        issues.append(dup_reason)
                        break

                # Overlap conflict test: cand_s < b_e and b_s < cand_e
                if cand_s < b_e and b_s < cand_e:
                    has_conf = True
                    conf_desc = f"Conflicts with {b_type_str} '{b.title}' ({b_start_str}–{b_end_str})"
                    issues.append(conf_desc)

        if item.confidence == "low":
            issues.append("Low confidence extraction — verify times")

        item.is_duplicate = is_dup
        item.duplicate_reason = dup_reason
        item.has_conflict = has_conf
        item.conflict_description = conf_desc
        item.issues = issues

        if has_conf:
            item.status = "conflict"
            conflict_count += 1
        elif is_dup:
            item.status = "duplicate"
            duplicate_count += 1
        elif item.confidence == "low" or len(issues) > 0:
            item.status = "needs_review"
            review_count += 1
        else:
            item.status = "valid"
            valid_count += 1

    return preview_items, valid_count, review_count, duplicate_count, conflict_count


LEGACY_REJECTED = {".doc", ".ppt", ".xls", ".xlsx"}

_EMPTY_MESSAGE = (
    "No timetable entries detected in this file. "
    "Please verify the format or try exporting from your university portal."
)


@router.post("/file", response_model=DataResponse[FilePreviewResponseData])
async def preview_file_timetable(
    file: UploadFile = File(..., description="Timetable file (.pdf, .docx, .pptx, .txt, .csv, .jpg, .jpeg, .png, .webp, .ics)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(10, 60, "file_import")),
):
    """
    Parse an uploaded timetable file of any supported type using Google Gemini API.

    - **.pdf, .jpg, .jpeg, .png, .webp, .docx, .pptx** – parsed via Gemini 1.5 Flash (with fallback)
    - **.txt, .csv** – parsed via fast structured timetable regex extractor
    - **.ics / .ical** – parsed via iCalendar parser (recurring events)

    Returns standardized preview items with confidence levels, conflict detection, and duplicate detection.
    Nothing is saved until confirmed.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "missing_filename", "message": "Uploaded file has no filename"},
        )

    raw_filename = file.filename
    # Path traversal detection and sanitization
    if ".." in raw_filename or "/" in raw_filename or "\\" in raw_filename:
        if ".." in raw_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_filename", "message": "Malicious filename or path traversal detected"},
            )
        file.filename = os.path.basename(raw_filename)

    # Check for executable or dangerous double extensions (e.g. timetable.pdf.exe or script.py)
    parts = raw_filename.lower().split(".")
    has_dangerous_inner = any(p in DANGEROUS_EXTENSIONS for p in parts[1:-1])
    ext = _ext(file.filename)

    if has_dangerous_inner or ext in DANGEROUS_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_format",
                "message": "File extension is not allowed. Executable or script files are strictly prohibited. Supported: PDF, Word, PowerPoint, images (JPG, PNG), TXT, ICS",
            },
        )

    # Reject legacy binary office formats explicitly
    if ext in LEGACY_REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "legacy_format",
                "message": (
                    f"Legacy file format '{ext}' is not supported. "
                    "Please save the file as .docx (Word) or .pptx (PowerPoint) and try again."
                ),
            },
        )

    # Reject unsupported file types
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_format",
                "message": "Supported: PDF, Word, PowerPoint, images (JPG, PNG), TXT, ICS",
            },
        )

    # Read file bytes into memory (never save to disk)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_file", "message": "Uploaded file is empty"},
        )

    # Check file size (max 20MB)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "file_too_large", "message": "File must be under 20MB"},
        )

    # ICS delegation
    if ext in (".ics", ".ical"):
        try:
            ics_preview, _unmatched = parse_ics_timetable(content)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_ics", "message": f"Failed to parse .ics file: {exc}"},
            )

        if not ics_preview:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "no_timetable_found",
                    "message": "No timetable found in this file. Try a clearer screenshot or export from your university portal",
                },
            )

        wrapped = [
            FilePreviewItem(
                temp_id=f"ics-{i}",
                title=item.title,
                day_of_week=item.day_of_week,
                start_time=item.start_time,
                end_time=item.end_time,
                location=item.location,
                course_code=item.course_code,
                is_recurring=True,
                confidence="high",
                source_line="",
                notes=item.notes or "",
            )
            for i, item in enumerate(ics_preview)
        ]
        enriched_items, v_count, r_count, d_count, c_count = enrich_preview_items(
            wrapped, current_user.user_id, db
        )
        return DataResponse(
            data=FilePreviewResponseData(
                preview=enriched_items,
                total_found=len(enriched_items),
                valid_count=v_count,
                review_count=r_count,
                duplicate_count=d_count,
                conflict_count=c_count,
                file_type="ics",
                message=f"Found {len(enriched_items)} classes. Review and confirm to add them.",
            )
        )

    # Fast & reliable local extractor for plain text and CSV
    if ext in (".txt", ".csv"):
        from app.services.text_extractor import text_to_blocks
        raw_text = content.decode("utf-8", errors="replace")
        extracted_blocks = text_to_blocks(raw_text, is_ocr=False)

        if not extracted_blocks:
            return DataResponse(
                data=FilePreviewResponseData(
                    preview=[],
                    total_found=0,
                    valid_count=0,
                    review_count=0,
                    duplicate_count=0,
                    conflict_count=0,
                    file_type="txt" if ext == ".txt" else "csv",
                    message=_EMPTY_MESSAGE,
                )
            )

        enriched_items, v_count, r_count, d_count, c_count = enrich_preview_items(
            extracted_blocks, current_user.user_id, db
        )
        return DataResponse(
            data=FilePreviewResponseData(
                preview=enriched_items,
                total_found=len(enriched_items),
                valid_count=v_count,
                review_count=r_count,
                duplicate_count=d_count,
                conflict_count=c_count,
                file_type="txt" if ext == ".txt" else "csv",
                message=f"Found {len(enriched_items)} classes. Review and confirm to add them.",
            )
        )

    # Gemini-powered timetable parser for documents and images (with local fallback)
    try:
        preview_items, file_type = await extract_timetable_with_gemini(
            content=content,
            filename=file.filename,
            ext=ext,
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY or exc.status_code < 500:
            raise
        # Fallback to local text extraction only if Gemini API is service unavailable (503/500/etc.)
        try:
            from app.services.file_extractor import extract_text
            from app.services.text_extractor import text_to_blocks
            raw_text, is_ocr = extract_text(content, file.filename)
            if raw_text.strip():
                preview_items = text_to_blocks(raw_text, is_ocr=is_ocr)
                file_type = ext.lstrip(".")
            else:
                raise exc
        except Exception:
            raise exc

    enriched_items, v_count, r_count, d_count, c_count = enrich_preview_items(
        preview_items, current_user.user_id, db
    )

    return DataResponse(
        data=FilePreviewResponseData(
            preview=enriched_items,
            total_found=len(enriched_items),
            valid_count=v_count,
            review_count=r_count,
            duplicate_count=d_count,
            conflict_count=c_count,
            file_type=file_type,
            message=f"Found {len(enriched_items)} classes. Review and confirm to add them." if enriched_items else _EMPTY_MESSAGE,
        )
    )


@router.post("/file/confirm", response_model=DataResponse[IcsConfirmResponseData])
def confirm_file_import(
    body: IcsConfirmRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Commit approved timetable blocks to the user's schedule in the database.
    Creates database time_blocks with user_id from JWT within an atomic transaction.
    """
    created_count = 0
    conflicts_detected = 0

    try:
        from app.store import detect_conflicts_and_totals

        for b in body.preview_blocks:
            st_parts = b.start_time.split(":") if b.start_time else ["09", "00"]
            et_parts = b.end_time.split(":") if b.end_time else ["10", "00"]
            st = dt_time(int(st_parts[0]), int(st_parts[1]))
            et = dt_time(int(et_parts[0]), int(et_parts[1]))

            s_min = st.hour * 60 + st.minute
            e_min = et.hour * 60 + et.minute
            duration = (e_min - s_min) % (24 * 60)
            if duration <= 0:
                duration = 60

            eff_from = None
            if b.effective_from:
                eff_from = (
                    b.effective_from
                    if isinstance(b.effective_from, date)
                    else date.fromisoformat(str(b.effective_from))
                )
            eff_until = None
            if b.effective_until:
                eff_until = (
                    b.effective_until
                    if isinstance(b.effective_until, date)
                    else date.fromisoformat(str(b.effective_until))
                )

            new_block = TimeBlock(
                user_id=current_user.user_id,
                type=BlockType.CLASS,
                status=BlockStatus.ENROLLED,
                title=b.title,
                location=b.location,
                day_of_week=b.day_of_week,
                start_time=st,
                end_time=et,
                duration_minutes=duration,
                is_recurring=True,
                effective_from=eff_from,
                effective_until=eff_until,
                is_flexible=False,
                hourly_wage=None,
                course_id=b.course_id,
                is_imported=True,
                deleted=False,
            )
            db.add(new_block)
            created_count += 1

        db.commit()

        record_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="IMPORT_CONFIRMED",
            entity_type="time_block",
            description=f"Imported {created_count} timetable classes",
            request=request,
        )

        conflicts, _ = detect_conflicts_and_totals(user_id=current_user.user_id, db=db)
        conflicts_detected = len(conflicts)

    except Exception as exc:
        db.rollback()
        logger.error(f"Error creating time blocks from file import: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "import_failed", "message": "Failed to save timetable blocks. Please try again."},
        )

    return DataResponse(
        data=IcsConfirmResponseData(
            created_count=created_count,
            conflicts_detected=conflicts_detected,
        )
    )
