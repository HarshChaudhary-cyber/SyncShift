from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.course import Course
from app.models.time_block import TimeBlock
from app.schemas.common import DataResponse

router = APIRouter(prefix="/debug", tags=["Debug"])


class OldestBlockInfo(BaseModel):
    id: int
    title: str
    type: str
    created_at: Optional[datetime] = None


class MyDataResponse(BaseModel):
    user_id: int
    block_count: int
    course_count: int
    oldest_block: Optional[OldestBlockInfo] = None


@router.get("/my-data", response_model=DataResponse[MyDataResponse])
def get_my_data(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Data verification endpoint (development only).
    Confirms user's blocks and courses exist in the database.
    """
    if settings.ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoint is only accessible in development mode",
        )

    # Count active (non-deleted) blocks strictly belonging to current user
    block_count = (
        db.query(TimeBlock)
        .filter(TimeBlock.user_id == current_user.user_id, TimeBlock.deleted == False)
        .count()
    )

    # Count courses strictly belonging to current user
    course_count = (
        db.query(Course)
        .filter(Course.user_id == current_user.user_id)
        .count()
    )

    # Get oldest block
    oldest = (
        db.query(TimeBlock)
        .filter(TimeBlock.user_id == current_user.user_id, TimeBlock.deleted == False)
        .order_by(asc(TimeBlock.created_at), asc(TimeBlock.id))
        .first()
    )

    oldest_info = None
    if oldest:
        oldest_info = OldestBlockInfo(
            id=oldest.id,
            title=oldest.title,
            type=str(oldest.type.value if hasattr(oldest.type, "value") else oldest.type),
            created_at=oldest.created_at,
        )

    return DataResponse(
        data=MyDataResponse(
            user_id=current_user.user_id,
            block_count=block_count,
            course_count=course_count,
            oldest_block=oldest_info,
        )
    )
