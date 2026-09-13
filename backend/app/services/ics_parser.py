import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import icalendar
from icalendar import Calendar, Event

from app.schemas.import_ics import IcsPreviewItem, IcsUnmatchedItem

# Mapping standard iCalendar two-letter weekday codes to 0=Monday..6=Sunday
ICAL_DAY_MAP: dict[str, int] = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


def convert_rrule_dtstart_to_day_of_week(rrule: Any, dtstart: datetime) -> int:
    """
    Helper function to convert RRULE/DTSTART to day_of_week integer (0=Mon, 6=Sun).
    If RRULE specifies BYDAY, uses the first specified day.
    Otherwise defaults to the weekday of dtstart.
    """
    if rrule:
        byday = rrule.get("BYDAY") if hasattr(rrule, "get") else None
        if byday:
            if isinstance(byday, list) and len(byday) > 0:
                day_code = str(byday[0])[:2].upper()
                if day_code in ICAL_DAY_MAP:
                    return ICAL_DAY_MAP[day_code]
            elif isinstance(byday, str):
                day_code = byday[:2].upper()
                if day_code in ICAL_DAY_MAP:
                    return ICAL_DAY_MAP[day_code]

    return dtstart.weekday()


def extract_recurring_days(rrule: Any, dtstart: datetime) -> list[int]:
    """
    Extracts all recurring days of the week (0=Mon, 6=Sun) specified in RRULE BYDAY.
    If BYDAY is not present, returns [dtstart.weekday()].
    """
    if not rrule:
        return [dtstart.weekday()]

    byday = rrule.get("BYDAY") if hasattr(rrule, "get") else None
    if not byday:
        return [dtstart.weekday()]

    day_list = byday if isinstance(byday, list) else [byday]
    extracted_days: list[int] = []

    for d in day_list:
        day_code = str(d)[:2].upper()
        if day_code in ICAL_DAY_MAP:
            day_idx = ICAL_DAY_MAP[day_code]
            if day_idx not in extracted_days:
                extracted_days.append(day_idx)

    return sorted(extracted_days) if extracted_days else [dtstart.weekday()]


def format_time_hhmm(dt_val: datetime) -> str:
    """
    Formats a datetime object to HH:MM 24-hour string.
    """
    return f"{dt_val.hour:02d}:{dt_val.minute:02d}"


def extract_course_code(title: str) -> Optional[str]:
    """
    Attempts to extract course code (e.g. CS101, CS 210, MATH 220) from title.
    """
    match = re.search(r"\b([A-Z]{2,5}\s*\d{3,4}[A-Z]?)\b", title)
    return match.group(1).strip() if match else None


