from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.schemas.planning import (
    PlanApplyBlock,
    PlanApplyRequest,
    PlanApplyResponse,
    PlanOptionOut,
    PlanOptionSummary,
    PlanPreviewRequest,
    PlanPreviewResponse,
    ProposedBlockOut,
    ScheduleContextSummary,
    ShiftAdjustmentOut,
)
from app.services.schedule import minutes_to_time
from app.services.smart_planner.context import ScheduleContextBuilder
from app.services.smart_planner.explainer import ExplanationEngine
from app.services.smart_planner.generator import CandidateGenerator
from app.services.smart_planner.scorer import ScheduleScorer
from app.store import add_block_to_store, detect_conflicts_and_totals, get_session


DOW_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class SmartPlannerService:
    @staticmethod
    def preview_plan(
        user_id: int,
        request: PlanPreviewRequest,
        db: Optional[Session] = None,
    ) -> PlanPreviewResponse:
        """
        Pure read-only preview of smart planning options for the target week.
        Mutates ZERO database records.
        """
        with get_session(db) as session:
            # 1. Gather comprehensive schedule context
            context = ScheduleContextBuilder.build(
                user_id=user_id,
                week_start=request.target_week_start,
                db=session,
            )

            # 2. Generate strategic candidate plans
            pref_tod = request.preferred_time_of_day or context.preferences.get("preferred_time_of_day", "any")
            density = request.schedule_density or context.preferences.get("schedule_density", "balanced")

            generated_options = CandidateGenerator.generate_options(
                context=context,
                allow_flexible_work_moves=request.allow_flexible_work_moves,
                preferred_time_of_day=pref_tod,
                schedule_density=density,
            )

            # 3. Score & explain each option
            scored_options = [ScheduleScorer.score_option(opt, context) for opt in generated_options]
            explained_options = [ExplanationEngine.explain_option(opt, context) for opt in scored_options]

            # 4. Transform into API response models
            api_options: list[PlanOptionOut] = []
            has_feasible = False
            all_blocking_issues: list[str] = []

            for opt in explained_options:
                if opt.is_valid:
                    has_feasible = True
                else:
                    all_blocking_issues.extend(opt.blocking_reasons)

                proposed_blocks: list[ProposedBlockOut] = []
                total_study_hours = 0.0

                for s in opt.slots:
                    dur_hrs = round(s.duration_min / 60.0, 2)
                    total_study_hours += dur_hrs
                    st_str = minutes_to_time(s.start_min) + ":00"
                    et_str = minutes_to_time(s.end_min) + ":00"

                    proposed_blocks.append(
                        ProposedBlockOut(
                            temp_id=s.temp_id,
                            title=f"Study: {s.task_title}",
                            day_of_week=s.day_of_week,
                            day_name=DOW_NAMES[s.day_of_week],
                            date=s.date.isoformat(),
                            start_time=st_str,
                            end_time=et_str,
                            duration_hours=dur_hrs,
                            study_task_id=s.task_id,
                            course_id=s.course_id,
                            type="study",
                        )
                    )

                summary = PlanOptionSummary(
                    added_study_blocks_count=len(proposed_blocks),
                    moved_flexible_shifts_count=len(opt.adjustments),
                    unchanged_classes_count=context.enrolled_classes_count,
                    unchanged_fixed_commitments_count=context.fixed_work_shifts_count + context.personal_events_count,
                    total_study_hours=round(total_study_hours, 1),
                    total_work_hours=round(context.fixed_work_shifts_count * 4.0, 1),
                    is_valid=opt.is_valid,
                    conflict_free=opt.is_valid,
                )

                api_options.append(
                    PlanOptionOut(
                        id=opt.option_id,
                        name=opt.name,
                        description=opt.description,
                        score=opt.score,
                        fit_percentage=opt.fit_percentage,
                        reasons=opt.reasons,
                        warnings=opt.warnings,
                        trade_offs=opt.trade_offs,
                        added_blocks=proposed_blocks,
                        moved_blocks=[],
                        summary=summary,
                    )
                )

            # Remove duplicate blocking issues
            unique_blocking = list(dict.fromkeys(all_blocking_issues))

            total_study_needed = sum(t["remaining_hours"] for t in context.tasks)

            context_summary = ScheduleContextSummary(
                enrolled_classes_count=context.enrolled_classes_count,
                fixed_work_shifts_count=context.fixed_work_shifts_count,
                flexible_work_shifts_count=context.flexible_work_shifts_count,
                personal_events_count=context.personal_events_count,
                pending_tasks_count=len(context.tasks),
                total_study_hours_needed=round(total_study_needed, 1),
            )

            return PlanPreviewResponse(
                week_start=context.week_start,
                week_end=context.week_end,
                context_summary=context_summary,
                has_feasible_solution=has_feasible,
                options=api_options,
                blocking_issues=unique_blocking,
            )

    @staticmethod
    def apply_plan(
        user_id: int,
        request: PlanApplyRequest,
        db: Optional[Session] = None,
    ) -> PlanApplyResponse:
        """
        Safely applies approved student-owned flexible items:
        1. Inserts proposed study blocks into TimeBlock.
        2. Updates associated StudyTask status to 'scheduled'.
        3. Never touches university class meetings or fixed commitments.
        4. Re-runs conflict engine to verify clean application.
        """
        with get_session(db) as session:
            created_block_ids: list[int] = []
            tasks_updated: set[int] = set()

            for blk in request.approved_new_blocks:
                st_clean = blk.start_time if len(blk.start_time) == 8 else f"{blk.start_time[:5]}:00"
                et_clean = blk.end_time if len(blk.end_time) == 8 else f"{blk.end_time[:5]}:00"

                spec_d = None
                if blk.date:
                    spec_d = date.fromisoformat(blk.date) if isinstance(blk.date, str) else blk.date

                new_tb = TimeBlock(
                    user_id=user_id,
                    type="study",
                    title=blk.title,
                    location="Self-study",
                    day_of_week=blk.day_of_week,
                    start_time=datetime.strptime(st_clean, "%H:%M:%S").time(),
                    end_time=datetime.strptime(et_clean, "%H:%M:%S").time(),
                    duration_minutes=int(round(blk.duration_hours * 60)),
                    is_recurring=False,
                    specific_date=spec_d,
                    is_flexible=True,
                    course_id=blk.course_id,
                    study_task_id=blk.study_task_id,
                    deleted=False,
                )
                session.add(new_tb)
                session.flush()
                created_block_ids.append(new_tb.id)

                if blk.study_task_id:
                    tasks_updated.add(blk.study_task_id)

            # Update study tasks to 'scheduled' if pending
            for tid in tasks_updated:
                task_rec = session.query(StudyTask).filter(StudyTask.id == tid, StudyTask.user_id == user_id).first()
                if task_rec and task_rec.status == "pending":
                    task_rec.status = "scheduled"

            session.commit()

            # 4. Post-application conflict validation
            conflicts, _ = detect_conflicts_and_totals(
                user_id=user_id,
                week_start=request.week_start,
                db=session,
            )

            conflicts_list = [
                {
                    "id": c.id,
                    "severity": c.severity,
                    "conflict_type": c.conflict_type,
                    "description": c.description,
                    "day_of_week": c.day_of_week,
                    "start": c.overlap_start,
                    "end": c.overlap_end,
                }
                for c in conflicts
            ]

            return PlanApplyResponse(
                success=True,
                message=f"Applied plan '{request.option_id}' with {len(created_block_ids)} study sessions.",
                created_blocks_count=len(created_block_ids),
                updated_shifts_count=0,
                applied_block_ids=created_block_ids,
                conflicts_detected_count=len(conflicts),
                conflicts=conflicts_list,
            )

    @staticmethod
    def revert_plan(
        user_id: int,
        week_start: date,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Reverts study sessions applied for the given week.
        Restores tasks to pending if no more sessions scheduled.
        """
        with get_session(db) as session:
            w_start = week_start - timedelta(days=week_start.weekday())
            w_end = w_start + timedelta(days=6)

            study_blocks = (
                session.query(TimeBlock)
                .filter(
                    TimeBlock.user_id == user_id,
                    TimeBlock.type == "study",
                    TimeBlock.study_task_id.isnot(None),
                    TimeBlock.specific_date >= w_start,
                    TimeBlock.specific_date <= w_end,
                    TimeBlock.deleted == False,
                )
                .all()
            )

            task_ids = set(b.study_task_id for b in study_blocks if b.study_task_id)
            deleted_count = len(study_blocks)

            for b in study_blocks:
                b.deleted = True

            session.commit()

            # Check if any remaining blocks exist for tasks
            for tid in task_ids:
                remaining = (
                    session.query(TimeBlock)
                    .filter(
                        TimeBlock.user_id == user_id,
                        TimeBlock.study_task_id == tid,
                        TimeBlock.deleted == False,
                    )
                    .count()
                )
                if remaining == 0:
                    t_rec = session.query(StudyTask).filter(StudyTask.id == tid, StudyTask.user_id == user_id).first()
                    if t_rec and t_rec.status == "scheduled":
                        t_rec.status = "pending"

            session.commit()

            return {
                "success": True,
                "reverted_blocks_count": deleted_count,
                "message": f"Reverted {deleted_count} planned study blocks for week of {w_start.isoformat()}.",
            }
