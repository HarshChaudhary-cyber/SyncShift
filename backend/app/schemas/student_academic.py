from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ── Student Profile Schemas ───────────────────────────────────────────────────

class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    student_number: Optional[str] = None
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime


class StudentProfileUpdate(BaseModel):
    department_id: Optional[int] = None
    student_number: Optional[str] = None
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    status: Optional[str] = None


# ── Section Enrollment Schemas ───────────────────────────────────────────────

class SectionEnrollmentCreate(BaseModel):
    section_id: int


class SectionEnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_number: Optional[str] = None
    section_id: int
    section_code: Optional[str] = None
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    credits: Optional[int] = None
    academic_term_id: Optional[int] = None
    term_name: Optional[str] = None
    instructors: List[str] = []
    status: str
    enrollment_date: datetime
    dropped_at: Optional[datetime] = None
    created_at: datetime


class AvailableSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    section_code: str
    course_id: int
    course_code: str
    course_name: str
    credits: int
    level: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    academic_term_id: int
    term_name: str
    capacity: int
    enrolled_count: int
    remaining_seats: int
    status: str
    instructors: List[str] = []
    is_enrolled_by_me: bool = False


# ── Student Availability Schemas ─────────────────────────────────────────────

class StudentAvailabilityItem(BaseModel):
    id: Optional[int] = None
    day_of_week: int = Field(..., ge=0, le=6, description="0=Sunday, 1=Monday ... 6=Saturday")
    start_time: str = Field(..., example="09:00:00")
    end_time: str = Field(..., example="17:00:00")
    is_available: bool = True
    title: Optional[str] = None


class StudentAvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution_id: Optional[int] = None
    day_of_week: int
    start_time: str
    end_time: str
    is_available: bool
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StudentAvailabilityPayload(BaseModel):
    slots: List[StudentAvailabilityItem]


# ── Student Constraint Schemas ───────────────────────────────────────────────

class StudentConstraintCreate(BaseModel):
    constraint_type: str = Field(..., example="earliest_start", description="earliest_start, latest_end, max_hours_per_day, max_consecutive_hours, day_off, protect_work_shifts, custom")
    is_hard: bool = True
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    time_value: Optional[str] = Field(None, example="18:00:00")
    int_value: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True


class StudentConstraintUpdate(BaseModel):
    constraint_type: Optional[str] = None
    is_hard: Optional[bool] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    time_value: Optional[str] = None
    int_value: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StudentConstraintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution_id: Optional[int] = None
    constraint_type: str
    is_hard: bool
    day_of_week: Optional[int] = None
    time_value: Optional[str] = None
    int_value: Optional[int] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Student Preference Schemas ───────────────────────────────────────────────

class StudentPreferencePayload(BaseModel):
    preferred_time_of_day: Optional[str] = Field("any", example="morning")
    schedule_density: Optional[str] = Field("balanced", example="compact")
    preferred_break_duration_minutes: Optional[int] = Field(30, ge=0, le=240)
    max_campus_days_per_week: Optional[int] = Field(None, ge=1, le=7)
    preferred_days_off: Optional[str] = Field(None, example="0,5")
    work_study_balance_weight: Optional[int] = Field(3, ge=1, le=5)


class StudentPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution_id: Optional[int] = None
    preferred_time_of_day: str
    schedule_density: str
    preferred_break_duration_minutes: int
    max_campus_days_per_week: Optional[int] = None
    preferred_days_off: Optional[str] = None
    work_study_balance_weight: int
    created_at: datetime
    updated_at: datetime


# ── Student Academic Dashboard Summary ────────────────────────────────────────

class StudentAcademicSummary(BaseModel):
    has_academic_profile: bool = True
    institution_id: int
    institution_name: str
    institution_code: str
    department_name: Optional[str] = None
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    student_number: Optional[str] = None
    current_term_name: Optional[str] = None
    enrolled_sections_count: int = 0
    total_credits: int = 0
    enrolled_sections: List[dict] = []
