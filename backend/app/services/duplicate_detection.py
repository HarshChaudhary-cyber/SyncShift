"""
Deterministic duplicate detection engine for SyncShift timetable imports.
Normalizes titles/codes, evaluates strong scheduling signals,
and categorizes matches into HIGH, POSSIBLE, or NOT duplicate.
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional

from app.models.time_block import TimeBlock


class DuplicateConfidence(str, Enum):
    HIGH = "high"
    POSSIBLE = "possible"
    NONE = "none"


def normalize_text(text: Optional[str]) -> str:
    """
    Normalizes textual event attributes:
    - Lowercases text
    - Strips punctuation and common separators (-, :, /, _, |, (, ), ,, .)
    - Collapses multiple whitespace characters into a single space
    Example:
      'CS301 - Database Systems (Lecture)' -> 'cs301 database systems lecture'
      'CS301 Database Systems' -> 'cs301 database systems'
    """
    if not text:
        return ""
    # Lowercase
    s = text.lower()
    # Replace punctuation and common separators with spaces
    s = re.sub(r"[\-_:/\(\)\[\]|,.\\]+", " ", s)
    # Collapse multiple whitespace characters
    s = re.sub(r"\s+", " ", s).strip()
    return s


def text_similarity(a: str, b: str) -> float:
    """Computes normalized text similarity ratio between 0.0 and 1.0."""
    norm_a = normalize_text(a)
    norm_b = normalize_text(b)
    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b:
        return 1.0
    # Check if one is a substring of the other with significant length
    if len(norm_a) >= 4 and len(norm_b) >= 4:
        if norm_a in norm_b or norm_b in norm_a:
            shorter = min(len(norm_a), len(norm_b))
            longer = max(len(norm_a), len(norm_b))
            return max(0.85, shorter / longer)
    return SequenceMatcher(None, norm_a, norm_b).ratio()


@dataclass
class DuplicateMatchResult:
    confidence: DuplicateConfidence
    is_duplicate: bool
    reason: Optional[str] = None
    matched_block_id: Optional[int] = None
    matched_block_title: Optional[str] = None
    matched_block_location: Optional[str] = None
    matched_block_start: Optional[str] = None
    matched_block_end: Optional[str] = None
    similarity_score: float = 0.0


def evaluate_duplicate_candidate(
    candidate_title: str,
    candidate_day_of_week: int,  # 0=Sunday, 1=Monday ... 6=Saturday OR SyncShift standard
    candidate_start_time: str,  # "HH:MM" or "HH:MM:SS"
    candidate_end_time: str,    # "HH:MM" or "HH:MM:SS"
    candidate_location: Optional[str] = None,
    candidate_course_code: Optional[str] = None,
    existing_blocks: Optional[list[TimeBlock]] = None,
    syncshift_dow_format: bool = True,  # candidate_day_of_week is 0=Sun..6=Sat
) -> DuplicateMatchResult:
    """
    Evaluates an imported candidate event against the user's existing time blocks.
    
    Confidence Rules:
    - HIGH CONFIDENCE DUPLICATE:
      * Same day of week
      * Same start time & end time
      * Exact normalized title match OR matching course code
      * Same room/location (or location empty in either)
      
    - POSSIBLE DUPLICATE:
      * Same day of week
      * Same start time & end time
      * Similar title (normalized similarity >= 0.70) OR course code match with title variance
      * Different room, OR same title with slight time misalignment
      
    - NOT DUPLICATE:
      * Different days, or non-matching times, or low title similarity (< 0.70)
    """
    if not existing_blocks:
        return DuplicateMatchResult(confidence=DuplicateConfidence.NONE, is_duplicate=False)

    cand_norm_title = normalize_text(candidate_title)
    cand_norm_loc = normalize_text(candidate_location)
    cand_norm_code = normalize_text(candidate_course_code) if candidate_course_code else ""

    # Parse candidate start and end to minutes
    s_parts = candidate_start_time.split(":")[:2]
    e_parts = candidate_end_time.split(":")[:2]
    if len(s_parts) < 2 or len(e_parts) < 2:
        return DuplicateMatchResult(confidence=DuplicateConfidence.NONE, is_duplicate=False)

    cand_s = int(s_parts[0]) * 60 + int(s_parts[1])
    cand_e = int(e_parts[0]) * 60 + int(e_parts[1])

    best_result = DuplicateMatchResult(confidence=DuplicateConfidence.NONE, is_duplicate=False)

    for b in existing_blocks:
        if getattr(b, "deleted", False):
            continue

        b_dow = b.day_of_week
        if b_dow is None or b_dow != candidate_day_of_week:
            continue

        b_s = b.start_time.hour * 60 + b.start_time.minute
        b_e = b.end_time.hour * 60 + b.end_time.minute

        same_time = (b_s == cand_s and b_e == cand_e)
        if not same_time:
            continue

        b_title = b.title or ""
        b_norm_title = normalize_text(b_title)
        b_loc = b.location or ""
        b_norm_loc = normalize_text(b_loc)
        b_start_str = b.start_time.strftime("%H:%M")
        b_end_str = b.end_time.strftime("%H:%M")

        sim = text_similarity(candidate_title, b_title)

        # Check course code match
        code_matched = False
        if cand_norm_code:
            if cand_norm_code in b_norm_title or (b_norm_title and b_norm_title in cand_norm_code):
                code_matched = True

        same_loc = (
            not cand_norm_loc
            or not b_norm_loc
            or cand_norm_loc == b_norm_loc
            or text_similarity(cand_norm_loc, b_norm_loc) >= 0.8
        )

        exact_title_match = (cand_norm_title == b_norm_title)

        # 1. High confidence duplicate check
        if same_time and (exact_title_match or (code_matched and sim >= 0.80)) and same_loc:
            reason = (
                f"Identical event already on your schedule: '{b_title}' "
                f"({b_start_str}–{b_end_str}"
                f"{', ' + b_loc if b_loc else ''})"
            )
            return DuplicateMatchResult(
                confidence=DuplicateConfidence.HIGH,
                is_duplicate=True,
                reason=reason,
                matched_block_id=b.id,
                matched_block_title=b_title,
                matched_block_location=b_loc,
                matched_block_start=b_start_str,
                matched_block_end=b_end_str,
                similarity_score=sim,
            )

        # 2. Possible duplicate check
        if same_time and (sim >= 0.70 or code_matched or exact_title_match):
            loc_note = " (different room)" if not same_loc else ""
            reason = (
                f"Likely duplicate of '{b_title}' "
                f"({b_start_str}–{b_end_str}{loc_note})"
            )
            # Store best candidate so far
            if best_result.confidence != DuplicateConfidence.HIGH:
                best_result = DuplicateMatchResult(
                    confidence=DuplicateConfidence.POSSIBLE,
                    is_duplicate=True,
                    reason=reason,
                    matched_block_id=b.id,
                    matched_block_title=b_title,
                    matched_block_location=b_loc,
                    matched_block_start=b_start_str,
                    matched_block_end=b_end_str,
                    similarity_score=sim,
                )

    return best_result
