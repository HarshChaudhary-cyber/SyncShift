"""
Reminder & Notification Engine for SyncShift.
Handles Web Push (VAPID), Email Reminders (SMTP with dev fallback),
Quiet Hours verification, Deduplication, and APScheduler background jobs.
"""
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import Any, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.notification import NotificationLog, NotificationPrefs, PushSubscription
from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.models.user import User
from app.services.schedule import get_user_zoneinfo
from app.services.timezone_helper import get_user_today
from app.store import get_all_blocks, get_user_tasks

logger = logging.getLogger("syncshift.reminders")
logging.basicConfig(level=logging.INFO)

scheduler: Optional[BackgroundScheduler] = None


# ---------------------------------------------------------------------------
# 1. Quiet Hours Logic
# ---------------------------------------------------------------------------

def parse_time_obj(val: Any) -> Optional[time]:
    if val is None or val == "":
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.split(":")
        if len(parts) >= 2:
            return time(int(parts[0]), int(parts[1]))
    return None


def is_in_quiet_hours(
    local_time: time,
    quiet_start: Optional[time | str],
    quiet_end: Optional[time | str],
) -> bool:
    """
    Checks if a local_time falls into the quiet hours interval.
    Handles overnight intervals (e.g. 22:00 -> 08:00) and same-day intervals.
    """
    start = parse_time_obj(quiet_start)
    end = parse_time_obj(quiet_end)

    if start is None or end is None:
        return False

    if start == end:
        return False

    if start < end:
        # e.g., 01:00 to 06:00
        return start <= local_time < end
    else:
        # Spans midnight, e.g., 22:00 to 08:00
        return local_time >= start or local_time < end


# ---------------------------------------------------------------------------
# 2. Web Push Notification Sender
# ---------------------------------------------------------------------------

def send_web_push(
    subscription: PushSubscription,
    payload: dict,
    db: Optional[Session] = None,
) -> bool:
    """
    Sends a push notification via pywebpush with VAPID keys.
    If the subscription has expired (HTTP 404 or 410), auto-deletes the row silently.
    """
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        logger.warning("VAPID keys not configured; cannot send push notification.")
        return False

    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
        )
        logger.info(f"Push notification sent successfully to endpoint {subscription.endpoint[:30]}...")
        return True
    except WebPushException as ex:
        # Check for expired/unregistered subscription (404 Not Found or 410 Gone)
        status_code = getattr(getattr(ex, "response", None), "status_code", None)
        if status_code in (404, 410):
            logger.info(f"Subscription expired ({status_code}). Silently removing endpoint {subscription.endpoint[:30]}...")
            if db:
                try:
                    db.delete(subscription)
                    db.commit()
                except Exception as del_err:
                    db.rollback()
                    logger.warning(f"Error removing expired subscription: {del_err}")
        else:
            logger.warning(f"WebPush failed for endpoint {subscription.endpoint[:30]}: {ex}")
        return False
    except Exception as ex:
        logger.warning(f"Unexpected error in send_web_push: {ex}")
        return False


# ---------------------------------------------------------------------------
# 3. Email Notification Sender (SMTP or Dev Log Fallback)
# ---------------------------------------------------------------------------

