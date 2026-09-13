import enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AssistantIntentType(str, enum.Enum):
    GET_TODAY_SCHEDULE = "GET_TODAY_SCHEDULE"
    GET_WEEK_SCHEDULE = "GET_WEEK_SCHEDULE"
    GET_NEXT_EVENT = "GET_NEXT_EVENT"
    GET_CONFLICTS = "GET_CONFLICTS"
    GET_WORK_HOURS = "GET_WORK_HOURS"
    GET_EARNINGS = "GET_EARNINGS"
    FIND_AVAILABLE_TIME = "FIND_AVAILABLE_TIME"
    FIND_WORK_SCHEDULE = "FIND_WORK_SCHEDULE"
    PLAN_STUDY = "PLAN_STUDY"
    CHECK_SCHEDULE_HEALTH = "CHECK_SCHEDULE_HEALTH"
    EXPLAIN_CONFLICT = "EXPLAIN_CONFLICT"
    REQUEST_OPTIMIZATION = "REQUEST_OPTIMIZATION"
    MOVE_EVENT = "MOVE_EVENT"
    RESCHEDULE_EVENT = "RESCHEDULE_EVENT"
    AMBIGUOUS_CHOICE = "AMBIGUOUS_CHOICE"
    GENERAL_HELP = "GENERAL_HELP"


class ActionCheckItem(BaseModel):
    label: str
    passed: bool
    warning: bool = False


class ActionPreview(BaseModel):
    action_type: str
    block_id: int
    title: str
    original: dict[str, Any]
    target: dict[str, Any]
    checks: list[ActionCheckItem]


class AssistantChatRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="Natural language prompt from student")
    context: Optional[dict[str, Any]] = None


class AssistantChatResponseData(BaseModel):
    message: str
    intent: str
    requires_confirmation: bool = False
    action: Optional[ActionPreview] = None
    choices: Optional[list[dict[str, Any]]] = None
    suggestions: list[str] = Field(default_factory=list)


class AssistantConfirmRequest(BaseModel):
    action: ActionPreview


class AssistantConfirmResponseData(BaseModel):
    success: bool
    message: str
    updated_block: Optional[dict[str, Any]] = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    health_score: Optional[int] = None
