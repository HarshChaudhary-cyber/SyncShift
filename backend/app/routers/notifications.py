"""
Notifications Router for SyncShift.
Provides endpoints for push subscriptions, notification preferences,
test push notifications, and notification logs.
"""
from datetime import datetime, time, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.notification import NotificationLog, NotificationPrefs, PushSubscription
from app.schemas.common import DataResponse
from app.schemas.notification import (
    NotificationListResponse,
    NotificationLogOut,
    NotificationMarkAllReadResponse,
    NotificationMarkReadResponse,
    NotificationPrefsOut,
    NotificationPrefsUpdate,
    NotificationUnreadCountResponse,
    PushSubscriptionDelete,
    PushSubscriptionIn,
    TestNotificationResponse,
)
from app.services.reminders import parse_time_obj, send_web_push
from app.services.timezone_helper import get_user_today

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _format_time_for_response(t: Optional[time | str]) -> Optional[str]:
    if t is None:
        return None
    if isinstance(t, str):
        return t[:5]
    return f"{t.hour:02d}:{t.minute:02d}"


@router.get("/prefs", response_model=DataResponse[NotificationPrefsOut])
def get_notification_prefs(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve notification preferences for current user.
    Auto-creates default row if not present.
    """
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == current_user.user_id).first()
    if not prefs:
        prefs = NotificationPrefs(
            user_id=current_user.user_id,
            push_enabled=True,
            email_enabled=False,
            timetable_changes_enabled=True,
            class_reminder_min=30,
            shift_reminder_min=60,
            study_reminder_min=15,
            deadline_reminder=True,
            conflict_alerts=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    out = NotificationPrefsOut(
        user_id=prefs.user_id,
        push_enabled=prefs.push_enabled,
        email_enabled=prefs.email_enabled,
        timetable_changes_enabled=getattr(prefs, "timetable_changes_enabled", True),
        class_reminder_min=prefs.class_reminder_min,
        shift_reminder_min=prefs.shift_reminder_min,
        study_reminder_min=prefs.study_reminder_min,
        deadline_reminder=prefs.deadline_reminder,
        conflict_alerts=prefs.conflict_alerts,
        quiet_hours_start=_format_time_for_response(prefs.quiet_hours_start),
        quiet_hours_end=_format_time_for_response(prefs.quiet_hours_end),
    )
    return DataResponse(data=out)



@router.put("/prefs", response_model=DataResponse[NotificationPrefsOut])
def update_notification_prefs(
    body: NotificationPrefsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update notification preferences for current user.
    Validates reminder minutes and quiet hours.
    """
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == current_user.user_id).first()
    if not prefs:
        prefs = NotificationPrefs(user_id=current_user.user_id)
        db.add(prefs)

    if body.push_enabled is not None:
        prefs.push_enabled = body.push_enabled
    if body.email_enabled is not None:
        prefs.email_enabled = body.email_enabled
    if body.timetable_changes_enabled is not None:
        prefs.timetable_changes_enabled = body.timetable_changes_enabled
    if body.class_reminder_min is not None:
        prefs.class_reminder_min = body.class_reminder_min
    if body.shift_reminder_min is not None:
        prefs.shift_reminder_min = body.shift_reminder_min
    if body.study_reminder_min is not None:
        prefs.study_reminder_min = body.study_reminder_min
    if body.deadline_reminder is not None:
        prefs.deadline_reminder = body.deadline_reminder
    if body.conflict_alerts is not None:
        prefs.conflict_alerts = body.conflict_alerts

    if body.quiet_hours_start is not None or body.quiet_hours_end is not None:
        prefs.quiet_hours_start = parse_time_obj(body.quiet_hours_start)
        prefs.quiet_hours_end = parse_time_obj(body.quiet_hours_end)
    elif body.quiet_hours_start is None and body.quiet_hours_end is None and "quiet_hours_start" in body.model_fields_set:
        prefs.quiet_hours_start = None
        prefs.quiet_hours_end = None

    db.commit()
    db.refresh(prefs)

    out = NotificationPrefsOut(
        user_id=prefs.user_id,
        push_enabled=prefs.push_enabled,
        email_enabled=prefs.email_enabled,
        timetable_changes_enabled=getattr(prefs, "timetable_changes_enabled", True),
        class_reminder_min=prefs.class_reminder_min,
        shift_reminder_min=prefs.shift_reminder_min,
        study_reminder_min=prefs.study_reminder_min,
        deadline_reminder=prefs.deadline_reminder,
        conflict_alerts=prefs.conflict_alerts,
        quiet_hours_start=_format_time_for_response(prefs.quiet_hours_start),
        quiet_hours_end=_format_time_for_response(prefs.quiet_hours_end),
    )
    return DataResponse(data=out)



