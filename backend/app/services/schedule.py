"""
Schedule & Timetable Shared Service
Consolidates today's timetable, next up countdown, week metrics,
conflict detection, and dashboard alerts.
"""
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.dependencies import CurrentUser
from app.schemas.conflict import ConflictItem
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardBlock,
    DashboardNextUp,
    DashboardToday,
    DashboardUser,
    DashboardWeek,
    NextUpBlock,
)
from app.services.timezone_helper import get_user_today
from app.store import detect_conflicts_and_totals, get_occurrences_for_range, get_all_blocks


def time_to_minutes(time_str: str) -> int:
    parts = str(time_str).split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time(m: int) -> str:
    m = m % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def get_user_zoneinfo(timezone_str: Optional[str]) -> ZoneInfo:
    if timezone_str:
        try:
            return ZoneInfo(timezone_str)
        except (ZoneInfoNotFoundError, ValueError, KeyError, Exception):
            pass
    try:
        return ZoneInfo("Europe/London")
    except Exception:
        return ZoneInfo("UTC")


def get_course_colors(user_id: int) -> dict[int, str]:
    course_color_map: dict[int, str] = {}
    try:
        from app.database import SessionLocal
        from app.models.course import Course
        with SessionLocal() as db:
            courses = db.query(Course).filter(Course.user_id == user_id).all()
            for c in courses:
                course_color_map[c.id] = c.color
    except Exception:
        pass
    return course_color_map


def get_today_schedule_data(
    current_user: CurrentUser,
    target_date: Optional[str] = None,
) -> tuple[DashboardToday, int]:
    """
    Computes today's schedule for the student in their registered timezone:
    - Active occurrences occurring today (with recurrence & exceptions applied), sorted by start_time
    - is_now flag indicating if current time falls within start and end time
    - Today's conflicts, shift_hours, class_hours, and expected_earnings
    Returns (DashboardToday, now_minutes_in_user_tz)
    """
    tz = get_user_zoneinfo(current_user.timezone)
    now_tz = datetime.now(tz)
    now_minutes = now_tz.hour * 60 + now_tz.minute

    if target_date:
        try:
            today_d = date.fromisoformat(target_date)
            today_dow = (today_d.weekday() + 1) % 7
        except ValueError:
            today_d, today_dow = get_user_today(current_user)
    else:
        today_d, today_dow = get_user_today(current_user)

    is_current_calendar_day = (today_d == now_tz.date())

    # Generate actual occurrences for today (including biweekly, single-occurrence modifications & cancellations)
    today_occurrences = get_occurrences_for_range(
        user_id=current_user.user_id,
        start_date=today_d,
        end_date=today_d,
    )
    course_colors = get_course_colors(current_user.user_id)

    today_blocks: list[DashboardBlock] = []

    for b in today_occurrences:
        s_min = time_to_minutes(b.start_time)
        e_min = time_to_minutes(b.end_time)

        # is_now is True if today is current date and current time is within [start_time, end_time)
        is_now = False
        if is_current_calendar_day:
            if e_min > s_min:
                is_now = (s_min <= now_minutes < e_min)
            else:
                # Overnight block
                is_now = (now_minutes >= s_min or now_minutes < e_min)

        color = b.color
        if not color:
            if b.type == "shift":
                color = "#10B981"  # Emerald
            elif b.course_id and b.course_id in course_colors:
                color = course_colors[b.course_id]
            elif b.type == "study":
                color = "#8B5CF6"  # Purple
            else:
                color = "#4F46E5"  # Indigo

        today_blocks.append(
            DashboardBlock(
                id=b.id,
                type=b.type,
                title=b.title,
                start_time=b.start_time[:5],
                end_time=b.end_time[:5],
                location=b.location,
                color=color,
                is_now=is_now,
                day_of_week=b.day_of_week,
                occurrence_date=today_d.isoformat(),
                is_exception=bool(getattr(b, "is_exception", False)),
            )
        )

    # Sort blocks chronologically by start_time
    today_blocks.sort(key=lambda b: time_to_minutes(b.start_time))

    # Calculate hours and expected earnings from actual occurrences
    shift_hours = 0.0
    class_hours = 0.0
    expected_earnings = 0.0

    for tb in today_occurrences:
        s = time_to_minutes(tb.start_time)
        e = time_to_minutes(tb.end_time)
        dur = (e + 24 * 60 - s) if e < s else (e - s)
        hrs = max(0.0, dur / 60.0)

        if tb.type == "shift":
            shift_hours += hrs
            wage = getattr(tb, "hourly_wage", None) or 0.0
            expected_earnings += hrs * float(wage)
        elif tb.type == "class":
            class_hours += hrs

    # Today conflicts (computed for this week aligned to Monday)
    week_start = today_d - timedelta(days=today_d.weekday())
    all_conflicts, _ = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=current_user.weekly_work_hour_limit or 20.0,
        week_start=week_start,
    )
    today_block_ids = {b.id for b in today_blocks}
    today_conflicts = [
        c
        for c in all_conflicts
        if c.block_a_id in today_block_ids and c.block_b_id in today_block_ids and c.day_of_week == today_dow
    ]

    day_name = today_d.strftime("%A")

    today_data = DashboardToday(
        date=today_d.isoformat(),
        day_name=day_name,
        blocks=today_blocks,
        conflicts=today_conflicts,
        shift_hours=round(shift_hours, 1),
        class_hours=round(class_hours, 1),
        expected_earnings=round(expected_earnings, 2),
    )

    return today_data, now_minutes


