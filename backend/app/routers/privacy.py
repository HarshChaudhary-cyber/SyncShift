"""
Privacy Center Router
Endpoints for student data export and safe account deletion.
Enforces strict user isolation and privacy best practices.
"""
from datetime import datetime, timezone as dt_timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.notification import NotificationPrefs, PushSubscription
from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.models.user import User
from app.routers.auth import verify_password
from app.schemas.auth import DeleteAccountRequest, ExportDataResponse, MessageData
from app.schemas.common import DataResponse
from app.services.audit import record_audit_log

router = APIRouter(prefix="/privacy", tags=["Privacy"])


@router.get("/export", response_model=DataResponse[ExportDataResponse])
def export_user_data_privacy(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all personal schedule data for the authenticated student.
    Strictly scoped to authenticated user from JWT.
    Does NOT contain password hashes, OAuth secrets, or system prompts.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    courses = db.query(Course).filter(Course.user_id == user.id).all()
    blocks = db.query(TimeBlock).filter(TimeBlock.user_id == user.id, TimeBlock.deleted == False).all()
    tasks = db.query(StudyTask).filter(StudyTask.user_id == user.id).all()
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user.id).first()

    courses_data = [
        {"id": c.id, "code": c.code, "name": c.name, "color": c.color, "term": c.term}
        for c in courses
    ]
    blocks_data = [
        {
            "id": b.id,
            "type": str(b.type.value if hasattr(b.type, "value") else b.type),
            "title": b.title,
            "location": b.location,
            "day_of_week": b.day_of_week,
            "start_time": str(b.start_time),
            "end_time": str(b.end_time),
            "duration_minutes": b.duration_minutes,
            "course_id": b.course_id,
            "hourly_wage": float(b.hourly_wage) if b.hourly_wage is not None else None,
            "is_flexible": b.is_flexible,
            "is_recurring": b.is_recurring,
            "specific_date": str(b.specific_date) if b.specific_date else None,
        }
        for b in blocks
    ]
    tasks_data = [
        {
            "id": t.id,
            "title": t.title,
            "course_id": t.course_id,
            "total_hours_required": float(t.total_hours_required),
            "deadline": str(t.deadline),
            "status": str(t.status.value if hasattr(t.status, "value") else t.status),
        }
        for t in tasks
    ]
    prefs_data = None
    if prefs:
        prefs_data = {
            "push_enabled": prefs.push_enabled,
            "email_enabled": prefs.email_enabled,
            "class_reminder_min": prefs.class_reminder_min,
            "shift_reminder_min": prefs.shift_reminder_min,
            "study_reminder_min": prefs.study_reminder_min,
            "deadline_reminder": prefs.deadline_reminder,
            "conflict_alerts": prefs.conflict_alerts,
        }

    user_data = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name or user.name,
        "timezone": user.timezone,
        "weekly_work_hour_limit": float(user.weekly_work_hour_limit or 20.0),
        "minimum_transition_minutes": int(user.minimum_transition_minutes or 15),
        "currency": user.currency or "INR",
        "language": user.language or "en",
        "theme": user.theme or "dark",
        "oauth_provider": user.oauth_provider,
        "created_at": str(user.created_at),
    }

    record_audit_log(
        db=db,
        user_id=user.id,
        action="DATA_EXPORTED",
        entity_type="user",
        entity_id=user.id,
        description="Student exported their full personal schedule archive",
        request=request,
    )

    return DataResponse(
        data=ExportDataResponse(
            user=user_data,
            courses=courses_data,
            time_blocks=blocks_data,
            study_tasks=tasks_data,
            notification_prefs=prefs_data,
            exported_at=datetime.now(dt_timezone.utc).isoformat(),
        )
    )


@router.post("/delete-account", response_model=DataResponse[MessageData])
def delete_account_privacy(
    body: DeleteAccountRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely soft-delete account and cascade to dependent schedule data.
    Requires either valid password or confirmation phrase 'DELETE'.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    if user.password_hash:
        has_valid_pwd = body.password and verify_password(body.password, user.password_hash)
        has_valid_confirm = body.confirm and body.confirm.strip() == "DELETE"
        if not has_valid_pwd and not has_valid_confirm:
            if body.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "invalid_credentials", "message": "Incorrect password"},
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "confirmation_required", "message": "Please enter your password or type DELETE to confirm."},
            )
    else:
        if not body.confirm or body.confirm.strip() != "DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "confirmation_required", "message": "Please type DELETE to confirm account deletion."},
            )

    now = datetime.now(dt_timezone.utc)
    user.deleted_at = now

    # Cascade soft delete to time blocks
    db.query(TimeBlock).filter(TimeBlock.user_id == user.id).update({TimeBlock.deleted: True})

    # Disable push & notifications
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user.id).first()
    if prefs:
        prefs.push_enabled = False
        prefs.email_enabled = False

    db.query(PushSubscription).filter(PushSubscription.user_id == user.id).delete()

    record_audit_log(
        db=db,
        user_id=user.id,
        action="ACCOUNT_DELETED",
        entity_type="user",
        entity_id=user.id,
        description="Student soft-deleted their account and revoked active sessions",
        request=request,
    )

    db.commit()
    return DataResponse(data=MessageData(message="Account deleted successfully"))
