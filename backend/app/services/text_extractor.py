"""
text_extractor.py – turn extracted plain text into structured FilePreviewItem list.

Strategy (regex-only; LLM can be layered in later):
  1. Split input into lines.
  2. For each line, try to match a day name + time range + optional title.
  3. Normalise times to "HH:MM" 24-hour format.
  4. Tag rows as confidence="low" when OCR is involved, or when times are
     vague / missing.
  5. Return [] if nothing is found (caller surfaces "Couldn't find a timetable").

Supported patterns (case-insensitive):
  Mon 9:00-10:30 CS101 Room 204
  Monday 09:00 - 10:30 CS101
  Tue 2pm-3:30pm ENG102
  9:00 AM - 10:30 AM CS101 Room 101
  Wed  09:00  11:00  MATH220  Hall B
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from app.schemas.file_import import FilePreviewItem

# ──────────────────────────────────────────────────────────────────────────────
# Day-name → weekday index (0=Monday … 6=Sunday)
# ──────────────────────────────────────────────────────────────────────────────

_DAY_MAP: dict[str, int] = {
    "monday": 0, "mon": 0, "mo": 0,
    "tuesday": 1, "tue": 1, "tu": 1,
    "wednesday": 2, "wed": 2, "we": 2,
    "thursday": 3, "thu": 3, "th": 3,
    "friday": 4, "fri": 4, "fr": 4,
    "saturday": 5, "sat": 5, "sa": 5,
    "sunday": 6, "sun": 6, "su": 6,
}

_DAY_PATTERN = r"(?P<day>monday|mon|mo|tuesday|tue|tu|wednesday|wed|we|thursday|thu|th|friday|fri|fr|saturday|sat|sa|sunday|sun|su)"

# ──────────────────────────────────────────────────────────────────────────────
# Time helpers
# ──────────────────────────────────────────────────────────────────────────────

# Matches: 9:00, 09:00, 9:00 AM, 9:00AM, 9am, 9 AM, 2:30pm, 14:00
_TIME_RE = re.compile(
    r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ampm>am|pm)?",
    re.IGNORECASE,
)


def _parse_time(raw: str) -> str:
    """
    Parse a raw time token into 'HH:MM' (24-hour).
    Returns "" if parsing fails.
    """
    raw = raw.strip()
    m = _TIME_RE.fullmatch(raw)
    if not m:
        # Try partial match (e.g. "9am" with no group boundary)
        m = _TIME_RE.match(raw)
    if not m:
        return ""

    h = int(m.group("h"))
    mins = int(m.group("m") or 0)
    ampm = (m.group("ampm") or "").lower()

    if ampm == "pm" and h != 12:
        h += 12
    elif ampm == "am" and h == 12:
        h = 0

    if h > 23 or mins > 59:
        return ""

    return f"{h:02d}:{mins:02d}"


def _normalise_time(raw: str) -> str:
    """Wrapper that tries harder on tricky tokens like '9AM', '2:30pm'."""
    raw = raw.strip()
    # Strip any non-time suffix (e.g., trailing punctuation)
    raw = re.sub(r"[^\d:apmAPM]$", "", raw)
    return _parse_time(raw)


# ──────────────────────────────────────────────────────────────────────────────
# Course code detector (reused from ics_parser)
# ──────────────────────────────────────────────────────────────────────────────

def _extract_course_code(text: str) -> Optional[str]:
    m = re.search(r"\b([A-Z]{2,5}\s*\d{3,4}[A-Z]?)\b", text)
    return m.group(1).strip() if m else None


# ──────────────────────────────────────────────────────────────────────────────
# Regex patterns for timetable lines
# ──────────────────────────────────────────────────────────────────────────────

# Time token: 9:00, 09:00, 9:00am, 9am, 2:30pm, etc.
# NOTE: We do NOT include the trailing hyphen in the ampm match to avoid
# consuming the range separator (e.g. "9:00-10:30", "2pm-3:30pm").
_TIME_TOKEN = r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)"

# Separator between start and end time.
# Important: must use a proper group so it can be made optional as a unit.
# Handles: "-", "–", "—", " - ", " to "
_SEP = r"(?:[ \t]*[-–—][ \t]*|[ \t]+to[ \t]+)"

# Pattern A: "Day HH:MM[-HH:MM] [rest]"   (day comes first)
# Uses named groups: day, (group 2)=start_time, (group 3)=end_time, rest
_PATTERN_A = re.compile(
    rf"(?i)^{_DAY_PATTERN}[ \t]+{_TIME_TOKEN}(?:{_SEP}{_TIME_TOKEN})?[ \t,]*(?P<rest>.*)$"
)

# Pattern B: "HH:MM[-HH:MM] [Day] [rest]"  (time comes first)
_PATTERN_B = re.compile(
    rf"(?i)^{_TIME_TOKEN}(?:{_SEP}{_TIME_TOKEN})?[ \t]+{_DAY_PATTERN}[ \t,]*(?P<rest>.*)$"
)

# Pattern C: loosely "Day … HH:MM … HH:MM … rest"  (column-separated, any whitespace)
_PATTERN_C = re.compile(
    rf"(?i)\b{_DAY_PATTERN}\b.*?{_TIME_TOKEN}.*?(?:{_SEP}|[ \t]+){_TIME_TOKEN}"
)



def _build_item(
    *,
    day: int,
    start_time: str,
    end_time: str,
    title: str,
    location: str,
    source_line: str,
    is_ocr: bool,
    counter: int,
) -> FilePreviewItem:
    confidence: str = "low" if is_ocr else "high"

    # Downgrade confidence when times are vague or very short title
    if not start_time or len(title.strip()) < 3:
        confidence = "low"

    course_code = _extract_course_code(title)
    temp_id = f"file-{counter}-{uuid.uuid4().hex[:6]}"

    return FilePreviewItem(
        temp_id=temp_id,
        title=title.strip() or "Unnamed Class",
        day_of_week=day,
        start_time=start_time,
        end_time=end_time,
        location=location.strip() or None,
        confidence=confidence,  # type: ignore[arg-type]
        source_line=source_line.strip(),
        course_code=course_code,
        notes="",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

def text_to_blocks(text: str, is_ocr: bool) -> list[FilePreviewItem]:
    """
    Parse `text` (plain text extracted from any document) into a list of
    FilePreviewItem candidates.

    Returns an empty list if no timetable entries are found.
    """
    items: list[FilePreviewItem] = []
    counter = 1

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 4:
            continue

        matched = _try_pattern_a(line, is_ocr, counter)
        if matched is None:
            matched = _try_pattern_b(line, is_ocr, counter)
        if matched is None:
            matched = _try_pattern_c(line, is_ocr, counter)

        if matched is not None:
            items.append(matched)
            counter += 1

    return items


# ──────────────────────────────────────────────────────────────────────────────
# Per-pattern matchers
# ──────────────────────────────────────────────────────────────────────────────

def _try_pattern_a(line: str, is_ocr: bool, counter: int) -> Optional[FilePreviewItem]:
    """Pattern A: Day start[-end] rest"""
    m = _PATTERN_A.match(line)
    if not m:
        return None

    day_str = m.group("day").lower()
    day = _DAY_MAP.get(day_str, -1)
    if day == -1:
        return None

    raw_start = m.group(2)
    raw_end = m.group(3) or ""
    rest = m.group("rest").strip()

    start_time = _normalise_time(raw_start) if raw_start else ""
    end_time = _normalise_time(raw_end) if raw_end else ""

    # Try to split rest into title + location
    title, location = _split_title_location(rest)

    return _build_item(
        day=day, start_time=start_time, end_time=end_time,
        title=title, location=location, source_line=line,
        is_ocr=is_ocr, counter=counter,
    )


def _try_pattern_b(line: str, is_ocr: bool, counter: int) -> Optional[FilePreviewItem]:
    """Pattern B: start[-end] Day rest"""
    m = _PATTERN_B.match(line)
    if not m:
        return None

    raw_start = m.group(1)
    raw_end = m.group(2) or ""
    day_str = m.group("day").lower()
    day = _DAY_MAP.get(day_str, -1)
    if day == -1:
        return None

    rest = m.group("rest").strip()

    start_time = _normalise_time(raw_start) if raw_start else ""
    end_time = _normalise_time(raw_end) if raw_end else ""
    title, location = _split_title_location(rest)

    return _build_item(
        day=day, start_time=start_time, end_time=end_time,
        title=title, location=location, source_line=line,
        is_ocr=is_ocr, counter=counter,
    )


def _try_pattern_c(line: str, is_ocr: bool, counter: int) -> Optional[FilePreviewItem]:
    """Pattern C: loose column-style (Day … time … time … rest)"""
    m = _PATTERN_C.search(line)
    if not m:
        return None

    day_str = m.group("day").lower()
    day = _DAY_MAP.get(day_str, -1)
    if day == -1:
        return None

    raw_start = m.group(2)
    raw_end = m.group(3) or ""

    start_time = _normalise_time(raw_start) if raw_start else ""
    end_time = _normalise_time(raw_end) if raw_end else ""

    if not start_time:
        return None  # too ambiguous without a time

    # Take everything after the second time token as title+location
    after_match = line[m.end():].strip()
    before_day = line[: m.start()].strip()
    rest = " ".join(filter(None, [before_day, after_match]))
    title, location = _split_title_location(rest)

    return _build_item(
        day=day, start_time=start_time, end_time=end_time,
        title=title, location=location, source_line=line,
        is_ocr=is_ocr, counter=counter,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

# Words that indicate a location ("Room 204", "Hall B", "Building 3")
_LOCATION_KEYWORDS = re.compile(
    r"\b(room|rm|hall|building|bldg|lab|theatre|theater|floor|level|suite)\b",
    re.IGNORECASE,
)


def _split_title_location(rest: str) -> tuple[str, str]:
    """
    Heuristically split 'rest' into (title, location).
    Location is identified by keywords like Room/Hall/Building.
    """
    rest = rest.strip()
    if not rest:
        return "", ""

    # Try splitting on " - " or comma
    for sep in (" - ", ", ", " | "):
        parts = rest.split(sep, 1)
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            if _LOCATION_KEYWORDS.search(b):
                return a, b
            if _LOCATION_KEYWORDS.search(a):
                return b, a

    # Check if location keywords appear in rest
    loc_match = _LOCATION_KEYWORDS.search(rest)
    if loc_match:
        # Everything from the keyword onwards is location
        loc_start = loc_match.start()
        title = rest[:loc_start].strip()
        location = rest[loc_start:].strip()
        return title, location

    # Fallback: entire rest is title
    return rest, ""
