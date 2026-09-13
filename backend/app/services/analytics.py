"""
Advanced Schedule Analytics Service
Aggregates schedule metrics, work-hour utilization, earnings,
daily workload breakdown, time distribution, and schedule health.
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies import CurrentUser
from app.schemas.analytics import (
    AnalyticsData,
    ConflictsAnalytics,
    DailyWorkloadItem,
    EarningsAnalytics,
    HealthFactorSchema,
    HoursBreakdown,
    ScheduleHealthData,
    TimeDistributionData,
    WorkLimitAnalytics,
)
from app.services.schedule import get_user_zoneinfo
from app.services.schedule_health import compute_schedule_health
from app.services.timezone_helper import get_user_today
from app.store import detect_conflicts_and_totals, get_all_blocks, get_occurrences_for_range

CURRENCY_SYMBOLS: dict[str, str] = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "CA$",
    "AUD": "A$",
    "JPY": "¥",
    "CHF": "CHF",
    "₹": "₹",
    "$": "$",
    "€": "€",
    "£": "£",
    "¥": "¥",
}


def _block_duration_hours(start_time: str, end_time: str) -> float:
    s_parts = [int(p) for p in start_time.split(":")[:2]]
    e_parts = [int(p) for p in end_time.split(":")[:2]]
    s_min = s_parts[0] * 60 + s_parts[1]
    e_min = e_parts[0] * 60 + e_parts[1]
    dur = (e_min + 24 * 60 - s_min) if e_min < s_min else (e_min - s_min)
    return max(0.0, dur / 60.0)


def compute_week_analytics(
    current_user: CurrentUser,
    week_start: Optional[date] = None,
    db: Optional[Session] = None,
) -> AnalyticsData:
    """
    Computes comprehensive weekly analytics strictly scoped to current_user:
    - Weekly total hours breakdown: class, work, study, total, free
    - Configured work limit compliance and percentage
    - Estimated weekly and monthly earnings from shifts with hourly_wage
    - Monday-to-Sunday daily workload distribution and heavy day indicators
    - Class vs Work vs Study vs Free time distribution
    - Schedule Health score, categories, checkmarks, and actionable tips
    """
    today_d, _ = get_user_today(current_user)

    if week_start is None:
        # Default to Monday of current week
        week_start = today_d - timedelta(days=today_d.weekday())
    else:
        # Align provided date to Monday
        week_start = week_start - timedelta(days=week_start.weekday())

    week_end = week_start + timedelta(days=6)
    configured_work_limit = float(current_user.weekly_work_hour_limit or 20.0)

    # 1. Fetch user's actual materialized occurrences for this week & detected conflicts
    week_occurrences = get_occurrences_for_range(
        user_id=current_user.user_id,
        start_date=week_start,
        end_date=week_end,
        db=db,
    )
    conflicts, totals = detect_conflicts_and_totals(
        user_id=current_user.user_id,
        weekly_hour_limit=configured_work_limit,
        week_start=week_start,
        db=db,
    )

    # 2. Daily workload calculation (Monday = 0 to Sunday = 6)
    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_items: list[DailyWorkloadItem] = []

    total_class_hours = 0.0
    total_work_hours = 0.0
    total_study_hours = 0.0
    estimated_weekly_earnings = 0.0
    missing_wage_shifts_count = 0

    for idx, day_name in enumerate(DAY_NAMES):
        day_date = week_start + timedelta(days=idx)
        syncshift_dow = (day_date.weekday() + 1) % 7

        day_cls = 0.0
        day_wrk = 0.0
        day_std = 0.0

        for b in week_occurrences:
            if b.occurrence_date:
                if b.occurrence_date != day_date:
                    continue
            elif b.day_of_week != syncshift_dow:
                continue

            hrs = _block_duration_hours(b.start_time, b.end_time)
            b_type = getattr(b, "type", "class")

            if b_type == "class":
                day_cls += hrs
            elif b_type == "shift":
                day_wrk += hrs
                wage = getattr(b, "hourly_wage", None)
                if wage is not None and float(wage) > 0:
                    estimated_weekly_earnings += hrs * float(wage)
                else:
                    missing_wage_shifts_count += 1
            elif b_type == "study":
                day_std += hrs

        day_total = day_cls + day_wrk + day_std
        is_heavy = day_total >= 8.0
        label = "Heavy" if is_heavy else ("Light" if day_total <= 2.0 else "Normal")

        daily_items.append(
            DailyWorkloadItem(
                day=day_name,
                date=day_date.isoformat(),
                day_of_week=syncshift_dow,
                class_hours=round(day_cls, 1),
                work_hours=round(day_wrk, 1),
                study_hours=round(day_std, 1),
                total_hours=round(day_total, 1),
                is_heavy=is_heavy,
                label=label,
            )
        )

        total_class_hours += day_cls
        total_work_hours += day_wrk
        total_study_hours += day_std

    total_planned_hours = total_class_hours + total_work_hours + total_study_hours

    # Standard waking window: 7 days * 15 active waking hours (08:00 to 23:00) = 105.0 hours
    waking_hours_base = 105.0
    free_hours = max(0.0, round(waking_hours_base - total_planned_hours, 1))

    # 3. Work Limit Utilization
    used_work_hours = round(total_work_hours, 1)
    remaining_work_hours = round(max(0.0, configured_work_limit - used_work_hours), 1)
    over_limit = used_work_hours > configured_work_limit
    over_hours = round(max(0.0, used_work_hours - configured_work_limit), 1)
    utilization_pct = (
        round((used_work_hours / configured_work_limit) * 100, 1)
        if configured_work_limit > 0
        else 0.0
    )

    # 4. Earnings
    user_curr = getattr(current_user, "currency", "INR") or "INR"
    curr_upper = user_curr.upper()
    curr_symbol = CURRENCY_SYMBOLS.get(curr_upper, user_curr)
    estimated_weekly_earnings = round(estimated_weekly_earnings, 2)
    # Average month is ~4.33 weeks
    estimated_monthly_earnings = round(estimated_weekly_earnings * 4.33, 2)

    # 5. Conflicts Summary
    hard_conflicts = [c for c in conflicts if c.severity == "hard"]
    warning_conflicts = [c for c in conflicts if c.severity == "warning"]

    # 6. Time Distribution Percentages
    total_base = max(total_planned_hours, waking_hours_base)
    class_pct = round((total_class_hours / total_base) * 100, 1)
    work_pct = round((total_work_hours / total_base) * 100, 1)
    study_pct = round((total_study_hours / total_base) * 100, 1)
    free_pct = max(0.0, round(100.0 - (class_pct + work_pct + study_pct), 1))

    # 7. Schedule Health Evaluation
    health_result = compute_schedule_health(
        blocks=week_occurrences,
        conflicts=conflicts,
        weekly_work_limit=configured_work_limit,
        week_start=week_start,
    )

    health_data = ScheduleHealthData(
        score=health_result.score,
        category=health_result.category,
        summary=health_result.summary,
        factors=[
            HealthFactorSchema(type=f.type, text=f.text, impact=f.impact)
            for f in health_result.factors
        ],
        improvements=health_result.improvements,
    )

    return AnalyticsData(
        period={
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
        },
        hours=HoursBreakdown(
            class_hours=round(total_class_hours, 1),
            work_hours=round(total_work_hours, 1),
            study_hours=round(total_study_hours, 1),
            total_hours=round(total_planned_hours, 1),
            free_hours=free_hours,
        ),
        work_limit=WorkLimitAnalytics(
            configured=configured_work_limit,
            used=used_work_hours,
            remaining=remaining_work_hours,
            percentage=utilization_pct,
            over_limit=over_limit,
            over_hours=over_hours,
        ),
        conflicts=ConflictsAnalytics(
            hard=len(hard_conflicts),
            warning=len(warning_conflicts),
            total=len(conflicts),
            trend=None,
        ),
        earnings=EarningsAnalytics(
            currency=curr_upper,
            currency_symbol=curr_symbol,
            estimated_week=estimated_weekly_earnings,
            estimated_month=estimated_monthly_earnings,
            missing_wage_shifts=missing_wage_shifts_count,
        ),
        daily_workload=daily_items,
        time_distribution=TimeDistributionData(
            class_percentage=class_pct,
            work_percentage=work_pct,
            study_percentage=study_pct,
            free_percentage=free_pct,
        ),
        health=health_data,
    )