@router.post("/subscribe", status_code=status.HTTP_200_OK)
def subscribe_push(
    body: PushSubscriptionIn,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save or update a browser push subscription for current user.
    """
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == body.endpoint).first()
    if existing:
        existing.user_id = current_user.user_id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
    else:
        new_sub = PushSubscription(
            user_id=current_user.user_id,
            endpoint=body.endpoint,
            p256dh=body.keys.p256dh,
            auth=body.keys.auth,
        )
        db.add(new_sub)
    db.commit()

    return {"ok": True}


@router.delete("/subscribe", status_code=status.HTTP_200_OK)
def unsubscribe_push(
    body: PushSubscriptionDelete,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove push subscription by endpoint for current user.
    """
    sub = db.query(PushSubscription).filter(
        PushSubscription.endpoint == body.endpoint,
        PushSubscription.user_id == current_user.user_id,
    ).first()

    if sub:
        db.delete(sub)
        db.commit()

    return {"ok": True}


@router.post("/test")
def test_notification(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sends a test push notification to all subscriptions of current user.
    Returns 404 if user has no subscriptions.
    """
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == current_user.user_id).all()
    if not subs:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "No push subscription found. Allow notifications in your browser first."},
        )

    title = "SyncShift"
    body = "Notifications are working 🎉"
    payload = {"title": title, "body": body, "url": "/dashboard"}

    sent_count = 0
    for sub in subs:
        if send_web_push(sub, payload, db=db):
            sent_count += 1

    # Record test event in notification_log
    log_entry = NotificationLog(
        user_id=current_user.user_id,
        type="test",
        title=title,
        body=body,
        channel="push",
        dedup_key=None,
    )
    db.add(log_entry)
    db.commit()

    return {"ok": True, "message": "Notifications are working 🎉", "sent_count": sent_count}


@router.get("/log", response_model=DataResponse[list[NotificationLogOut]])
def get_notification_log(
    today: bool = Query(False, description="Filter to notifications sent today in user local timezone"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve up to 10 recent notifications for current user.
    """
    query = db.query(NotificationLog).filter(NotificationLog.user_id == current_user.user_id)

    if today:
        today_d, _ = get_user_today(current_user)
        # Filter for sent_at starting from today midnight UTC/local
        start_of_today = datetime.combine(today_d, time.min)
        query = query.filter(NotificationLog.sent_at >= start_of_today)

    logs = query.order_by(NotificationLog.sent_at.desc()).limit(10).all()
    return DataResponse(data=logs)


@router.get("", response_model=DataResponse[NotificationListResponse])
def list_notifications(
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Max notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List notifications for current user with unread filter and pagination.
    Returns list of items, unread_count, and total matching count.
    """
    base_query = db.query(NotificationLog).filter(NotificationLog.user_id == current_user.user_id)

    unread_count = (
        db.query(func.count(NotificationLog.id))
        .filter(
            NotificationLog.user_id == current_user.user_id,
            NotificationLog.read_at.is_(None),
        )
        .scalar()
        or 0
    )

    if unread_only:
        base_query = base_query.filter(NotificationLog.read_at.is_(None))

    total = base_query.count()
    items = (
        base_query
        .order_by(NotificationLog.sent_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return DataResponse(
        data=NotificationListResponse(
            items=items,
            unread_count=unread_count,
            total=total,
        )
    )


@router.get("/unread-count", response_model=DataResponse[NotificationUnreadCountResponse])
def get_unread_notification_count(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fast query for unread notification count for badge rendering.
    """
    unread_count = (
        db.query(func.count(NotificationLog.id))
        .filter(
            NotificationLog.user_id == current_user.user_id,
            NotificationLog.read_at.is_(None),
        )
        .scalar()
        or 0
    )
    return DataResponse(data=NotificationUnreadCountResponse(unread_count=unread_count))


@router.patch("/{notification_id}/read", response_model=DataResponse[NotificationMarkReadResponse])
def mark_notification_read(
    notification_id: int = Path(..., description="ID of notification to mark as read"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks a notification as read. Enforces user ownership.
    """
    notif = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == current_user.user_id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "notification_not_found", "message": f"Notification {notification_id} not found"},
        )

    now_utc = datetime.now(timezone.utc)
    notif.read_at = now_utc
    db.commit()

    return DataResponse(
        data=NotificationMarkReadResponse(
            id=notif.id,
            read_at=now_utc,
            ok=True,
        )
    )


@router.post("/read-all", response_model=DataResponse[NotificationMarkAllReadResponse])
def mark_all_notifications_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks all unread notifications as read for current user.
    """
    now_utc = datetime.now(timezone.utc)
    updated = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.user_id == current_user.user_id,
            NotificationLog.read_at.is_(None),
        )
        .update({"read_at": now_utc}, synchronize_session=False)
    )
    db.commit()

    return DataResponse(
        data=NotificationMarkAllReadResponse(
            marked_count=updated,
            ok=True,
        )
    )

