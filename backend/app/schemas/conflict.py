from typing import Any, Optional
from pydantic import BaseModel, Field


class ConflictItem(BaseModel):
    id: int
    block_a_id: int
    block_b_id: int
    overlap_minutes: int
    severity: str = Field(..., description="'hard', 'warning', or 'info'")
    overlap_start: str
    overlap_end: str
    day_of_week: Optional[int] = None
    description: Optional[str] = None
    status: str = Field(default="unresolved", description="'unresolved', 'resolved', or 'acknowledged'")
    conflict_type: str = Field(default="class_shift", description="'class_shift', 'class_class', 'shift_shift', 'same_course', 'transition'")
    reason: Optional[str] = None
    recommended_action: Optional[str] = None
    message: Optional[str] = None
    block_a: Optional[dict[str, Any]] = None
    block_b: Optional[dict[str, Any]] = None
    available_transition_minutes: Optional[int] = None
    required_transition_minutes: Optional[int] = None
    location_a: Optional[str] = None
    location_b: Optional[str] = None



class WeeklyTotals(BaseModel):
    shift_hours: float
    class_hours: float
    expected_earnings: float
    over_limit: bool


class ConflictsResponseData(BaseModel):
    conflicts: list[ConflictItem]
    weekly_totals: WeeklyTotals


class ScheduleSuggestion(BaseModel):
    id: str
    block_id: int
    day_of_week: int
    day_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    score: int
    reasons: list[str]
    warnings: list[str]
    weekly_hours_after: float
    weekly_limit: float


class ConflictSuggestionsData(BaseModel):
    conflict: ConflictItem
    suggestions: list[ScheduleSuggestion]


class ResolveConflictRequest(BaseModel):
    block_id: int
    day_of_week: int
    start_time: str
    end_time: str


class ResolveConflictData(BaseModel):
    success: bool
    message: str
    updated_block: dict[str, Any]
    conflicts: list[ConflictItem]
    weekly_totals: WeeklyTotals


class AcknowledgeConflictData(BaseModel):
    success: bool
    message: str
    conflict: ConflictItem
