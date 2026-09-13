"""
Schedule Optimizer Service
Provides deterministic, constraint-aware shift scheduling and optimization.
Considers class overlaps, weekly work limits, transition buffers, and location differences.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.dependencies import CurrentUser
from app.services.schedule import get_user_zoneinfo, minutes_to_time, time_to_minutes
from app.services.timezone_helper import get_user_today
from app.store import detect_conflicts_and_totals, get_occurrences_for_range, get_session

DAY_NAME_TO_DOW = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}

DOW_TO_DAY_NAME = {v: k.capitalize() for k, v in DAY_NAME_TO_DOW.items()}


@dataclass
class CandidateShift:
    day_name: str
    day_of_week: int
    date: str
    start_time: str
    end_time: str
    duration_hours: float
    location: Optional[str]
    score: int
    reasons: list[str]
    warnings: list[str]
    is_valid: bool
    transition_ok: bool


def optimize_work_schedule(
    current_user: CurrentUser,
    target_hours: float = 8.0,
    preferred_days: Optional[list[str]] = None,
    shift_duration_hours: float = 4.0,
    target_week_start: Optional[date] = None,
    location: Optional[str] = "Work",
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Finds deterministic, conflict-free, travel-aware work shift combinations
    that satisfy student's requested work hours.
    """
    with get_session(db) as session:
        today_d, _ = get_user_today(current_user)
        if target_week_start is None:
            # Current week starting Monday
            w_start = today_d - timedelta(days=today_d.weekday())
        else:
            w_start = target_week_start - timedelta(days=target_week_start.weekday())

        w_end = w_start + timedelta(days=6)
        work_limit = float(current_user.weekly_work_hour_limit or 20.0)
        min_transition = max(0, int(getattr(current_user, "minimum_transition_minutes", 15) or 15))

        # 1. Fetch current week's existing occurrences & totals
        occurrences = get_occurrences_for_range(
            user_id=current_user.user_id,
            start_date=w_start,
            end_date=w_end,
            db=session,
        )
        _, totals = detect_conflicts_and_totals(
            user_id=current_user.user_id,
            weekly_hour_limit=work_limit,
            week_start=w_start,
            db=session,
        )

        current_shift_hours = totals.shift_hours
        remaining_capacity = max(0.0, work_limit - current_shift_hours)

        # Normalize preferred days
        pref_dows = set()
        if preferred_days:
            for d in preferred_days:
                clean_d = str(d).strip().lower()
                if clean_d in DAY_NAME_TO_DOW:
                    pref_dows.add(DAY_NAME_TO_DOW[clean_d])

        # If no preferred days specified, default to weekdays / weekend mix
        if not pref_dows:
            pref_dows = {1, 2, 3, 4, 5, 6}  # Mon - Sat

        # Map occurrences by day_of_week and date
        occurrences_by_day: dict[int, list] = {d: [] for d in range(7)}
        for occ in occurrences:
            dow = occ.day_of_week if occ.day_of_week is not None else 1
            occurrences_by_day[dow].append(occ)

        # Standard shift time templates to evaluate
        shift_templates = [
            ("09:00", 9 * 60),
            ("10:00", 10 * 60),
            ("12:00", 12 * 60),
            ("13:00", 13 * 60),
            ("14:00", 14 * 60),
            ("16:00", 16 * 60),
            ("17:00", 17 * 60),
            ("18:00", 18 * 60),
        ]

        dur_minutes = int(shift_duration_hours * 60)
        candidate_shifts: list[CandidateShift] = []

        for day_offset in range(7):
            curr_date = w_start + timedelta(days=day_offset)
            dow = (curr_date.weekday() + 1) % 7
            day_name = DOW_TO_DAY_NAME.get(dow, "Unknown")

            # Check if this day is among preferred
            is_preferred = dow in pref_dows
            existing_blocks = occurrences_by_day.get(dow, [])

            for tm_label, s_min in shift_templates:
                e_min = s_min + dur_minutes
                if e_min > 23 * 60:  # don't schedule past 11 PM
                    continue

                # 1. Overlap test against all existing blocks on this day
                has_overlap = False
                overlap_with = ""
                for b in existing_blocks:
                    b_s = time_to_minutes(b.start_time)
                    b_e = time_to_minutes(b.end_time)
                    if s_min < b_e and b_s < e_min:
                        has_overlap = True
                        overlap_with = b.title
                        break

                if has_overlap:
                    continue  # Invalid: hard clash with class/shift

                # 2. Transition test against preceding and succeeding events
                transition_penalty = 0
                transition_ok = True
                warnings: list[str] = []
                reasons: list[str] = ["✓ No class overlap", "✓ No shift overlap"]

                cand_loc = (location or "Work").strip().lower()

                for b in existing_blocks:
                    b_s = time_to_minutes(b.start_time)
                    b_e = time_to_minutes(b.end_time)
                    b_loc = (b.location or "Campus").strip().lower()
                    same_loc = bool(cand_loc and b_loc and cand_loc == b_loc)
                    required_buffer = 0 if same_loc else min_transition

                    # Preceding event: b ends before candidate starts
                    if b_e <= s_min:
                        gap_before = s_min - b_e
                        if required_buffer > 0 and gap_before < required_buffer:
                            transition_ok = False
                            transition_penalty += 20
                            warnings.append(f"⚠ Tight transition ({gap_before}m available, {required_buffer}m preferred) after {b.title}")
                        elif gap_before >= 45:
                            reasons.append(f"✓ Comfortable {gap_before}m transition after {b.title}")

                    # Succeeding event: candidate ends before b starts
                    elif e_min <= b_s:
                        gap_after = b_s - e_min
                        if required_buffer > 0 and gap_after < required_buffer:
                            transition_ok = False
                            transition_penalty += 20
                            warnings.append(f"⚠ Tight transition ({gap_after}m available, {required_buffer}m preferred) before {b.title}")
                        elif gap_after >= 45:
                            reasons.append(f"✓ Comfortable {gap_after}m transition before {b.title}")

                # 3. Base scoring
                score = 80 - transition_penalty
                if is_preferred:
                    score += 15
                    reasons.append(f"✓ Preferred day ({day_name})")
                if 10 * 60 <= s_min and e_min <= 19 * 60:
                    score += 10
                    reasons.append("✓ Daytime focus hours")
                elif e_min >= 21 * 60:
                    score -= 10
                    warnings.append("⚠ Ends late in the evening")

                if transition_ok:
                    reasons.append(f"✓ Travel buffer respected ({min_transition}m)")

                score = max(30, min(100, score))

                candidate_shifts.append(
                    CandidateShift(
                        day_name=day_name,
                        day_of_week=dow,
                        date=curr_date.isoformat(),
                        start_time=minutes_to_time(s_min),
                        end_time=minutes_to_time(e_min),
                        duration_hours=shift_duration_hours,
                        location=location,
                        score=score,
                        reasons=reasons,
                        warnings=warnings,
                        is_valid=True,
                        transition_ok=transition_ok,
                    )
                )

        # Sort candidates by score descending
        candidate_shifts.sort(key=lambda c: (c.score, c.transition_ok), reverse=True)

        # Select top candidates to fulfill target_hours
        needed_shifts = int(round(target_hours / shift_duration_hours))
        if needed_shifts <= 0:
            needed_shifts = 1

        selected: list[CandidateShift] = []
        selected_dates = set()

        for cand in candidate_shifts:
            if len(selected) >= needed_shifts:
                break
            # Prefer distinct days
            if cand.date not in selected_dates:
                selected.append(cand)
                selected_dates.add(cand.date)

        # If couldn't fill with distinct days, allow secondary slots on same days
        if len(selected) < needed_shifts:
            for cand in candidate_shifts:
                if len(selected) >= needed_shifts:
                    break
                if cand not in selected:
                    selected.append(cand)

        total_scheduled_hours = sum(s.duration_hours for s in selected)
        over_work_limit = (current_shift_hours + total_scheduled_hours) > work_limit

        return {
            "target_hours": target_hours,
            "scheduled_hours": total_scheduled_hours,
            "remaining_capacity": remaining_capacity,
            "work_limit": work_limit,
            "over_limit_after": over_work_limit,
            "candidates_evaluated": len(candidate_shifts),
            "recommendation": [
                {
                    "day_name": s.day_name,
                    "day_of_week": s.day_of_week,
                    "date": s.date,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration_hours": s.duration_hours,
                    "location": s.location,
                    "score": s.score,
                    "reasons": s.reasons,
                    "warnings": s.warnings,
                    "transition_ok": s.transition_ok,
                }
                for s in selected
            ],
        }
