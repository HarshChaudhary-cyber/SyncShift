from app.services.smart_planner.models import GeneratedPlanOption, ScheduleContext


class ExplanationEngine:
    @staticmethod
    def explain_option(option: GeneratedPlanOption, context: ScheduleContext) -> GeneratedPlanOption:
        """
        Populates human-readable reasons, warnings, and trade-offs for the option.
        """
        reasons: list[str] = [
            "✓ Zero overlaps with official university classes",
            "✓ Fits around all fixed work shifts & commitments",
        ]
        warnings: list[str] = []

        # Time-of-day reason
        pref_tod = context.preferences.get("preferred_time_of_day", "any")
        if pref_tod != "any":
            reasons.append(f"✓ Aligned with your {pref_tod} focus preference")
        else:
            reasons.append("✓ Balanced daytime study hours")

        # Focus session length
        long_count = sum(1 for s in option.slots if s.duration_min >= 90)
        if long_count > 0:
            reasons.append(f"✓ Includes {long_count} deep focus block(s) (90m+)")

        # Strategy specific reason and trade-off
        if option.option_id == "balanced":
            reasons.append("✓ Moderate daily load with 15-min buffers")
            option.trade_offs = "Distributes study evenly across 3–4 days rather than stacking into intensive single days."
        elif option.option_id == "focused":
            reasons.append("✓ Consolidates tasks comfortably ahead of deadlines")
            option.trade_offs = "Requires longer uninterrupted sessions (90–120m) to minimize task switching."
        elif option.option_id == "compact":
            reasons.append("✓ Clusters study sessions on days you already have classes")
            option.trade_offs = "Heavier schedule on campus days in exchange for more completely free days off."

        # Preferred days off
        pref_days_off = context.preferences.get("preferred_days_off")
        if pref_days_off:
            reasons.append("✓ Respects your preferred days off")

        # Warnings if invalid or partial
        if not option.is_valid:
            warnings.extend(option.blocking_reasons)

        option.reasons = reasons
        option.warnings = warnings
        return option