def send_email_alert(
    to_email: str,
    title: str,
    body: str,
    url: str = "/dashboard",
) -> bool:
    """
    Sends an email using SMTP if configured. Otherwise prints to console as dev fallback.
    """
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email

            text_content = f"{title}\n\n{body}\n\nView details: {url}"
            html_content = f"""
            <html>
              <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px;">
                <div style="max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
                  <h2 style="color: #818cf8; margin-top: 0;">⚡ SyncShift</h2>
                  <h3 style="color: #ffffff; font-size: 18px; margin-bottom: 8px;">{title}</h3>
                  <p style="color: #94a3b8; font-size: 15px; line-height: 1.5;">{body}</p>
                  <div style="margin-top: 24px;">
                    <a href="{url}" style="background-color: #6366f1; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block;">Open SyncShift</a>
                  </div>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
            logger.info(f"Email sent via SMTP to {to_email}: {title}")
            return True
        except Exception as ex:
            logger.warning(f"SMTP send failed: {ex}. Falling back to console log.")

    # Log-only fallback in dev mode
    print(f"\n=======================================================")
    print(f"[EMAIL WOULD SEND] To: {to_email}")
    print(f"Subject: {title}")
    print(f"Body: {body}")
    print(f"Action URL: {url}")
    print(f"=======================================================\n")
    return True


# ---------------------------------------------------------------------------
# 4. Central Dispatcher with Quiet Hours & Deduplication
# ---------------------------------------------------------------------------

def dispatch_notification(
    user_id: int,
    user_email: str,
    type_: str,
    title: str,
    body: str,
    url: str,
    db: Session,
    dedup_key: Optional[str] = None,
    check_quiet_hours: bool = True,
    user_timezone: Optional[str] = None,
) -> dict:
    """
    Sends push and/or email notifications based on user preferences.
    Respects quiet hours and dedup_key to prevent duplicate sends.
    """
    # 1. Deduplication check
    if dedup_key:
        existing = db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id,
            NotificationLog.dedup_key == dedup_key,
        ).first()
        if existing:
            return {"status": "skipped", "reason": "duplicate", "dedup_key": dedup_key}

    # 2. Get user preferences
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user_id).first()
    if not prefs:
        prefs = NotificationPrefs(user_id=user_id, push_enabled=True, email_enabled=False)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    # 3. Check quiet hours if requested (quiet hours apply to everything)
    if check_quiet_hours and prefs.quiet_hours_start and prefs.quiet_hours_end:
        tz = get_user_zoneinfo(user_timezone)
        now_local = datetime.now(tz).time()
        if is_in_quiet_hours(now_local, prefs.quiet_hours_start, prefs.quiet_hours_end):
            logger.info(f"User {user_id} is inside quiet hours ({prefs.quiet_hours_start}-{prefs.quiet_hours_end}). Skipping notification.")
            return {"status": "skipped", "reason": "quiet_hours"}

    push_sent = False
    email_sent = False

    # 4. Push notifications
    if prefs.push_enabled:
        subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        for sub in subs:
            success = send_web_push(sub, {"title": title, "body": body, "url": url}, db=db)
            if success:
                push_sent = True

        if push_sent or (len(subs) > 0 and not settings.VAPID_PUBLIC_KEY):
            # Record in notification_log
            log_entry = NotificationLog(
                user_id=user_id,
                type=type_,
                title=title,
                body=body,
                channel="push",
                dedup_key=dedup_key,
            )
            db.add(log_entry)
            db.commit()

    # 5. Email notifications
    if prefs.email_enabled and user_email:
        if send_email_alert(user_email, title, body, url):
            email_sent = True
            log_entry = NotificationLog(
                user_id=user_id,
                type=type_,
                title=title,
                body=body,
                channel="email",
                dedup_key=dedup_key if not push_sent else f"{dedup_key}_email",
            )
            db.add(log_entry)
            db.commit()

    return {
        "status": "sent" if (push_sent or email_sent) else "no_channels",
        "push": push_sent,
        "email": email_sent,
        "dedup_key": dedup_key,
    }


# ---------------------------------------------------------------------------
# 5. Real-time Conflict Alert Dispatcher
# ---------------------------------------------------------------------------

def notify_conflict_if_applicable(
    user_id: int,
    block_a_title: str,
    block_b_title: str,
    db: Session,
    block_a_id: int = 0,
    block_b_id: int = 0,
) -> None:
    """
    Called when a new schedule clash is created/updated.
    Dispatches real-time conflict alert if enabled in user preferences.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return

        prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user_id).first()
        if prefs and not prefs.conflict_alerts:
            return

        today_d, _ = get_user_today(user)
        min_id = min(block_a_id, block_b_id)
        max_id = max(block_a_id, block_b_id)
        dedup_key = f"{user_id}_{min_id}_{max_id}_{today_d.isoformat()}_conflict"

        title = "⚠️ Schedule Conflict Detected"
        body = f"⚠️ New conflict: {block_a_title} clashes with {block_b_title} — tap to fix"
        url = "/dashboard"

        dispatch_notification(
            user_id=user.id,
            user_email=user.email,
            type_="conflict",
            title=title,
            body=body,
            url=url,
            db=db,
            dedup_key=dedup_key,
            check_quiet_hours=True,
            user_timezone=user.timezone,
        )
    except Exception as ex:
        logger.warning(f"Error dispatching conflict notification: {ex}")


