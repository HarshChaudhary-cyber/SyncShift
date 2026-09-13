"""
Schemas for the multi-format file import endpoints.

POST /api/v1/import/file       → FilePreviewResponseData
POST /api/v1/import/file/confirm → IcsConfirmResponseData (reused from import_ics)
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class FilePreviewItem(BaseModel):
    """
    One candidate timetable entry extracted from any file type.
    """
    temp_id: str
    title: str
    day_of_week: int = Field(
        ...,
        ge=-1,
        le=6,
        description="0=Monday … 6=Sunday; -1 means day could not be parsed",
    )
    day_name: Optional[str] = None
    start_time: str = Field(
        ...,
        description="24-hour HH:MM; empty string if unparseable",
    )
    end_time: str = Field(
        ...,
        description="24-hour HH:MM; empty string if unparseable",
    )
    location: Optional[str] = None
    course_code: Optional[str] = None
    is_recurring: bool = True
    confidence: Literal["high", "low"] = "high"
    status: Literal["valid", "needs_review", "duplicate", "conflict"] = "valid"
    is_duplicate: bool = False
    duplicate_reason: Optional[str] = None
    has_conflict: bool = False
    conflict_description: Optional[str] = None
    issues: list[str] = Field(default_factory=list)
    source_line: Optional[str] = ""
    notes: Optional[str] = ""


class FilePreviewResponseData(BaseModel):
    """Top-level response body for /import/file preview."""
    preview: list[FilePreviewItem]
    total_found: Optional[int] = None
    valid_count: int = 0
    review_count: int = 0
    duplicate_count: int = 0
    conflict_count: int = 0
    file_type: Optional[str] = None
    message: Optional[str] = None
