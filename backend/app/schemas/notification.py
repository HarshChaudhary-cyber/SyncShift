from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionIn(BaseModel):
    endpoint: str
    expirationTime: Optional[float | int] = None
    keys: PushSubscriptionKeys


class PushSubscriptionDelete(BaseModel):
    endpoint: str


class NotificationPrefsOut(BaseModel):
    user_id: int
    push_enabled: bool
    email_enabled: bool
    class_reminder_min: int
    shift_reminder_min: int
    study_reminder_min: int
    deadline_reminder: bool
    conflict_alerts: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationPrefsUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    class_reminder_min: Optional[int] = Field(None, ge=0, le=1440)
    shift_reminder_min: Optional[int] = Field(None, ge=0, le=1440)
    study_reminder_min: Optional[int] = Field(None, ge=0, le=1440)
    deadline_reminder: Optional[bool] = None
    conflict_alerts: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        # Accept "HH:MM" or "HH:MM:SS"
        parts = v.split(":")
        if len(parts) not in (2, 3):
            raise ValueError("Time must be in HH:MM or HH:MM:SS format")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Hours must be 0-23 and minutes 0-59")
        return f"{h:02d}:{m:02d}"

    @model_validator(mode="after")
    def validate_quiet_hours_pair(self):
        # Quiet hours: both or neither
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        if (start is not None and end is None) or (start is None and end is not None):
            raise ValueError("Quiet hours require both start and end times, or neither")
        return self


class NotificationLogOut(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    body: str
    sent_at: datetime
    channel: str

    class Config:
        from_attributes = True


class TestNotificationResponse(BaseModel):
    ok: bool = True
    message: str = "Test notification sent"
