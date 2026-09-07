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
    Superset of IcsPreviewItem: adds `confidence` and `source_line`.
    """
    temp_id: str
    title: str
    day_of_week: int = Field(
        ...,
        ge=-1,
        le=6,
        description="0=Monday … 6=Sunday; -1 means day could not be parsed",
    )
    start_time: str = Field(
        ...,
        description="24-hour HH:MM; empty string if unparseable",
    )
    end_time: str = Field(
        ...,
        description="24-hour HH:MM; empty string if unparseable",
    )
    location: Optional[str] = None
    confidence: Literal["high", "low"] = "high"
    source_line: str = ""
    course_code: Optional[str] = None
    notes: Optional[str] = ""


class FilePreviewResponseData(BaseModel):
    """Top-level response body for /import/file preview."""
    preview: list[FilePreviewItem]
    message: Optional[str] = None  # set when preview is empty
