"""
Tasks & Study Planner Router
Endpoints for managing study tasks, generating free-gap study plans,
confirming study blocks, and dynamic replanning.
"""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse, DeletedData
from app.schemas.task import (
    CourseBrief,
    PlanConfirmBlock,
    PlanConfirmRequest,
    PlanResponse,
    StudyTaskCreate,
    StudyTaskOut,
    StudyTaskUpdate,
)
from app.services.planner import find_free_gaps, plan_study_blocks
from app.services.schedule import get_user_zoneinfo, time_to_minutes
from app.services.timezone_helper import get_user_today
from app.store import (
    add_block_to_store,
    create_task_in_store,
    delete_study_blocks_for_task,
    delete_task_in_store,
    get_all_blocks,
    get_task_by_id,
    get_user_tasks,
    update_task_in_store,
)

router = APIRouter(prefix="/tasks", tags=["Study Planner"])


def _get_course_brief(course_id: Optional[int], user_id: int) -> Optional[CourseBrief]:
    if not course_id:
        return None
    try:
        from app.database import SessionLocal
        from app.models.course import Course
        with SessionLocal() as db:
            c = db.query(Course).filter(Course.id == course_id, Course.user_id == user_id).first()
            if c:
                return CourseBrief(id=c.id, code=c.code, name=c.name, color=c.color)
    except Exception:
        pass
    return None


def _enrich_task(task_dict: dict, user_id: int, current_user: CurrentUser) -> StudyTaskOut:
    """
    Computes hours_scheduled, hours_done, and auto-updates status if completed.
    """
    task_id = task_dict["id"]
    total_hours = float(task_dict.get("total_hours_required", 0.0))

    tz = get_user_zoneinfo(current_user.timezone)
    now_tz = datetime.now(tz)
    now_minutes = now_tz.hour * 60 + now_tz.minute
    today_d, today_dow = get_user_today(current_user)

    # Get all active blocks for this user
    all_blocks = get_all_blocks(user_id=user_id, include_deleted=False)
    task_study_blocks = [
        b for b in all_blocks
        if getattr(b, "study_task_id", None) == task_id
    ]

    hours_scheduled = 0.0
    hours_done = 0.0

    for b in task_study_blocks:
        s_min = time_to_minutes(b.start_time)
        e_min = time_to_minutes(b.end_time)
        dur = (e_min + 24 * 60 - s_min) if e_min < s_min else (e_min - s_min)
        hrs = max(0.0, dur / 60.0)
        hours_scheduled += hrs

        # Determine if block is in the past
        is_past = False
        if getattr(b, "specific_date", None):
            b_date = b.specific_date if isinstance(b.specific_date, date) else date.fromisoformat(str(b.specific_date))
            if b_date < today_d:
                is_past = True
            elif b_date == today_d and e_min <= now_minutes:
                is_past = True
        else:
            if b.day_of_week < today_dow:
                is_past = True
            elif b.day_of_week == today_dow and e_min <= now_minutes:
                is_past = True

        if is_past:
            hours_done += hrs

    # Stored completed_hours can take precedence if manually marked done
    stored_completed = float(task_dict.get("completed_hours") or 0.0)
    effective_hours_done = max(hours_done, stored_completed)

    # Auto-update status to 'done' if completed
    current_status = task_dict.get("status", "pending")
    if effective_hours_done >= total_hours and total_hours > 0 and current_status != "done":
        current_status = "done"
        task_dict["status"] = "done"
        update_task_in_store(task_id, {"status": "done"}, user_id=user_id)

    deadline_val = task_dict["deadline"]
    if isinstance(deadline_val, str):
        deadline_val = date.fromisoformat(deadline_val)

    course_brief = _get_course_brief(task_dict.get("course_id"), user_id)

    return StudyTaskOut(
        id=task_dict["id"],
        user_id=user_id,
        title=task_dict["title"],
        course_id=task_dict.get("course_id"),
        course=course_brief,
        total_hours_required=total_hours,
        deadline=deadline_val,
        status=current_status,
        priority=task_dict.get("priority", "medium") or "medium",
        preferred_duration=int(task_dict.get("preferred_duration", 90) or 90),
        completed_hours=round(effective_hours_done, 1),
        hours_scheduled=round(hours_scheduled, 1),
        hours_done=round(effective_hours_done, 1),
        created_at=task_dict.get("created_at"),
    )


@router.get("", response_model=DataResponse[list[StudyTaskOut]])
def list_tasks(current_user: CurrentUser = Depends(get_current_user)):
    """
    Lists all study tasks with progress tracking:
    - hours_scheduled: sum of study blocks scheduled for this task
    - hours_done: study blocks that have elapsed in the past
    - auto-marks done if hours_done >= total_hours_required
    """
    raw_tasks = get_user_tasks(user_id=current_user.user_id)
    enriched = [_enrich_task(t, current_user.user_id, current_user) for t in raw_tasks]
    return DataResponse(data=enriched)


