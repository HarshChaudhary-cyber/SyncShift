from dataclasses import dataclass, field
from datetime import date
from typing import Any, List, Optional


@dataclass
class PlanningEvent:
    id: int
    event_type: str  # 'class', 'fixed_shift', 'flexible_shift', 'personal', 'blackout'
    title: str
    day_of_week: int  # 0=Sun..6=Sat
    date: date
    start_min: int  # minutes from midnight
    end_min: int
    location: Optional[str] = None
    is_fixed: bool = True
    study_task_id: Optional[int] = None
    course_id: Optional[int] = None
    original_block_id: Optional[int] = None


@dataclass
class FreeGap:
    date: date
    day_of_week: int
    start_min: int
    end_min: int
    length_min: int


@dataclass
class ScheduleContext:
    user_id: int
    institution_id: Optional[int]
    week_start: date
    week_end: date
    events: list[PlanningEvent] = field(default_factory=list)
    hard_constraints: list[dict] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)
    tasks: list[dict] = field(default_factory=list)
    enrolled_classes_count: int = 0
    fixed_work_shifts_count: int = 0
    flexible_work_shifts_count: int = 0
    personal_events_count: int = 0
    transition_buffer_min: int = 15


@dataclass
class CandidateSlot:
    temp_id: str
    task_id: int
    task_title: str
    course_id: Optional[int]
    date: date
    day_of_week: int
    start_min: int
    end_min: int
    duration_min: int
    score: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProposedAdjustment:
    block_id: int
    title: str
    original_date: date
    original_start_min: int
    original_end_min: int
    new_date: date
    new_start_min: int
    new_end_min: int
    reason: str


@dataclass
class GeneratedPlanOption:
    option_id: str
    name: str
    description: str
    score: int
    fit_percentage: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trade_offs: str = ""
    slots: list[CandidateSlot] = field(default_factory=list)
    adjustments: list[ProposedAdjustment] = field(default_factory=list)
    is_valid: bool = True
    blocking_reasons: list[str] = field(default_factory=list)
