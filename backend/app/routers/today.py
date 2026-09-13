from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, get_current_user
from app.schemas.block import BlockOut
from app.schemas.common import DataResponse
from app.schemas.today import TodayViewData
from app.services.timezone_helper import get_user_today
from app.store import detect_conflicts_and_totals, get_all_blocks

from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/today", tags=["Today View"])


def _to_minutes(time_str: str) -> int:
    parts = str(time_str).split(":")
    return int(parts[0]) * 60 + int(parts[1])


@router.get("", response_model=DataResponse[TodayViewData])
def get_today_schedule(
    target_date: Optional[str] = Query(
        None,
        alias="date",
        description="Optional override date (YYYY-MM-DD) for previewing/testing",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Convenience endpoint returning today's schedule in the user's registered timezone:
    - User's active blocks occurring today, sorted by start_time
    - Detected conflicts among today's blocks
    - Calculated total shift hours, class hours, and expected earnings
    """
    # 1. Resolve today's date & day_of_week in user's timezone
    if target_date:
        try:
            today_d = date.fromisoformat(target_date)
            today_dow = (today_d.weekday() + 1) % 7
        except ValueError:
            today_d, today_dow = get_user_today(current_user)
    else:
        today_d, today_dow = get_user_today(current_user)

    # 3. Fetch user blocks and filter by today's day of week & effective dates
    all_blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False, db=db)
    today_blocks: list[BlockOut] = []

    # Map courses to colors
    from app.services.schedule import get_course_colors
    course_color_map: dict[int, str] = get_course_colors(current_user.user_id)

    for b in all_blocks:
        if b.day_of_week != today_dow:
            continue
        # Verify date range if specified
        if b.effective_from and today_d < b.effective_from:
            continue
        if b.effective_until and today_d > b.effective_until:
            continue

        # Assign color if not already set
        color = b.color
        if not color:
            if b.type == "shift":
                color = "#10b981"  # Emerald
            elif b.course_id and b.course_id in course_color_map:
                color = course_color_map[b.course_id]
            else:
                color = "#3b82f6"  # Blue

        # Create a shallow copy with color
        b_with_color = BlockOut(
            id=b.id,
            user_id=b.user_id,
            type=b.type,
            title=b.title,
            location=b.location,
            day_of_week=b.day_of_week,
            start_time=b.start_time,
            end_time=b.end_time,
            effective_from=b.effective_from,
            effective_until=b.effective_until,
            is_flexible=b.is_flexible,
            hourly_wage=b.hourly_wage,
            course_id=b.course_id,
            color=color,
        )
        today_blocks.append(b_with_color)

    # 4. Sort blocks chronologically by start_time
    today_blocks.sort(key=lambda item: _to_minutes(item.start_time))

    # 5. Compute shift_hours, class_hours, and expected_earnings
    shift_hours = 0.0
    class_hours = 0.0
    expected_earnings = 0.0

    for b in today_blocks:
        s = _to_minutes(b.start_time)
        e = _to_minutes(b.end_time)
        dur = (e + 24 * 60 - s) if e < s else (e - s)
        hours = max(0.0, dur / 60.0)

        if b.type == "shift":
            shift_hours += hours
            wage = b.hourly_wage or 0.0
            expected_earnings += hours * wage
        elif b.type == "class":
            class_hours += hours

    # 6. Detect conflicts among today's blocks
    today_block_ids = {b.id for b in today_blocks}
    all_conflicts, _ = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=current_user.weekly_work_hour_limit or 20.0,
    )
    today_conflicts = [
        c
        for c in all_conflicts
        if c.block_a_id in today_block_ids and c.block_b_id in today_block_ids
    ]

    return DataResponse(
        data=TodayViewData(
            date=today_d.isoformat(),
            day_of_week=today_dow,
            blocks=today_blocks,
            conflicts=today_conflicts,
            shift_hours=round(shift_hours, 1),
            expected_earnings=round(expected_earnings, 2),
            class_hours=round(class_hours, 1),
        )
    )
