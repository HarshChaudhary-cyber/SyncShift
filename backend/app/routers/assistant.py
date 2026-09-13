"""
SyncShift Assistant Router
Endpoints:
- POST /api/v1/assistant/chat: Natural-language scheduling queries (rate limited)
- POST /api/v1/assistant/confirm: Execution of student-confirmed scheduling changes
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponseData,
    AssistantConfirmRequest,
    AssistantConfirmResponseData,
)
from app.schemas.common import DataResponse
from app.services.assistant import execute_confirmed_action, process_assistant_chat
from app.services.rate_limiter import rate_limit

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=DataResponse[AssistantChatResponseData],
    dependencies=[Depends(rate_limit(max_requests=25, window_seconds=60, bucket="assistant_chat"))],
)
def chat_with_assistant(
    payload: AssistantChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Interprets natural language scheduling requests through deterministic backend logic.
    Returns factual schedule analysis, conflict explanations, optimization suggestions,
    or action previews requiring explicit student confirmation.
    """
    response_data = process_assistant_chat(
        current_user=current_user,
        message=payload.message,
        db=db,
    )
    return DataResponse(data=response_data)


@router.post("/confirm", response_model=DataResponse[AssistantConfirmResponseData])
def confirm_assistant_action(
    payload: AssistantConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Executes a user-confirmed scheduling change with re-validation of constraints
    and records an audit log entry upon success.
    """
    confirm_data = execute_confirmed_action(
        current_user=current_user,
        action=payload.action,
        db=db,
    )
    return DataResponse(data=confirm_data)
