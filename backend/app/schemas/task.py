from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CourseBrief(BaseModel):
    id: int
    code: str
    name: str
    color: str


class StudyTaskBase(BaseModel):
    title: str = Field(..., max_length=255, description="Task or exam title (e.g. DBMS Project)")
    course_id: Optional[int] = Field(None, description="Associated course ID")
    total_hours_required: float = Field(..., gt=0.0, description="Total study hours needed")
    deadline: date = Field(..., description="Due date (YYYY-MM-DD)")
    priority: Optional[str] = Field(default="medium", description="'high' | 'medium' | 'low'")
    preferred_duration: Optional[int] = Field(default=90, description="Preferred duration in minutes (e.g. 60, 90, 120)")


class StudyTaskCreate(StudyTaskBase):
    @field_validator("deadline")
    @classmethod
    def validate_future_deadline(cls, v: date) -> date:
        # Prevent deadlines before today
        if v < date.today():
            raise ValueError("Deadline date cannot be in the past")
        return v


class StudyTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    course_id: Optional[int] = None
    total_hours_required: Optional[float] = Field(None, gt=0.0)
    deadline: Optional[date] = None
    status: Optional[str] = Field(None, description="'pending' | 'scheduled' | 'done'")
    priority: Optional[str] = None
    preferred_duration: Optional[int] = None
    completed_hours: Optional[float] = None


class StudyTaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    course_id: Optional[int] = None
    course: Optional[CourseBrief] = None
    total_hours_required: float
    deadline: date
    status: str
    priority: str = "medium"
    preferred_duration: int = 90
    completed_hours: float = 0.0
    hours_scheduled: float = 0.0
    hours_done: float = 0.0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanSessionSuggested(BaseModel):
    temp_id: str
    day_of_week: int
    day_name: str
    date: str
    start_time: str
    end_time: str
    duration_hours: float
    task_id: int
    type: str = "study"
    score: int = 90
    reasons: list[str] = Field(default_factory=list)
    is_healthy: bool = True


class PlanResponse(BaseModel):
    suggested: list[PlanSessionSuggested]
    hours_scheduled: float
    short_by_hours: Optional[float] = None
    gaps_considered: int


class PlanConfirmBlock(BaseModel):
    temp_id: Optional[str] = None
    day_of_week: int
    start_time: str
    end_time: str
    date: Optional[str] = None


class PlanConfirmRequest(BaseModel):
    approved_blocks: list[PlanConfirmBlock]
