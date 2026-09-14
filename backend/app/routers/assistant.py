"""
SyncShift Assistant Router
Endpoints:
- POST /api/v1/assistant/chat: Natural-language scheduling queries (rate limited)
- GET /api/v1/assistant/conversations: List user's conversations
- GET /api/v1/assistant/conversations/{id}: Full conversation history
- DELETE /api/v1/assistant/conversations/{id}: Delete conversation
- POST /api/v1/assistant/confirm: Execution of user-confirmed scheduling changes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponseData,
    AssistantConfirmRequest,
    AssistantConfirmResponseData,
    AssistantConversationDetailOut,
    AssistantConversationOut,
)
from app.schemas.common import DataResponse, DeletedData
from app.services.assistant import (
    delete_user_conversation,
    execute_confirmed_action,
    get_conversation_detail,
    list_user_conversations,
    process_assistant_chat,
)
from app.services.rate_limiter import rate_limit

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=DataResponse[AssistantChatResponseData],
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60, bucket="assistant_chat"))],
)
def chat_with_assistant(
    payload: AssistantChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Interprets natural language scheduling requests through deterministic backend logic.
    Returns factual schedule analysis, conflict explanations, optimization suggestions,
    or action previews requiring explicit user confirmation.
    """
    response_data = process_assistant_chat(
        current_user=current_user,
        message=payload.message,
        db=db,
        conversation_id=payload.conversation_id,
        institution_id=payload.institution_id,
    )
    return DataResponse(data=response_data)


@router.get("/conversations", response_model=DataResponse[List[AssistantConversationOut]])
def get_conversations(
    institution_id: Optional[int] = Query(None, description="Optional institution ID context"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists persistent conversations for the authenticated user."""
    convs = list_user_conversations(db=db, current_user=current_user, institution_id=institution_id)
    return DataResponse(data=convs)


@router.get("/conversations/{conversation_id}", response_model=DataResponse[AssistantConversationDetailOut])
def get_conversation_history(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full message history for a specific conversation."""
    detail = get_conversation_detail(db=db, current_user=current_user, conversation_id=conversation_id)
    return DataResponse(data=detail)


@router.delete("/conversations/{conversation_id}", response_model=DataResponse[DeletedData])
def delete_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a conversation owned by the authenticated user."""
    delete_user_conversation(db=db, current_user=current_user, conversation_id=conversation_id)
    return DataResponse(data=DeletedData(id=conversation_id, message="Conversation deleted successfully"))


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
