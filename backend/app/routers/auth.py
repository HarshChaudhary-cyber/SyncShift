from datetime import datetime, timezone as dt_timezone
from typing import Optional
import re
import zoneinfo
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, create_access_token, get_current_user
from app.models.course import Course
from app.models.notification import NotificationPrefs
from app.models.study_task import StudyTask
from app.models.time_block import TimeBlock
from app.models.user import User
from app.schemas.auth import (
    AuthResponseData,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ExportDataResponse,
    MessageData,
    OAuthAppleRequest,
    OAuthFacebookRequest,
    OAuthGoogleRequest,
    UserLogin,
    UserProfileData,
    UserProfileUpdate,
    UserRegister,
)
from app.schemas.common import DataResponse
from app.services.audit import record_audit_log
from app.services.oauth_service import (
    verify_apple_id_token,
    verify_facebook_token,
    verify_google_id_token,
)
from app.services.rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Auth"])



def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_password",
                "message": "Password must be at least 8 characters long",
            },
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_password",
                "message": "Password must contain at least one uppercase letter",
            },
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_password",
                "message": "Password must contain at least one number",
            },
        )


def validate_iana_timezone(tz: Optional[str]) -> None:
    if tz is None or tz == "":
        return
    if tz not in zoneinfo.available_timezones():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "validation_error",
                "message": f"'{tz}' is not a valid IANA timezone string",
            },
        )


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


@router.post("/register", response_model=DataResponse[AuthResponseData])
def register(
    body: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(5, 60, "register")),
):
    """
    Register a new student user account in the database.
    Validates password complexity (8+ chars, 1 uppercase, 1 number),
    validates IANA timezone, verifies email uniqueness (409 on duplicate),
    hashes password with bcrypt, and returns JWT access token.
    """
    validate_password_strength(body.password)
    validate_iana_timezone(body.timezone)

    if body.weekly_work_hour_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "validation_error",
                "message": "weekly_work_hour_limit must be greater than 0",
            },
        )

    # Check if email already exists
    normalized_email = body.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "email_exists",
                "message": "Email already registered",
            },
        )

    hashed = hash_password(body.password)
    new_user = User(
        name=normalized_email.split("@")[0],
        email=normalized_email,
        password_hash=hashed,
        timezone=body.timezone,
        weekly_work_hour_limit=body.weekly_work_hour_limit,
        minimum_transition_minutes=body.minimum_transition_minutes if body.minimum_transition_minutes is not None else 15,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(user_id=new_user.id, email=new_user.email)
    record_audit_log(
        db=db,
        user_id=new_user.id,
        action="USER_REGISTERED",
        entity_type="user",
        entity_id=new_user.id,
        description="New student account registered",
        request=request,
    )

    return DataResponse(
        data=AuthResponseData(
            user_id=new_user.id,
            email=new_user.email,
            token=token,
            timezone=new_user.timezone,
            display_name=new_user.display_name or new_user.name,
            avatar_url=new_user.avatar_url,
        )
    )


@router.post("/login", response_model=DataResponse[AuthResponseData])
def login(
    body: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(10, 60, "login")),
):
    """
    Authenticate user with email and password.
    Compares provided password against bcrypt hash in database.
    Returns JWT access token with 7-day expiration.
    """
    normalized_email = body.email.lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        if user:
            record_audit_log(
                db=db,
                user_id=user.id,
                action="LOGIN_FAILED",
                entity_type="user",
                entity_id=user.id,
                description="Failed login attempt (incorrect credentials)",
                request=request,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Invalid email or password",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "user_deleted",
                "message": "This account has been deleted",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, email=user.email)
    record_audit_log(
        db=db,
        user_id=user.id,
        action="LOGIN_SUCCESS",
        entity_type="user",
        entity_id=user.id,
        description="Student successfully authenticated via password",
        request=request,
    )

    return DataResponse(
        data=AuthResponseData(
            user_id=user.id,
            email=user.email,
            timezone=user.timezone,
            token=token,
            display_name=user.display_name or user.name,
            avatar_url=user.avatar_url,
        )
    )


@router.get("/me", response_model=DataResponse[UserProfileData])
def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch authenticated user profile details from validated JWT and database.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    display_name = user.display_name or user.name or current_user.display_name
    avatar_url = user.avatar_url or current_user.avatar_url

    return DataResponse(
        data=UserProfileData(
            user_id=user.id,
            email=user.email,
            timezone=user.timezone,
            weekly_work_hour_limit=float(user.weekly_work_hour_limit or 20.0),
            display_name=display_name,
            avatar_url=avatar_url,
            currency=user.currency or "INR",
            language=user.language or "en",
            theme=user.theme or "dark",
            minimum_transition_minutes=int(getattr(user, "minimum_transition_minutes", 15) or 15),
            oauth_provider=user.oauth_provider,
            has_password=bool(user.password_hash),
            created_at=user.created_at,
        )
    )


