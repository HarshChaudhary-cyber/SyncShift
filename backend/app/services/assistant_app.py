"""Grounded app help and explicit, date-scoped personal schedule commands."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.block_override import BlockOverride
from app.models.time_block import TimeBlock, BlockType, BlockStatus
from app.services.audit import record_audit_log
from app.store import get_occurrences_for_range


APP_GUIDE = {
    "calendar": "Calendar shows your classes, work shifts and study sessions. Use Add Class or Add Shift to create an event, select an event to edit it, and choose a date or week to browse. My Timetable shows your university's published classes.",
    "import": "Use Attach timetable in this chat, or Calendar → Import Timetable. Upload PDF, ICS, CSV, Excel (.xlsx/.xls), Word (.docx/.doc), PowerPoint (.pptx), text or a PNG/JPG/WebP image. Review extracted days and times, uncheck duplicates or uncertain entries, then import the selected events. Scanned documents need readable text or the configured AI/OCR service; a format alone cannot guarantee accurate extraction.",
    "work": "Work Shifts lets you add hours, location and hourly wage. The dashboard totals weekly hours and estimated earnings against your work-hour limit in Settings. Say 'Move my today work to tomorrow' to move today's work occurrences at the same times. I check conflicts first and preserve the weekly recurring schedule.",
    "study": "Study Tasks stores assignments, deadlines, required hours and progress. Add a task, then use Smart Planner to find study sessions around classes and shifts. Review a proposed plan before applying it.",
    "conflicts": "Conflicts lists overlapping events and work-limit problems. Open a clash to inspect the events, then change a personal event or use Smart Planner for alternatives. Official university classes are managed by authorized staff.",
    "settings": "Settings controls your profile, timezone, appearance, weekly work-hour limit and notification preferences. Times use your profile timezone. Notifications lists timetable changes and reminders; email and push delivery depend on their service configuration.",
    "admin": "Administrators manage departments, terms, rooms, courses, sections, faculty and enrollments. Create a timetable draft, edit its meetings, preview impact, review/approve and publish it. University-wide changes require an authorized administrator and confirmation.",
    "access": "I can read your authorized schedule, courses, tasks, work hours, conflicts, preferences and notifications using app tools. I can prepare supported scheduling changes and directly move today's work to tomorrow when unambiguous and conflict-free. I cannot access another user's private data or control unrelated apps. Other changes may require a preview or more details.",
}


def app_help(message, role):
    text = message.lower()
    if re.search(r"\bhow (many|much)\b|\bwhat (is|are) my\b", text):
        return None
    if not re.search(r"\b(how|help|guide|explain|tell me about|what can|what is|what does|features|use this|use the)\b", text):
        return None
    if not re.search(r"app|syncshift|website|platform|calendar|import|upload|timetable|work shift|study task|planner|notification|setting|feature|you do|your access", text):
        return None
    topics = {
        "import": r"import|upload|file|pdf|excel|csv|image",
        "work": r"work shift|earn|wage|move.*work",
        "study": r"study|planner|task",
        "conflicts": r"conflict|overlap",
        "settings": r"setting|profile|notification|timezone",
        "calendar": r"calendar|timetable",
        "access": r"you do|your access|jarvis|permission",
    }
    selected = [key for key, pattern in topics.items() if re.search(pattern, text)]
    if not selected:
        selected = ["calendar", "import", "work", "study", "conflicts", "settings", "access"]
    if role == "admin" and (not selected or re.search(r"admin|whole|app|website", text)):
        selected.append("admin")
    return "\n\n".join(f"**{key.title()}** — {APP_GUIDE[key]}" for key in selected)


def is_today_work_move(message):
    text = message.lower().strip().rstrip(".!?").replace("’", "'").replace("tommorrow", "tomorrow")
    prefix = r"(?:(?:can|could|would) you )?(?:please )?(?:move|reschedule|postpone|shift) "
    subject = r"(?:all )?(?:my )?(?:today(?:'s)? (?:work(?: shifts?)?|shifts?)|(?:work(?: shifts?)?|shifts?) (?:from )?today)"
    return bool(re.fullmatch(prefix + subject + r" to tomorrow(?: please)?", text))


def move_today_work(db, user, today=None):
    """Move only today's occurrences, atomically; no change to recurring series."""
    today = today or datetime.now(ZoneInfo(user.timezone or "UTC")).date()
    tomorrow = today + timedelta(days=1)
    events = get_occurrences_for_range(user.user_id, today, today, db=db)
    dropped = {b.id for b in db.query(TimeBlock).filter_by(user_id=user.user_id, status=BlockStatus.DROPPED).all()}
    shifts = [e for e in events if e.type == BlockType.SHIFT and e.id not in dropped]
    if not shifts:
        return "You have no work shifts today to move. No schedule changes were made.", False
    if len(shifts) > 20:
        return "There are more than 20 work shifts today. Please move a smaller selection in Calendar.", False
    targets = get_occurrences_for_range(user.user_id, tomorrow - timedelta(days=1), tomorrow + timedelta(days=1), db=db)

    def interval(event, day):
        start = datetime.combine(day, datetime.strptime(event.start_time[:5], "%H:%M").time())
        end = datetime.combine(day, datetime.strptime(event.end_time[:5], "%H:%M").time())
        if end <= start:
            end += timedelta(days=1)
        return start, end

    planned = []
    for shift in shifts:
        start, end = interval(shift, tomorrow)
        for other in targets:
            if other.id in {s.id for s in shifts} and other.occurrence_date == today:
                continue
            if other.id in dropped:
                continue
            other_start, other_end = interval(other, other.occurrence_date)
            gap = timedelta(minutes=user.minimum_transition_minutes or 0)
            if start < other_end + gap and other_start < end + gap:
                return f"I haven't moved anything: '{shift.title}' would overlap or leave too little transition time with '{other.title}' tomorrow. Choose another time in Calendar or ask me to find free time.", False
        if any(start < e and s < end for s, e in planned):
            return "Today's shifts overlap each other. Please choose which shift to move in Calendar.", False
        planned.append((start, end))

    target_week = tomorrow - timedelta(days=tomorrow.weekday())
    if today < target_week:
        week_events = get_occurrences_for_range(user.user_id, target_week, target_week+timedelta(days=6), db=db)
        minutes = sum((interval(e, e.occurrence_date)[1] - interval(e, e.occurrence_date)[0]).total_seconds() / 60
            for e in week_events if e.type == BlockType.SHIFT and e.id not in dropped)
        minutes += sum((end-start).total_seconds() / 60 for start, end in planned)
        if minutes > float(user.weekly_work_hour_limit) * 60:
            return "I haven't moved anything: these shifts would exceed your work-hour limit next week. Choose another date or review your limit in Settings.", False

    try:
        for shift in shifts:
            block = db.query(TimeBlock).filter_by(id=shift.id, user_id=user.user_id, deleted=False).with_for_update().one()
            # Find a previously moved occurrence, if today's event was already overridden.
            override = db.query(BlockOverride).filter_by(time_block_id=block.id,
                user_id=user.user_id, override_date=today, is_cancelled=False).first()
            if block.is_recurring:
                override = override or db.query(BlockOverride).filter_by(
                    time_block_id=block.id, user_id=user.user_id, original_date=today).first()
                if override is None:
                    override = BlockOverride(time_block_id=block.id, user_id=user.user_id, original_date=today)
                    db.add(override)
                override.override_date = tomorrow
                override.start_time = datetime.strptime(shift.start_time[:5], "%H:%M").time()
                override.end_time = datetime.strptime(shift.end_time[:5], "%H:%M").time()
                start, end = interval(shift, tomorrow)
                override.duration_minutes = int((end-start).total_seconds() / 60)
                override.is_cancelled = False
                override.note = "Moved by your explicit assistant request"
            else:
                if override:
                    override.override_date = tomorrow
                else:
                    block.specific_date = tomorrow
                    block.effective_from = tomorrow
                    if block.effective_until:
                        block.effective_until = tomorrow
                    block.day_of_week = (tomorrow.weekday() + 1) % 7
        db.commit()
    except Exception:
        db.rollback()
        raise
    record_audit_log(db=db, user_id=user.user_id, action="ASSISTANT_MOVE_TODAY_WORK",
        entity_type="time_block", description=f"Moved {len(shifts)} work occurrences from {today} to {tomorrow}")
    detail = "\n".join(f"- {e.title}: {e.start_time[:5]}–{e.end_time[:5]}" for e in shifts)
    return f"Moved {len(shifts)} work shift(s) from {today} to {tomorrow}:\n{detail}\nOnly these occurrences changed; recurring weekly times are preserved. You can edit them in Calendar.", True
