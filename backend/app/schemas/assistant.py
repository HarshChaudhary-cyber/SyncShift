from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class AssistantIntentType(str, enum.Enum):
    # Schedule inspection
    GET_TODAY_SCHEDULE = "GET_TODAY_SCHEDULE"
    GET_WEEK_SCHEDULE = "GET_WEEK_SCHEDULE"
    GET_NEXT_EVENT = "GET_NEXT_EVENT"
    GET_COURSES = "GET_COURSES"
    GET_CONFLICTS = "GET_CONFLICTS"
    GET_WORK_HOURS = "GET_WORK_HOURS"
    GET_EARNINGS = "GET_EARNINGS"
    # New expanded read intents
    GET_MY_PROFILE = "GET_MY_PROFILE"
    GET_MY_WORK_SHIFTS = "GET_MY_WORK_SHIFTS"
    GET_MY_PERSONAL_BLOCKS = "GET_MY_PERSONAL_BLOCKS"
    GET_MY_TASKS = "GET_MY_TASKS"
    GET_MY_CALENDAR = "GET_MY_CALENDAR"
    # Planning
    FIND_AVAILABLE_TIME = "FIND_AVAILABLE_TIME"
    FIND_AVAILABLE_TIME_SLOTS = "FIND_AVAILABLE_TIME_SLOTS"
    FIND_WORK_SCHEDULE = "FIND_WORK_SCHEDULE"
    CHECK_SCHEDULE_CONFLICT = "CHECK_SCHEDULE_CONFLICT"
    CALCULATE_TRANSITION = "CALCULATE_TRANSITION"
    GENERATE_PLANNER_OPTIONS = "GENERATE_PLANNER_OPTIONS"
    EXPLAIN_CONFLICT = "EXPLAIN_CONFLICT"
    PLAN_STUDY = "PLAN_STUDY"
    PLAN_WEEK = "PLAN_WEEK"
    CHECK_SCHEDULE_HEALTH = "CHECK_SCHEDULE_HEALTH"
    REQUEST_OPTIMIZATION = "REQUEST_OPTIMIZATION"
    # University data
    GET_TIMETABLE_CHANGES = "GET_TIMETABLE_CHANGES"
    GET_CURRENT_TIMETABLE = "GET_CURRENT_TIMETABLE"
    GET_COURSE_INFORMATION = "GET_COURSE_INFORMATION"
    GET_CLASS_DETAILS = "GET_CLASS_DETAILS"
    GET_TIMETABLE_CHANGE_INFORMATION = "GET_TIMETABLE_CHANGE_INFORMATION"
    # Mutations — shifts
    MOVE_EVENT = "MOVE_EVENT"
    MOVE_WORK_SHIFT = "MOVE_WORK_SHIFT"
    RESCHEDULE_EVENT = "RESCHEDULE_EVENT"
    CREATE_WORK_SHIFT = "CREATE_WORK_SHIFT"
    UPDATE_WORK_SHIFT = "UPDATE_WORK_SHIFT"
    DELETE_WORK_SHIFT = "DELETE_WORK_SHIFT"
    # Mutations — personal blocks
    CREATE_STUDY_BLOCK = "CREATE_STUDY_BLOCK"
    CREATE_PERSONAL_BLOCK = "CREATE_PERSONAL_BLOCK"
    UPDATE_PERSONAL_BLOCK = "UPDATE_PERSONAL_BLOCK"
    DELETE_PERSONAL_BLOCK = "DELETE_PERSONAL_BLOCK"
    # Mutations — study tasks
    CREATE_STUDY_TASK = "CREATE_STUDY_TASK"
    UPDATE_STUDY_TASK = "UPDATE_STUDY_TASK"
    DELETE_STUDY_TASK = "DELETE_STUDY_TASK"
    # Apply plan
    APPLY_PLAN = "APPLY_PLAN"
    APPLY_PLANNER_OPTION = "APPLY_PLANNER_OPTION"
    # Admin intents
    GET_UNIVERSITY_TIMETABLE = "GET_UNIVERSITY_TIMETABLE"
    GET_ROOM_AVAILABILITY = "GET_ROOM_AVAILABILITY"
    GET_AFFECTED_STUDENTS = "GET_AFFECTED_STUDENTS"
    PREVIEW_TIMETABLE_CHANGE = "PREVIEW_TIMETABLE_CHANGE"
    GET_VERSION_HISTORY = "GET_VERSION_HISTORY"
    CREATE_TIMETABLE_DRAFT = "CREATE_TIMETABLE_DRAFT"
    PUBLISH_TIMETABLE = "PUBLISH_TIMETABLE"
    GET_UNIVERSITY_OVERVIEW_ANALYTICS = "GET_UNIVERSITY_OVERVIEW_ANALYTICS"
    GET_ENROLLMENT_ANALYTICS = "GET_ENROLLMENT_ANALYTICS"
    GET_ROOM_UTILIZATION_ANALYTICS = "GET_ROOM_UTILIZATION_ANALYTICS"
    GET_FACULTY_ANALYTICS = "GET_FACULTY_ANALYTICS"
    GET_TIMETABLE_HEALTH_ANALYTICS = "GET_TIMETABLE_HEALTH_ANALYTICS"
    # Meta
    AMBIGUOUS_CHOICE = "AMBIGUOUS_CHOICE"
    GENERAL_HELP = "GENERAL_HELP"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"


