from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., description="User password (min 8 chars, 1 uppercase, 1 number)")
    timezone: str = Field(default="Europe/London", description="Valid IANA timezone string")
    weekly_work_hour_limit: float = Field(
        default=20.0,
        gt=0.0,
        le=168.0,
        description="Weekly work limit in hours (must be > 0)",
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AuthResponseData(BaseModel):
    user_id: int
    email: str
    token: str
    timezone: Optional[str] = None


class UserProfileData(BaseModel):
    user_id: int
    email: str
    timezone: str
    weekly_work_hour_limit: float