# ---------------------------------------------------------------------------
# 6. Scheduled Engine: Upcoming Block Reminders (Every Minute)
# ---------------------------------------------------------------------------

def check_upcoming_reminders():
    """
    Runs every minute:
    1. Loads users with push_enabled or email_enabled
    2. Computes "now" in user's timezone
    3. Skips if inside quiet hours
    4. Finds blocks starting in exactly X minutes from now (class X=30, shift X=60, study X=15 or custom)
    5. Deduplicates via notification_log
    6. Sends push / email and logs
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user.id).first()
            if not prefs:
                # Default prefs: push_enabled=True, email_enabled=False
                prefs = NotificationPrefs(
                    user_id=user.id,
                    push_enabled=True,
                    email_enabled=False,
                    class_reminder_min=30,
                    shift_reminder_min=60,
                    study_reminder_min=15,
                    deadline_reminder=True,
                    conflict_alerts=True,
                )
                db.add(prefs)
                db.commit()
                db.refresh(prefs)

            if not prefs.push_enabled and not prefs.email_enabled:
                continue

            tz = get_user_zoneinfo(user.timezone)
            now_local = datetime.now(tz)
            today_date = now_local.date()
            today_dow = (today_date.weekday() + 1) % 7  # 0=Sun..6=Sat

            # Skip if in quiet hours
            if prefs.quiet_hours_start and prefs.quiet_hours_end:
                if is_in_quiet_hours(now_local.time(), prefs.quiet_hours_start, prefs.quiet_hours_end):
                    continue

            # Fetch active blocks for user from both store and DB
            store_blocks = get_all_blocks(user_id=user.id, include_deleted=False)
            try:
                db_blocks = db.query(TimeBlock).filter(TimeBlock.user_id == user.id, TimeBlock.deleted == False).all()
            except Exception:
                db_blocks = []

            all_blocks = []
            seen_ids = set()
            for b in store_blocks:
                all_blocks.append(b)
                seen_ids.add(b.id)
            for b in db_blocks:
                if b.id not in seen_ids:
                    all_blocks.append(b)


            for b in all_blocks:
                b_type = str(getattr(b, "type", "class")).lower()
                if "class" in b_type:
                    reminder_min = prefs.class_reminder_min
                    type_label = "Class"
                elif "shift" in b_type:
                    reminder_min = prefs.shift_reminder_min
                    type_label = "Shift"
                elif "study" in b_type:
                    reminder_min = prefs.study_reminder_min
                    type_label = "Study session"
                else:
                    reminder_min = prefs.class_reminder_min
                    type_label = "Event"

                # Check if block occurs today
                is_recurring = getattr(b, "is_recurring", True)
                b_dow = getattr(b, "day_of_week", None)
                b_spec_date = getattr(b, "specific_date", None)
                eff_from = getattr(b, "effective_from", None)
                eff_until = getattr(b, "effective_until", None)

                applies_today = False
                if is_recurring:
                    if b_dow == today_dow:
                        if eff_from and isinstance(eff_from, (date, datetime)) and today_date < (eff_from if isinstance(eff_from, date) else eff_from.date()):
                            applies_today = False
                        elif eff_until and isinstance(eff_until, (date, datetime)) and today_date > (eff_until if isinstance(eff_until, date) else eff_until.date()):
                            applies_today = False
                        else:
                            applies_today = True
                else:
                    spec_d = b_spec_date.date() if isinstance(b_spec_date, datetime) else b_spec_date
                    if spec_d == today_date:
                        applies_today = True

                if not applies_today:
                    continue

                # Check start time match: block.start_time == now + X minutes (compare on same day)
                b_start = getattr(b, "start_time", None)
                start_time_obj = parse_time_obj(b_start)
                if not start_time_obj:
                    continue

                target_dt = now_local + timedelta(minutes=reminder_min)
                if target_dt.date() != today_date:
                    continue

                if start_time_obj.hour == target_dt.hour and start_time_obj.minute == target_dt.minute:
                    # Target match!
                    dedup_key = f"{user.id}_{b.id}_{today_date.isoformat()}_{b_type}"
                    formatted_start = f"{start_time_obj.hour:02d}:{start_time_obj.minute:02d}"
                    loc = getattr(b, "location", None)
                    loc_suffix = f" at {loc}" if loc else ""
                    title = f"{type_label} starting soon"
                    body = f"{b.title}{loc_suffix} at {formatted_start} (in {reminder_min} min)"
                    url = "/dashboard"

                    dispatch_notification(
                        user_id=user.id,
                        user_email=user.email,
                        type_=b_type,
                        title=title,
                        body=body,
                        url=url,
                        db=db,
                        dedup_key=dedup_key,
                        check_quiet_hours=True,
                        user_timezone=user.timezone,
                    )
    except Exception as ex:
        logger.error(f"Error in check_upcoming_reminders: {ex}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 7. Scheduled Engine: Deadline Reminders (Daily 08:00 local)
# ---------------------------------------------------------------------------

def check_deadline_reminders():
    """
    Checks study tasks with deadline == tomorrow.
    Dispatches at 08:00 user local time.
    """
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user.id).first()
            if not prefs or not prefs.deadline_reminder:
                continue

            if not prefs.push_enabled and not prefs.email_enabled:
                continue

            tz = get_user_zoneinfo(user.timezone)
            now_local = datetime.now(tz)

            # Only trigger at 08:00 local time
            if now_local.hour != 8 or now_local.minute != 0:
                continue

            # Skip if inside quiet hours
            if prefs.quiet_hours_start and prefs.quiet_hours_end:
                if is_in_quiet_hours(now_local.time(), prefs.quiet_hours_start, prefs.quiet_hours_end):
                    continue

            tomorrow = now_local.date() + timedelta(days=1)

            # Query store and DB for tasks
            store_tasks = get_user_tasks(user.id)
            try:
                db_tasks = db.query(StudyTask).filter(StudyTask.user_id == user.id).all()
            except Exception:
                db_tasks = []


            all_tasks = []
            seen_ids = set()
            for t in store_tasks:
                all_tasks.append(t)
                seen_ids.add(t.get("id"))
            for t in db_tasks:
                if t.id not in seen_ids:
                    all_tasks.append({
                        "id": t.id,
                        "title": t.title,
                        "deadline": t.deadline.isoformat() if isinstance(t.deadline, date) else str(t.deadline),
                        "status": t.status,
                    })

            for task in all_tasks:
                if str(task.get("status", "")).lower() == "done":
                    continue

                t_deadline = task.get("deadline")
                if isinstance(t_deadline, str):
                    try:
                        t_deadline = date.fromisoformat(t_deadline)
                    except Exception:
                        continue

                if t_deadline == tomorrow:
                    dedup_key = f"{user.id}_{task['id']}_{tomorrow.isoformat()}_deadline"
                    title = "Upcoming Assignment Deadline"
                    body = f"Due tomorrow: {task['title']}"
                    url = "/planner"

                    dispatch_notification(
                        user_id=user.id,
                        user_email=user.email,
                        type_="deadline",
                        title=title,
                        body=body,
                        url=url,
                        db=db,
                        dedup_key=dedup_key,
                        check_quiet_hours=True,
                        user_timezone=user.timezone,
                    )
    except Exception as ex:
        logger.error(f"Error in check_deadline_reminders: {ex}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. Scheduler Lifecycle
# ---------------------------------------------------------------------------

def start_reminder_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        return

    scheduler = BackgroundScheduler()
    # Run upcoming reminders check every minute
    scheduler.add_job(check_upcoming_reminders, "cron", second=0, id="upcoming_reminders_job")
    # Run deadline check every minute (inspects if user local time == 08:00)
    scheduler.add_job(check_deadline_reminders, "cron", second=0, id="deadline_reminders_job")
    scheduler.start()
    logger.info("APScheduler reminder engine started.")


def stop_reminder_scheduler():
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler reminder engine stopped.")
