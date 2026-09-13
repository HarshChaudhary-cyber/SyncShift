"""
Schedule Health Service
Calculates a deterministic, explainable Schedule Health Score (0-100)
based on actual calendar schedule data, conflict status, and configured limits.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.schemas.block import BlockOut
from app.schemas.conflict import ConflictItem


@dataclass
class HealthFactor:
    type: str  # "positive" | "warning" | "info"
    text: str
    impact: int = 0


@dataclass
class ScheduleHealthResult:
    score: int
    category: str
    summary: str
    factors: list[HealthFactor]
    improvements: list[str]


def compute_schedule_health(
    blocks: list[BlockOut],
    conflicts: list[ConflictItem],
    weekly_work_limit: float = 20.0,
    week_start: Optional[date] = None,
) -> ScheduleHealthResult:
    """
    Computes a deterministic, explainable 0-100 score for a student's weekly schedule.
    
    Categories:
      90–100: Excellent
      75–89:  Healthy
      60–74:  Moderate
      40–59:  Needs attention
      0–39:   Overloaded
    """
    score = 100
    factors: list[HealthFactor] = []
    improvements: list[str] = []

    # 1. Evaluate Conflicts
    hard_conflicts = [c for c in conflicts if c.severity == "hard"]
    warning_conflicts = [c for c in conflicts if c.severity == "warning"]

    if hard_conflicts:
        penalty = len(hard_conflicts) * 15
        score -= penalty
        factors.append(
            HealthFactor(
                type="warning",
                text=f"{len(hard_conflicts)} hard schedule {'conflict' if len(hard_conflicts) == 1 else 'conflicts'}",
                impact=-penalty,
            )
        )
        for hc in hard_conflicts[:2]:
            desc = hc.description or f"Block #{hc.block_a_id} and #{hc.block_b_id}"
            improvements.append(f"Resolve hard schedule clash: {desc}")
    else:
        score += 5
        factors.append(
            HealthFactor(
                type="positive",
                text="No hard schedule conflicts",
                impact=5,
            )
        )

    transition_conflicts = [c for c in warning_conflicts if getattr(c, "conflict_type", "") == "transition"]
    other_warnings = [c for c in warning_conflicts if getattr(c, "conflict_type", "") != "transition"]

    if transition_conflicts:
        t_penalty = len(transition_conflicts) * 4
        score -= t_penalty
        factors.append(
            HealthFactor(
                type="warning",
                text=f"{len(transition_conflicts)} tight transition {'warning' if len(transition_conflicts) == 1 else 'warnings'}",
                impact=-t_penalty,
            )
        )
        for tc in transition_conflicts[:2]:
            improvements.append(f"Increase transition buffer: {tc.description}")

    if other_warnings:
        penalty = len(other_warnings) * 5
        score -= penalty
        factors.append(
            HealthFactor(
                type="warning",
                text=f"{len(other_warnings)} schedule {'warning' if len(other_warnings) == 1 else 'warnings'}",
                impact=-penalty,
            )
        )
        for wc in other_warnings[:2]:
            desc = wc.description or f"Overlap on day {wc.day_of_week}"
            improvements.append(f"Adjust timing to clear warning: {desc}")


    # 2. Daily Workload & Work Hours Analysis
    # Group active non-deleted blocks by day of week
    daily_hours: dict[int, float] = {i: 0.0 for i in range(7)}
    daily_study_hours: dict[int, float] = {i: 0.0 for i in range(7)}
    daily_shift_hours: dict[int, float] = {i: 0.0 for i in range(7)}
    daily_blocks: dict[int, list[BlockOut]] = {i: [] for i in range(7)}

    for b in blocks:
        if getattr(b, "deleted", False):
            continue
        dow = b.day_of_week if b.day_of_week is not None else 1
        daily_blocks[dow].append(b)

        s_parts = [int(p) for p in b.start_time.split(":")[:2]]
        e_parts = [int(p) for p in b.end_time.split(":")[:2]]
        s_min = s_parts[0] * 60 + s_parts[1]
        e_min = e_parts[0] * 60 + e_parts[1]
        dur_min = (e_min + 24 * 60 - s_min) if e_min < s_min else (e_min - s_min)
        hrs = max(0.0, dur_min / 60.0)

        daily_hours[dow] += hrs
        if b.type == "study":
            daily_study_hours[dow] += hrs
        elif b.type == "shift":
            daily_shift_hours[dow] += hrs

    total_shift_hours = sum(daily_shift_hours.values())
    total_study_hours = sum(daily_study_hours.values())

    # Check work-hour limit
    if total_shift_hours > weekly_work_limit:
        over = round(total_shift_hours - weekly_work_limit, 1)
        score -= 15
        factors.append(
            HealthFactor(
                type="warning",
                text=f"Work limit exceeded by {over:g}h ({total_shift_hours:g}h scheduled)",
                impact=-15,
            )
        )
        improvements.append(
            f"Reduce work shifts by {over:g}h to stay within your {weekly_work_limit:g}h limit"
        )
    elif total_shift_hours > 0:
        score += 3
        factors.append(
            HealthFactor(
                type="positive",
                text=f"Work hours within configured limit ({total_shift_hours:g}/{weekly_work_limit:g}h)",
                impact=3,
            )
        )

    # 3. High daily workload (> 9.0 hours) & repeated heavy days (>= 8.0 hours)
    DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    overloaded_days: list[tuple[str, float]] = []
    heavy_days_count = 0

    for dow in range(7):
        h = daily_hours[dow]
        if h > 9.0:
            overloaded_days.append((DAY_NAMES[dow], round(h, 1)))
        if h >= 8.0:
            heavy_days_count += 1

    if overloaded_days:
        for day_name, d_hours in overloaded_days:
            score -= 5
            factors.append(
                HealthFactor(
                    type="warning",
                    text=f"{day_name} has a heavy workload ({d_hours:g}h scheduled)",
                    impact=-5,
                )
            )
            improvements.append(f"Shift flexible sessions away from {day_name} to lower peak strain")

    if heavy_days_count >= 3:
        score -= 5
        factors.append(
            HealthFactor(
                type="warning",
                text=f"Repeated heavy days ({heavy_days_count} days >= 8h scheduled)",
                impact=-5,
            )
        )

    # 4. Short Rest Periods (Transition / overnight rest < 8 hours)
    # Check consecutive blocks within each day and across adjacent days
    short_rest_found = False
    for dow in range(7):
        b_list = sorted(
            daily_blocks[dow],
            key=lambda x: int(x.start_time.split(":")[0]) * 60 + int(x.start_time.split(":")[1]),
        )
        # Check next day start
        next_dow = (dow + 1) % 7
        next_b_list = sorted(
            daily_blocks[next_dow],
            key=lambda x: int(x.start_time.split(":")[0]) * 60 + int(x.start_time.split(":")[1]),
        )
        if b_list and next_b_list:
            last_end = int(b_list[-1].end_time.split(":")[0]) * 60 + int(b_list[-1].end_time.split(":")[1])
            first_next_start = int(next_b_list[0].start_time.split(":")[0]) * 60 + int(next_b_list[0].start_time.split(":")[1])
            rest_hours = (first_next_start + 24 * 60 - last_end) / 60.0
            if 0 < rest_hours < 8.0:
                short_rest_found = True
                factors.append(
                    HealthFactor(
                        type="warning",
                        text=f"Short rest period ({round(rest_hours, 1)}h) between {DAY_NAMES[dow]} night and {DAY_NAMES[next_dow]} morning",
                        impact=-5,
                    )
                )
                improvements.append(
                    f"Allow at least 8 hours of rest between {DAY_NAMES[dow]} and {DAY_NAMES[next_dow]}"
                )
                break  # Record one rest penalty to avoid cascading

    if short_rest_found:
        score -= 5

    # 5. Study Distribution
    active_study_days = sum(1 for dow in range(7) if daily_study_hours[dow] > 0)
    if total_study_hours > 0:
        if active_study_days >= 2:
            score += 2
            factors.append(
                HealthFactor(
                    type="positive",
                    text="Study sessions distributed across multiple days",
                    impact=2,
                )
            )
        elif total_study_hours >= 4.0 and active_study_days == 1:
            score -= 3
            factors.append(
                HealthFactor(
                    type="warning",
                    text="Study hours concentrated in a single day",
                    impact=-3,
                )
            )
            improvements.append("Spread study sessions across 2 or more days for better retention")

    # Clamp score to [0, 100]
    final_score = max(0, min(100, score))

    # Map category
    if final_score >= 90:
        category = "Excellent"
        summary = "Outstanding schedule balance with healthy workloads and no major clashes."
    elif final_score >= 75:
        category = "Healthy"
        summary = "Well-balanced week with comfortable pace across study, work, and classes."
    elif final_score >= 60:
        category = "Moderate"
        summary = "Manageable schedule, but some days or commitments have elevated workload."
    elif final_score >= 40:
        category = "Needs attention"
        summary = "Noticeable scheduling strain detected. Consider resolving clashes or reallocating hours."
    else:
        category = "Overloaded"
        summary = "High workload strain or multiple conflicts. Action is recommended to maintain well-being."

    if not improvements:
        improvements.append("Your schedule looks well-balanced! Maintain healthy breaks throughout the week.")

    return ScheduleHealthResult(
        score=final_score,
        category=category,
        summary=summary,
        factors=factors,
        improvements=improvements,
    )
