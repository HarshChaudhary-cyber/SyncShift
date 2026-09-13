from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field


class IcsPreviewItem(BaseModel):
    temp_id: str
    title: str
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str
    end_time: str
    location: Optional[str] = None
    is_recurring: bool = True
    recurring: Optional[bool] = True
    recurrence_interval: Optional[int] = 1
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    course_code: Optional[str] = None
    notes: Optional[str] = ""


class IcsUnmatchedItem(BaseModel):
    summary: str
    reason: str
    raw_data: Optional[dict[str, Any]] = None


class IcsPreviewResponseData(BaseModel):
    preview: list[IcsPreviewItem]
    unmatched: list[IcsUnmatchedItem]


class IcsConfirmBlock(BaseModel):
    title: str
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str
    end_time: str
    location: Optional[str] = None
    course_id: Optional[int] = None
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    recurrence_interval: Optional[int] = 1
    is_recurring: Optional[bool] = True


class IcsConfirmRequest(BaseModel):
    preview_blocks: list[IcsConfirmBlock]


class IcsConfirmResponseData(BaseModel):
    created_count: int
    conflicts_detected: int
