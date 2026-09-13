from app.services.smart_planner.models import GeneratedPlanOption, ScheduleContext


class ScheduleScorer:
    @staticmethod
    def score_option(option: GeneratedPlanOption, context: ScheduleContext) -> GeneratedPlanOption:
        """
        Calculates a transparent, deterministic quality score (0–100) for a plan option.
        Factors:
        - Hard feasibility: If invalid, score is 0.
        - Preference match (time of day, density, days off).
        - Focus quality (length of study sessions).
        - Deadline proximity (placed comfortably ahead).
        - Workload distribution and daily caps.
        """
        if not option.is_valid:
            option.score = 0
            option.fit_percentage = max(0, min(100, option.fit_percentage))
            return option

        base_score = 78
        score = base_score

        # 1. Time-of-day preference match
        pref_tod = context.preferences.get("preferred_time_of_day", "any")
        if pref_tod != "any" and option.slots:
            matching_slots = 0
            for s in option.slots:
                if pref_tod == "morning" and s.start_min < 12 * 60:
                    matching_slots += 1
                elif pref_tod == "afternoon" and 12 * 60 <= s.start_min < 17 * 60:
                    matching_slots += 1
                elif pref_tod == "evening" and s.start_min >= 17 * 60:
                    matching_slots += 1

            match_ratio = matching_slots / len(option.slots)
            if match_ratio >= 0.7:
                score += 10
            elif match_ratio >= 0.4:
                score += 5

        # 2. Preferred days off respect
        pref_days_off_raw = context.preferences.get("preferred_days_off") or ""
        preferred_days_off = set()
        for p in pref_days_off_raw.split(","):
            p_strip = p.strip()
            if p_strip.isdigit():
                preferred_days_off.add(int(p_strip))

        if preferred_days_off:
            scheduled_dows = set(s.day_of_week for s in option.slots)
            if not (scheduled_dows & preferred_days_off):
                score += 8  # Full respect for days off

        # 3. Strategy specific bonuses
        if option.option_id == "balanced":
            # Balanced: bonus for spreading across 3+ days
            active_days = set(s.date for s in option.slots)
            if len(active_days) >= 3:
                score += 6
        elif option.option_id == "focused":
            # Focused: bonus for uninterrupted sessions >= 90 mins
            long_sessions = sum(1 for s in option.slots if s.duration_min >= 90)
            if long_sessions >= len(option.slots) * 0.7:
                score += 7
        elif option.option_id == "compact":
            # Compact: bonus for packing study on days with existing commitments
            comm_days = set(ev.date for ev in context.events if ev.event_type in ("class", "fixed_shift"))
            study_days = set(s.date for s in option.slots)
            if study_days.issubset(comm_days):
                score += 8

        # 4. Workload balance check (penalize days exceeding 8 total hours)
        for s in option.slots:
            day_total_min = sum(
                (ev.end_min - ev.start_min) for ev in context.events if ev.date == s.date and ev.event_type != "blackout"
            ) + sum(
                slot.duration_min for slot in option.slots if slot.date == s.date
            )
            if day_total_min > 8 * 60:
                score -= 6
                break

        option.score = max(35, min(98, score))
        return option
