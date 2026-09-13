from datetime import date
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProposedBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    temp_id: str = Field(..., description="Temporary identifier for preview UI")
    title: str
    day_of_week: int = Field(..., ge=0, le=6, description="0=Sun, 1=Mon, ..., 6=Sat")
    day_name: str
    date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., description="HH:MM:SS")
    end_time: str = Field(..., description="HH:MM:SS")
    duration_hours: float
    study_task_id: Optional[int] = None
    course_id: Optional[int] = None
    type: str = "study"


class ShiftAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    block_id: int
    title: str
    original_date: str
    original_start_time: str
    original_end_time: str
    new_date: str
    new_start_time: str
    new_end_time: str
    reason: str


class PlanOptionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    added_study_blocks_count: int = 0
    moved_flexible_shifts_count: int = 0
    unchanged_classes_count: int = 0
    unchanged_fixed_commitments_count: int = 0
    total_study_hours: float = 0.0
    total_work_hours: float = 0.0
    is_valid: bool = True
    conflict_free: bool = True


class PlanOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="'balanced' | 'focused' | 'compact'")
    name: str
    description: str
    score: int = Field(..., ge=0, le=100)
    fit_percentage: int = Field(..., ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trade_offs: str
    added_blocks: list[ProposedBlockOut] = Field(default_factory=list)
    moved_blocks: list[ShiftAdjustmentOut] = Field(default_factory=list)
    summary: PlanOptionSummary


class ScheduleContextSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrolled_classes_count: int = 0
    fixed_work_shifts_count: int = 0
    flexible_work_shifts_count: int = 0
    personal_events_count: int = 0
    pending_tasks_count: int = 0
    total_study_hours_needed: float = 0.0


class PlanPreviewRequest(BaseModel):
    target_week_start: Optional[date] = Field(None, description="Monday of the target planning week (default: current/upcoming)")
    allow_flexible_work_moves: bool = Field(False, description="Whether optimizer may adjust flexible work shifts (is_flexible=True)")
    preferred_time_of_day: Optional[str] = Field(None, description="'morning' | 'afternoon' | 'evening' | 'any'")
    schedule_density: Optional[str] = Field(None, description="'compact' | 'balanced' | 'spread'")


class PlanPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_start: date
    week_end: date
    context_summary: ScheduleContextSummary
    has_feasible_solution: bool
    options: list[PlanOptionOut] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)


class PlanApplyBlock(BaseModel):
    title: str
    day_of_week: int = Field(..., ge=0, le=6)
    date: Optional[str] = None
    start_time: str
    end_time: str
    duration_hours: float
    study_task_id: Optional[int] = None
    course_id: Optional[int] = None
    type: str = "study"


class PlanApplyShift(BaseModel):
    block_id: int
    new_date: Optional[str] = None
    new_day_of_week: Optional[int] = None
    new_start_time: str
    new_end_time: str


class PlanApplyRequest(BaseModel):
    option_id: str
    week_start: Optional[date] = None
    approved_new_blocks: list[PlanApplyBlock] = Field(default_factory=list)
    approved_moved_shifts: list[PlanApplyShift] = Field(default_factory=list)


class PlanApplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    created_blocks_count: int = 0
    updated_shifts_count: int = 0
    applied_block_ids: list[int] = Field(default_factory=list)
    conflicts_detected_count: int = 0
    conflicts: list[Any] = Field(default_factory=list)