@router.post("", response_model=DataResponse[StudyTaskOut], status_code=status.HTTP_201_CREATED)
def create_task(
    body: StudyTaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Creates a new assignment or exam study task.
    """
    new_task = create_task_in_store(
        {
            "title": body.title,
            "course_id": body.course_id,
            "total_hours_required": float(body.total_hours_required),
            "deadline": body.deadline.isoformat(),
            "status": "pending",
            "priority": body.priority or "medium",
            "preferred_duration": body.preferred_duration or 90,
            "completed_hours": 0.0,
        },
        user_id=current_user.user_id,
    )
    enriched = _enrich_task(new_task, current_user.user_id, current_user)
    return DataResponse(data=enriched)


@router.patch("/{task_id}", response_model=DataResponse[StudyTaskOut])
def update_task(
    body: StudyTaskUpdate,
    task_id: int = Path(..., description="ID of the study task to update"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Updates an existing study task.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    updates = body.dict(exclude_unset=True)
    updated = update_task_in_store(task_id, updates, user_id=current_user.user_id)
    enriched = _enrich_task(updated, current_user.user_id, current_user)
    return DataResponse(data=enriched)


@router.delete("/{task_id}", response_model=DataResponse[DeletedData])
def delete_task(
    task_id: int = Path(..., description="ID of the study task to delete"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Deletes task and removes all its associated study blocks from the calendar.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    delete_task_in_store(task_id, user_id=current_user.user_id)
    return DataResponse(data=DeletedData(deleted=True))


@router.post("/{task_id}/plan", response_model=DataResponse[PlanResponse])
def plan_task(
    task_id: int = Path(..., description="Task ID to generate study plan for"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Runs gap-finding and scheduling algorithm.
    Does NOT modify database. Returns preview of suggested study slots with quality scores and reasons.
    Respects remaining needed hours (accounting for completed partial goals) and preferred duration.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    today_d, _ = get_user_today(current_user)
    deadline_val = task["deadline"]
    if isinstance(deadline_val, str):
        deadline_d = date.fromisoformat(deadline_val)
    else:
        deadline_d = deadline_val

    gaps = find_free_gaps(
        current_user=current_user,
        start_date=today_d,
        deadline_date=deadline_d,
        exclude_task_id=task_id,
    )

    enriched = _enrich_task(task, current_user.user_id, current_user)
    remaining_hours = max(0.0, float(task["total_hours_required"]) - enriched.hours_done)
    preferred_dur = int(task.get("preferred_duration", 90) or 90)

    plan = plan_study_blocks(
        task_id=task_id,
        total_hours_required=remaining_hours,
        deadline_date=deadline_d,
        current_user=current_user,
        gaps=gaps,
        preferred_duration_min=preferred_dur,
    )

    return DataResponse(data=plan)


@router.post("/{task_id}/plan/add-slot", response_model=DataResponse[StudyTaskOut])
def add_single_study_slot(
    body: PlanConfirmBlock,
    task_id: int = Path(..., description="Task ID to add study session for"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Approves and inserts a single study block directly into time_blocks.
    Runs class collision safety check: rejects with 422 if it overlaps a class.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    # Class collision safety check
    all_blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False)
    class_blocks = [b for b in all_blocks if b.type == "class"]

    prop_s = time_to_minutes(body.start_time)
    prop_e = time_to_minutes(body.end_time)

    for cb in class_blocks:
        if cb.day_of_week == body.day_of_week:
            cls_s = time_to_minutes(cb.start_time)
            cls_e = time_to_minutes(cb.end_time)
            if prop_s < cls_e and cls_s < prop_e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "class_clash",
                        "message": f"Study session ({body.start_time}–{body.end_time}) clashes with class: {cb.title}",
                    },
                )

    # Insert study block into store
    block_dict = {
        "type": "study",
        "title": f"Study: {task['title']}",
        "location": "Self-study",
        "day_of_week": body.day_of_week,
        "start_time": body.start_time if len(body.start_time) == 8 else f"{body.start_time[:5]}:00",
        "end_time": body.end_time if len(body.end_time) == 8 else f"{body.end_time[:5]}:00",
        "course_id": task.get("course_id"),
        "study_task_id": task_id,
        "color": "#8B5CF6",
        "is_flexible": True,
        "hourly_wage": None,
        "deleted": False,
    }
    add_block_to_store(block_dict, user_id=current_user.user_id)

    if task.get("status") == "pending":
        update_task_in_store(task_id, {"status": "scheduled"}, user_id=current_user.user_id)

    updated_task = get_task_by_id(task_id, user_id=current_user.user_id)
    enriched = _enrich_task(updated_task, current_user.user_id, current_user)
    return DataResponse(data=enriched)


@router.post("/{task_id}/complete", response_model=DataResponse[StudyTaskOut])
def complete_task(
    task_id: int = Path(..., description="Task ID to mark complete"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Marks a study task as completed and syncs completed_hours.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    updated = update_task_in_store(
        task_id,
        {
            "status": "done",
            "completed_hours": float(task["total_hours_required"]),
        },
        user_id=current_user.user_id,
    )
    enriched = _enrich_task(updated, current_user.user_id, current_user)
    return DataResponse(data=enriched)


@router.post("/{task_id}/plan/confirm", response_model=DataResponse[StudyTaskOut])
def confirm_task_plan(
    body: PlanConfirmRequest,
    task_id: int = Path(..., description="Task ID to confirm study plan for"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Approves and inserts suggested study blocks into time_blocks.
    Runs class collision safety check: rejects with 422 if any block overlaps a class.
    Sets task.status = 'scheduled'.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    # 1. Class collision safety check
    all_blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False)
    class_blocks = [b for b in all_blocks if b.type == "class"]

    for approved in body.approved_blocks:
        prop_s = time_to_minutes(approved.start_time)
        prop_e = time_to_minutes(approved.end_time)

        for cb in class_blocks:
            if cb.day_of_week == approved.day_of_week:
                cls_s = time_to_minutes(cb.start_time)
                cls_e = time_to_minutes(cb.end_time)
                # Overlap condition: s1 < e2 and s2 < e1
                if prop_s < cls_e and cls_s < prop_e:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "code": "class_clash",
                            "message": f"Study session ({approved.start_time}–{approved.end_time}) clashes with class: {cb.title}",
                        },
                    )

    # 2. Insert approved study blocks into store
    for approved in body.approved_blocks:
        block_dict = {
            "type": "study",
            "title": f"Study: {task['title']}",
            "location": "Self-study",
            "day_of_week": approved.day_of_week,
            "start_time": approved.start_time if len(approved.start_time) == 8 else f"{approved.start_time[:5]}:00",
            "end_time": approved.end_time if len(approved.end_time) == 8 else f"{approved.end_time[:5]}:00",
            "course_id": task.get("course_id"),
            "study_task_id": task_id,
            "color": "#8B5CF6",  # Purple
            "is_flexible": True,
            "hourly_wage": None,
            "deleted": False,
        }
        add_block_to_store(block_dict, user_id=current_user.user_id)

    # 3. Mark task scheduled
    update_task_in_store(task_id, {"status": "scheduled"}, user_id=current_user.user_id)
    updated_task = get_task_by_id(task_id, user_id=current_user.user_id)

    enriched = _enrich_task(updated_task, current_user.user_id, current_user)
    return DataResponse(data=enriched)


@router.post("/{task_id}/replan", response_model=DataResponse[PlanResponse])
def replan_task(
    task_id: int = Path(..., description="Task ID to replan"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Deletes FUTURE study blocks for this task (keeping past completed blocks),
    re-runs the gap-finding and planner with remaining needed hours,
    and returns a fresh preview.
    """
    task = get_task_by_id(task_id, user_id=current_user.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": f"Task {task_id} not found"},
        )

    tz = get_user_zoneinfo(current_user.timezone)
    now_tz = datetime.now(tz)
    now_minutes = now_tz.hour * 60 + now_tz.minute
    today_d, today_dow = get_user_today(current_user)

    # 1. Delete future study blocks for this task
    delete_study_blocks_for_task(
        task_id=task_id,
        future_only=True,
        now_dow=today_dow,
        now_minutes=now_minutes,
    )

    # 2. Calculate remaining hours needed
    enriched = _enrich_task(task, current_user.user_id, current_user)
    remaining_hours = max(0.0, enriched.total_hours_required - enriched.hours_done)

    deadline_val = task["deadline"]
    deadline_d = date.fromisoformat(deadline_val) if isinstance(deadline_val, str) else deadline_val

    # 3. Find free gaps and plan
    gaps = find_free_gaps(
        current_user=current_user,
        start_date=today_d,
        deadline_date=deadline_d,
        exclude_task_id=task_id,
    )

    plan = plan_study_blocks(
        task_id=task_id,
        total_hours_required=remaining_hours,
        deadline_date=deadline_d,
        current_user=current_user,
        gaps=gaps,
    )

    return DataResponse(data=plan)
