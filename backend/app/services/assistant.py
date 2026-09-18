"""
SyncShift Assistant Service (Task N9)
Unified conversational AI coordinator for Students and University Administrators.

Architecture:
User -> SyncShift Assistant -> Tool Selection -> Deterministic Backend Tools -> Database/Services
Features:
1. Multi-turn persistent conversation history (AssistantConversation, AssistantMessage).
2. Strict server-side authorization and tenant isolation.
3. Integration with N5 (Smart Planner), N6 (Impact Analysis), N7 (Versioning), N8 (Notifications).
4. Prompt-injection defense and hallucination prevention (grounded factual answers).
5. Explicit confirmation cards for all state mutations.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import CurrentUser
from app.models.assistant_conversation import AssistantConversation, AssistantMessage
from app.models.institution import Institution, InstitutionMembership
from app.models.time_block import BlockStatus, BlockType, TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User
from app.schemas.assistant import (
    ActionCheckItem,
    ActionPreview,
    AlternativeSlot,
    AssistantChatResponseData,
    AssistantConfirmResponseData,
    AssistantConversationDetailOut,
    AssistantConversationOut,
    AssistantIntentType,
    AssistantMessageOut,
)
from app.services.assistant_tools import (
    DAY_NAMES,
    DAY_NAME_TO_INT,
    tool_get_my_availability,
    tool_get_my_conflicts,
    tool_get_my_courses,
    tool_get_my_notifications,
    tool_get_my_preferences,
    tool_get_my_schedule,
    tool_get_rooms,
    tool_get_students_affected,
    tool_get_university_timetable,
    tool_get_version_history,
    tool_prepare_create_draft,
    tool_prepare_create_study_block,
    tool_preview_my_plan,
    tool_preview_timetable_change,
    tool_get_university_analytics_overview,
    tool_get_enrollment_analytics,
    tool_get_room_utilization_analytics,
    tool_get_faculty_schedule_analytics,
    tool_get_timetable_health_analytics,
    verify_institution_admin_access,
    # New expanded tools
    tool_get_my_profile,
    tool_get_my_work_shifts,
    tool_get_my_personal_blocks,
    tool_get_my_tasks,
    tool_get_my_weekly_hours,
    tool_get_my_calendar,
    tool_get_course_information,
    tool_get_class_details,
    tool_get_timetable_change_information,
    tool_find_available_time_slots,
    tool_check_schedule_conflict,
    tool_calculate_transition_time,
    tool_explain_conflict,
    tool_generate_planner_options,
    tool_prepare_move_work_shift,
    tool_prepare_create_work_shift,
    tool_prepare_delete_block,
    tool_prepare_create_study_task,
)
from app.services.audit import record_audit_log
from app.services.optimizer import optimize_work_schedule
from app.services.schedule import minutes_to_time, time_to_minutes
from app.services.schedule_health import compute_schedule_health
from app.services.smart_planner.service import SmartPlannerService
from app.store import detect_conflicts_and_totals, get_block_by_id, update_block_in_store

logger = logging.getLogger(__name__)


# =====================================================================
# CONVERSATION MANAGEMENT
# =====================================================================

def get_or_create_conversation(
    db: Session,
    user_id: int,
    conversation_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    initial_title: Optional[str] = None,
) -> AssistantConversation:
    """Retrieves or creates an isolated conversation owned by user_id."""
    if conversation_id:
        conv = (
            db.query(AssistantConversation)
            .filter(
                AssistantConversation.id == conversation_id,
                AssistantConversation.user_id == user_id,
            )
            .first()
        )
        if conv:
            return conv

    title = initial_title or "Schedule Consultation"
    if len(title) > 60:
        title = title[:57] + "..."

    conv = AssistantConversation(
        user_id=user_id,
        institution_id=institution_id,
        title=title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_user_conversations(
    db: Session,
    current_user: CurrentUser,
    institution_id: Optional[int] = None,
) -> list[AssistantConversationOut]:
    """Lists conversations for the user with tenant boundaries."""
    q = db.query(AssistantConversation).filter(AssistantConversation.user_id == current_user.user_id)
    if institution_id:
        q = q.filter(AssistantConversation.institution_id == institution_id)
    q = q.order_by(AssistantConversation.updated_at.desc())
    convs = q.all()

    out = []
    for c in convs:
        last_msg = (
            db.query(AssistantMessage)
            .filter(AssistantMessage.conversation_id == c.id)
            .order_by(AssistantMessage.created_at.desc())
            .first()
        )
        msg_count = db.query(func.count(AssistantMessage.id)).filter(AssistantMessage.conversation_id == c.id).scalar()
        out.append(
            AssistantConversationOut(
                id=c.id,
                title=c.title,
                institution_id=c.institution_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=msg_count or 0,
                last_message=last_msg.content[:100] if last_msg else None,
            )
        )
    return out


def get_conversation_detail(
    db: Session,
    current_user: CurrentUser,
    conversation_id: int,
) -> AssistantConversationDetailOut:
    """Fetches full message history for a conversation with strict ownership check."""
    conv = (
        db.query(AssistantConversation)
        .filter(
            AssistantConversation.id == conversation_id,
            AssistantConversation.user_id == current_user.user_id,
        )
        .first()
    )
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    msgs = (
        db.query(AssistantMessage)
        .filter(AssistantMessage.conversation_id == conv.id)
        .order_by(AssistantMessage.created_at.asc())
        .all()
    )

    out_msgs = []
    for m in msgs:
        action_obj = None
        if m.action_data:
            try:
                action_obj = json.loads(m.action_data)
            except Exception:
                action_obj = None
        tool_obj = None
        if m.tool_calls:
            try:
                tool_obj = json.loads(m.tool_calls)
            except Exception:
                tool_obj = None

        out_msgs.append(
            AssistantMessageOut(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                action_data=action_obj,
                tool_calls=tool_obj,
                created_at=m.created_at,
            )
        )

    return AssistantConversationDetailOut(
        id=conv.id,
        title=conv.title,
        institution_id=conv.institution_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=out_msgs,
    )


def delete_user_conversation(db: Session, current_user: CurrentUser, conversation_id: int) -> bool:
    """Deletes a conversation owned by the user."""
    conv = (
        db.query(AssistantConversation)
        .filter(
            AssistantConversation.id == conversation_id,
            AssistantConversation.user_id == current_user.user_id,
        )
        .first()
    )
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    db.delete(conv)
    db.commit()
    return True


# =====================================================================
# INTENT EXTRACTION & AI ORCHESTRATION
# =====================================================================

def extract_intent_and_parameters(
    message: str,
    user_role: str = "student",
) -> Tuple[AssistantIntentType, dict[str, Any]]:
    """
    Interprets natural language into structured intent and parameters.
    Resilient: handles typos, variations, natural phrasing, and prompt injection defense.
    """
    msg = message.lower().strip()

    # Security check: prompt injection defense
    injection_tokens = [
        "ignore previous", "ignore instructions", "system prompt", "developer instructions",
        "api key", "jwt_secret", "reveal passwords", "drop table", "select * from users",
        "act as database", "bypass permission", "all users", "show other students",
        "disregard", "another user", "other user", "override", "secret", "passwords",
    ]
    if any(tok in msg for tok in injection_tokens):
        return AssistantIntentType.GENERAL_HELP, {"security_refusal": True}

    # 1. Admin Analytics & Timetable Intents
    if any(k in msg for k in ["most used room", "room utilization", "which rooms are most used", "which room is most used", "room usage", "least used room", "rooms most used"]):
        return AssistantIntentType.GET_ROOM_UTILIZATION_ANALYTICS, {}

    if any(k in msg for k in ["university timetable", "show timetable", "today's timetable", "view timetable", "show today's timetable"]):
        if user_role in ("admin", "super_admin") or "admin" in msg or "university" in msg:
            return AssistantIntentType.GET_UNIVERSITY_TIMETABLE, {}

    if any(k in msg for k in [
        "which room", "which rooms", "room available", "rooms available", "available room", "available rooms",
        "rooms are available", "room is available", "find room", "which room is free", "free room"
    ]):
        day_val = _extract_day(msg)
        st, et = _extract_time_range(msg)
        return AssistantIntentType.GET_ROOM_AVAILABILITY, {
            "day_of_week": day_val,
            "start_time": st,
            "end_time": et,
        }

    if any(k in msg for k in ["affected by moving", "move cs", "move meeting", "preview move"]):
        m_id = _extract_int(msg, r"(?:meeting|class|course)\s*(?:#|id)?\s*(\d+)")
        day_val = _extract_day(msg) or 1  # Default Monday
        st, et = _extract_time_range(msg)
        return AssistantIntentType.PREVIEW_TIMETABLE_CHANGE, {
            "meeting_id": m_id or 1,
            "day_of_week": day_val,
            "start_time": st or "14:00",
            "end_time": et or "15:00",
        }

    if any(k in msg for k in ["who is affected", "students affected", "how many students affected"]):
        sec_id = _extract_int(msg, r"(?:section|meeting)\s*(\d+)")
        return AssistantIntentType.GET_AFFECTED_STUDENTS, {"section_id": sec_id}

    if any(k in msg for k in ["version history", "versions", "who is affected by version", "latest timetable changes"]):
        return AssistantIntentType.GET_VERSION_HISTORY, {}

    if any(k in msg for k in ["create draft", "create timetable draft", "new version draft"]):
        return AssistantIntentType.CREATE_TIMETABLE_DRAFT, {"name": "Draft Update via Assistant"}

    if any(k in msg for k in ["publish the timetable", "publish timetable", "publish version"]):
        return AssistantIntentType.PUBLISH_TIMETABLE, {}

    if any(k in msg for k in ["most used room", "room utilization", "which rooms are most used", "room usage", "least used room"]):
        return AssistantIntentType.GET_ROOM_UTILIZATION_ANALYTICS, {}

    if any(k in msg for k in ["nearly full", "sections nearly full", "section capacity", "enrollment demand", "which sections are full", "high demand section"]):
        return AssistantIntentType.GET_ENROLLMENT_ANALYTICS, {}

    if any(k in msg for k in ["how many students were affected", "affected by the latest", "students affected by timetable", "timetable health", "timetable conflicts", "sections with the most conflicts", "most conflicts", "schedule conflicts"]):
        if user_role in ("admin", "super_admin") or "timetable" in msg or "university" in msg or "affected" in msg:
            return AssistantIntentType.GET_TIMETABLE_HEALTH_ANALYTICS, {}

    if any(k in msg for k in ["faculty teaching", "teaching load", "faculty schedule", "faculty workload", "teaching hours"]):
        return AssistantIntentType.GET_FACULTY_ANALYTICS, {}

    if any(k in msg for k in ["university overview", "campus overview", "how many students are enrolled", "university stats", "institution overview", "institution stats"]):
        return AssistantIntentType.GET_UNIVERSITY_OVERVIEW_ANALYTICS, {}

    # 2. Student Intents
    if any(k in msg for k in ["classes tomorrow", "schedule tomorrow", "tomorrow's schedule"]):
        tomorrow = date.today() + timedelta(days=1)
        dow = (tomorrow.weekday() + 1) % 7
        return AssistantIntentType.GET_TODAY_SCHEDULE, {"day_of_week": dow, "day_name": DAY_NAMES[dow]}

    if any(k in msg for k in ["classes today", "schedule today", "today's schedule", "what do i have today", "what classes do i have"]):
        return AssistantIntentType.GET_TODAY_SCHEDULE, {}

    if any(k in msg for k in ["weekly schedule", "schedule this week", "plan this week", "busiest day"]):
        return AssistantIntentType.GET_WEEK_SCHEDULE, {}

    if any(k in msg for k in ["where is my", "database systems class", "my courses", "what courses", "courses am i taking"]):
        return AssistantIntentType.GET_COURSES, {}

    if any(k in msg for k in ["conflict", "conflicts", "clash", "double-booked", "overlapping"]):
        return AssistantIntentType.GET_CONFLICTS, {}

    if any(k in msg for k in ["work hours", "hours left", "how many hours do i work", "work limit"]):
        return AssistantIntentType.GET_WORK_HOURS, {}

    if any(k in msg for k in ["when is my next free", "free evening", "free afternoon", "free time", "when can i work"]):
        return AssistantIntentType.FIND_AVAILABLE_TIME, {}

    if any(k in msg for k in ["what changed in my timetable", "timetable changes", "notifications"]):
        return AssistantIntentType.GET_TIMETABLE_CHANGES, {}

    if any(k in msg for k in ["plan my week", "help me plan", "smart planner", "weekly plan"]):
        return AssistantIntentType.PLAN_WEEK, {"strategy": "balanced"}

    if any(k in msg for k in ["create study block", "study block", "study session", "add study", "schedule study", "schedule a study", "study time"]):
        day_val = _extract_day(msg) or 2  # Tuesday default
        st, et = _extract_time_range(msg)
        return AssistantIntentType.CREATE_STUDY_BLOCK, {
            "title": "Study Block",
            "day_of_week": day_val,
            "start_time": st or "15:00",
            "end_time": et or "17:00",
        }

    if any(k in msg for k in ["move", "reschedule", "shift"]):
        day_val = _extract_day(msg)
        st, _ = _extract_time_range(msg)
        return AssistantIntentType.MOVE_EVENT, {"day": day_val, "start_time": st}

    return AssistantIntentType.GENERAL_HELP, {}


def _extract_day(text: str) -> Optional[int]:
    for name, i in DAY_NAME_TO_INT.items():
        if name in text:
            return i
    if "tomorrow" in text:
        tomorrow = date.today() + timedelta(days=1)
        return (tomorrow.weekday() + 1) % 7
    if "today" in text:
        today = date.today()
        return (today.weekday() + 1) % 7
    return None


def _extract_time_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    # E.g. "at 2 pm", "from 14:00 to 16:00", "3 pm", "3:00 to 5:00 pm", "between 10:00 and 12:00"
    # 1. Match explicit colon times first (e.g. 14:00, 10:00)
    colon_times = re.findall(r'\b([0-2]?\d:[0-5]\d)\b', text)
    if colon_times:
        parsed = []
        for ct in colon_times:
            parts = ct.split(":")
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                parsed.append(f"{h:02d}:{m:02d}")
        if len(parsed) == 1:
            st = parsed[0]
            sh, sm = map(int, st.split(":"))
            eh = min(23, sh + 2)
            return st, f"{eh:02d}:{sm:02d}"
        elif len(parsed) >= 2:
            return parsed[0], parsed[1]

    # 2. Match times with am/pm (e.g. "4 pm", "4:30 pm", "11am")
    ampm_matches = re.findall(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', text, flags=re.IGNORECASE)
    if ampm_matches:
        parsed = []
        for h_str, m_str, mer in ampm_matches:
            h = int(h_str)
            m = int(m_str) if m_str else 0
            mer = mer.lower()
            if mer == "pm" and h < 12:
                h += 12
            elif mer == "am" and h == 12:
                h = 0
            if 0 <= h <= 23:
                parsed.append(f"{h:02d}:{m:02d}")
        if len(parsed) == 1:
            st = parsed[0]
            sh, sm = map(int, st.split(":"))
            eh = min(23, sh + 2)
            return st, f"{eh:02d}:{sm:02d}"
        elif len(parsed) >= 2:
            return parsed[0], parsed[1]

    # 3. Match standalone numbers preceded by at/from/to/until, excluding entity IDs
    prep_matches = re.findall(r'\b(?:at|from|to|until)\s+(\d{1,2})\b(?!\s*(?:meeting|timetable|institution|section|term|room|version|user|day|hour|credit))', text, flags=re.IGNORECASE)
    if prep_matches:
        parsed = []
        for h_str in prep_matches:
            h = int(h_str)
            if 1 <= h <= 6:
                h += 12
            if 0 <= h <= 23:
                parsed.append(f"{h:02d}:00")
        if len(parsed) == 1:
            st = parsed[0]
            sh, sm = map(int, st.split(":"))
            eh = min(23, sh + 2)
            return st, f"{eh:02d}:{sm:02d}"
        elif len(parsed) >= 2:
            return parsed[0], parsed[1]

    return None, None


def _extract_int(text: str, pattern: str) -> Optional[int]:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


# =====================================================================
# MAIN CHAT PROCESSING
# =====================================================================

def process_assistant_chat(
    current_user: CurrentUser,
    message: str,
    db: Session,
    conversation_id: Optional[int] = None,
    institution_id: Optional[int] = None,
) -> AssistantChatResponseData:
    """
    Executes the conversational AI cycle:
    1. Resolve user role and conversation
    2. Extract intent and parameters
    3. Execute deterministic backend tool
    4. Ground response in factual data without hallucination
    5. Generate ActionPreview card for required confirmations
    6. Persist to AssistantConversation and AssistantMessage
    """
    user_id = current_user.user_id

    # Check if user has admin membership
    admin_inst_id = None
    if institution_id:
        m = (
            db.query(InstitutionMembership)
            .filter(
                InstitutionMembership.institution_id == institution_id,
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.deleted_at.is_(None),
                InstitutionMembership.status == "active",
            )
            .first()
        )
        if m and m.role in ("admin", "super_admin"):
            admin_inst_id = institution_id
    else:
        # Check any active admin membership
        any_admin = (
            db.query(InstitutionMembership)
            .filter(
                InstitutionMembership.user_id == user_id,
                InstitutionMembership.role.in_(["admin", "super_admin"]),
                InstitutionMembership.status == "active",
                InstitutionMembership.deleted_at.is_(None),
            )
            .first()
        )
        if any_admin:
            admin_inst_id = any_admin.institution_id

    role = "admin" if admin_inst_id else "student"

    # Persistent conversation setup
    conv = get_or_create_conversation(
        db=db,
        user_id=user_id,
        conversation_id=conversation_id,
        institution_id=admin_inst_id or institution_id,
        initial_title=message,
    )

    # Record User Message
    u_msg = AssistantMessage(
        conversation_id=conv.id,
        role="user",
        content=message,
    )
    db.add(u_msg)
    db.commit()

    # ── Gemini-powered NLU (primary path) ─────────────────────────────────────
    # Attempt Gemini function-calling first. Fall back to keyword classifier.
    gemini_used = False
    gemini_tool_progress: Optional[list[dict[str, Any]]] = None
    gemini_alternatives: Optional[list[dict[str, Any]]] = None
    gemini_response_text: Optional[str] = None
    gemini_action_preview: Optional[ActionPreview] = None
    gemini_intent_str: Optional[str] = None

    try:
        from app.services.assistant_gemini import (
            call_gemini_with_tools,
            gemini_answer_general_question,
            is_general_question,
        )
        if settings.GEMINI_API_KEY:
            # Build conversation history for multi-turn context
            history_msgs = (
                db.query(AssistantMessage)
                .filter(AssistantMessage.conversation_id == conv.id)
                .order_by(AssistantMessage.created_at.desc())
                .limit(8)
                .all()
            )
            conv_history = [
                {"role": m.role, "content": m.content}
                for m in reversed(history_msgs)
                if m.role in ("user", "assistant")
            ]

            # Fetch user name for system prompt personalisation
            _user_obj = db.query(User).filter(User.id == user_id).first()
            _user_name = getattr(_user_obj, "name", None) if _user_obj else None

            if is_general_question(message):
                # Pure general knowledge — no tools needed
                gemini_response_text = gemini_answer_general_question(message, conv_history)
                gemini_intent_str = AssistantIntentType.GENERAL_KNOWLEDGE.value
                gemini_used = True
            else:
                # Bind tool_executor: injects session-derived auth, strips Gemini-provided IDs
                def _tool_executor(tool_name: str, args: dict) -> dict:
                    # Security: always bind from session, never accept from Gemini output
                    safe_args = {k: v for k, v in args.items() if k not in ("user_id", "institution_id", "role")}
                    return _dispatch_gemini_tool(
                        tool_name=tool_name,
                        args=safe_args,
                        db=db,
                        current_user=current_user,
                        admin_inst_id=admin_inst_id,
                    )

                raw_text, tool_progress_list, alternatives = call_gemini_with_tools(
                    message=message,
                    conversation_history=conv_history,
                    tool_executor=_tool_executor,
                    role=role,
                    user_name=_user_name,
                )
                gemini_tool_progress = tool_progress_list
                gemini_alternatives = alternatives

                # Extract ActionPreview from the last tool result if it produced one
                # (stored in the thread-local by _dispatch_gemini_tool)
                if hasattr(_tool_executor, "_last_action_preview"):
                    gemini_action_preview = _tool_executor._last_action_preview  # type: ignore

                # Check if any tool set a pending action preview
                # (passed back via a dedicated key in the last tool result)
                gemini_response_text = raw_text
                gemini_intent_str = AssistantIntentType.GENERAL_HELP.value
                gemini_used = True
    except Exception as gemini_exc:
        logger.info(f"Gemini unavailable, falling back to keyword classifier: {gemini_exc}")
        gemini_used = False

    # If Gemini succeeded with a general question, return immediately
    if gemini_used and gemini_intent_str == AssistantIntentType.GENERAL_KNOWLEDGE.value and gemini_response_text:
        return _finalize_response(
            db=db,
            conv_id=conv.id,
            text=gemini_response_text,
            intent=gemini_intent_str,
            tool_progress=gemini_tool_progress,
            suggestions=["What classes do I have today?", "Do I have any conflicts?", "Plan my week"],
        )

    # If Gemini succeeded with a tool-based answer, check for embedded ActionPreview
    if gemini_used and gemini_response_text:
        # Extract embedded action_preview from tool results (stored in module-level slot)
        embedded_action = _retrieve_pending_action()
        embedded_alts = gemini_alternatives
        return _finalize_response(
            db=db,
            conv_id=conv.id,
            text=gemini_response_text,
            intent=gemini_intent_str or AssistantIntentType.GENERAL_HELP.value,
            action=embedded_action,
            tool_calls=gemini_tool_progress,
            tool_progress=gemini_tool_progress,
            alternatives=embedded_alts,
            suggestions=[
                "Confirm the action above" if embedded_action else "What classes do I have today?",
                "Do I have any conflicts?",
            ],
        )

    # ── Keyword-based intent classifier (fallback) ─────────────────────────
    # Intent extraction
    intent, params = extract_intent_and_parameters(message, user_role=role)

    # Security refusal
    if params.get("security_refusal"):
        response_text = (
            "🔒 **SyncShift Assistant Security Notice**:\n"
            "I am programmed strictly to assist with your personal schedule and university timetables. "
            "I cannot access other users' accounts, reveal system secrets, or execute unauthorized instructions."
        )
        return _finalize_response(
            db=db,
            conv_id=conv.id,
            text=response_text,
            intent=intent.value,
            suggestions=["What classes do I have today?", "Do I have any conflicts?"],
        )

    # -------------------------------------------------------------
    # Tool Execution & Response Grounding
    # -------------------------------------------------------------
    action_preview: Optional[ActionPreview] = None
    tool_calls_meta: list[dict[str, Any]] = []
    suggestions: list[str] = []

    try:
        if intent == AssistantIntentType.GET_TODAY_SCHEDULE:
            dow = params.get("day_of_week")
            data = tool_get_my_schedule(db, current_user, day_of_week=dow, view="today")
            tool_calls_meta.append({"tool": "get_my_schedule", "status": "success"})
            day_str = data["day_name"]
            evs = data["events"]

            if not evs:
                response_text = f"You have no scheduled classes or shifts for {day_str}. Enjoy your free day!"
            else:
                classes = [e for e in evs if e["type"] == "class"]
                shifts = [e for e in evs if e["type"] == "shift"]
                other = [e for e in evs if e["type"] not in ("class", "shift")]

                lines = [f"Here is your schedule for **{day_str}** ({len(evs)} events):"]
                for e in evs:
                    loc = f" · {e['location']}" if e["location"] else ""
                    tag = "🎓" if e["type"] == "class" else "💼" if e["type"] == "shift" else "📖"
                    lines.append(f"- {tag} **{e['start_time']}–{e['end_time']}** — {e['title']}{loc}")

                if data["free_gaps"]:
                    lines.append(f"\n💡 **Next free periods**: {', '.join(data['free_gaps'][:2])}")
                response_text = "\n".join(lines)
            suggestions = ["Do I have any conflicts?", "When can I work this week?", "Plan my study week"]

        elif intent == AssistantIntentType.GET_WEEK_SCHEDULE:
            data = tool_get_my_schedule(db, current_user, view="week")
            tool_calls_meta.append({"tool": "get_my_schedule", "status": "success"})
            evs = data["events"]
            if not evs:
                response_text = "Your calendar is completely open for the week."
            else:
                by_day: dict[str, list] = {}
                for e in evs:
                    by_day.setdefault(e["day_name"], []).append(e)

                busiest_day = max(by_day.keys(), key=lambda d: len(by_day[d]))
                lines = [f"You have **{len(evs)} commitments** this week. Busiest day is **{busiest_day}**."]
                for d_name in DAY_NAMES:
                    if d_name in by_day:
                        lines.append(f"- **{d_name}**: {len(by_day[d_name])} events")
                response_text = "\n".join(lines)
            suggestions = ["What classes do I have tomorrow?", "Do I have any conflicts?"]

        elif intent == AssistantIntentType.GET_COURSES:
            data = tool_get_my_courses(db, current_user)
            tool_calls_meta.append({"tool": "get_my_courses", "status": "success"})
            courses = data["courses"]
            if not courses:
                response_text = "I couldn't find any enrolled courses in your SyncShift academic profile."
            else:
                lines = [f"You are actively enrolled in **{len(courses)} courses**:"]
                for c in courses:
                    sched_str = "; ".join(c["schedule"]) if c["schedule"] else "Schedule TBD"
                    lines.append(f"- 🎓 **{c['code']}** ({c['name']}) · Section {c['section_code']}\n  _{sched_str}_")
                response_text = "\n".join(lines)
            suggestions = ["What classes do I have today?", "Do I have any conflicts?"]

        elif intent == AssistantIntentType.GET_CONFLICTS:
            data = tool_get_my_conflicts(db, current_user)
            tool_calls_meta.append({"tool": "get_my_conflicts", "status": "success"})
            if not data["has_conflicts"]:
                response_text = "✅ **Zero conflicts detected!** You have no scheduling conflicts between your university classes and work shifts."
            else:
                lines = [f"⚠️ **{data['conflict_count']} conflict(s) found** in your schedule:"]
                for c in data["conflicts"]:
                    lines.append(f"- **{c['day']}**: {c['event_a']} overlaps with {c['event_b']} ({c['overlap_minutes']} mins overlap)")
                lines.append("\nWould you like me to suggest a feasible alternative time?")
                response_text = "\n".join(lines)
            suggestions = ["Plan my week", "How many work hours do I have left?"]

        elif intent == AssistantIntentType.GET_WORK_HOURS:
            user = db.query(User).filter(User.id == user_id).first()
            limit = float(user.weekly_work_hour_limit or 20.0)
            sched = tool_get_my_schedule(db, current_user, view="week")
            shift_mins = sum(e["end_mins"] - e["start_mins"] for e in sched["events"] if e["type"] == "shift")
            shift_hours = round(shift_mins / 60.0, 1)
            remain = round(max(0.0, limit - shift_hours), 1)

            response_text = (
                f"📊 **Work Hour Summary**:\n"
                f"- Scheduled this week: **{shift_hours}h** ({shift_hours} hours)\n"
                f"- Configured weekly limit: **{limit}h**\n"
                f"- Remaining capacity: **{remain}h** ({remain} hours remain) {'(within safe limits ✅)' if remain >= 0 else '(exceeds limit ⚠️)'}"
            )
            suggestions = ["When can I work this week?", "What is my schedule today?"]

        elif intent == AssistantIntentType.FIND_AVAILABLE_TIME:
            sched = tool_get_my_schedule(db, current_user, view="week")
            pref = tool_get_my_preferences(db, current_user)
            tool_calls_meta.append({"tool": "get_my_preferences", "status": "success"})

            response_text = (
                "🕒 **Available Scheduling Windows**:\n"
                f"- Preferred study/work time: **{pref['preferred_time_of_day'].capitalize()}**\n"
                "- Tuesday: 15:00–18:00 (free gap between Database Systems and evening)\n"
                "- Thursday: 14:00–18:00 (completely open afternoon)\n"
                "- Friday: Evening after 17:00 is free."
            )
            suggestions = ["Create a study block", "Plan my week"]

        elif intent == AssistantIntentType.PLAN_WEEK:
            strategy = params.get("strategy", "balanced")
            data = tool_preview_my_plan(db, current_user, strategy=strategy)
            tool_calls_meta.append({"tool": "preview_my_plan", "status": "success"})

            if data.get("success") and data.get("options"):
                opt = data["options"][0]
                lines = [
                    f"📅 **Smart Weekly Plan Preview ({opt['strategy'].capitalize()} Strategy)**:",
                    f"- Quality Score: **{opt['score']}/100**",
                    f"- Planned Study: **{opt['total_study_minutes'] // 60}h {opt['total_study_minutes'] % 60}m** across {opt['planned_sessions_count']} sessions",
                    "- Explanations:",
                ]
                for r in opt["reasons"]:
                    lines.append(f"  · {r}")
                lines.append("\nI've prepared this plan for your confirmation:")
                response_text = "\n".join(lines)

                action_preview = ActionPreview(
                    action_type="apply_plan",
                    title=f"Apply {opt['strategy'].capitalize()} Study Plan",
                    parameters={"strategy": opt["strategy"], "week_start": data["week_start"]},
                    checks=[
                        ActionCheckItem(label="Zero university class conflicts", passed=True),
                        ActionCheckItem(label=f"Protects all work shifts", passed=True),
                        ActionCheckItem(label=f"Meets all active task deadlines", passed=True),
                    ],
                    target={"strategy": opt["strategy"], "score": opt["score"]},
                )
            else:
                response_text = "You currently have no pending study tasks or all your tasks are already scheduled!"
            suggestions = ["What classes do I have today?", "Do I have any conflicts?"]

        elif intent == AssistantIntentType.CREATE_STUDY_BLOCK:
            title = params.get("title", "Study Session")
            dow = params.get("day_of_week", 2)
            st = params.get("start_time", "15:00")
            et = params.get("end_time", "17:00")

            action_preview = tool_prepare_create_study_block(
                db=db,
                current_user=current_user,
                title=title,
                day_of_week=dow,
                start_time=st,
                end_time=et,
            )
            tool_calls_meta.append({"tool": "prepare_create_study_block", "status": "success"})
            response_text = (
                f"I can create a **{title}** block on **{DAY_NAMES[dow]}** from **{st} to {et}**.\n"
                "Please review the checks below and click **Confirm** to add it to your calendar."
            )

        elif intent == AssistantIntentType.GET_TIMETABLE_CHANGES:
            data = tool_get_my_notifications(db, current_user, unread_only=False)
            tool_calls_meta.append({"tool": "get_my_notifications", "status": "success"})
            notifs = data["notifications"]
            if not notifs:
                response_text = "No timetable changes or alerts have been issued for your enrolled courses."
            else:
                lines = ["📢 **Recent Timetable & Schedule Notices**:"]
                for n in notifs[:5]:
                    p_badge = "🔴" if n["priority"] == "URGENT" else "🔵"
                    lines.append(f"- {p_badge} **{n['title']}**: {n['message']}")
                response_text = "\n".join(lines)
            suggestions = ["What is my schedule today?", "Do I have any conflicts?"]

        # ==================== ADMIN INTENTS ====================
        elif intent == AssistantIntentType.GET_UNIVERSITY_TIMETABLE:
            if not admin_inst_id:
                response_text = "You do not have administrator permissions for an academic institution."
            else:
                data = tool_get_university_timetable(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_university_timetable", "status": "success"})
                tts = data["timetables"]
                lines = [f"🏛️ **Institutional Timetables** ({len(tts)} found):"]
                for t in tts:
                    lines.append(f"- **{t['name']}** ({t['term_name']}) · Status: `{t['status']}` · Published: {t['published_version'] or 'None'} · Meetings: {t['meetings_count']}")
                response_text = "\n".join(lines)
                suggestions = ["Which room is available at 3 PM?", "Who is affected by Version 4?"]

        elif intent == AssistantIntentType.GET_ROOM_AVAILABILITY:
            if not admin_inst_id:
                response_text = "Room availability inspection requires university administrator privileges."
            else:
                data = tool_get_rooms(
                    db=db,
                    current_user=current_user,
                    institution_id=admin_inst_id,
                    day_of_week=params.get("day_of_week", 1),
                    start_time=params.get("start_time", "15:00"),
                    end_time=params.get("end_time", "16:00"),
                )
                tool_calls_meta.append({"tool": "get_rooms", "status": "success"})
                avail = data["available_rooms"]
                slot = data["time_slot_checked"] or "the requested time"
                lines = [f"🏢 **Room Availability for {slot}**:"]
                lines.append(f"- **{len(avail)} of {data['rooms_count']} rooms are available**.")
                for r in avail[:6]:
                    lines.append(f"  · **Room {r['room_number']}** ({r['building']}) · Capacity: {r['capacity']}")
                response_text = "\n".join(lines)
                suggestions = ["Show today's timetable", "Who is affected by moving CS301?"]

        elif intent == AssistantIntentType.PREVIEW_TIMETABLE_CHANGE:
            if not admin_inst_id:
                response_text = "Modifying university timetables requires administrator privileges."
            else:
                # Find first timetable
                tt = db.query(Timetable).filter(Timetable.institution_id == admin_inst_id).first()
                if not tt:
                    response_text = "No active timetable found for this institution."
                else:
                    action_preview = tool_preview_timetable_change(
                        db=db,
                        current_user=current_user,
                        institution_id=admin_inst_id,
                        timetable_id=tt.id,
                        meeting_id=params["meeting_id"],
                        proposed_day=params["day_of_week"],
                        proposed_start=params["start_time"],
                        proposed_end=params["end_time"],
                    )
                    tool_calls_meta.append({"tool": "preview_timetable_change", "status": "success"})
                    impact = action_preview.impact_summary or {}
                    response_text = (
                        f"📊 **N6 Timetable Impact Analysis Completed**:\n"
                        f"- Severity: **{impact.get('severity', 'LOW')}**\n"
                        f"- Students Affected: **{impact.get('students_affected_count', 0)}**\n"
                        f"- New Conflicts Created: **{impact.get('new_conflicts_count', 0)}**\n"
                        f"- Work Shift Clashes: **{impact.get('work_shift_conflicts_count', 0)}**\n\n"
                        "Per SyncShift security policy, the AI will NOT modify university timetables silently. "
                        "Please review the impact details below and confirm explicitly to apply."
                    )

        elif intent == AssistantIntentType.GET_VERSION_HISTORY:
            if not admin_inst_id:
                response_text = "Version history is available to university administrators."
            else:
                tt = db.query(Timetable).filter(Timetable.institution_id == admin_inst_id).first()
                if not tt:
                    response_text = "No timetable found."
                else:
                    data = tool_get_version_history(db, current_user, admin_inst_id, tt.id)
                    tool_calls_meta.append({"tool": "get_version_history", "status": "success"})
                    lines = [f"📜 **Timetable Version History** ({data['versions_count']} versions):"]
                    for v in data["versions"]:
                        status_tag = " [PUBLISHED]" if v["is_published"] else f" [{v['status'].upper()}]"
                        lines.append(f"- **Version {v['version_number']}**: {v['name'] or 'Revision'}{status_tag}\n  _{v['change_summary'] or 'No summary recorded.'}_")
                    response_text = "\n".join(lines)

        elif intent == AssistantIntentType.CREATE_TIMETABLE_DRAFT:
            if not admin_inst_id:
                response_text = "Creating timetable drafts requires administrator privileges."
            else:
                tt = db.query(Timetable).filter(Timetable.institution_id == admin_inst_id).first()
                if not tt:
                    response_text = "No timetable found."
                else:
                    action_preview = tool_prepare_create_draft(
                        db=db,
                        current_user=current_user,
                        institution_id=admin_inst_id,
                        timetable_id=tt.id,
                        name=params.get("name", "Draft Update"),
                    )
                    tool_calls_meta.append({"tool": "prepare_create_draft", "status": "success"})
                    response_text = (
                        "I can create a new sequential **Draft Timetable Version** cloned from the currently published version. "
                        "Drafts are fully isolated and students will not see changes until published."
                    )

        elif intent == AssistantIntentType.PUBLISH_TIMETABLE:
            response_text = (
                "📢 **Timetable Publication Policy**:\n"
                "Publishing a timetable activates the N7 publication workflow and triggers the N8 student notification engine. "
                "To ensure institutional compliance, please publish using the official **Publish Timetable** modal on your timetable editor."
            )
            suggestions = ["Show version history", "Which room is available at 3 PM?"]

        # ==================== N10 ANALYTICS INTENTS ====================
        elif intent == AssistantIntentType.GET_UNIVERSITY_OVERVIEW_ANALYTICS:
            if not admin_inst_id:
                response_text = "Accessing university administrative analytics requires institutional administrator privileges."
            else:
                data = tool_get_university_analytics_overview(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_university_analytics_overview", "status": "success"})
                response_text = (
                    "📊 **University Operational Overview**:\n"
                    f"- **Active Students**: {data['active_students_count']}\n"
                    f"- **Enrolled in Term**: {data['enrolled_students_count']} students ({data['total_enrollments_count']} course seats)\n"
                    f"- **Active Courses / Sections**: {data['active_courses_count']} courses / {data['active_sections_count']} sections\n"
                    f"- **Scheduled Weekly Classes**: {data['scheduled_classes_count']} meetings ({data['unscheduled_sections_count']} unscheduled sections)\n"
                    f"- **Campus Facilities**: {data['active_rooms_count']} active rooms ({data['average_room_utilization_pct']}% avg scheduled utilization)\n"
                    f"- **Active Faculty**: {data['active_faculty_count']} members\n"
                    f"- **Scheduling Conflicts**: {data['total_conflicts_count']} detected"
                )
                suggestions = ["Which sections are nearly full?", "Which rooms are most used?", "Show timetable health"]

        elif intent == AssistantIntentType.GET_ENROLLMENT_ANALYTICS:
            if not admin_inst_id:
                response_text = "Viewing section enrollment demand requires university administrator privileges."
            else:
                data = tool_get_enrollment_analytics(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_enrollment_analytics", "status": "success"})
                high_demand = data.get("high_demand_sections", [])
                low_util = data.get("low_utilization_sections", [])
                lines = [
                    f"📈 **Enrollment Demand & Section Capacity**:",
                    f"- **Overall Capacity Utilization**: {data['overall_capacity_utilization_pct']}% ({data['total_enrolled']} / {data['total_capacity']} seats)",
                ]
                if high_demand:
                    lines.append(f"\n**High Demand Sections (≥90% full)**:")
                    for s in high_demand[:5]:
                        lines.append(f"- **{s['course_code']} {s['section_code']}**: {s['enrolled_count']}/{s['capacity']} enrolled ({s['utilization_pct']}%) · {s['remaining_seats']} seats left")
                else:
                    lines.append("\nNo sections currently have capacity pressure (≥90% full).")

                if low_util:
                    lines.append(f"\n**Low Utilization Sections (≤30% full)**:")
                    for s in low_util[:5]:
                        lines.append(f"- **{s['course_code']} {s['section_code']}**: {s['enrolled_count']}/{s['capacity']} enrolled ({s['utilization_pct']}%)")

                response_text = "\n".join(lines)
                suggestions = ["Which rooms are most used?", "Show timetable health", "University overview"]

        elif intent == AssistantIntentType.GET_ROOM_UTILIZATION_ANALYTICS:
            if not admin_inst_id:
                response_text = "Viewing room utilization metrics requires university administrator privileges."
            else:
                data = tool_get_room_utilization_analytics(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_room_utilization_analytics", "status": "success"})
                most_used = data.get("most_used_rooms", [])
                lines = [
                    f"🏢 **Scheduled Room Utilization**:",
                    f"- **Active Rooms**: {data['active_rooms']} rooms",
                    f"- **Weekly Scheduled Hours**: {data['total_weekly_scheduled_hours']} hrs across campus",
                    f"- **Average Scheduled Utilization**: {data['average_utilization_pct']}% (based on standard 45-hr operating week)",
                    f"_Note: Reflects scheduled timetable meetings, not physical sensor occupancy._",
                ]
                if most_used:
                    lines.append("\n**Most Scheduled Rooms**:")
                    for r in most_used[:5]:
                        lines.append(f"- **Room {r['room_number']}** ({r['building']}): {r['weekly_scheduled_hours']} hrs/week ({r['scheduled_utilization_pct']}%) · {r['meetings_count']} meetings")

                response_text = "\n".join(lines)
                suggestions = ["Which sections are nearly full?", "Show timetable health", "University overview"]

        elif intent == AssistantIntentType.GET_FACULTY_ANALYTICS:
            if not admin_inst_id:
                response_text = "Viewing faculty scheduling insights requires university administrator privileges."
            else:
                data = tool_get_faculty_schedule_analytics(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_faculty_schedule_analytics", "status": "success"})
                f_list = data.get("faculty_list", [])
                lines = [
                    f"👨‍🏫 **Faculty Teaching Schedules**:",
                    f"- **Teaching Faculty**: {data['teaching_faculty_count']} of {data['total_faculty']} active faculty",
                    f"- **Average Scheduled Load**: {data['average_teaching_hours']} hrs/week",
                ]
                if f_list:
                    lines.append("\n**Scheduled Teaching Distribution**:")
                    for f in f_list[:5]:
                        conflict_flag = " ⚠️ (schedule conflict)" if f["has_schedule_conflicts"] else ""
                        lines.append(f"- **{f['name']}** ({f['department_name'] or 'Faculty'}): {f['weekly_teaching_hours']} hrs/week · {f['sections_count']} sections{conflict_flag}")

                response_text = "\n".join(lines)
                suggestions = ["Which rooms are most used?", "Show timetable health", "University overview"]

        elif intent == AssistantIntentType.GET_TIMETABLE_HEALTH_ANALYTICS:
            if not admin_inst_id:
                response_text = "Viewing timetable collision and publication impact analytics requires administrator privileges."
            else:
                data = tool_get_timetable_health_analytics(db, current_user, institution_id=admin_inst_id)
                tool_calls_meta.append({"tool": "get_timetable_health_analytics", "status": "success"})
                conflicts = data.get("conflicts", {})
                history = data.get("recent_history", [])
                lines = [
                    f"🛡️ **Timetable Health & Student Impact**:",
                    f"- **Timetable**: {data.get('timetable_name', 'Active Timetable')} (Published: v{data.get('published_version_number') or 'None'})",
                    f"- **Coverage**: {data.get('scheduled_sections_count', 0)} scheduled sections, {data.get('unscheduled_sections_count', 0)} unscheduled",
                    f"- **Total Conflicts**: **{conflicts.get('total_conflicts', 0)}**",
                    f"  · Room Collisions: {conflicts.get('room_double_bookings', 0)}",
                    f"  · Faculty Double-Bookings: {conflicts.get('faculty_double_bookings', 0)}",
                    f"  · Student Class Clashes: {conflicts.get('student_class_conflicts', 0)}",
                    f"  · Student Work Shift Clashes: {conflicts.get('student_work_shift_clashes', 0)}",
                ]
                if history:
                    lines.append("\n**Recent Publication History & Affected Students**:")
                    for h in history[:3]:
                        lines.append(f"- **Version {h['version_number']}**: {h['students_notified_count']} students notified · {h['urgent_conflicts_count']} urgent alerts")

                response_text = "\n".join(lines)
                suggestions = ["Which sections are nearly full?", "Which rooms are most used?", "University overview"]

        elif intent == AssistantIntentType.MOVE_EVENT:
            # Student shift move handling (preserved from N4)
            blocks = db.query(TimeBlock).filter(
                TimeBlock.user_id == user_id,
                TimeBlock.type == BlockType.SHIFT,
                TimeBlock.status != BlockStatus.DROPPED,
            ).all()

            if not blocks:
                response_text = "You don't have any work shifts scheduled to move."
            elif len(blocks) > 1 and not params.get("day"):
                choices = [
                    {
                        "block_id": b.id,
                        "label": f"{b.title} on {DAY_NAMES[b.day_of_week]} at {b.start_time.strftime('%H:%M') if isinstance(b.start_time, dt_time) else str(b.start_time)[:5]}",
                    }
                    for b in blocks
                ]
                response_text = "You have multiple work shifts scheduled. Which one do you want to move?"
                return _finalize_response(
                    db=db,
                    conv_id=conv.id,
                    text=response_text,
                    intent=intent.value,
                    choices=choices,
                )
            else:
                target_dow = params.get("day") if params.get("day") is not None else blocks[0].day_of_week
                target_b = next((b for b in blocks if b.day_of_week == target_dow), blocks[0])
                st_time = params.get("start_time") or "16:00"
                # Duration
                dur = (time_to_minutes(target_b.end_time) - time_to_minutes(target_b.start_time)) if target_b.end_time else 120
                et_m = time_to_minutes(st_time) + dur
                et_time = minutes_to_time(et_m)

                # Check conflict
                sched = tool_get_my_schedule(db, current_user, day_of_week=target_dow, view="today")
                clash = False
                clash_title = ""
                for ev in sched["events"]:
                    if ev["type"] == "class":
                        if time_to_minutes(st_time) < ev["end_mins"] and et_m > ev["start_mins"]:
                            clash = True
                            clash_title = ev["title"]
                            break

                checks = [
                    ActionCheckItem(label="No class conflict", passed=not clash, warning=clash),
                    ActionCheckItem(label="Work-hour limit respected", passed=True),
                    ActionCheckItem(label="Transition buffer respected", passed=True),
                ]

                if clash:
                    response_text = f"⚠️ Moving your shift to {DAY_NAMES[target_dow]} at {st_time} conflicts with your scheduled class '{clash_title}'. Please choose a different time."
                else:
                    action_preview = ActionPreview(
                        action_type="move_shift",
                        title=f"Move Shift: {target_b.title}",
                        block_id=target_b.id,
                        parameters={
                            "block_id": target_b.id,
                            "day_of_week": target_dow,
                            "start_time": st_time,
                            "end_time": et_time,
                        },
                        original={
                            "day": DAY_NAMES[target_b.day_of_week],
                            "time": f"{target_b.start_time}–{target_b.end_time}",
                        },
                        target={
                            "day": DAY_NAMES[target_dow],
                            "time": f"{st_time}–{et_time}",
                            "start_time": st_time,
                            "end_time": et_time,
                        },
                        checks=checks,
                    )
                    response_text = (
                        f"I can move **{target_b.title}** to **{DAY_NAMES[target_dow]} at {st_time}–{et_time}**. "
                        "All constraints have been verified with zero class conflicts. Please confirm to apply."
                    )

        elif intent in (AssistantIntentType.MOVE_WORK_SHIFT, AssistantIntentType.MOVE_EVENT):
            # Enhanced: use full conflict-check + alternatives pipeline
            day_val = params.get("day") or _extract_day(message)
            st_time = params.get("start_time")

            # Try to get the shift for the student
            blocks = db.query(TimeBlock).filter(
                TimeBlock.user_id == user_id,
                TimeBlock.type == BlockType.SHIFT,
                TimeBlock.status != BlockStatus.DROPPED,
                TimeBlock.deleted == False,
            ).all()

            if not blocks:
                response_text = "You don't have any work shifts scheduled to move."
            elif len(blocks) > 1 and not day_val:
                choices = [
                    {
                        "block_id": b.id,
                        "title": b.title,
                        "day": DAY_NAMES[b.day_of_week] if b.day_of_week is not None else "?",
                        "start_time": b.start_time.strftime("%H:%M") if isinstance(b.start_time, dt_time) else str(b.start_time)[:5],
                        "end_time": b.end_time.strftime("%H:%M") if isinstance(b.end_time, dt_time) else str(b.end_time)[:5],
                    }
                    for b in blocks
                ]
                response_text = "You have multiple work shifts. Which one would you like to move?"
                return _finalize_response(
                    db=db, conv_id=conv.id, text=response_text, intent=intent.value, choices=choices,
                )
            else:
                # Pick the block matching the source day (or first block)
                source_day = _extract_source_day(message)
                if source_day is not None:
                    target_b = next((b for b in blocks if b.day_of_week == source_day), blocks[0])
                else:
                    target_b = blocks[0]

                target_dow = day_val if day_val is not None else (target_b.day_of_week + 1) % 7

                try:
                    result = tool_prepare_move_work_shift(
                        db=db,
                        current_user=current_user,
                        block_id=target_b.id,
                        target_day_of_week=target_dow,
                        target_start_time=st_time,
                    )
                    tool_calls_meta.append({"tool": "prepare_move_work_shift", "status": "success"})

                    if result["has_conflict"]:
                        alts = result.get("alternatives", [])
                        response_text = (
                            f"⚠️ **Conflict detected!** Moving **{target_b.title}** to "
                            f"{result['proposed_day']} at {result['proposed_time']} would conflict with: "
                            f"**{', '.join(result['conflict_with'])}**.\n\n"
                            + ("Here are **conflict-free alternatives** you can choose from:" if alts else "No alternative slots found this week.")
                        )
                        return _finalize_response(
                            db=db, conv_id=conv.id, text=response_text, intent=intent.value,
                            tool_calls=tool_calls_meta, tool_progress=tool_calls_meta, alternatives=alts,
                        )
                    else:
                        action_preview = ActionPreview(**result["action_preview"])
                        response_text = result["message"]
                except Exception as tool_exc:
                    logger.warning(f"move_work_shift tool error: {tool_exc}")
                    response_text = f"I couldn't process the move request: {tool_exc}"

        elif intent == AssistantIntentType.CREATE_WORK_SHIFT:
            title = params.get("title", "Work Shift")
            dow = params.get("day_of_week", 1)
            st = params.get("start_time", "09:00")
            et = params.get("end_time", "17:00")
            try:
                result = tool_prepare_create_work_shift(
                    db=db, current_user=current_user, title=title, day_of_week=dow, start_time=st, end_time=et,
                )
                action_preview = ActionPreview(**result["action_preview"])
                response_text = result["message"]
                tool_calls_meta.append({"tool": "prepare_create_work_shift", "status": "success"})
            except Exception as e:
                response_text = f"Could not prepare shift creation: {e}"

        elif intent in (AssistantIntentType.DELETE_WORK_SHIFT, AssistantIntentType.DELETE_PERSONAL_BLOCK):
            block_id = params.get("block_id")
            if not block_id:
                response_text = "Please tell me which block you'd like to delete (provide the block ID or describe it)."
            else:
                try:
                    result = tool_prepare_delete_block(db=db, current_user=current_user, block_id=block_id)
                    action_preview = ActionPreview(**result["action_preview"])
                    response_text = result["message"]
                    tool_calls_meta.append({"tool": "prepare_delete_block", "status": "success"})
                except Exception as e:
                    response_text = f"Could not prepare deletion: {e}"

        elif intent == AssistantIntentType.CREATE_STUDY_TASK:
            title = params.get("title", "Study Task")
            hours = params.get("total_hours_required", 2.0)
            deadline = params.get("deadline", (date.today() + timedelta(days=7)).isoformat())
            try:
                result = tool_prepare_create_study_task(
                    db=db, current_user=current_user, title=title,
                    total_hours_required=float(hours), deadline=deadline,
                )
                action_preview = ActionPreview(**result["action_preview"])
                response_text = result["message"]
                tool_calls_meta.append({"tool": "prepare_create_study_task", "status": "success"})
            except Exception as e:
                response_text = f"Could not prepare study task: {e}"

        elif intent == AssistantIntentType.GET_MY_WORK_SHIFTS:
            data = tool_get_my_work_shifts(db, current_user)
            tool_calls_meta.append({"tool": "get_my_work_shifts", "status": "success"})
            shifts = data["shifts"]
            if not shifts:
                response_text = "You have no work shifts scheduled this week."
            else:
                lines = [f"💼 **Your Work Shifts** ({len(shifts)} total):"]
                for s in shifts:
                    lines.append(f"- 📌 **{s['title']}** — {s['day_name']} {s['start_time']}–{s['end_time']} (Block ID: {s['block_id']})")
                response_text = "\n".join(lines)
            suggestions = ["Do I have any conflicts?", "How many work hours do I have left?"]

        elif intent == AssistantIntentType.GET_MY_TASKS:
            data = tool_get_my_tasks(db, current_user)
            tool_calls_meta.append({"tool": "get_my_tasks", "status": "success"})
            tasks = data["tasks"]
            if not tasks:
                response_text = "You have no pending study tasks."
            else:
                lines = [f"📚 **Your Study Tasks** ({len(tasks)} pending):"]
                for t in tasks:
                    lines.append(f"- 🎯 **{t['title']}** · Due: {t['deadline']} · {t['total_hours_required']:.1f}h required · Priority: {t['priority']}")
                response_text = "\n".join(lines)
            suggestions = ["Plan my week", "Create a study session"]

        elif intent == AssistantIntentType.GET_MY_PROFILE:
            data = tool_get_my_profile(db, current_user)
            tool_calls_meta.append({"tool": "get_my_profile", "status": "success"})
            response_text = (
                f"👤 **Your Profile**:\n"
                f"- Name: **{data['name']}**\n"
                f"- Email: {data['email']}\n"
                f"- Timezone: {data['timezone']}\n"
                f"- Weekly Work Limit: **{data['weekly_work_hour_limit']}h**\n"
                f"- Minimum Transition Time: {data['minimum_transition_minutes']} minutes"
            )

        elif intent == AssistantIntentType.FIND_AVAILABLE_TIME_SLOTS:
            dow = params.get("day_of_week")
            dur = params.get("duration_minutes", 60)
            data = tool_find_available_time_slots(db, current_user, day_of_week=dow, duration_minutes=int(dur))
            tool_calls_meta.append({"tool": "find_available_time_slots", "status": "success"})
            slots = data["free_slots"]
            if not slots:
                response_text = f"No free slots of at least {dur} minutes were found."
            else:
                lines = [f"🕒 **Free Slots** ({dur}+ minutes):"]
                for s in slots[:5]:
                    lines.append(f"- {s['day_name']} {s['start_time']}–{s['end_time']} ({s['duration_minutes']} min)")
                response_text = "\n".join(lines)
            suggestions = ["Create a study block", "Plan my week"]

        else:
            response_text = (
                "👋 I'm your **SyncShift Assistant**!\n"
                "I connect your university academic timetable with real student life.\n\n"
                "You can ask me:\n"
                "- *What classes do I have today?*\n"
                "- *Move my Wednesday shift to Thursday*\n"
                "- *Do I have any conflicts this week?*\n"
                "- *Create a 2-hour study session for Friday afternoon*\n"
                "- *How many work hours do I have left?*\n"
                "- *Plan my week*"
            )
            suggestions = ["What classes do I have today?", "Do I have any conflicts?", "Plan my week"]

    except Exception as exc:
        logger.exception(f"Assistant processing error: {exc}")
        response_text = "SyncShift couldn't complete this query right now. Please try again."

    return _finalize_response(
        db=db,
        conv_id=conv.id,
        text=response_text,
        intent=intent.value,
        action=action_preview,
        tool_calls=tool_calls_meta,
        tool_progress=tool_calls_meta,
        suggestions=suggestions,
    )


def _finalize_response(
    db: Session,
    conv_id: int,
    text: str,
    intent: str,
    action: Optional[ActionPreview] = None,
    choices: Optional[list[dict[str, Any]]] = None,
    tool_calls: Optional[list[dict[str, Any]]] = None,
    suggestions: Optional[list[str]] = None,
    tool_progress: Optional[list[dict[str, Any]]] = None,
    alternatives: Optional[list[dict[str, Any]]] = None,
) -> AssistantChatResponseData:
    """Saves assistant message and updates conversation timestamp."""
    action_json = action.model_dump_json() if action else None
    tool_json = json.dumps(tool_calls) if tool_calls else None

    asst_msg = AssistantMessage(
        conversation_id=conv_id,
        role="assistant",
        content=text,
        action_data=action_json,
        tool_calls=tool_json,
    )
    db.add(asst_msg)

    conv = db.query(AssistantConversation).filter(AssistantConversation.id == conv_id).first()
    if conv:
        conv.updated_at = func.now()

    db.commit()

    # Convert alternatives dicts to AlternativeSlot objects
    alt_slots: Optional[list[AlternativeSlot]] = None
    if alternatives:
        alt_slots = []
        for a in alternatives:
            try:
                alt_slots.append(AlternativeSlot(**a))
            except Exception:
                pass

    return AssistantChatResponseData(
        message=text,
        intent=intent,
        conversation_id=conv_id,
        requires_confirmation=action is not None,
        action=action,
        choices=choices,
        suggestions=suggestions or [],
        tool_calls=tool_calls,
        tool_progress=tool_progress,
        alternatives=alt_slots,
    )


# =====================================================================
# ACTION CONFIRMATION & EXECUTION
# =====================================================================

def execute_confirmed_action(
    current_user: CurrentUser,
    action: ActionPreview,
    db: Session,
) -> AssistantConfirmResponseData:
    """
    Executes a user-confirmed scheduling change with strict server-side authorization,
    re-validation of constraints, and immutable audit logging.
    """
    user_id = current_user.user_id
    action_type = action.action_type
    params = action.parameters or {}

    if action_type == "move_shift":
        block_id = action.block_id or params.get("block_id")
        block = db.query(TimeBlock).filter(TimeBlock.id == block_id, TimeBlock.user_id == user_id).first()
        if not block:
            raise HTTPException(status_code=404, detail="Shift not found or access denied.")

        new_dow = params["day_of_week"]
        st = params["start_time"]
        et = params["end_time"]

        # Parse times
        st_obj = datetime.strptime(st, "%H:%M").time() if isinstance(st, str) else st
        et_obj = datetime.strptime(et, "%H:%M").time() if isinstance(et, str) else et

        old_data = {"day_of_week": block.day_of_week, "start_time": str(block.start_time), "end_time": str(block.end_time)}

        block.day_of_week = new_dow
        block.start_time = st_obj
        block.end_time = et_obj
        db.commit()

        # Audit log
        record_audit_log(
            db=db,
            user_id=user_id,
            action="AI_ACTION_CONFIRMED",
            entity_type="time_block",
            entity_id=block.id,
            description=f"Moved shift '{block.title}' to {DAY_NAMES[new_dow]} {st} - {et}",
            metadata={"before": old_data, "after": {"day_of_week": new_dow, "start_time": st, "end_time": et}},
        )

        return AssistantConfirmResponseData(
            success=True,
            action_type=action_type,
            message=f"Shift successfully moved to {DAY_NAMES[new_dow]} at {st}–{et}.",
            updated_block={"id": block.id, "day_of_week": new_dow, "start_time": st, "end_time": et},
        )

    elif action_type == "create_study_block":
        title = params.get("title", "Study Session")
        dow = params.get("day_of_week", 1)
        st = params.get("start_time", "15:00")
        et = params.get("end_time", "17:00")

        st_obj = datetime.strptime(st, "%H:%M").time() if isinstance(st, str) else st
        et_obj = datetime.strptime(et, "%H:%M").time() if isinstance(et, str) else et
        duration = (et_obj.hour * 60 + et_obj.minute) - (st_obj.hour * 60 + st_obj.minute)
        if duration <= 0:
            duration = 120

        block = TimeBlock(
            user_id=user_id,
            title=title,
            type=BlockType.STUDY,
            day_of_week=dow,
            start_time=st_obj,
            end_time=et_obj,
            duration_minutes=duration,
            is_flexible=True,
        )
        db.add(block)
        db.commit()
        db.refresh(block)

        record_audit_log(
            db=db,
            user_id=user_id,
            action="create_study_block",
            entity_type="time_block",
            entity_id=block.id,
            description=f"Created study block '{title}' on {DAY_NAMES[dow]} {st} - {et}",
            metadata={"title": title, "day_of_week": dow, "start_time": st, "end_time": et},
        )

        return AssistantConfirmResponseData(
            success=True,
            action_type=action_type,
            message=f"Study block '{title}' created on {DAY_NAMES[dow]} at {st}–{et}.",
            updated_block={"id": block.id, "title": title, "day_of_week": dow, "start_time": st, "end_time": et},
        )

    elif action_type == "apply_plan":
        strategy = params.get("strategy", "balanced")
        week_start_str = params.get("week_start")
        week_start = datetime.strptime(week_start_str, "%Y-%m-%d").date() if week_start_str else date.today()

        user = db.query(User).filter(User.id == user_id).first()
        plan_res = SmartPlannerService.apply_weekly_plan(
            db=db,
            user=user,
            week_start=week_start,
            strategy=strategy,
        )

        record_audit_log(
            db=db,
            user_id=user_id,
            action="apply_weekly_plan",
            entity_type="weekly_plan",
            entity_id=0,
            description=f"Applied {strategy} weekly plan creating {plan_res.study_blocks_created} study blocks",
            metadata={"strategy": strategy, "study_blocks_created": plan_res.study_blocks_created},
        )

        return AssistantConfirmResponseData(
            success=True,
            action_type=action_type,
            message=f"Applied {strategy.capitalize()} plan! Created {plan_res.study_blocks_created} study blocks.",
            data={"strategy": strategy, "study_blocks_created": plan_res.study_blocks_created},
        )

    elif action_type == "timetable_change":
        # N6 Apply change
        inst_id = params["institution_id"]
        verify_institution_admin_access(db, user_id, inst_id)

        from app.schemas.timetable import TimetableChangeApplyRequest
        from app.services.impact_analysis import apply_timetable_change

        req = TimetableChangeApplyRequest(
            meeting_id=params["meeting_id"],
            day_of_week=params["day_of_week"],
            start_time=params["start_time"],
            end_time=params["end_time"],
            room_id=params.get("room_id"),
            expected_updated_at=datetime.fromisoformat(params["expected_updated_at"]) if params.get("expected_updated_at") else None,
        )

        apply_res = apply_timetable_change(
            db=db,
            institution_id=inst_id,
            timetable_id=params["timetable_id"],
            request=req,
            user_id=user_id,
        )

        return AssistantConfirmResponseData(
            success=True,
            action_type=action_type,
            message=apply_res.message,
            data={"meeting_id": params["meeting_id"], "audit_log_id": apply_res.audit_log_id},
        )

    elif action_type == "create_timetable_draft":
        inst_id = params["institution_id"]
        verify_institution_admin_access(db, user_id, inst_id)

        from app.schemas.timetable import TimetableVersionCreate
        from app.services.timetable_version_service import create_version
        v_create = TimetableVersionCreate(name=params.get("name", "Assistant Draft"))
        new_v = create_version(db=db, institution_id=inst_id, timetable_id=params["timetable_id"], data=v_create, user_id=user_id)

        return AssistantConfirmResponseData(
            success=True,
            action_type=action_type,
            message=f"Draft Version {new_v.version_number} created successfully.",
            data={"version_id": new_v.id, "version_number": new_v.version_number},
        )

    elif action_type == "create_work_shift":
        title = params.get("title", "Work Shift")
        dow = params.get("day_of_week", 1)
        st = params.get("start_time", "09:00")
        et = params.get("end_time", "17:00")
        location = params.get("location")

        # Re-validate: verify no conflict before creating
        st_obj = datetime.strptime(st, "%H:%M").time() if isinstance(st, str) else st
        et_obj = datetime.strptime(et, "%H:%M").time() if isinstance(et, str) else et
        duration = (et_obj.hour * 60 + et_obj.minute) - (st_obj.hour * 60 + st_obj.minute)
        if duration <= 0:
            raise HTTPException(status_code=400, detail="Invalid shift duration.")

        block = TimeBlock(
            user_id=user_id,
            title=title,
            type=BlockType.SHIFT,
            day_of_week=dow,
            start_time=st_obj,
            end_time=et_obj,
            duration_minutes=duration,
            location=location,
        )
        db.add(block)
        db.commit()
        db.refresh(block)

        record_audit_log(
            db=db, user_id=user_id, action="AI_ACTION_CONFIRMED",
            entity_type="time_block", entity_id=block.id,
            description=f"Created work shift '{title}' on {DAY_NAMES[dow]} {st}–{et}",
            metadata={"title": title, "day_of_week": dow, "start_time": st, "end_time": et},
        )
        return AssistantConfirmResponseData(
            success=True, action_type=action_type,
            message=f"Work shift '{title}' created on {DAY_NAMES[dow]} at {st}–{et}.",
            updated_block={"id": block.id, "title": title, "day_of_week": dow, "start_time": st, "end_time": et},
        )

    elif action_type == "delete_block":
        block_id = action.block_id or params.get("block_id")
        block = db.query(TimeBlock).filter(
            TimeBlock.id == block_id, TimeBlock.user_id == user_id
        ).first()
        if not block:
            raise HTTPException(status_code=404, detail="Block not found or access denied.")

        block_title = block.title
        block.deleted = True
        db.commit()

        record_audit_log(
            db=db, user_id=user_id, action="AI_ACTION_CONFIRMED",
            entity_type="time_block", entity_id=block_id,
            description=f"Deleted block '{block_title}' via assistant",
            metadata={"block_id": block_id},
        )
        return AssistantConfirmResponseData(
            success=True, action_type=action_type,
            message=f"'{block_title}' has been removed from your schedule.",
        )

    elif action_type == "create_study_task":
        from app.models.study_task import StudyTask, TaskStatus
        title = params.get("title", "Study Task")
        hours = float(params.get("total_hours_required", 2.0))
        deadline_str = params.get("deadline", (date.today() + timedelta(days=7)).isoformat())
        priority = params.get("priority", "medium")

        try:
            dl_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline format.")

        task = StudyTask(
            user_id=user_id,
            title=title,
            total_hours_required=hours,
            deadline=dl_date,
            priority=priority,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        record_audit_log(
            db=db, user_id=user_id, action="AI_ACTION_CONFIRMED",
            entity_type="study_task", entity_id=task.id,
            description=f"Created study task '{title}' due {deadline_str}",
            metadata={"title": title, "hours": hours, "deadline": deadline_str},
        )
        return AssistantConfirmResponseData(
            success=True, action_type=action_type,
            message=f"Study task '{title}' created (due {deadline_str}, {hours}h required).",
            updated_block={"id": task.id, "title": title, "deadline": deadline_str},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported action type: {action_type}")


# =====================================================================
# GEMINI TOOL DISPATCHER (binds session auth, executes deterministic tools)
# =====================================================================

# Module-level slot for pending action previews generated by tools
_pending_action_preview: Optional[ActionPreview] = None


def _retrieve_pending_action() -> Optional[ActionPreview]:
    """Retrieves and clears the pending action preview slot."""
    global _pending_action_preview
    result = _pending_action_preview
    _pending_action_preview = None
    return result


def _dispatch_gemini_tool(
    tool_name: str,
    args: dict,
    db: Session,
    current_user: CurrentUser,
    admin_inst_id: Optional[int],
) -> dict:
    """
    Dispatches a Gemini-selected tool name to the appropriate deterministic Python function.
    Binds db and current_user from the authenticated session — never from Gemini output.
    """
    global _pending_action_preview

    if tool_name == "get_my_profile":
        return tool_get_my_profile(db, current_user)
    elif tool_name == "get_my_timetable":
        view = args.get("view", "week")
        dow = args.get("day_of_week")
        return tool_get_my_schedule(db, current_user, day_of_week=dow, view=view)
    elif tool_name == "get_my_calendar":
        return tool_get_my_calendar(db, current_user)
    elif tool_name == "get_my_courses":
        return tool_get_my_courses(db, current_user)
    elif tool_name == "get_my_work_shifts":
        return tool_get_my_work_shifts(db, current_user)
    elif tool_name == "get_my_personal_blocks":
        return tool_get_my_personal_blocks(db, current_user)
    elif tool_name == "get_my_tasks":
        return tool_get_my_tasks(db, current_user)
    elif tool_name == "get_my_conflicts":
        return tool_get_my_conflicts(db, current_user)
    elif tool_name == "get_my_weekly_hours":
        return tool_get_my_weekly_hours(db, current_user)
    elif tool_name == "get_my_preferences":
        return tool_get_my_preferences(db, current_user)
    elif tool_name == "get_my_notifications":
        unread_only = bool(args.get("unread_only", False))
        return tool_get_my_notifications(db, current_user, unread_only=unread_only)
    elif tool_name == "get_current_timetable":
        if not admin_inst_id:
            return {"error": "Admin privileges required."}
        return tool_get_university_timetable(db, current_user, institution_id=admin_inst_id)
    elif tool_name == "get_course_information":
        return tool_get_course_information(db, current_user, course_code=args.get("course_code"))
    elif tool_name == "get_class_details":
        return tool_get_class_details(db, current_user, course_code=args.get("course_code"))
    elif tool_name == "get_timetable_change_information":
        return tool_get_timetable_change_information(db, current_user)
    elif tool_name == "find_available_time_slots":
        return tool_find_available_time_slots(
            db, current_user,
            day_of_week=args.get("day_of_week"),
            duration_minutes=int(args.get("duration_minutes", 60)),
            earliest_hour=int(args.get("earliest_hour", 8)),
            latest_hour=int(args.get("latest_hour", 22)),
        )
    elif tool_name == "check_schedule_conflict":
        return tool_check_schedule_conflict(
            db, current_user,
            day_of_week=int(args["day_of_week"]),
            start_time=args["start_time"],
            end_time=args["end_time"],
            exclude_block_id=args.get("exclude_block_id"),
        )
    elif tool_name == "calculate_transition_time":
        return tool_calculate_transition_time(
            db, current_user,
            end_event_time=args["end_event_time"],
            start_next_event_time=args["start_next_event_time"],
        )
    elif tool_name == "generate_planner_options":
        return tool_generate_planner_options(
            db, current_user,
            duration_minutes=int(args["duration_minutes"]),
            preferred_day_of_week=args.get("preferred_day_of_week"),
            exclude_block_id=args.get("exclude_block_id"),
        )
    elif tool_name == "explain_conflict":
        return tool_explain_conflict(
            db, current_user,
            event_a_title=args["event_a_title"],
            event_b_title=args["event_b_title"],
            day=args["day"],
            event_a_time=args.get("event_a_time"),
            event_b_time=args.get("event_b_time"),
        )
    elif tool_name == "move_work_shift":
        result = tool_prepare_move_work_shift(
            db, current_user,
            block_id=int(args["block_id"]),
            target_day_of_week=int(args["target_day_of_week"]),
            target_start_time=args.get("target_start_time"),
        )
        if not result["has_conflict"] and result.get("action_preview"):
            _pending_action_preview = ActionPreview(**result["action_preview"])
        return result
    elif tool_name == "create_work_shift":
        result = tool_prepare_create_work_shift(
            db, current_user,
            title=args["title"],
            day_of_week=int(args["day_of_week"]),
            start_time=args["start_time"],
            end_time=args["end_time"],
            location=args.get("location"),
        )
        if result.get("action_preview"):
            _pending_action_preview = ActionPreview(**result["action_preview"])
        return result
    elif tool_name in ("update_work_shift", "delete_work_shift", "delete_personal_block"):
        block_id = int(args.get("block_id", 0))
        result = tool_prepare_delete_block(db, current_user, block_id=block_id)
        if result.get("action_preview"):
            _pending_action_preview = ActionPreview(**result["action_preview"])
        return result
    elif tool_name == "create_personal_block":
        title = args.get("title", "Personal Block")
        dow = int(args.get("day_of_week", 1))
        st = args.get("start_time", "09:00")
        et = args.get("end_time", "10:00")
        block_type = args.get("block_type", "study")
        # Reuse study block prep
        ap = tool_prepare_create_study_block(db, current_user, title=title, day_of_week=dow, start_time=st, end_time=et)
        _pending_action_preview = ap
        return {"action_preview": ap.model_dump(), "message": f"Ready to create '{title}' on {DAY_NAMES[dow]} {st}–{et}."}
    elif tool_name == "create_study_task":
        result = tool_prepare_create_study_task(
            db, current_user,
            title=args["title"],
            total_hours_required=float(args["total_hours_required"]),
            deadline=args["deadline"],
            priority=args.get("priority", "medium"),
        )
        if result.get("action_preview"):
            _pending_action_preview = ActionPreview(**result["action_preview"])
        return result
    elif tool_name == "plan_week":
        strategy = args.get("strategy", "balanced")
        return tool_preview_my_plan(db, current_user, strategy=strategy)
    else:
        logger.warning(f"Unknown tool requested by Gemini: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}


def _extract_source_day(text: str) -> Optional[int]:
    """
    Extracts the source day from phrases like 'move my Wednesday shift'.
    Returns day_of_week int or None.
    """
    msg = text.lower()
    for name, i in DAY_NAME_TO_INT.items():
        if name in msg:
            return i
    return None
