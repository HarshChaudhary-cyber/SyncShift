from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Courses Schemas
# ---------------------------------------------------------------------------

class AcademicCourseCreate(BaseModel):
    department_id: int
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    credits: int = Field(default=3, ge=1, le=30)
    level: Optional[str] = Field("undergraduate", max_length=32)
    status: Optional[str] = Field("active", max_length=32)
    min_room_capacity: Optional[int] = Field(None, ge=1)
    required_room_type: Optional[str] = Field(None, max_length=32)


class AcademicCourseUpdate(BaseModel):
    department_id: Optional[int] = None
    code: Optional[str] = Field(None, min_length=1, max_length=32)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    credits: Optional[int] = Field(None, ge=1, le=30)
    level: Optional[str] = Field(None, max_length=32)
    status: Optional[str] = Field(None, max_length=32)
    min_room_capacity: Optional[int] = Field(None, ge=1)
    required_room_type: Optional[str] = Field(None, max_length=32)


class AcademicCourseOut(BaseModel):
    id: int
    institution_id: int
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    code: str
    name: str
    description: Optional[str] = None
    credits: int
    level: Optional[str] = None
    status: str
    min_room_capacity: Optional[int] = None
    required_room_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Faculty Assignment Schemas
# ---------------------------------------------------------------------------

class FacultyAssignmentCreate(BaseModel):
    faculty_id: int
    role: Optional[str] = Field("instructor", max_length=32)  # 'instructor', 'co_instructor', 'teaching_assistant'
    is_primary: Optional[bool] = False


class FacultyAssignmentOut(BaseModel):
    id: int
    institution_id: int
    section_id: int
    faculty_id: int
    user_id: int
    faculty_name: Optional[str] = None
    faculty_email: Optional[str] = None
    faculty_title: Optional[str] = None
    role: str
    is_primary: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Academic Section Schemas
# ---------------------------------------------------------------------------

class AcademicSectionCreate(BaseModel):
    course_id: int
    academic_term_id: int
    section_code: str = Field(..., min_length=1, max_length=32)
    capacity: int = Field(default=30, ge=1, le=5000)
    status: Optional[str] = Field("active", max_length=32)
    description: Optional[str] = Field(None, max_length=500)


class AcademicSectionUpdate(BaseModel):
    section_code: Optional[str] = Field(None, min_length=1, max_length=32)
    capacity: Optional[int] = Field(None, ge=1, le=5000)
    status: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=500)


class AcademicSectionOut(BaseModel):
    id: int
    institution_id: int
    course_id: int
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    academic_term_id: int
    term_name: Optional[str] = None
    section_code: str
    capacity: int
    status: str
    description: Optional[str] = None
    instructors: list[FacultyAssignmentOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Faculty Profile Schemas
# ---------------------------------------------------------------------------

class FacultyProfileCreate(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    department_id: Optional[int] = None
    employee_code: Optional[str] = Field(None, max_length=64)
    title: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field("active", max_length=32)


class FacultyProfileUpdate(BaseModel):
    department_id: Optional[int] = None
    employee_code: Optional[str] = Field(None, max_length=64)
    title: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, max_length=32)


class FacultyProfileOut(BaseModel):
    id: int
    institution_id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    employee_code: Optional[str] = None
    title: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Room Schemas
# ---------------------------------------------------------------------------

class RoomCreate(BaseModel):
    building: str = Field(..., min_length=1, max_length=100)
    room_number: str = Field(..., min_length=1, max_length=32)
    name: Optional[str] = Field(None, max_length=255)
    capacity: int = Field(..., ge=1, le=10000)
    room_type: Optional[str] = Field("classroom", max_length=32)
    description: Optional[str] = Field(None, max_length=500)
    basic_features: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field("active", max_length=32)


class RoomUpdate(BaseModel):
    building: Optional[str] = Field(None, min_length=1, max_length=100)
    room_number: Optional[str] = Field(None, min_length=1, max_length=32)
    name: Optional[str] = Field(None, max_length=255)
    capacity: Optional[int] = Field(None, ge=1, le=10000)
    room_type: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = Field(None, max_length=500)
    basic_features: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, max_length=32)


class RoomOut(BaseModel):
    id: int
    institution_id: int
    building: str
    room_number: str
    name: Optional[str] = None
    capacity: int
    room_type: str
    description: Optional[str] = None
    basic_features: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
