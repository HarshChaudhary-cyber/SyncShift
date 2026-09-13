"""
Smart Study Planner Service
Finds free gaps between classes and shifts, enforces 10-minute buffers,
and schedules balanced study blocks without schedule clashes.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from app.dependencies import CurrentUser
from app.schemas.task import PlanResponse, PlanSessionSuggested
from app.services.schedule import get_user_zoneinfo, minutes_to_time, time_to_minutes
from app.services.timezone_helper import get_user_today
from app.store import get_all_blocks, get_occurrences_for_range

MIN_GAP_MINUTES = 30
MAX_SESSION_MINUTES = 120  # 2 hours
MIN_SESSION_MINUTES = 30
MAX_DAILY_STUDY_MINUTES = 180  # 3 hours/day per task
BUFFER_MINUTES = 10  # 10 min rest/travel buffer between blocks


def find_free_gaps(
    current_user: CurrentUser,
    start_date: date,
    deadline_date: date,
    exclude_task_id: Optional[int] = None,
) -> list[dict]:
    """
    Finds available free time intervals (>= 30 mins) between start_date and deadline_date:
    1. Loads actual active occurrences for the user per day (accounting for recurrence, cancellations, and modifications).
    2. Merges overlapping busy intervals per day.
    3. Respects day bounds (08:00 - 22:00, 18:00 on deadline day).
    4. Enforces 10 min buffers before/after busy intervals.
    5. Discards past time on start_date.
    """
    tz = get_user_zoneinfo(current_user.timezone)
    now_tz = datetime.now(tz)
    now_minutes = now_tz.hour * 60 + now_tz.minute

    # Load all active occurrences across the entire planning window
    all_occurrences = get_occurrences_for_range(
        user_id=current_user.user_id,
        start_date=start_date,
        end_date=deadline_date,
    )

    # Exclude study blocks belonging to exclude_task_id (used when replanning)
    if exclude_task_id is not None:
        all_occurrences = [
            b for b in all_occurrences
            if getattr(b, "study_task_id", None) != exclude_task_id
        ]

    # Map occurrences by occurrence_date
    occurrences_by_date: dict[date, list] = {}
    for occ in all_occurrences:
        d = occ.occurrence_date or start_date
        if d not in occurrences_by_date:
            occurrences_by_date[d] = []
        occurrences_by_date[d].append(occ)

    gaps: list[dict] = []
    curr_d = start_date

    user_buffer = max(5, int(getattr(current_user, "minimum_transition_minutes", 10) or 10))

    while curr_d <= deadline_date:
        dow = (curr_d.weekday() + 1) % 7
        day_name = curr_d.strftime("%A")

        # 1. Determine day bounds
        day_start = 8 * 60  # 08:00 AM
        day_end = 22 * 60   # 10:00 PM

        # On the deadline day itself, study is allowed only until 18:00 (06:00 PM)
        if curr_d == deadline_date:
            day_end = min(day_end, 18 * 60)

        # On today, start after current time + buffer
        if curr_d == now_tz.date():
            day_start = max(day_start, now_minutes + user_buffer)

        if day_start >= day_end:
            curr_d += timedelta(days=1)
            continue

        # 2. Collect busy intervals on this day from actual occurrences
        busy_intervals: list[tuple[int, int]] = []
        day_blocks = occurrences_by_date.get(curr_d, [])
        for b in day_blocks:
            s = time_to_minutes(b.start_time)
            e = time_to_minutes(b.end_time)
            if e <= s:
                e += 24 * 60  # Handle overnight

            # Apply user transition buffer before and after each busy block
            b_start = max(0, s - user_buffer)
            b_end = min(24 * 60, e + user_buffer)
            busy_intervals.append((b_start, b_end))


        # 3. Sort and merge overlapping busy intervals
        busy_intervals.sort(key=lambda x: x[0])
        merged_busy: list[tuple[int, int]] = []
        for interval in busy_intervals:
            if not merged_busy:
                merged_busy.append(interval)
            else:
                last_s, last_e = merged_busy[-1]
                if interval[0] <= last_e:
                    merged_busy[-1] = (last_s, max(last_e, interval[1]))
                else:
                    merged_busy.append(interval)

        # 4. Find free gaps within [day_start, day_end]
        cursor = day_start
        for b_start, b_end in merged_busy:
            if b_end <= day_start:
                continue
            if b_start >= day_end:
                break

            if b_start > cursor:
                gap_len = b_start - cursor
                if gap_len >= MIN_GAP_MINUTES:
                    gaps.append({
                        "date": curr_d,
                        "day_of_week": dow,
                        "day_name": day_name,
                        "start_min": cursor,
                        "end_min": b_start,
                        "length_min": gap_len,
                    })
            cursor = max(cursor, b_end)

        if cursor < day_end:
            gap_len = day_end - cursor
            if gap_len >= MIN_GAP_MINUTES:
                gaps.append({
                    "date": curr_d,
                    "day_of_week": dow,
                    "day_name": day_name,
                    "start_min": cursor,
                    "end_min": day_end,
                    "length_min": gap_len,
                })

        curr_d += timedelta(days=1)

    return gaps


def plan_study_blocks(
    task_id: int,
    total_hours_required: float,
    deadline_date: date,
    current_user: CurrentUser,
    gaps: list[dict],
    preferred_duration_min: int = 90,
) -> PlanResponse:
    """
    Slices free gaps into balanced study sessions:
    - Target session length: respects preferred_duration_min (clamped between 30 and 120 mins).
    - Max 3 hours of study per day for one task.
    - Spreads across days, preferring earlier days and lighter workload days.
    - Leaves 10 min buffer between study blocks.
    - Deterministically scores each session with explainable reasons.
    - Returns suggested sessions + short_by_hours if free time is insufficient.
    """
    remaining_min = int(round(total_hours_required * 60))
    suggested: list[PlanSessionSuggested] = []

    preferred_len = max(MIN_SESSION_MINUTES, min(MAX_SESSION_MINUTES, preferred_duration_min))

    # Pre-calculate existing busy workload hours per day to score slots
    all_blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False)
    existing_dow_hours: dict[int, float] = {i: 0.0 for i in range(7)}
    for b in all_blocks:
        dow = b.day_of_week if b.day_of_week is not None else 0
        s = time_to_minutes(b.start_time)
        e = time_to_minutes(b.end_time)
        hrs = max(0.0, ((e + 24 * 60 - s) if e < s else (e - s)) / 60.0)
        existing_dow_hours[dow] += hrs

    # Group gaps by date
    days_dict: dict[date, list[dict]] = {}
    for g in gaps:
        d = g["date"]
        if d not in days_dict:
            days_dict[d] = []
        days_dict[d].append(g)

    sorted_dates = sorted(days_dict.keys())

    for d in sorted_dates:
        if remaining_min <= 0:
            break

        day_gaps = days_dict[d]
        day_study_min = 0
        dow = (d.weekday() + 1) % 7
        existing_day_hrs = existing_dow_hours.get(dow, 0.0)

        for gap in day_gaps:
            if remaining_min <= 0 or day_study_min >= MAX_DAILY_STUDY_MINUTES:
                break

            g_start = gap["start_min"]
            g_end = gap["end_min"]

            while g_start + MIN_SESSION_MINUTES <= g_end and day_study_min < MAX_DAILY_STUDY_MINUTES and remaining_min > 0:
                available_in_gap = g_end - g_start
                daily_remaining = MAX_DAILY_STUDY_MINUTES - day_study_min

                # Session length: min(preferred_len, available in gap, daily remaining, task remaining)
                session_len = min(preferred_len, available_in_gap, daily_remaining, remaining_min)
                if session_len < MIN_SESSION_MINUTES:
                    break

                # Round to clean 15-minute increments
                session_len = (session_len // 15) * 15
                if session_len < MIN_SESSION_MINUTES:
                    break

                s_end = g_start + session_len
                temp_id = f"plan_{d.isoformat()}_{g_start}_{s_end}"

                # Calculate deterministic score and reasons
                slot_score = 85
                reasons: list[str] = [
                    "No class conflict",
                    "No work conflict",
                    "10-minute transition buffer respected",
                ]

                if session_len == preferred_len:
                    slot_score += 5
                    reasons.append(f"{session_len}m preferred duration")
                if session_len >= 90:
                    slot_score += 4
                    reasons.append("Uninterrupted focus block")
                if 9 * 60 <= g_start and s_end <= 19 * 60:
                    slot_score += 4
                    reasons.append("Prime daytime focus hours")
                if existing_day_hrs < 4.0:
                    slot_score += 5
                    reasons.append("Day has light existing commitments")
                elif existing_day_hrs > 7.0:
                    slot_score -= 8
                    reasons.append("Caution: heavy existing workload on this day")

                days_to_deadline = (deadline_date - d).days
                if days_to_deadline >= 2:
                    slot_score += 2
                    reasons.append("Comfortably ahead of deadline")
                elif days_to_deadline == 0:
                    slot_score -= 5
                    reasons.append("Deadline day session")

                slot_score = max(50, min(100, slot_score))
                is_healthy = slot_score >= 75

                suggested.append(
                    PlanSessionSuggested(
                        temp_id=temp_id,
                        day_of_week=gap["day_of_week"],
                        day_name=gap["day_name"],
                        date=d.isoformat(),
                        start_time=minutes_to_time(g_start),
                        end_time=minutes_to_time(s_end),
                        duration_hours=round(session_len / 60.0, 2),
                        task_id=task_id,
                        type="study",
                        score=slot_score,
                        reasons=reasons,
                        is_healthy=is_healthy,
                    )
                )

                day_study_min += session_len
                remaining_min -= session_len

                # Advance gap cursor with 10 min buffer between study sessions
                g_start = s_end + BUFFER_MINUTES

    hours_scheduled = round(sum(s.duration_hours for s in suggested), 2)
    short_by_hours = None
    if hours_scheduled < total_hours_required:
        short_by_hours = round(total_hours_required - hours_scheduled, 2)

    return PlanResponse(
        suggested=suggested,
        hours_scheduled=hours_scheduled,
        short_by_hours=short_by_hours,
        gaps_considered=len(gaps),
    )
