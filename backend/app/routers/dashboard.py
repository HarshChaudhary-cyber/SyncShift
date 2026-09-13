"""
Dashboard Router
GET /api/v1/dashboard
Consolidates user profile, today's schedule, next upcoming block countdown,
week statistics, conflict alerts, schedule health, work capacity, study goals,
and deterministic recommendations in a single round-trip.
"""
from datetime import date as dt_date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.institution import Institution, InstitutionMembership
from app.models.department import Department
from app.models.academic_term import AcademicTerm
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.student_profile import StudentProfile
from app.models.section_enrollment import SectionEnrollment
from app.schemas.student_academic import StudentAcademicSummary
from app.schemas.analytics import HealthFactorSchema, ScheduleHealthData
from app.schemas.common import DataResponse
from app.schemas.dashboard import (
    DashboardData,
    DashboardQuickAnalytics,
    DashboardStudySummary,
    DashboardStudyTask,
    DashboardUser,
    DashboardWorkSummary,
)
from app.services.schedule import (
    compute_adaptive_state,
    get_dashboard_alerts,
    get_dashboard_recommendations,
    get_next_up_block,
    get_today_schedule_data,
    get_user_today,
    get_week_schedule_data,
)
from app.services.schedule_health import compute_schedule_health
from app.store import get_all_blocks, get_occurrences_for_range, get_user_tasks
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DataResponse[DashboardData])
def get_dashboard(
    date: Optional[str] = Query(
        None,
        description="Optional date in YYYY-MM-DD format, defaults to today in user's timezone",
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns complete dashboard state answering 'What do I need to know right now?':
    - User profile details and configured work limit
    - Today's blocks sorted chronologically with is_now indicator
    - Next up countdown block
    - Weekly statistics and limit compliance
    - Actionable alerts for hard conflicts and over-limit warnings
    - Schedule Health score and factors
    - Work capacity meter and study progress
    - Deterministic actionable recommendations
    - Adaptive state for personalized UI
    """
    today_d, _ = get_user_today(current_user)
    if date:
        try:
            today_d = dt_date.fromisoformat(date)
        except ValueError:
            pass

    week_start = today_d - timedelta(days=today_d.weekday())
    week_end = week_start + timedelta(days=6)

    # 1. Today's blocks and current minute in user's timezone
    today_data, now_minutes = get_today_schedule_data(
        current_user=current_user,
        target_date=today_d.isoformat(),
    )

    # 2. Next upcoming block today
    next_up = get_next_up_block(
        today_blocks=today_data.blocks,
        now_minutes=now_minutes,
    )

    # 3. Weekly totals and conflicts using actual occurrences
    week_data, week_conflicts = get_week_schedule_data(current_user=current_user, week_start=week_start)

    # 4. Actionable alerts
    alerts = get_dashboard_alerts(
        week_conflicts=week_conflicts,
        week_data=week_data,
        work_limit=week_data.work_limit,
    )

    # 5. User information
    display_name = current_user.display_name
    if not display_name:
        display_name = current_user.email.split("@")[0].capitalize() if current_user.email else "Student"

    CURRENCY_SYMBOLS = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "₹": "₹",
        "$": "$",
        "€": "€",
        "£": "£",
        "¥": "¥",
    }
    user_currency = getattr(current_user, "currency", "INR") or "INR"
    currency_symbol = CURRENCY_SYMBOLS.get(user_currency.upper(), user_currency)

    user_info = DashboardUser(
        display_name=display_name,
        email=current_user.email,
        avatar_url=current_user.avatar_url,
        timezone=current_user.timezone or "Europe/London",
        weekly_work_hour_limit=float(current_user.weekly_work_hour_limit or 20.0),
        currency=currency_symbol,
    )

    # 6. Fetch week occurrences for health, work & study analytics
    week_occurrences = get_occurrences_for_range(
        user_id=current_user.user_id,
        start_date=week_start,
        end_date=week_end,
        db=db,
    )

    # 7. Schedule Health calculation
    health_result = compute_schedule_health(
        blocks=week_occurrences,
        conflicts=week_conflicts,
        weekly_work_limit=week_data.work_limit,
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

    # 8. Work Summary
    hours_used = week_data.total_shift_hours
    limit = week_data.work_limit
    pct = round((hours_used / limit) * 100, 1) if limit > 0 else 0.0
    rem_work = round(max(0.0, limit - hours_used), 1)
    over_work_hrs = round(max(0.0, hours_used - limit), 1)
    work_summary = DashboardWorkSummary(
        hours_used=hours_used,
        limit=limit,
        percentage=pct,
        remaining_hours=rem_work,
        over_limit=week_data.over_work_limit,
        over_hours=over_work_hrs,
    )

    # 9. Study Summary
    user_tasks = get_user_tasks(current_user.user_id, db=db)
    study_hours_this_week = 0.0
    for occ in week_occurrences:
        if getattr(occ, "type", "") == "study":
            s_m = int(occ.start_time.split(":")[0]) * 60 + int(occ.start_time.split(":")[1])
            e_m = int(occ.end_time.split(":")[0]) * 60 + int(occ.end_time.split(":")[1])
            dur = ((e_m + 24 * 60 - s_m) if e_m < s_m else (e_m - s_m)) / 60.0
            study_hours_this_week += dur

    next_task_dto: Optional[DashboardStudyTask] = None
    pending_tasks = [
        t for t in user_tasks
        if t.get("status") != "done" and (t.get("completed_hours", 0) < t.get("total_hours_required", 0))
    ]
    if pending_tasks:
        first_t = sorted(pending_tasks, key=lambda x: str(x.get("deadline", "9999")))[0]
        rem_hrs = max(0.1, round(first_t.get("total_hours_required", 0) - first_t.get("completed_hours", 0), 1))
        next_task_dto = DashboardStudyTask(
            id=first_t["id"],
            title=first_t["title"],
            deadline=str(first_t.get("deadline", "")),
            hours_remaining=rem_hrs,
            preferred_duration=first_t.get("preferred_duration", 90),
            course_code=None,
        )

    study_summary = DashboardStudySummary(
        hours_planned=round(study_hours_this_week, 1),
        hours_done=round(sum(float(t.get("completed_hours", 0)) for t in user_tasks), 1),
        has_goals=len(user_tasks) > 0,
        next_task=next_task_dto,
    )

    # 10. Quick Analytics
    analytics_summary = DashboardQuickAnalytics(
        class_hours=week_data.total_class_hours,
        work_hours=week_data.total_shift_hours,
        study_hours=round(study_hours_this_week, 1),
        conflict_count=week_data.conflict_count,
        expected_earnings=week_data.expected_earnings,
        currency_symbol=currency_symbol,
    )

    # 11. Recommendations
    recs = get_dashboard_recommendations(
        week_data=week_data,
        week_conflicts=week_conflicts,
        week_occurrences=week_occurrences,
        tasks=user_tasks,
        health_result=health_result,
    )

    # 12. Adaptive State
    all_raw_blocks = get_all_blocks(user_id=current_user.user_id, include_deleted=False, db=db)
    adaptive_state = compute_adaptive_state(
        all_blocks=all_raw_blocks,
        week_conflicts=week_conflicts,
        week_data=week_data,
    )

    # 13. Academic Summary (if enrolled in an institution)
    academic_summary = None
    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    if membership:
        inst = db.query(Institution).filter(Institution.id == membership.institution_id).first()
        profile = (
            db.query(StudentProfile)
            .filter(
                StudentProfile.user_id == current_user.user_id,
                StudentProfile.institution_id == membership.institution_id,
                StudentProfile.deleted_at.is_(None),
            )
            .first()
        )
        dept = None
        if profile and profile.department_id:
            dept = db.query(Department).filter(Department.id == profile.department_id).first()

        active_term = (
            db.query(AcademicTerm)
            .filter(
                AcademicTerm.institution_id == membership.institution_id,
                AcademicTerm.status == "active",
                AcademicTerm.deleted_at.is_(None),
            )
            .first()
        )

        enrollments = (
            db.query(SectionEnrollment, AcademicSection, AcademicCourse, AcademicTerm)
            .join(AcademicSection, SectionEnrollment.section_id == AcademicSection.id)
            .join(AcademicCourse, AcademicSection.course_id == AcademicCourse.id)
            .join(AcademicTerm, AcademicSection.academic_term_id == AcademicTerm.id)
            .filter(
                SectionEnrollment.student_id == current_user.user_id,
                SectionEnrollment.institution_id == membership.institution_id,
                SectionEnrollment.status == "active",
            )
            .all()
        )

        sec_list = []
        tot_credits = 0
        for enr, sec, crs, trm in enrollments:
            tot_credits += crs.credits
            sec_list.append({
                "enrollment_id": enr.id,
                "section_id": sec.id,
                "section_code": sec.section_code,
                "course_code": crs.code,
                "course_name": crs.name,
                "credits": crs.credits,
                "term_name": trm.name,
            })

        if inst:
            academic_summary = StudentAcademicSummary(
                has_academic_profile=True,
                institution_id=inst.id,
                institution_name=inst.name,
                institution_code=inst.code,
                department_name=dept.name if dept else None,
                program=profile.program if profile else None,
                year_of_study=profile.year_of_study if profile else None,
                student_number=profile.student_number if profile else None,
                current_term_name=active_term.name if active_term else None,
                enrolled_sections_count=len(sec_list),
                total_credits=tot_credits,
                enrolled_sections=sec_list,
            )

    return DataResponse(
        data=DashboardData(
            user=user_info,
            today=today_data,
            next_up=next_up,
            week=week_data,
            alerts=alerts,
            health=health_data,
            work=work_summary,
            study=study_summary,
            analytics=analytics_summary,
            recommendations=recs,
            adaptive_state=adaptive_state,
            academics=academic_summary,
        )
    )