class ActionCheckItem(BaseModel):
    label: str
    passed: bool
    warning: bool = False


class ActionPreview(BaseModel):
    action_type: str
    title: str
    block_id: Optional[int] = None
    target_id: Optional[int] = None
    original: Optional[dict[str, Any]] = None
    target: Optional[dict[str, Any]] = None
    parameters: Optional[dict[str, Any]] = None
    checks: list[ActionCheckItem] = Field(default_factory=list)
    impact_summary: Optional[dict[str, Any]] = None


class AlternativeSlot(BaseModel):
    """A conflict-free alternative scheduling slot suggested by the AI planner."""
    option_number: int
    option_label: str
    day_of_week: int
    day_name: str
    start_time: str
    end_time: str
    duration_minutes: int
    label: str
    action_preview: Optional[dict[str, Any]] = None


class AssistantChatRequest(BaseModel):
    message: str = Field(..., max_length=2000, description="Natural language prompt from student or administrator")
    conversation_id: Optional[int] = Field(None, description="Optional conversation ID for persistent multi-turn history")
    institution_id: Optional[int] = Field(None, description="Institution ID context for university admin queries")
    context: Optional[dict[str, Any]] = None


class AssistantChatResponseData(BaseModel):
    message: str
    intent: str
    conversation_id: Optional[int] = None
    requires_confirmation: bool = False
    action: Optional[ActionPreview] = None
    choices: Optional[list[dict[str, Any]]] = None
    suggestions: list[str] = Field(default_factory=list)
    tool_calls: Optional[list[dict[str, Any]]] = None
    # New fields for enhanced UI
    tool_progress: Optional[list[dict[str, Any]]] = None
    alternatives: Optional[list[AlternativeSlot]] = None


class AssistantConfirmRequest(BaseModel):
    action: ActionPreview


class AssistantConfirmResponseData(BaseModel):
    success: bool
    message: str
    action_type: str = "general"
    updated_block: Optional[dict[str, Any]] = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    health_score: Optional[int] = None
    data: Optional[dict[str, Any]] = None


class AssistantMessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    action_data: Optional[dict[str, Any]] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    created_at: datetime


class AssistantConversationOut(BaseModel):
    id: int
    title: str
    institution_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0
    last_message: Optional[str] = None


class AssistantConversationDetailOut(BaseModel):
    id: int
    title: str
    institution_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: list[AssistantMessageOut] = Field(default_factory=list)