def parse_ics_timetable(content: bytes | str) -> tuple[list[IcsPreviewItem], list[IcsUnmatchedItem]]:
    """
    Parses an uploaded iCalendar (.ics) timetable file.
    Extracts ONLY recurring weekly timed events, skipping:
      - All-day events (DTSTART is date only)
      - One-off events (no RRULE or non-weekly recurrence)
      - Events older than today minus 6 months
      - Events with invalid timezone or missing end time

    Returns:
        tuple of (preview_items, unmatched_items)
    """
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content

    # 1. Parse using icalendar
    try:
        cal = Calendar.from_ical(content_bytes)
    except Exception as exc:
        raise ValueError(f"Invalid iCalendar syntax: {exc}") from exc

    today_date = datetime.now(timezone.utc).date()
    cutoff_date = today_date - timedelta(days=180)  # ~6 months

    preview: list[IcsPreviewItem] = []
    unmatched: list[IcsUnmatchedItem] = []
    item_counter = 1

    for component in cal.walk("VEVENT"):
        summary = str(component.get("SUMMARY", "")).strip() or "Untitled Class"
        location_raw = component.get("LOCATION")
        location = str(location_raw).strip() if location_raw else ""

        # --- Check DTSTART ---
        dtstart_prop = component.get("DTSTART")
        if not dtstart_prop or not hasattr(dtstart_prop, "dt"):
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="Missing DTSTART",
                    raw_data={"summary": summary},
                )
            )
            continue

        dtstart_val = dtstart_prop.dt

        # Skip all-day events (isinstance date but not datetime)
        if isinstance(dtstart_val, date) and not isinstance(dtstart_val, datetime):
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="All-day event without explicit time boundaries",
                    raw_data={"dtstart": str(dtstart_val), "summary": summary},
                )
            )
            continue

        # --- Check DTEND ---
        dtend_prop = component.get("DTEND")
        if not dtend_prop or not hasattr(dtend_prop, "dt"):
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="Missing DTEND (missing end time)",
                    raw_data={"dtstart": str(dtstart_val), "summary": summary},
                )
            )
            continue

        dtend_val = dtend_prop.dt
        if not isinstance(dtend_val, datetime):
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="DTEND is not a valid datetime",
                    raw_data={"dtend": str(dtend_val), "summary": summary},
                )
            )
            continue

        # Validate timezone accessibility
        try:
            if dtstart_val.tzinfo:
                _ = dtstart_val.tzname()
            if dtend_val.tzinfo:
                _ = dtend_val.tzname()
        except Exception:
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="Invalid or unresolvable timezone definition",
                    raw_data={"summary": summary},
                )
            )
            continue

        # --- Check RRULE ---
        rrule = component.get("RRULE")
        if not rrule:
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="One-off event (no RRULE recurrence)",
                    raw_data={"dtstart": str(dtstart_val), "summary": summary},
                )
            )
            continue

        freq_val = rrule.get("FREQ") if hasattr(rrule, "get") else None
        freq_list = [str(f).upper() for f in (freq_val if isinstance(freq_val, list) else [freq_val])]
        if "WEEKLY" not in freq_list:
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason=f"Non-weekly recurrence (FREQ={freq_val})",
                    raw_data={"dtstart": str(dtstart_val), "summary": summary},
                )
            )
            continue

        # --- Check Age (older than today minus 6 months) ---
        until_val = rrule.get("UNTIL") if hasattr(rrule, "get") else None
        if until_val:
            until_item = until_val[0] if isinstance(until_val, list) else until_val
            if isinstance(until_item, datetime):
                until_date = until_item.date()
            elif isinstance(until_item, date):
                until_date = until_item
            else:
                until_date = None

            if until_date and until_date < cutoff_date:
                unmatched.append(
                    IcsUnmatchedItem(
                        summary=summary,
                        reason=f"Event ended more than 6 months ago (UNTIL={until_date})",
                        raw_data={"until": str(until_date), "summary": summary},
                    )
                )
                continue
        else:
            # If no UNTIL, verify DTSTART date is not older than cutoff
            start_date = dtstart_val.date()
            if start_date < cutoff_date:
                unmatched.append(
                    IcsUnmatchedItem(
                        summary=summary,
                        reason=f"Event started more than 6 months ago without UNTIL date ({start_date})",
                        raw_data={"dtstart": str(start_date), "summary": summary},
                    )
                )
                continue

        # Format times
        start_time_str = format_time_hhmm(dtstart_val)
        end_time_str = format_time_hhmm(dtend_val)

        if start_time_str == end_time_str:
            unmatched.append(
                IcsUnmatchedItem(
                    summary=summary,
                    reason="Event start and end times are identical",
                    raw_data={"start_time": start_time_str, "summary": summary},
                )
            )
            continue

        # Extract recurrence interval (e.g. 1=weekly, 2=biweekly)
        interval_val = rrule.get("INTERVAL", 1) if rrule else 1
        try:
            interval_int = int(interval_val[0] if isinstance(interval_val, list) else interval_val)
        except Exception:
            interval_int = 1

        effective_from_date = dtstart_val.date() if isinstance(dtstart_val, datetime) else (dtstart_val if isinstance(dtstart_val, date) else None)
        effective_until_date = until_date if 'until_date' in locals() and until_date else None

        # Extract days of week (0=Monday, 6=Sunday)
        days = extract_recurring_days(rrule, dtstart_val)
        course_code = extract_course_code(summary)

        for day in days:
            temp_id = f"import-{item_counter}-{uuid.uuid4().hex[:6]}"
            item_counter += 1

            notes = ""
            if len(days) > 1:
                notes = f"Recurring multi-day session ({len(days)} days/week)"
            if interval_int == 2:
                notes = f"Biweekly class (every 2 weeks){(' · ' + notes) if notes else ''}"
            elif interval_int > 2:
                notes = f"Repeats every {interval_int} weeks{(' · ' + notes) if notes else ''}"

            preview.append(
                IcsPreviewItem(
                    temp_id=temp_id,
                    title=summary,
                    day_of_week=day,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    location=location,
                    is_recurring=True,
                    recurring=True,
                    recurrence_interval=interval_int,
                    effective_from=effective_from_date,
                    effective_until=effective_until_date,
                    course_code=course_code,
                    notes=notes,
                )
            )

    return preview, unmatched
