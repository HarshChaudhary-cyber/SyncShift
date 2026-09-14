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
    timetable_changes_enabled: bool = True
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
    timetable_changes_enabled: Optional[bool] = None
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
    read_at: Optional[datetime] = None
    priority: str = "INFO"
    action_url: Optional[str] = None
    institution_id: Optional[int] = None
    timetable_version_id: Optional[int] = None
    delivery_status: str = "delivered"
    metadata_json: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: list[NotificationLogOut]
    unread_count: int
    total: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    id: int
    read_at: datetime
    ok: bool = True


class NotificationMarkAllReadResponse(BaseModel):
    marked_count: int
    ok: bool = True


class NotificationAdminItemOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    type: str
    priority: str
    channel: str
    delivery_status: str
    title: str
    sent_at: datetime
    read_at: Optional[datetime] = None


class UniversityNotificationSummaryOut(BaseModel):
    version_id: int
    version_number: int
    students_affected: int
    total_notifications: int
    in_app_count: int
    email_delivered_count: int
    email_failed_count: int
    push_delivered_count: int
    push_failed_count: int
    conflict_alerts_count: int
    summary_status: str  # all_delivered | partially_delivered | none_sent
    logs: list[NotificationAdminItemOut] = []


class TestNotificationResponse(BaseModel):
    ok: bool = True
    message: str = "Test notification sent"