@router.patch("/me", response_model=DataResponse[UserProfileData])
def update_current_user_profile(
    body: UserProfileUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update authenticated student profile details.
    Validates IANA timezone, weekly_work_hour_limit (0-168), and minimum_transition_minutes.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    if body.timezone is not None:
        validate_iana_timezone(body.timezone)
        user.timezone = body.timezone

    if body.display_name is not None:
        user.display_name = body.display_name.strip()
        user.name = body.display_name.strip()

    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url.strip() if body.avatar_url else None

    if body.weekly_work_hour_limit is not None:
        if body.weekly_work_hour_limit < 0.0 or body.weekly_work_hour_limit > 168.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "validation_error",
                    "message": "weekly_work_hour_limit must be between 0 and 168",
                },
            )
        user.weekly_work_hour_limit = body.weekly_work_hour_limit

    if body.currency is not None:
        user.currency = body.currency.strip()

    if body.language is not None:
        user.language = body.language.strip()

    if body.theme is not None:
        user.theme = body.theme.strip()

    if body.minimum_transition_minutes is not None:
        user.minimum_transition_minutes = body.minimum_transition_minutes

    db.commit()
    db.refresh(user)

    record_audit_log(
        db=db,
        user_id=user.id,
        action="SETTINGS_CHANGED",
        entity_type="user",
        entity_id=user.id,
        description="Student updated profile and preferences",
        request=request,
    )

    return DataResponse(
        data=UserProfileData(
            user_id=user.id,
            email=user.email,
            timezone=user.timezone,
            weekly_work_hour_limit=float(user.weekly_work_hour_limit or 20.0),
            display_name=user.display_name or user.name,
            avatar_url=user.avatar_url,
            currency=user.currency or "INR",
            language=user.language or "en",
            theme=user.theme or "dark",
            minimum_transition_minutes=int(getattr(user, "minimum_transition_minutes", 15) or 15),
            oauth_provider=user.oauth_provider,
            has_password=bool(user.password_hash),
            created_at=user.created_at,
        )
    )


@router.post("/change-password", response_model=DataResponse[MessageData])
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change password for authenticated student.
    Only available for email/password users (not OAuth-only users).
    Verifies current password, validates new password complexity (8+ chars, 1 uppercase, 1 digit),
    hashes new password with bcrypt, and updates in database.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "oauth_user",
                "message": "Password management is not available for OAuth accounts.",
            },
        )

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
                "message": "Incorrect current password",
            },
        )

    validate_password_strength(body.new_password)

    user.password_hash = hash_password(body.new_password)
    db.commit()

    record_audit_log(
        db=db,
        user_id=user.id,
        action="PASSWORD_CHANGED",
        entity_type="user",
        entity_id=user.id,
        description="Student changed their account password",
        request=request,
    )

    return DataResponse(data=MessageData(message="Password changed successfully"))



@router.post("/delete-account", response_model=DataResponse[MessageData])
def delete_account(
    body: DeleteAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete authenticated student account.
    Requires password verification for email users, or confirm: 'DELETE' for OAuth users.
    Sets user.deleted_at = now() and cascades soft-delete to time blocks and prefs.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "User not found"},
        )

    if user.password_hash:
        # Email/password user: accept either valid password or confirm == "DELETE"
        has_valid_pwd = body.password and verify_password(body.password, user.password_hash)
        has_valid_confirm = body.confirm and body.confirm.strip() == "DELETE"
        if not has_valid_pwd and not has_valid_confirm:
            if body.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "invalid_credentials",
                        "message": "Incorrect password",
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "confirmation_required",
                    "message": "Please enter your password or type DELETE to confirm.",
                },
            )
    else:
        # OAuth user: require confirm == "DELETE"
        if not body.confirm or body.confirm.strip() != "DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "confirmation_required",
                    "message": "Please type DELETE to confirm account deletion.",
                },
            )

    # Soft delete user
    now = datetime.now(dt_timezone.utc)
    user.deleted_at = now

    # Cascade soft delete: mark time blocks as deleted
    db.query(TimeBlock).filter(TimeBlock.user_id == user.id).update({TimeBlock.deleted: True})

    # Disable notification prefs
    prefs = db.query(NotificationPrefs).filter(NotificationPrefs.user_id == user.id).first()
    if prefs:
        prefs.push_enabled = False
        prefs.email_enabled = False

    db.commit()

    return DataResponse(data=MessageData(message="Account deleted"))


