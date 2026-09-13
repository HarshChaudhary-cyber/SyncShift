from typing import Optional
from pydantic import BaseModel, Field


class HealthFactorSchema(BaseModel):
    type: str = Field(..., description="'positive' | 'warning' | 'info'")
    text: str
    impact: int = 0


class ScheduleHealthData(BaseModel):
    score: int
    category: str = Field(..., description="'Excellent' | 'Healthy' | 'Moderate' | 'Needs attention' | 'Overloaded'")
    summary: str
    factors: list[HealthFactorSchema]
    improvements: list[str]


class DailyWorkloadItem(BaseModel):
    day: str
    date: str
    day_of_week: int
    class_hours: float
    work_hours: float
    study_hours: float
    total_hours: float
    is_heavy: bool
    label: str


class HoursBreakdown(BaseModel):
    class_hours: float
    work_hours: float
    study_hours: float
    total_hours: float
    free_hours: float


class WorkLimitAnalytics(BaseModel):
    configured: float
    used: float
    remaining: float
    percentage: float
    over_limit: bool
    over_hours: float


class ConflictsAnalytics(BaseModel):
    hard: int
    warning: int
    total: int
    trend: Optional[str] = None


class EarningsAnalytics(BaseModel):
    currency: str
    currency_symbol: str
    estimated_week: float
    estimated_month: float
    missing_wage_shifts: int


class TimeDistributionData(BaseModel):
    class_percentage: float
    work_percentage: float
    study_percentage: float
    free_percentage: float


class AnalyticsData(BaseModel):
    period: dict[str, str]
    hours: HoursBreakdown
    work_limit: WorkLimitAnalytics
    conflicts: ConflictsAnalytics
    earnings: EarningsAnalytics
    daily_workload: list[DailyWorkloadItem]
    time_distribution: TimeDistributionData
    health: ScheduleHealthData
