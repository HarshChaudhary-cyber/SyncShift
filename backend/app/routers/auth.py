import re
import zoneinfo
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponseData,
    UserLogin,
    UserProfileData,
    UserRegister,
)
from app.schemas.common import DataResponse

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


def validate_iana_timezone(tz: str) -> None:
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
def register(body: UserRegister, db: Session = Depends(get_db)):
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
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(user_id=new_user.id, email=new_user.email)
    return DataResponse(
        data=AuthResponseData(
            user_id=new_user.id,
            email=new_user.email,
            token=token,
            timezone=new_user.timezone,
        )
    )


@router.post("/login", response_model=DataResponse[AuthResponseData])
def login(body: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user with email and password.
    Compares provided password against bcrypt hash in database.
    Returns JWT access token with 7-day expiration.
    """
    normalized_email = body.email.lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Invalid email or password",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, email=user.email)
    return DataResponse(
        data=AuthResponseData(
            user_id=user.id,
            email=user.email,
            timezone=user.timezone,
            token=token,
        )
    )


@router.get("/me", response_model=DataResponse[UserProfileData])
def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Fetch authenticated user profile details from validated JWT.
    """
    return DataResponse(
        data=UserProfileData(
            user_id=current_user.user_id,
            email=current_user.email,
            timezone=current_user.timezone,
            weekly_work_hour_limit=current_user.weekly_limit,
        )
    )