@router.get("/export", response_model=DataResponse[ExportDataResponse])
def export_user_data(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all schedule data for the authenticated student: profile, courses, time blocks, study tasks, and notification preferences.
    """
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
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
        "currency": user.currency or "INR",
        "language": user.language or "en",
        "theme": user.theme or "dark",
        "oauth_provider": user.oauth_provider,
        "created_at": str(user.created_at),
    }

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


@router.post("/oauth/google", response_model=DataResponse[AuthResponseData])
async def oauth_google(body: OAuthGoogleRequest, db: Session = Depends(get_db)):
    """
    Authenticate or register user using Google ID token.
    Extracts sub (google_id), email, name, and picture.
    """
    profile = await verify_google_id_token(body.id_token)
    google_id = profile["google_id"]
    email = profile["email"]
    display_name = profile.get("display_name")
    avatar_url = profile.get("avatar_url")

    # 1. Check if user with google_id exists
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_deleted", "message": "This account has been deleted"},
            )
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if display_name and not user.display_name:
            user.display_name = display_name
        db.commit()
        db.refresh(user)
    else:
        # 2. Check if email already registered with email/password or different provider
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "user_deleted", "message": "This account has been deleted"},
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "email_exists",
                    "message": "This email is already registered with email/password. Please sign in that way.",
                },
            )

        # 3. Create new OAuth user
        user = User(
            name=display_name or email.split("@")[0],
            display_name=display_name or email.split("@")[0],
            email=email,
            google_id=google_id,
            oauth_provider="google",
            avatar_url=avatar_url,
            password_hash=None,
            timezone="Europe/London",
            weekly_work_hour_limit=20.0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return DataResponse(
        data=AuthResponseData(
            user_id=user.id,
            email=user.email,
            token=token,
            timezone=user.timezone,
            display_name=user.display_name or user.name,
            avatar_url=user.avatar_url,
        )
    )


@router.post("/oauth/facebook", response_model=DataResponse[AuthResponseData])
async def oauth_facebook(body: OAuthFacebookRequest, db: Session = Depends(get_db)):
    """
    Authenticate or register user using Facebook access token and user_id.
    """
    profile = await verify_facebook_token(body.access_token, body.user_id)
    facebook_id = profile["facebook_id"]
    email = profile["email"]
    display_name = profile.get("display_name")
    avatar_url = profile.get("avatar_url")

    # 1. Check if user with facebook_id exists
    user = db.query(User).filter(User.facebook_id == facebook_id).first()
    if user:
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_deleted", "message": "This account has been deleted"},
            )
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        if display_name and not user.display_name:
            user.display_name = display_name
        db.commit()
        db.refresh(user)
    else:
        # 2. Check if email already registered
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "user_deleted", "message": "This account has been deleted"},
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "email_exists",
                    "message": "This email is already registered with email/password. Please sign in that way.",
                },
            )

        # 3. Create new OAuth user
        user = User(
            name=display_name or email.split("@")[0],
            display_name=display_name or email.split("@")[0],
            email=email,
            facebook_id=facebook_id,
            oauth_provider="facebook",
            avatar_url=avatar_url,
            password_hash=None,
            timezone="Europe/London",
            weekly_work_hour_limit=20.0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return DataResponse(
        data=AuthResponseData(
            user_id=user.id,
            email=user.email,
            token=token,
            timezone=user.timezone,
            display_name=user.display_name or user.name,
            avatar_url=user.avatar_url,
        )
    )


@router.post("/oauth/apple", response_model=DataResponse[AuthResponseData])
async def oauth_apple(body: OAuthAppleRequest, db: Session = Depends(get_db)):
    """
    Authenticate or register user using Apple ID token and optional display_name.
    """
    profile = await verify_apple_id_token(body.id_token, body.display_name)
    apple_id = profile["apple_id"]
    email = profile["email"]
    display_name = profile.get("display_name") or body.display_name

    # 1. Check if user with apple_id exists
    user = db.query(User).filter(User.apple_id == apple_id).first()
    if user:
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_deleted", "message": "This account has been deleted"},
            )
        if display_name and not user.display_name:
            user.display_name = display_name
            user.name = display_name
            db.commit()
            db.refresh(user)
    else:
        # 2. Check if email already registered
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "user_deleted", "message": "This account has been deleted"},
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "email_exists",
                    "message": "This email is already registered with email/password. Please sign in that way.",
                },
            )

        # 3. Create new OAuth user
        user = User(
            name=display_name or email.split("@")[0],
            display_name=display_name or email.split("@")[0],
            email=email,
            apple_id=apple_id,
            oauth_provider="apple",
            avatar_url=None,
            password_hash=None,
            timezone="Europe/London",
            weekly_work_hour_limit=20.0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return DataResponse(
        data=AuthResponseData(
            user_id=user.id,
            email=user.email,
            token=token,
            timezone=user.timezone,
            display_name=user.display_name or user.name,
            avatar_url=user.avatar_url,
        )
    )

