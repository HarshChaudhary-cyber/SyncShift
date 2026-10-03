from datetime import date, timedelta
from typing import List, Tuple

from app.services.schedule import minutes_to_time
from app.services.smart_planner.constraints import ConstraintEngine
from app.services.smart_planner.models import (
    CandidateSlot,
    GeneratedPlanOption,
    ProposedAdjustment,
    ScheduleContext,
)


class CandidateGenerator:
    @staticmethod
    def generate_options(
        context: ScheduleContext,
        allow_flexible_work_moves: bool = False,
        preferred_time_of_day: str = "any",
        schedule_density: str = "balanced",
    ) -> list[GeneratedPlanOption]:
        """
        Produces up to 3 distinct, explainable candidate planning options:
        - 'balanced': Even distribution across available days with standard breaks.
        - 'focused': Longer, consolidated focus sessions (90–120m) ahead of deadlines.
        - 'compact': Clusters study sessions onto existing commitment days to maximize full days off.
        """
        strategies = [
            ("balanced", "Balanced Week", "Distributes study evenly across available days with comfortable buffers."),
            ("focused", "Deep Focus", "Consolidates study sessions into longer uninterrupted blocks ahead of deadlines."),
            ("compact", "Compact Schedule", "Clusters study sessions around existing classes to maximize free days off."),
        ]

        results: list[GeneratedPlanOption] = []

        for strat_id, strat_name, strat_desc in strategies:
            option = CandidateGenerator._generate_single_strategy(
                strategy=strat_id,
                name=strat_name,
                description=strat_desc,
                context=context,
                allow_flexible_work_moves=allow_flexible_work_moves,
                preferred_time_of_day=preferred_time_of_day,
                schedule_density=schedule_density,
            )
            results.append(option)

        return results

    @staticmethod
    def _generate_single_strategy(
        strategy: str,
        name: str,
        description: str,
        context: ScheduleContext,
        allow_flexible_work_moves: bool,
        preferred_time_of_day: str,
        schedule_density: str,
    ) -> GeneratedPlanOption:
        # Configuration per strategy tailored to user's preferred_session_duration
        user_session_pref = int(context.preferences.get("preferred_session_duration") or 45)
        if strategy == "focused":
            target_session_min = max(60, int(user_session_pref * 1.5))
            max_daily_study_min = max(240, target_session_min * 2)
        elif strategy == "compact":
            target_session_min = max(45, user_session_pref)
            max_daily_study_min = 240
        else:  # balanced
            target_session_min = user_session_pref
            max_daily_study_min = max(120, target_session_min * 3)

        # Effective time-of-day preference
        effective_tod = preferred_time_of_day if preferred_time_of_day != "any" else context.preferences.get("preferred_time_of_day", "any")

        # Preferred days off from context
        pref_days_off_raw = context.preferences.get("preferred_days_off") or ""
        preferred_days_off = set()
        for p in pref_days_off_raw.split(","):
            p_strip = p.strip()
            if p_strip.isdigit():
                preferred_days_off.add(int(p_strip))

        # Calculate dates in target week
        week_dates = [context.week_start + timedelta(days=i) for i in range(7)]

        # If compact, order dates prioritizing days that already have classes/work
        if strategy == "compact":
            days_with_commitments = set(ev.date for ev in context.events if ev.event_type in ("class", "fixed_shift", "personal"))
            week_dates.sort(key=lambda d: 0 if d in days_with_commitments else 1)

        placed_slots: list[CandidateSlot] = []
        raw_placed_dicts: list[dict] = []
        blocking_reasons: list[str] = []

        # Iterate through all active tasks
        for task in context.tasks:
            task_id = task["id"]
            remaining_min = int(round(task["remaining_hours"] * 60))
            if remaining_min <= 0:
                continue

            task_pref_dur = task.get("preferred_duration")
            if task_pref_dur and task_pref_dur != 90:
                session_dur = task_pref_dur
            else:
                session_dur = target_session_min
            session_dur = max(15, session_dur)

            # Try to place study sessions across week dates
            for curr_d in week_dates:
                if remaining_min <= 0:
                    break

                dow = (curr_d.weekday() + 1) % 7

                # In compact or balanced mode, skip preferred days off if possible
                if dow in preferred_days_off and remaining_min < 180 and strategy != "focused":
                    continue

                # Check daily study budget for this day
                curr_day_study = sum(ps["end_min"] - ps["start_min"] for ps in raw_placed_dicts if ps["date"] == curr_d)
                if curr_day_study >= max_daily_study_min:
                    continue

                # Determine candidate starting times based on time-of-day preference and planning hours
                candidate_starts = CandidateGenerator._get_candidate_start_times(effective_tod, context)

                for s_min in candidate_starts:
                    if remaining_min <= 0:
                        break
                    if curr_day_study >= max_daily_study_min:
                        break

                    # Duration: clamp to remaining or session_dur
                    dur = min(session_dur, remaining_min)
                    # Round to 15m increments
                    dur = max(15, (dur // 15) * 15)
                    e_min = s_min + dur

                    feasible, block_reason = ConstraintEngine.is_slot_feasible(
                        slot_date=curr_d,
                        start_min=s_min,
                        end_min=e_min,
                        task=task,
                        context=context,
                        existing_plan_slots=raw_placed_dicts,
                        allow_flexible_shift_overlap=False,
                    )

                    if feasible:
                        temp_id = f"plan_{strategy}_{task_id}_{curr_d.isoformat()}_{s_min}"
                        slot = CandidateSlot(
                            temp_id=temp_id,
                            task_id=task_id,
                            task_title=task["title"],
                            course_id=task.get("course_id"),
                            date=curr_d,
                            day_of_week=dow,
                            start_min=s_min,
                            end_min=e_min,
                            duration_min=dur,
                            score=85,
                        )
                        placed_slots.append(slot)
                        raw_placed_dicts.append({
                            "date": curr_d,
                            "day_of_week": dow,
                            "start_min": s_min,
                            "end_min": e_min,
                        })
                        remaining_min -= dur
                        curr_day_study += dur
                    elif block_reason and block_reason not in blocking_reasons:
                        blocking_reasons.append(block_reason)

            # If task still has remaining hours that couldn't fit
            if remaining_min > 0:
                short_hrs = round(remaining_min / 60.0, 1)
                blocking_reasons.append(f"Insufficient free time to schedule {short_hrs}h for '{task['title']}'")

        # Determine overall feasibility
        has_tasks = len(context.tasks) > 0
        total_requested = sum(t["remaining_hours"] for t in context.tasks)
        total_scheduled = sum(s.duration_min for s in placed_slots) / 60.0

        is_valid = True
        if has_tasks and total_scheduled < (total_requested * 0.7) and total_requested > 0:
            is_valid = False

        return GeneratedPlanOption(
            option_id=strategy,
            name=name,
            description=description,
            score=85,
            fit_percentage=min(100, int((total_scheduled / total_requested * 100))) if total_requested > 0 else 100,
            slots=placed_slots,
            adjustments=[],
            is_valid=is_valid,
            blocking_reasons=blocking_reasons if not is_valid else [],
        )

    @staticmethod
    def _get_candidate_start_times(preferred_tod: str, context: ScheduleContext = None) -> list[int]:
        """
        Returns an ordered list of start minute candidates tailored to time-of-day preference
        and constrained to the user's planning hours window.
        """
        plan_start_h = 8
        plan_end_h = 22
        if context and context.preferences:
            plan_start_h = max(0, min(23, int(context.preferences.get("planning_hours_start", 8) or 8)))
            plan_end_h = max(plan_start_h + 1, min(24, int(context.preferences.get("planning_hours_end", 22) or 22)))

        all_slots = [h * 60 + m for h in range(plan_start_h, plan_end_h) for m in (0, 15, 30, 45)]

        morning_slots = [s for s in all_slots if s < 12 * 60]
        afternoon_slots = [s for s in all_slots if 12 * 60 <= s < 17 * 60]
        evening_slots = [s for s in all_slots if s >= 17 * 60]

        if preferred_tod == "morning":
            ordered = morning_slots + afternoon_slots + evening_slots
        elif preferred_tod == "evening":
            ordered = evening_slots + afternoon_slots + morning_slots
        elif preferred_tod == "afternoon":
            ordered = afternoon_slots + morning_slots + evening_slots
        else:  # any / balanced
            ordered = afternoon_slots + morning_slots + evening_slots

        return ordered or all_slots
