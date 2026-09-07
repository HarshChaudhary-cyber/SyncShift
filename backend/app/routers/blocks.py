from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas.block import BlockCreate, BlockDuplicate, BlockOut, BlockUpdate
from app.schemas.common import DataResponse, DeletedData
from app.store import (
    add_block_to_store,
    delete_block_from_store,
    get_all_blocks,
    get_block_by_id,
    update_block_in_store,
)

router = APIRouter(prefix="/blocks", tags=["Time Blocks"])


@router.get("", response_model=DataResponse[list[BlockOut]])
def get_blocks(
    week_start: Optional[date] = Query(None, description="Filter blocks active during the week of week_start"),
    type: Optional[str] = Query(None, pattern="^(class|shift)$", description="Filter by block type ('class' or 'shift')"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Retrieve active time blocks for the user, with optional week and type filters.
    """
    blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False)
    if type:
        blocks = [b for b in blocks if b.type == type]
    return DataResponse(data=blocks)


@router.post("", response_model=DataResponse[BlockOut], status_code=status.HTTP_201_CREATED)
def create_block(
    body: BlockCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Add a new recurring class timetable section or work shift.
    Enforces user_id isolation from JWT token.
    """
    block_dict = {
        "user_id": current_user.user_id,
        "type": body.type,
        "title": body.title,
        "location": body.location,
        "day_of_week": body.day_of_week,
        "start_time": str(body.start_time),
        "end_time": str(body.end_time),
        "effective_from": body.effective_from or date(2026, 9, 1),
        "effective_until": body.effective_until,
        "is_flexible": body.is_flexible,
        "hourly_wage": body.hourly_wage,
        "course_id": body.course_id,
    }
    new_block = add_block_to_store(block_dict, user_id=current_user.user_id)
    return DataResponse(data=new_block)


@router.patch("/{block_id}", response_model=DataResponse[BlockOut])
def update_block(
    body: BlockUpdate,
    block_id: int = Path(..., description="ID of the block to update"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update details of an existing time block and persist changes.
    Enforces user_id ownership check.
    """
    updates = body.model_dump(exclude_unset=True)
    if "start_time" in updates:
        updates["start_time"] = str(updates["start_time"])
    if "end_time" in updates:
        updates["end_time"] = str(updates["end_time"])

    updated = update_block_in_store(block_id, updates, user_id=current_user.user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with id {block_id} not found",
        )
    return DataResponse(data=updated)


@router.delete("/{block_id}", response_model=DataResponse[DeletedData])
def delete_block(
    block_id: int = Path(..., description="ID of the block to soft-delete"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Soft-delete a block (sets deleted = True).
    Enforces user_id ownership check.
    """
    deleted = delete_block_from_store(block_id, user_id=current_user.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with id {block_id} not found",
        )
    return DataResponse(data=DeletedData(deleted=True))


@router.post("/{block_id}/duplicate", response_model=DataResponse[BlockOut])
def duplicate_block(
    body: BlockDuplicate,
    block_id: int = Path(..., description="ID of the source block to duplicate"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Duplicate a block with an optional offset in days.
    Enforces user_id ownership check.
    """
    source = get_block_by_id(block_id, user_id=current_user.user_id)
    if not source or source.get("deleted"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with id {block_id} not found",
        )

    target_day = (source["day_of_week"] + body.days_offset) % 7
    dup_data = dict(source)
    dup_data.pop("id", None)
    dup_data["title"] = f"{source['title']} (Copy)"
    dup_data["day_of_week"] = target_day
    dup_data["user_id"] = current_user.user_id
    new_block = add_block_to_store(dup_data, user_id=current_user.user_id)
    return DataResponse(data=new_block)

