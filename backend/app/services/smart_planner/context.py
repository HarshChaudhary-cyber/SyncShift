from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.institution import InstitutionMembership
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint, StudentPreference
from app.models.study_task import StudyTask
from app.models.user import User
from app.services.schedule import time_to_minutes
from app.services.smart_planner.models import PlanningEvent, ScheduleContext
from app.store import get_occurrences_for_range, get_user_tasks


class ScheduleContextBuilder:
    @staticmethod
    def build(
        user_id: int,
        week_start: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> ScheduleContext:
        """
        Gathers complete schedule context for user_id over the target week:
        - University class meetings (from active section enrollments)
        - Student work shifts (fixed and flexible)
        - Student personal events
        - Blackout unavailable time windows
        - Hard constraints & soft preferences
        - Active study tasks needing planning
        """
        from app.store import get_session

        with get_session(db) as session:
            # 1. Determine week range (Monday to Sunday)
            if week_start is None:
                today_d = date.today()
                w_start = today_d - timedelta(days=today_d.weekday())
            else:
                w_start = week_start - timedelta(days=week_start.weekday())
            w_end = w_start + timedelta(days=6)

            # 2. Get user's institution ID if enrolled
            membership = (
                session.query(InstitutionMembership)
                .filter(
                    InstitutionMembership.user_id == user_id,
                    InstitutionMembership.status == "active",
                    InstitutionMembership.deleted_at.is_(None),
                )
                .first()
            )
            institution_id = membership.institution_id if membership else None

            # 3. User transition buffer
            user_rec = session.query(User).filter(User.id == user_id).first()
            min_transition = 15
            if user_rec and user_rec.minimum_transition_minutes is not None:
                min_transition = max(5, int(user_rec.minimum_transition_minutes))

            # 4. Fetch materialized occurrences from store
            # This automatically includes:
            # - University CourseMeetings (negative IDs, type="class")
            # - User TimeBlocks (shifts, personal events, study blocks)
            raw_occurrences = get_occurrences_for_range(
                user_id=user_id,
                start_date=w_start,
                end_date=w_end,
                db=session,
            )

            events: list[PlanningEvent] = []
            enrolled_classes = 0
            fixed_shifts = 0
            flexible_shifts = 0
            personal_events = 0

            for occ in raw_occurrences:
                s_min = time_to_minutes(occ.start_time)
                e_min = time_to_minutes(occ.end_time)
                if e_min <= s_min:
                    e_min += 24 * 60

                occ_d = occ.occurrence_date or w_start
                dow = occ.day_of_week if occ.day_of_week is not None else ((occ_d.weekday() + 1) % 7)

                if occ.type == "class":
                    enrolled_classes += 1
                    events.append(
                        PlanningEvent(
                            id=occ.id,
                            event_type="class",
                            title=occ.title,
                            day_of_week=dow,
                            date=occ_d,
                            start_min=s_min,
                            end_min=e_min,
                            location=occ.location,
                            is_fixed=True,
                            course_id=occ.course_id,
                        )
                    )
                elif occ.type == "shift":
                    if occ.is_flexible:
                        flexible_shifts += 1
                        events.append(
                            PlanningEvent(
                                id=occ.id,
                                event_type="flexible_shift",
                                title=occ.title,
                                day_of_week=dow,
                                date=occ_d,
                                start_min=s_min,
                                end_min=e_min,
                                location=occ.location,
                                is_fixed=False,
                                original_block_id=occ.id,
                            )
                        )
                    else:
                        fixed_shifts += 1
                        events.append(
                            PlanningEvent(
                                id=occ.id,
                                event_type="fixed_shift",
                                title=occ.title,
                                day_of_week=dow,
                                date=occ_d,
                                start_min=s_min,
                                end_min=e_min,
                                location=occ.location,
                                is_fixed=True,
                                original_block_id=occ.id,
                            )
                        )
                elif occ.type in ("personal", "event"):
                    personal_events += 1
                    events.append(
                        PlanningEvent(
                            id=occ.id,
                            event_type="personal",
                            title=occ.title,
                            day_of_week=dow,
                            date=occ_d,
                            start_min=s_min,
                            end_min=e_min,
                            location=occ.location,
                            is_fixed=True,
                            original_block_id=occ.id,
                        )
                    )

            # 5. Fetch recurring unavailable/blackout slots
            avail_slots = (
                session.query(StudentAvailability)
                .filter(
                    StudentAvailability.user_id == user_id,
                    StudentAvailability.is_available == False,
                )
                .all()
            )
            for av in avail_slots:
                av_s = av.start_time.hour * 60 + av.start_time.minute
                av_e = av.end_time.hour * 60 + av.end_time.minute
                # Materialize blackout for every matching day in target week
                for day_offset in range(7):
                    curr_d = w_start + timedelta(days=day_offset)
                    curr_dow = (curr_d.weekday() + 1) % 7
                    if curr_dow == av.day_of_week:
                        events.append(
                            PlanningEvent(
                                id=-(9000 + int(av.id)),
                                event_type="blackout",
                                title=av.title or "Unavailable (Blackout)",
                                day_of_week=curr_dow,
                                date=curr_d,
                                start_min=av_s,
                                end_min=av_e,
                                is_fixed=True,
                            )
                        )

            # 6. Fetch hard constraints
            constraints_rec = (
                session.query(StudentConstraint)
                .filter(
                    StudentConstraint.user_id == user_id,
                    StudentConstraint.is_active == True,
                    StudentConstraint.is_hard == True,
                )
                .all()
            )
            hard_constraints = []
            for c in constraints_rec:
                hard_constraints.append({
                    "id": c.id,
                    "type": c.constraint_type,
                    "day_of_week": c.day_of_week,
                    "time_value": c.time_value.strftime("%H:%M:%S") if c.time_value else None,
                    "int_value": c.int_value,
                    "description": c.description,
                })

            # 7. Fetch soft preferences
            pref_rec = (
                session.query(StudentPreference)
                .filter(StudentPreference.user_id == user_id)
                .first()
            )
            preferences = {
                "preferred_time_of_day": pref_rec.preferred_time_of_day if pref_rec else "any",
                "schedule_density": pref_rec.schedule_density if pref_rec else "balanced",
                "preferred_break_duration_minutes": pref_rec.preferred_break_duration_minutes if pref_rec else 30,
                "max_campus_days_per_week": pref_rec.max_campus_days_per_week if pref_rec else None,
                "preferred_days_off": pref_rec.preferred_days_off if pref_rec else None,
                "work_study_balance_weight": pref_rec.work_study_balance_weight if pref_rec else 3,
            }

            # 8. Fetch active tasks needing study planning
            raw_tasks = (
                session.query(StudyTask)
                .filter(
                    StudyTask.user_id == user_id,
                    StudyTask.status != "done",
                )
                .order_by(StudyTask.deadline, StudyTask.id)
                .all()
            )
            tasks = []
            for t in raw_tasks:
                comp = float(t.completed_hours or 0.0)
                tot = float(t.total_hours_required or 0.0)
                rem = max(0.0, tot - comp)
                if rem > 0:
                    tasks.append({
                        "id": t.id,
                        "title": t.title,
                        "course_id": t.course_id,
                        "total_hours": tot,
                        "completed_hours": comp,
                        "remaining_hours": rem,
                        "deadline": t.deadline,
                        "priority": t.priority or "medium",
                        "preferred_duration": t.preferred_duration or 90,
                    })

            return ScheduleContext(
                user_id=user_id,
                institution_id=institution_id,
                week_start=w_start,
                week_end=w_end,
                events=events,
                hard_constraints=hard_constraints,
                preferences=preferences,
                tasks=tasks,
                enrolled_classes_count=enrolled_classes,
                fixed_work_shifts_count=fixed_shifts,
                flexible_work_shifts_count=flexible_shifts,
                personal_events_count=personal_events,
                transition_buffer_min=min_transition,
            )
