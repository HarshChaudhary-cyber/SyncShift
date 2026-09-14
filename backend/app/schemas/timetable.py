from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TimetableBase(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the timetable, e.g. Fall 2026 Baseline Schedule")
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field("draft", pattern="^(draft|active|archived)$")


class TimetableCreate(TimetableBase):
    academic_term_id: int = Field(..., description="ID of the academic term this timetable belongs to")


class TimetableUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")


class TimetableOut(TimetableBase):
    id: int
    institution_id: int
    academic_term_id: int
    created_at: datetime
    updated_at: datetime

    # Enriched fields
    term_name: Optional[str] = None
    academic_year: Optional[str] = None
    meetings_count: Optional[int] = 0
    sections_count: Optional[int] = 0
    courses_count: Optional[int] = 0
    published_version_id: Optional[int] = None
    published_version_number: Optional[int] = None
    versions_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)



class CourseMeetingBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Sunday, 1=Monday, ..., 6=Saturday)")
    start_time: str = Field(..., description="Meeting start time e.g. '09:00' or '09:00:00'")
    end_time: str = Field(..., description="Meeting end time e.g. '10:30' or '10:30:00'")
    room_id: Optional[int] = Field(None, description="Optional room ID")
    faculty_id: Optional[int] = Field(None, description="Optional assigned faculty ID")
    meeting_type: Optional[str] = Field("lecture", description="Meeting type: lecture, laboratory, tutorial, seminar, practical, other")
    status: Optional[str] = Field("active", pattern="^(active|cancelled)$")
    version_id: Optional[int] = Field(None, description="Optional timetable version ID")


class CourseMeetingCreate(CourseMeetingBase):
    section_id: int = Field(..., description="Academic section offering this meeting")


class CourseMeetingUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room_id: Optional[int] = None
    faculty_id: Optional[int] = None
    meeting_type: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|cancelled)$")
    version_id: Optional[int] = None


class CourseMeetingOut(BaseModel):
    id: int
    institution_id: int
    timetable_id: int
    version_id: Optional[int] = None
    section_id: int
    academic_term_id: int

    day_of_week: int
    start_time: str
    end_time: str
    room_id: Optional[int] = None
    faculty_id: Optional[int] = None
    meeting_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    # Enriched section/course/room/faculty metadata
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    section_code: Optional[str] = None
    section_capacity: Optional[int] = None
    room_building: Optional[str] = None
    room_number: Optional[str] = None
    room_name: Optional[str] = None
    room_capacity: Optional[int] = None
    faculty_name: Optional[str] = None
    faculty_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudentAcademicScheduleOut(BaseModel):
    institution_id: int
    institution_name: Optional[str] = None
    academic_term_id: Optional[int] = None
    academic_term_name: Optional[str] = None
    enrolled_sections_count: int
    meetings: List[CourseMeetingOut]

    model_config = ConfigDict(from_attributes=True)


# ── Task N6 University Timetable Editor & Impact Analysis Schemas ───────────

class TimetableChangeProposal(BaseModel):
    meeting_id: int = Field(..., description="ID of the course meeting to change")
    day_of_week: int = Field(..., ge=0, le=6, description="Proposed day of week (0=Sunday, 1=Monday, ..., 6=Saturday)")
    start_time: str = Field(..., description="Proposed start time e.g. '14:00'")
    end_time: str = Field(..., description="Proposed end time e.g. '15:15'")
    room_id: Optional[int] = Field(None, description="Proposed room ID (None to leave unchanged or unassigned)")
    faculty_id: Optional[int] = Field(None, description="Proposed faculty ID (None to leave unchanged or unassigned)")
    meeting_type: Optional[str] = Field(None, description="Optional updated meeting type")


class MeetingSnapshot(BaseModel):
    meeting_id: int
    section_id: int
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    section_code: Optional[str] = None
    section_capacity: Optional[int] = None
    day_of_week: int
    day_name: str
    start_time: str
    end_time: str
    room_id: Optional[int] = None
    room_label: Optional[str] = None
    room_capacity: Optional[int] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudentImpactDetail(BaseModel):
    student_id: int
    student_name: str
    conflict_type: str  # 'work_shift', 'personal', 'other_class', 'unavailable', 'hard_constraint', 'none'
    conflict_description: str
    overlap_time: Optional[str] = None
    is_new_conflict: bool = True
    is_resolved_conflict: bool = False


class ImpactSummary(BaseModel):
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'BLOCKED'
    students_affected: int = 0
    new_conflicts: int = 0
    resolved_conflicts: int = 0
    work_conflicts: int = 0
    personal_conflicts: int = 0
    class_conflicts: int = 0
    availability_conflicts: int = 0
    hard_constraint_conflicts: int = 0
    room_issues: List[str] = []
    faculty_issues: List[str] = []
    blocked_reasons: List[str] = []


