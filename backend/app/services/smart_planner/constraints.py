from datetime import date
from typing import Optional, Tuple

from app.services.schedule import minutes_to_time, time_to_minutes
from app.services.smart_planner.models import PlanningEvent, ScheduleContext


class ConstraintEngine:
    @staticmethod
    def is_slot_feasible(
        slot_date: date,
        start_min: int,
        end_min: int,
        task: dict,
        context: ScheduleContext,
        existing_plan_slots: list[dict],
        allow_flexible_shift_overlap: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates hard feasibility of placing a study session [start_min, end_min] on slot_date:
        1. Temporal bounds: 08:00 to 22:00.
        2. Overlap with official university classes (strict anchor, never allowed).
        3. Overlap with fixed student work shifts and personal events.
        4. Overlap with student unavailable blackout slots.
        5. Overlap with other already-placed slots in the plan.
        6. Task deadline: session date must not be after task deadline; if on deadline day, ends by 18:00.
        7. Hard constraints (earliest_start, latest_end, day_off, max_hours_per_day).
        8. Travel / transition buffer with adjacent events.
        """
        dow = (slot_date.weekday() + 1) % 7

        # 1. Day bounds
        if start_min < 8 * 60:
            return False, "Cannot schedule before 08:00"
        if end_min > 22 * 60:
            return False, "Cannot schedule after 22:00"

        # 2. Deadline check
        task_deadline = task.get("deadline")
        if task_deadline:
            if isinstance(task_deadline, str):
                task_deadline = date.fromisoformat(task_deadline)
            if slot_date > task_deadline:
                return False, f"Date {slot_date} is after task deadline ({task_deadline})"
            if slot_date == task_deadline and end_min > 18 * 60:
                return False, f"On deadline day ({task_deadline}), sessions must end by 18:00"

        # 3. Check hard constraints
        for hc in context.hard_constraints:
            hc_type = hc["type"]
            hc_dow = hc.get("day_of_week")
            if hc_dow is not None and hc_dow != dow:
                continue

            if hc_type == "day_off":
                return False, f"Day {dow} is configured as a mandatory day off"

            if hc_type == "earliest_start" and hc.get("time_value"):
                earliest_m = time_to_minutes(hc["time_value"])
                if start_min < earliest_m:
                    return False, f"Starts before earliest allowed start ({hc['time_value']})"

            if hc_type == "latest_end" and hc.get("time_value"):
                latest_m = time_to_minutes(hc["time_value"])
                if end_min > latest_m:
                    return False, f"Ends after latest allowed end ({hc['time_value']})"

        # 4. Check overlap with existing schedule events
        for ev in context.events:
            if ev.date != slot_date:
                continue

            if ev.event_type == "flexible_shift" and allow_flexible_shift_overlap:
                # Flexible shifts may be adjusted if permitted
                continue

            # Standard interval overlap: s1 < e2 and s2 < e1
            if start_min < ev.end_min and ev.start_min < end_min:
                if ev.event_type == "class":
                    return False, f"Clashes with university class: {ev.title} ({minutes_to_time(ev.start_min)}–{minutes_to_time(ev.end_min)})"
                elif ev.event_type == "fixed_shift":
                    return False, f"Clashes with fixed work shift: {ev.title}"
                elif ev.event_type == "blackout":
                    return False, "Falls within your unavailable/blackout period"
                else:
                    return False, f"Clashes with commitment: {ev.title}"

            # Transition buffer check with adjacent events
            buffer = context.transition_buffer_min
            # Prior event ends before slot starts
            if ev.end_min <= start_min and (start_min - ev.end_min) < buffer:
                # If locations differ, buffer must be respected
                if ev.location and ev.location.lower() != "self-study":
                    return False, f"Insufficient travel buffer ({start_min - ev.end_min}m < {buffer}m) after {ev.title}"

            # Slot ends before subsequent event starts
            if end_min <= ev.start_min and (ev.start_min - end_min) < buffer:
                if ev.location and ev.location.lower() != "self-study":
                    return False, f"Insufficient travel buffer ({ev.start_min - end_min}m < {buffer}m) before {ev.title}"

        # 5. Check overlap with other proposed slots in this candidate plan
        for ps in existing_plan_slots:
            if ps["date"] != slot_date:
                continue
            if start_min < ps["end_min"] and ps["start_min"] < end_min:
                return False, "Overlaps with another proposed study block in this plan"
            # 10-minute spacing between study sessions
            if ps["end_min"] <= start_min and (start_min - ps["end_min"]) < 10:
                return False, "Insufficient rest buffer between study sessions"
            if end_min <= ps["start_min"] and (ps["start_min"] - end_min) < 10:
                return False, "Insufficient rest buffer between study sessions"

        # 6. Max hours per day check
        for hc in context.hard_constraints:
            if hc["type"] == "max_hours_per_day" and hc.get("int_value"):
                max_daily_min = hc["int_value"] * 60
                existing_day_min = sum(
                    (ev.end_min - ev.start_min) for ev in context.events if ev.date == slot_date and ev.event_type != "blackout"
                )
                existing_plan_day_min = sum(
                    (ps["end_min"] - ps["start_min"]) for ps in existing_plan_slots if ps["date"] == slot_date
                )
                proposed_min = end_min - start_min
                if (existing_day_min + existing_plan_day_min + proposed_min) > max_daily_min:
                    return False, f"Exceeds max allowed daily commitment of {hc['int_value']} hours"

        return True, None