def get_next_up_block(
    today_blocks: list[DashboardBlock],
    now_minutes: int,
) -> Optional[DashboardNextUp]:
    """
    Finds the next relevant block today:
    - If a block is currently in progress, highlights it as "In progress"
    - Otherwise finds the first upcoming block today where start_time > now_minutes
    """
    # 1. Check if an event is currently happening
    for b in today_blocks:
        s_min = time_to_minutes(b.start_time)
        e_min = time_to_minutes(b.end_time)
        if (e_min > s_min and s_min <= now_minutes < e_min) or (e_min <= s_min and (now_minutes >= s_min or now_minutes < e_min)):
            remaining = (e_min - now_minutes) if e_min > now_minutes else (e_min + 24 * 60 - now_minutes)
            return DashboardNextUp(
                block=NextUpBlock(
                    id=b.id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    location=b.location,
                    type=b.type,
                    color=b.color,
                    occurrence_date=b.occurrence_date,
                ),
                minutes_until=0,
                label=f"{b.title} in progress ({remaining}m left)",
            )

    # 2. Check for upcoming event today
    for b in today_blocks:
        s_min = time_to_minutes(b.start_time)
        if s_min > now_minutes:
            minutes_until = s_min - now_minutes
            if minutes_until < 60:
                label = f"{b.title} in {minutes_until}m"
            else:
                hours = minutes_until // 60
                mins = minutes_until % 60
                label = f"{b.title} in {hours}h {mins}m" if mins > 0 else f"{b.title} in {hours}h"

            return DashboardNextUp(
                block=NextUpBlock(
                    id=b.id,
                    title=b.title,
                    start_time=b.start_time,
                    end_time=b.end_time,
                    location=b.location,
                    type=b.type,
                    color=b.color,
                    occurrence_date=b.occurrence_date,
                ),
                minutes_until=minutes_until,
                label=label,
            )
    return None


def get_week_schedule_data(
    current_user: CurrentUser,
    week_start: Optional[date] = None,
) -> tuple[DashboardWeek, list[ConflictItem]]:
    """
    Calculates week statistics (Monday-Sunday) in the user's timezone:
    - total_shift_hours
    - total_class_hours
    - expected_earnings
    - conflict_count
    - over_work_limit
    Uses actual occurrences active in this week.
    """
    if week_start is None:
        today_d, _ = get_user_today(current_user)
        # Python weekday: Monday is 0, Sunday is 6
        week_start = today_d - timedelta(days=today_d.weekday())

    week_end = week_start + timedelta(days=6)
    work_limit = float(current_user.weekly_work_hour_limit or 20.0)

    conflicts, totals = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=work_limit,
        week_start=week_start,
    )

    over_work_limit = totals.shift_hours > work_limit

    week_data = DashboardWeek(
        start=week_start.isoformat(),
        end=week_end.isoformat(),
        total_shift_hours=totals.shift_hours,
        total_class_hours=totals.class_hours,
        expected_earnings=totals.expected_earnings,
        conflict_count=len(conflicts),
        over_work_limit=over_work_limit,
        work_limit=work_limit,
    )

    return week_data, conflicts