class TimetableImpactResponse(BaseModel):
    is_blocked: bool = False
    summary: ImpactSummary
    before: MeetingSnapshot
    after: MeetingSnapshot
    student_impacts: List[StudentImpactDetail] = []


class TimetableChangeApplyRequest(BaseModel):
    meeting_id: int = Field(..., description="ID of the course meeting to modify")
    day_of_week: int = Field(..., ge=0, le=6, description="Confirmed day of week")
    start_time: str = Field(..., description="Confirmed start time")
    end_time: str = Field(..., description="Confirmed end time")
    room_id: Optional[int] = Field(None, description="Confirmed room ID")
    faculty_id: Optional[int] = Field(None, description="Confirmed faculty ID")
    meeting_type: Optional[str] = Field(None, description="Confirmed meeting type")
    expected_updated_at: Optional[datetime] = Field(None, description="Meeting timestamp for concurrency/stale check")


class TimetableChangeApplyResponse(BaseModel):
    success: bool = True
    message: str
    meeting: CourseMeetingOut
    impact_summary: ImpactSummary
    applied_at: datetime


# ── Task N7 Timetable Versions, Review & Publishing Schemas ───────────────────

class TimetableVersionBase(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Human-friendly label e.g. 'Fall 2026 Baseline'")
    change_summary: Optional[str] = Field(None, description="Summary notes of changes in this version")


class TimetableVersionCreate(TimetableVersionBase):
    source_version_id: Optional[int] = Field(None, description="ID of source version to clone meetings from; defaults to current published version")


class TimetableVersionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    change_summary: Optional[str] = None


class TimetableVersionOut(TimetableVersionBase):
    id: int
    institution_id: int
    timetable_id: int
    version_number: int
    status: str  # draft, in_review, approved, published, archived, rejected
    created_by_user_id: Optional[int] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    meetings_count: int = 0
    sections_count: int = 0
    is_current_published: bool = False

    model_config = ConfigDict(from_attributes=True)


class VersionChecklistItem(BaseModel):
    code: str
    title: str
    description: str
    status: str  # 'passed', 'failed', 'warning'
    details: List[str] = []


class VersionChecklistOut(BaseModel):
    version_id: int
    version_number: int
    version_status: str
    is_publishable: bool
    can_submit_review: bool
    can_approve: bool
    blocking_issues: List[str] = []
    warnings: List[str] = []
    checklist_items: List[VersionChecklistItem] = []
    summary: str


class VersionMeetingDiff(BaseModel):
    section_id: int
    course_code: str
    course_name: str
    section_code: str
    change_type: str  # 'added', 'removed', 'moved', 'room_changed', 'faculty_changed', 'modified', 'unchanged'
    before_day: Optional[int] = None
    before_day_name: Optional[str] = None
    before_start_time: Optional[str] = None
    before_end_time: Optional[str] = None
    before_room: Optional[str] = None
    before_faculty: Optional[str] = None
    after_day: Optional[int] = None
    after_day_name: Optional[str] = None
    after_start_time: Optional[str] = None
    after_end_time: Optional[str] = None
    after_room: Optional[str] = None
    after_faculty: Optional[str] = None
    human_summary: str


class VersionComparisonOut(BaseModel):
    base_version_id: int
    base_version_number: int
    base_version_name: Optional[str] = None
    target_version_id: int
    target_version_number: int
    target_version_name: Optional[str] = None
    total_classes_changed: int = 0
    time_changes_count: int = 0
    room_changes_count: int = 0
    faculty_changes_count: int = 0
    added_classes_count: int = 0
    removed_classes_count: int = 0
    students_affected: int = 0
    new_conflicts: int = 0
    resolved_conflicts: int = 0
    diffs: List[VersionMeetingDiff] = []


class PublishVersionRequest(BaseModel):
    expected_updated_at: Optional[datetime] = Field(None, description="Optimistic concurrency timestamp of the version")
    notes: Optional[str] = Field(None, description="Optional publication audit note")


class TimetableNotificationSummary(BaseModel):
    students_affected: int = 0
    classes_changed: int = 0
    notifications_created: int = 0
    in_app_delivered: int = 0
    email_delivered: int = 0
    email_failed: int = 0
    push_delivered: int = 0
    push_failed: int = 0
    new_conflicts: int = 0
    resolved_conflicts: int = 0


class PublishVersionResponse(BaseModel):
    success: bool = True
    message: str
    published_version: TimetableVersionOut
    archived_version_id: Optional[int] = None
    published_at: datetime
    notification_summary: Optional[TimetableNotificationSummary] = None



class SubmitReviewRequest(BaseModel):
    notes: Optional[str] = None


class ApproveVersionRequest(BaseModel):
    notes: Optional[str] = None

