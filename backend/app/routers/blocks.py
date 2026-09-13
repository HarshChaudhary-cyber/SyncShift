from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.schemas.block import (
    BlockCreate,
    BlockDuplicate,
    BlockExceptionCreate,
    BlockOut,
    BlockUpdate,
)
from app.schemas.common import DataResponse, DeletedData
from app.services.audit import record_audit_log
from app.services.reminders import notify_conflict_if_applicable
from app.store import (
    add_block_to_store,
    create_or_update_override,
    delete_block_from_store,
    delete_recurring_scope,
    detect_conflicts_and_totals,
    get_all_blocks,
    get_block_by_id,
    get_occurrences_for_range,
    split_recurring_block,
    update_block_in_store,
)
from sqlalchemy.orm import Session



router = APIRouter(prefix="/blocks", tags=["Time Blocks"])


@router.get("", response_model=DataResponse[list[BlockOut]])
def get_blocks(
    week_start: Optional[date] = Query(None, description="Filter blocks active during the week of week_start"),
    type: Optional[str] = Query(None, pattern="^(class|shift)$", description="Filter by block type ('class' or 'shift')"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve active time blocks for the user. If week_start is supplied, returns
    materialized occurrences for that week (with biweekly, non-recurring, and single-occurrence exceptions applied).
    """
    if week_start is not None:
        week_end = week_start + timedelta(days=6)
        blocks = get_occurrences_for_range(
            user_id=current_user.user_id,
            start_date=week_start,
            end_date=week_end,
            db=db,
        )
    else:
        blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False, db=db)

    if type:
        blocks = [b for b in blocks if b.type == type]
    return DataResponse(data=blocks)


@router.get("/{block_id}", response_model=DataResponse[BlockOut])
def get_single_block(
    block_id: int = Path(..., description="ID of the block to retrieve"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific time block by ID.
    Strictly isolated to authenticated user. Returns 404 if not found or owned by another student (IDOR defense).
    """
    raw = get_block_by_id(block_id, user_id=current_user.user_id, db=db)
    if not raw or raw.get("deleted"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Block {block_id} not found"},
        )
    return DataResponse(data=BlockOut(**raw))


def _check_and_notify_new_conflicts(user_id: int, target_block_id: int, db: Session):
    try:
        conflicts, _ = detect_conflicts_and_totals(user_id=user_id, db=db)
        for c in conflicts:
            if c.block_a_id == target_block_id or c.block_b_id == target_block_id:
                b_a = get_block_by_id(c.block_a_id, user_id=user_id, db=db)
                b_b = get_block_by_id(c.block_b_id, user_id=user_id, db=db)
                title_a = b_a.get("title", "Block A") if b_a else "Block A"
                title_b = b_b.get("title", "Block B") if b_b else "Block B"
                notify_conflict_if_applicable(
                    user_id=user_id,
                    block_a_title=title_a,
                    block_b_title=title_b,
                    db=db,
                    block_a_id=c.block_a_id,
                    block_b_id=c.block_b_id,
                )
    except Exception:
        pass


@router.post("", response_model=DataResponse[BlockOut], status_code=status.HTTP_201_CREATED)
def create_block(
    body: BlockCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a new recurring class timetable section, work shift, or non-recurring event.
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
        "is_recurring": body.is_recurring,
        "recurrence_interval": body.recurrence_interval or 1,
        "specific_date": body.specific_date,
        "effective_from": body.effective_from or date(2026, 9, 1),
        "effective_until": body.effective_until,
        "is_flexible": body.is_flexible,
        "hourly_wage": body.hourly_wage,
        "course_id": body.course_id,
    }
    new_block = add_block_to_store(block_dict, user_id=current_user.user_id, db=db)
    _check_and_notify_new_conflicts(current_user.user_id, new_block.id, db)
    record_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="BLOCK_CREATED",
        entity_type="time_block",
        entity_id=new_block.id,
        description=f"Created {new_block.type} block: {new_block.title}",
        request=request,
    )
    return DataResponse(data=new_block)


@router.patch("/{block_id}", response_model=DataResponse[BlockOut])
def update_block(
    body: BlockUpdate,
    request: Request,
    block_id: int = Path(..., description="ID of the block to update"),
    scope: Optional[str] = Query(None, pattern="^(this|future|all)$", description="Scope of update"),
    occurrence_date: Optional[date] = Query(None, description="Date of occurrence if updating 'this' or 'future'"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    """
    Update details of an existing time block with recurrence scope support:
    - scope: "this" -> modifies only the occurrence on occurrence_date via BlockOverride
    - scope: "future" -> splits series starting at occurrence_date
    - scope: "all" -> updates the entire series definition
    """
    updates = body.model_dump(exclude_unset=True)
    active_scope = scope or updates.get("scope") or "all"
    active_date = occurrence_date or updates.get("occurrence_date")
    if isinstance(active_date, str):
        active_date = date.fromisoformat(active_date)

    if "start_time" in updates and updates["start_time"] is not None:
        updates["start_time"] = str(updates["start_time"])
    if "end_time" in updates and updates["end_time"] is not None:
        updates["end_time"] = str(updates["end_time"])

    # 1. Single occurrence override
    if active_scope == "this" and active_date:
        override_fields = {}
        for k in ("start_time", "end_time", "title", "location", "override_date"):
            if k in updates:
                override_fields[k] = updates[k]

        ov = create_or_update_override(
            user_id=current_user.user_id,
            block_id=block_id,
            original_date=active_date,
            override_data=override_fields,
            db=db,
        )
        base = get_block_by_id(block_id, user_id=current_user.user_id, db=db)
        if not base:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Block {block_id} not found")

        # Return synthesized occurrence
        st = ov.start_time.strftime("%H:%M:00") if ov.start_time else base["start_time"]
        et = ov.end_time.strftime("%H:%M:00") if ov.end_time else base["end_time"]
        res_block = BlockOut(
            id=block_id,
            user_id=current_user.user_id,
            type=base["type"],
            title=ov.title or base["title"],
            location=ov.location if ov.location is not None else base.get("location"),
            day_of_week=base["day_of_week"],
            start_time=st,
            end_time=et,
            is_recurring=base["is_recurring"],
            recurrence_interval=base["recurrence_interval"],
            occurrence_date=ov.override_date or active_date,
            is_exception=True,
            original_date=active_date,
            override_id=ov.id,
            hourly_wage=base.get("hourly_wage"),
            course_id=base.get("course_id"),
        )
        _check_and_notify_new_conflicts(current_user.user_id, block_id, db)
        record_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="BLOCK_UPDATED",
            entity_type="time_block",
            entity_id=block_id,
            description=f"Updated single occurrence of block #{block_id}",
            request=request,
        )
        return DataResponse(data=res_block)

    # 2. This and future split
    elif active_scope == "future" and active_date:
        updated = split_recurring_block(
            user_id=current_user.user_id,
            block_id=block_id,
            split_date=active_date,
            updates=updates,
            db=db,
        )
        _check_and_notify_new_conflicts(current_user.user_id, updated.id, db)
        record_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="BLOCK_UPDATED",
            entity_type="time_block",
            entity_id=updated.id,
            description=f"Split block series starting from {active_date}",
            request=request,
        )
        return DataResponse(data=updated)

    # 3. Entire series update
    else:
        updated = update_block_in_store(block_id, updates, user_id=current_user.user_id, db=db)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block with id {block_id} not found",
            )
        _check_and_notify_new_conflicts(current_user.user_id, updated.id, db)
        record_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="BLOCK_UPDATED",
            entity_type="time_block",
            entity_id=block_id,
            description=f"Updated time block #{block_id}",
            request=request,
        )
        return DataResponse(data=updated)