def get_dashboard_alerts(
    week_conflicts: list[ConflictItem],
    week_data: DashboardWeek,
    work_limit: float,
) -> list[DashboardAlert]:
    """
    Generates high-priority actionable alerts for the dashboard:
    - One entry per unresolved hard conflict this week
    - One warning if weekly work limit is exceeded
    """
    alerts: list[DashboardAlert] = []

    # 1. Hard conflicts
    for c in week_conflicts:
        if c.severity == "hard":
            day_map = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
            day_str = day_map.get(c.day_of_week or 1, "")
            msg = c.description or f"Schedule clash ({day_str} {c.overlap_start}–{c.overlap_end})"
            if day_str and day_str not in msg:
                msg = f"{msg} ({day_str} {c.overlap_start}–{c.overlap_end})"

            alerts.append(
                DashboardAlert(
                    id=f"conflict-{c.block_a_id}-{c.block_b_id}",
                    type="conflict",
                    severity="hard",
                    message=msg,
                    block_ids=[c.block_a_id, c.block_b_id],
                )
            )

    # 2. Work limit warning
    if week_data.over_work_limit:
        over = round(week_data.total_shift_hours - work_limit, 1)
        alerts.append(
            DashboardAlert(
                id="work-limit",
                type="work_limit",
                severity="warning",
                message=f"{week_data.total_shift_hours:g}h scheduled this week — {over:g}h over your {work_limit:g}h configured limit",
                block_ids=None,
            )
        )

    return alerts


def get_dashboard_recommendations(
    week_data: DashboardWeek,
    week_conflicts: list[ConflictItem],
    week_occurrences: list,
    tasks: list[dict],
    health_result: Optional[object] = None,
) -> list[str]:
    """
    Generates intelligent, deterministic recommendations based strictly on real schedule data.
    """
    recs: list[str] = []

    # 1. Hard conflicts
    hard_c = [c for c in week_conflicts if c.severity == "hard"]
    if hard_c:
        recs.append(f"🔴 You have {len(hard_c)} hard schedule clash{'es' if len(hard_c) > 1 else ''} needing resolution.")
    else:
        recs.append("✓ This week has no unresolved hard schedule conflicts.")

    # 2. Busiest day analysis
    day_hours: dict[str, float] = {}
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for occ in week_occurrences:
        dow = getattr(occ, "day_of_week", 1)
        name = day_names[dow % 7]
        s = time_to_minutes(occ.start_time)
        e = time_to_minutes(occ.end_time)
        dur = ((e + 24 * 60 - s) if e < s else (e - s)) / 60.0
        day_hours[name] = day_hours.get(name, 0.0) + dur

    if day_hours:
        busiest_day, max_h = max(day_hours.items(), key=lambda item: item[1])
        if max_h >= 7.0:
            recs.append(f"⚠ {busiest_day} is your busiest day with {round(max_h, 1):g}h scheduled.")

    # 3. Work capacity
    if week_data.over_work_limit:
        over = round(week_data.total_shift_hours - week_data.work_limit, 1)
        recs.append(f"💼 You are {over:g}h over your configured weekly work limit.")
    else:
        rem_work = round(max(0.0, week_data.work_limit - week_data.total_shift_hours), 1)
        if rem_work > 0:
            recs.append(f"💼 You have {rem_work:g}h of configured work capacity remaining.")
        else:
            recs.append("💼 You have reached your configured weekly work hour limit.")

    # 4. Study tasks
    pending_tasks = [
        t for t in tasks
        if t.get("status") != "done" and (t.get("completed_hours", 0) < t.get("total_hours_required", 0))
    ]
    if pending_tasks:
        first_t = sorted(pending_tasks, key=lambda x: str(x.get("deadline", "9999")))[0]
        rem_hrs = max(0.1, round(first_t.get("total_hours_required", 0) - first_t.get("completed_hours", 0), 1))
        recs.append(f"📚 You still need {rem_hrs:g}h for {first_t.get('title')} before deadline.")

    # 5. Health factor
    if health_result and hasattr(health_result, "improvements") and health_result.improvements:
        tip = health_result.improvements[0]
        if tip and not tip.startswith("Your schedule looks well-balanced"):
            recs.append(f"⚡ {tip}")

    return recs[:4]


def compute_adaptive_state(
    all_blocks: list,
    week_conflicts: list[ConflictItem],
    week_data: DashboardWeek,
) -> str:
    """
    Computes adaptive dashboard state:
    - new_user: zero blocks
    - academic_only: has classes but no shifts
    - has_conflicts: hard conflicts present
    - over_limit: shift hours exceed limit
    - near_limit: shift hours >= 80% of limit
    - on_track: balanced with no conflicts
    """
    if not all_blocks:
        return "new_user"

    has_shifts = any(getattr(b, "type", "") == "shift" for b in all_blocks)
    has_classes = any(getattr(b, "type", "") == "class" for b in all_blocks)

    if has_classes and not has_shifts:
        return "academic_only"

    hard_c = [c for c in week_conflicts if c.severity == "hard"]
    if hard_c:
        return "has_conflicts"

    if week_data.over_work_limit:
        return "over_limit"

    if week_data.work_limit > 0 and (week_data.total_shift_hours / week_data.work_limit) >= 0.8:
        return "near_limit"

    return "on_track"
