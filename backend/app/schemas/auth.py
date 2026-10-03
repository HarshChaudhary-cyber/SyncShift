from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., description="User password (min 8 chars, 1 uppercase, 1 number)")
    timezone: Optional[str] = Field(default=None, description="Valid IANA timezone string (e.g. Asia/Kolkata)")
    weekly_work_hour_limit: float = Field(
        default=20.0,
        gt=0.0,
        le=168.0,
        description="Weekly work limit in hours (must be > 0)",
    )
    minimum_transition_minutes: Optional[int] = Field(
        default=15,
        ge=0,
        le=120,
        description="Configured minimum transition buffer between events in minutes",
    )
    captcha_token: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    captcha_token: Optional[str] = None


class OAuthGoogleRequest(BaseModel):
    id_token: str
    captcha_token: Optional[str] = None


class OAuthMicrosoftRequest(BaseModel):
    id_token: str
    nonce: Optional[str] = None
    captcha_token: Optional[str] = None


class AuthResponseData(BaseModel):
    user_id: int
    email: str
    token: str
    timezone: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    institution_id: Optional[int] = None
    institution_role: Optional[str] = None  # 'student' | 'faculty' | 'professor' | 'admin' | 'super_admin'


class UserProfileData(BaseModel):
    user_id: int
    email: str
    timezone: Optional[str] = None
    weekly_work_hour_limit: float
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    currency: Optional[str] = "INR"
    language: Optional[str] = "en"
    theme: Optional[str] = "dark"
    minimum_transition_minutes: int = 15
    week_starts_on: str = "monday"
    time_format: str = "12h"
    default_calendar_view: str = "week"
    reduced_motion: str = "system"
    planning_hours_start: int = 9
    planning_hours_end: int = 18
    preferred_session_duration: int = 45
    preferred_break_duration: int = 15
    oauth_provider: Optional[str] = None
    has_password: bool = False
    created_at: Optional[datetime] = None
    institution_id: Optional[int] = None
    institution_role: Optional[str] = None  # 'student' | 'faculty' | 'professor' | 'admin' | 'super_admin'


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    weekly_work_hour_limit: Optional[float] = Field(None, ge=0.0, le=168.0)
    currency: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    avatar_url: Optional[str] = None
    minimum_transition_minutes: Optional[int] = Field(None, ge=0, le=120)
    week_starts_on: Optional[str] = Field(None, pattern="^(monday|sunday)$")
    time_format: Optional[str] = Field(None, pattern="^(12h|24h)$")
    default_calendar_view: Optional[str] = Field(None, pattern="^(week|day|month|7day|5day)$")
    reduced_motion: Optional[str] = Field(None, pattern="^(system|reduced|normal)$")
    planning_hours_start: Optional[int] = Field(None, ge=0, le=23)
    planning_hours_end: Optional[int] = Field(None, ge=0, le=23)
    preferred_session_duration: Optional[int] = Field(None, ge=15, le=240)
    preferred_break_duration: Optional[int] = Field(None, ge=0, le=120)



class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None
    confirm: Optional[str] = None


class MessageData(BaseModel):
    message: str


class ExportDataResponse(BaseModel):
    user: dict[str, Any]
    courses: list[dict[str, Any]]
    time_blocks: list[dict[str, Any]]
    study_tasks: list[dict[str, Any]]
    notification_prefs: Optional[dict[str, Any]] = None
    exported_at: str