@router.delete("/{block_id}", response_model=DataResponse[DeletedData])
def delete_block(
    request: Request,
    block_id: int = Path(..., description="ID of the block to delete"),
    scope: Optional[str] = Query("all", pattern="^(this|future|all)$", description="Scope of deletion"),
    occurrence_date: Optional[date] = Query(None, description="Date of occurrence if deleting 'this' or 'future'"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a time block with recurrence scope support:
    - scope="this" & occurrence_date: cancels only that single occurrence
    - scope="future" & occurrence_date: ends the recurrence before occurrence_date
    - scope="all": soft-deletes the entire series
    """
    deleted = delete_recurring_scope(
        user_id=current_user.user_id,
        block_id=block_id,
        scope=scope or "all",
        occurrence_date=occurrence_date,
        db=db,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with id {block_id} not found",
        )
    record_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="BLOCK_DELETED",
        entity_type="time_block",
        entity_id=block_id,
        description=f"Deleted block #{block_id} (scope: {scope or 'all'})",
        request=request,
    )
    return DataResponse(data=DeletedData(deleted=True))



@router.post("/{block_id}/exceptions", response_model=DataResponse[BlockOut])
def add_block_exception(
    body: BlockExceptionCreate,
    block_id: int = Path(..., description="ID of the parent recurring block"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Explicit endpoint to cancel or modify a single occurrence of a recurring block.
    """
    ov_dict = body.model_dump(exclude_unset=True)
    ov = create_or_update_override(
        user_id=current_user.user_id,
        block_id=block_id,
        original_date=body.original_date,
        override_data=ov_dict,
        db=db,
    )
    base = get_block_by_id(block_id, user_id=current_user.user_id, db=db)
    if not base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Block {block_id} not found")

    st = ov.start_time.strftime("%H:%M:00") if ov.start_time else base["start_time"]
    et = ov.end_time.strftime("%H:%M:00") if ov.end_time else base["end_time"]

    res_block = BlockOut(
        id=block_id,
        user_id=current_user.user_id,
        type=base["type"],
        title=ov.title or base["title"],
        location=ov.location if ov.location is not None else base.get("location"),
        day_of_week=base["day_of_week"],
        start_time=st,
        end_time=et,
        is_recurring=base["is_recurring"],
        recurrence_interval=base["recurrence_interval"],
        occurrence_date=ov.override_date or body.original_date,
        is_exception=True,
        original_date=body.original_date,
        override_id=ov.id,
        hourly_wage=base.get("hourly_wage"),
        course_id=base.get("course_id"),
    )
    _check_and_notify_new_conflicts(current_user.user_id, block_id, db)
    return DataResponse(data=res_block)


@router.post("/{block_id}/duplicate", response_model=DataResponse[BlockOut])
def duplicate_block(
    body: BlockDuplicate,
    block_id: int = Path(..., description="ID of the source block to duplicate"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Duplicate a block with an optional offset in days.
    Enforces user_id ownership check.
    """
    source = get_block_by_id(block_id, user_id=current_user.user_id, db=db)
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
    new_block = add_block_to_store(dup_data, user_id=current_user.user_id, db=db)
    _check_and_notify_new_conflicts(current_user.user_id, new_block.id, db)
    return DataResponse(data=new_block)
