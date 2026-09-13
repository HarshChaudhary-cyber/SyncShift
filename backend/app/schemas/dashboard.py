from typing import Optional
from pydantic import BaseModel
from app.schemas.analytics import ScheduleHealthData
from app.schemas.student_academic import StudentAcademicSummary
from app.schemas.conflict import ConflictItem


class DashboardUser(BaseModel):
    display_name: str
    email: str
    avatar_url: Optional[str] = None
    timezone: str
    weekly_work_hour_limit: float
    currency: Optional[str] = "₹"


class DashboardBlock(BaseModel):
    id: int
    type: str
    title: str
    start_time: str
    end_time: str
    location: Optional[str] = None
    color: Optional[str] = None
    is_now: bool = False
    day_of_week: Optional[int] = None
    occurrence_date: Optional[str] = None
    is_exception: bool = False


class NextUpBlock(BaseModel):
    id: int
    title: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    type: str
    color: Optional[str] = None
    occurrence_date: Optional[str] = None


class DashboardNextUp(BaseModel):
    block: NextUpBlock
    minutes_until: int
    label: str


class DashboardToday(BaseModel):
    date: str
    day_name: str
    blocks: list[DashboardBlock]
    conflicts: list[ConflictItem]
    shift_hours: float
    class_hours: float
    expected_earnings: float


class DashboardWeek(BaseModel):
    start: str
    end: str
    total_shift_hours: float
    total_class_hours: float
    expected_earnings: float
    conflict_count: int
    over_work_limit: bool
    work_limit: float


class DashboardAlert(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    block_ids: Optional[list[int]] = None


class DashboardWorkSummary(BaseModel):
    hours_used: float
    limit: float
    percentage: float
    remaining_hours: float
    over_limit: bool
    over_hours: float


class DashboardStudyTask(BaseModel):
    id: int
    title: str
    deadline: str
    hours_remaining: float
    preferred_duration: int
    course_code: Optional[str] = None


class DashboardStudySummary(BaseModel):
    hours_planned: float
    hours_done: float
    has_goals: bool
    next_task: Optional[DashboardStudyTask] = None


class DashboardQuickAnalytics(BaseModel):
    class_hours: float
    work_hours: float
    study_hours: float
    conflict_count: int
    expected_earnings: float
    currency_symbol: str


class DashboardData(BaseModel):
    user: DashboardUser
    today: DashboardToday
    next_up: Optional[DashboardNextUp] = None
    week: DashboardWeek
    alerts: list[DashboardAlert]

    # Intelligent Dashboard Extensions
    health: Optional[ScheduleHealthData] = None
    work: Optional[DashboardWorkSummary] = None
    study: Optional[DashboardStudySummary] = None
    analytics: Optional[DashboardQuickAnalytics] = None
    recommendations: list[str] = []
    adaptive_state: str = "on_track"  # new_user, academic_only, has_conflicts, on_track, near_limit, over_limit
    academics: Optional[StudentAcademicSummary] = None
