"""
Pydantic Schemas for Task N10 — University Analytics & Decision Dashboard.
Provides structured, term-aware, and beginner-friendly reporting models for:
- Overview KPIs
- Enrollment Demand & Capacity Utilization
- Room Scheduled Utilization (honest scheduled hours, not physical occupancy)
- Faculty Teaching Load & Scheduling
- Timetable Health, Conflicts & Student Impact History
- Departmental Operations Comparison
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnalyticsTermOption(BaseModel):
    id: int
    name: str
    academic_year: str
    status: str = "active"
    is_active: bool = False
    start_date: date
    end_date: date

    model_config = ConfigDict(from_attributes=True)


class AnalyticsOverviewKPIs(BaseModel):
    active_students_count: int = Field(0, description="Total active students enrolled in institution")
    enrolled_students_count: int = Field(0, description="Unique students with at least one active section enrollment in the term")
    total_enrollments_count: int = Field(0, description="Aggregate active section enrollment seats occupied")
    active_courses_count: int = Field(0, description="Active catalog courses for this institution")
    active_sections_count: int = Field(0, description="Active sections offered in the selected term")
    scheduled_classes_count: int = Field(0, description="Total active weekly timetable class meetings")
    unscheduled_sections_count: int = Field(0, description="Sections with zero scheduled class meetings in the timetable")
    active_rooms_count: int = Field(0, description="Active physical rooms in the institution")
    average_room_utilization_pct: float = Field(0.0, description="Average scheduled weekly room utilization percentage")
    active_faculty_count: int = Field(0, description="Total active faculty members")
    total_conflicts_count: int = Field(0, description="Detected scheduling and resource collisions")
    published_timetable_version: Optional[int] = Field(None, description="Current published timetable version number, if any")


class SectionDemandItem(BaseModel):
    section_id: int
    section_code: str
    course_code: str
    course_name: str
    department_name: Optional[str] = None
    capacity: int
    enrolled_count: int
    remaining_seats: int
    utilization_pct: float
    demand_status: str  # 'full', 'high_demand' (>=90%), 'moderate' (30-89%), 'low_utilization' (<30%), 'over_capacity' (>100%)


class EnrollmentAnalyticsData(BaseModel):
    total_capacity: int = 0
    total_enrolled: int = 0
    overall_capacity_utilization_pct: float = 0.0
    high_demand_sections: List[SectionDemandItem] = []
    low_utilization_sections: List[SectionDemandItem] = []
    all_sections: List[SectionDemandItem] = []


class RoomUtilizationItem(BaseModel):
    room_id: int
    room_number: str
    building: str
    room_type: str
    capacity: int
    weekly_scheduled_hours: float
    scheduled_utilization_pct: float
    meetings_count: int
    status: str


class DailyRoomUtilization(BaseModel):
    day_of_week: int
    day_name: str
    scheduled_hours: float
    meeting_count: int


class RoomAnalyticsData(BaseModel):
    total_rooms: int = 0
    active_rooms: int = 0
    total_weekly_capacity_hours: float = 0.0
    total_weekly_scheduled_hours: float = 0.0
    average_utilization_pct: float = 0.0
    most_used_rooms: List[RoomUtilizationItem] = []
    least_used_rooms: List[RoomUtilizationItem] = []
    daily_distribution: List[DailyRoomUtilization] = []
    rooms: List[RoomUtilizationItem] = []


class FacultyScheduleItem(BaseModel):
    faculty_id: int
    user_id: int
    name: str
    email: str
    department_name: Optional[str] = None
    title: Optional[str] = None
    sections_count: int = 0
    weekly_teaching_hours: float = 0.0
    has_schedule_conflicts: bool = False


class FacultyAnalyticsData(BaseModel):
    total_faculty: int = 0
    teaching_faculty_count: int = 0
    average_teaching_hours: float = 0.0
    faculty_list: List[FacultyScheduleItem] = []


class TimetableConflictSummary(BaseModel):
    room_double_bookings: int = 0
    faculty_double_bookings: int = 0
    student_class_conflicts: int = 0
    student_work_shift_clashes: int = 0
    total_conflicts: int = 0


class TimetableChangeHistoryItem(BaseModel):
    version_id: int
    version_number: int
    version_name: Optional[str] = None
    change_summary: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by_name: Optional[str] = None
    students_notified_count: int = 0
    urgent_conflicts_count: int = 0


class TimetableHealthAnalyticsData(BaseModel):
    timetable_id: Optional[int] = None
    timetable_name: Optional[str] = None
    published_version_number: Optional[int] = None
    draft_versions_count: int = 0
    scheduled_sections_count: int = 0
    unscheduled_sections_count: int = 0
    total_meetings_count: int = 0
    conflicts: TimetableConflictSummary
    recent_history: List[TimetableChangeHistoryItem] = []


class DepartmentComparisonItem(BaseModel):
    department_id: int
    name: str
    code: str
    courses_count: int = 0
    sections_count: int = 0
    total_capacity: int = 0
    total_enrolled: int = 0
    capacity_utilization_pct: float = 0.0
    weekly_scheduled_hours: float = 0.0


class UniversityDashboardAnalyticsResponse(BaseModel):
    institution_id: int
    institution_name: str
    generated_at: datetime
    active_term: Optional[AnalyticsTermOption] = None
    available_terms: List[AnalyticsTermOption] = []
    overview: AnalyticsOverviewKPIs
    enrollment: EnrollmentAnalyticsData
    rooms: RoomAnalyticsData
    faculty: FacultyAnalyticsData
    timetable: TimetableHealthAnalyticsData
    departments: List[DepartmentComparisonItem] = []
