from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Institution Schemas
# ---------------------------------------------------------------------------

class InstitutionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: str = Field(default="Europe/London", max_length=64)
    email_domain: Optional[str] = Field(default=None, max_length=255)


class InstitutionCreate(InstitutionBase):
    @model_validator(mode="after")
    def validate_non_empty(self) -> "InstitutionCreate":
        if not self.name.strip():
            raise ValueError("Institution name cannot be empty or whitespace only")
        if not self.code.strip():
            raise ValueError("Institution code cannot be empty or whitespace only")
        self.code = self.code.strip().upper()
        return self


class InstitutionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=64)
    email_domain: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_updates(self) -> "InstitutionUpdate":
        if self.name is not None and not self.name.strip():
            raise ValueError("Institution name cannot be empty")
        if self.code is not None:
            if not self.code.strip():
                raise ValueError("Institution code cannot be empty")
            self.code = self.code.strip().upper()
        return self


class InstitutionOut(InstitutionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Membership Schemas
# ---------------------------------------------------------------------------

class MembershipCreate(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: str = Field(default="student", pattern="^(student|professor|admin|super_admin)$")
    status: str = Field(default="active", pattern="^(active|inactive|pending)$")

    @model_validator(mode="after")
    def check_user_specified(self) -> "MembershipCreate":
        if self.user_id is None and not self.email:
            raise ValueError("Either user_id or email must be provided")
        return self


class MembershipOut(BaseModel):
    id: int
    user_id: int
    institution_id: int
    role: str
    status: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInstitutionStatus(BaseModel):
    has_institution: bool
    institution: Optional[InstitutionOut] = None
    membership: Optional[MembershipOut] = None


# ---------------------------------------------------------------------------
# Department Schemas
# ---------------------------------------------------------------------------

class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=32)
    description: Optional[str] = Field(default=None, max_length=500)


class DepartmentCreate(DepartmentBase):
    @model_validator(mode="after")
    def validate_non_empty(self) -> "DepartmentCreate":
        if not self.name.strip():
            raise ValueError("Department name cannot be empty or whitespace only")
        if not self.code.strip():
            raise ValueError("Department code cannot be empty or whitespace only")
        self.code = self.code.strip().upper()
        return self


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, min_length=1, max_length=32)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_updates(self) -> "DepartmentUpdate":
        if self.name is not None and not self.name.strip():
            raise ValueError("Department name cannot be empty")
        if self.code is not None:
            if not self.code.strip():
                raise ValueError("Department code cannot be empty")
            self.code = self.code.strip().upper()
        return self


class DepartmentOut(DepartmentBase):
    id: int
    institution_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Academic Term Schemas
# ---------------------------------------------------------------------------

class AcademicTermBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    academic_year: str = Field(..., min_length=1, max_length=32)
    term_type: str = Field(default="semester", max_length=32)
    start_date: date
    end_date: date
    status: str = Field(default="upcoming", pattern="^(draft|upcoming|active|completed|archived)$")


class AcademicTermCreate(AcademicTermBase):
    @model_validator(mode="after")
    def validate_dates(self) -> "AcademicTermCreate":
        if not self.name.strip():
            raise ValueError("Term name cannot be empty")
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly after start_date")
        return self


class AcademicTermUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    academic_year: Optional[str] = Field(default=None, min_length=1, max_length=32)
    term_type: Optional[str] = Field(default=None, max_length=32)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|upcoming|active|completed|archived)$")

    @model_validator(mode="after")
    def validate_dates_if_both(self) -> "AcademicTermUpdate":
        if self.name is not None and not self.name.strip():
            raise ValueError("Term name cannot be empty")
        if self.start_date is not None and self.end_date is not None:
            if self.end_date <= self.start_date:
                raise ValueError("end_date must be strictly after start_date")
        return self


class AcademicTermOut(AcademicTermBase):
    id: int
    institution_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Dashboard Overview Schema
# ---------------------------------------------------------------------------

class UniversityDashboardOut(BaseModel):
    institution: InstitutionOut
    membership: MembershipOut
    department_count: int
    member_count: int
    course_count: int = 0
    section_count: int = 0
    faculty_count: int = 0
    room_count: int = 0
    active_term: Optional[AcademicTermOut] = None
