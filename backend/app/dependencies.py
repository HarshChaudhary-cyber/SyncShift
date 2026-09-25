from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(
        self,
        user_id: int,
        email: str,
        timezone: str = "Europe/London",
        weekly_limit: float = 20.0,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        currency: str = "INR",
        language: str = "en",
        theme: str = "dark",
        minimum_transition_minutes: int = 15,
        oauth_provider: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.timezone = timezone
        self.weekly_limit = weekly_limit
        self.weekly_work_hour_limit = weekly_limit
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.currency = currency
        self.language = language
        self.theme = theme
        self.minimum_transition_minutes = minimum_transition_minutes
        self.oauth_provider = oauth_provider
        self.deleted_at = deleted_at


    def __int__(self) -> int:
        return self.user_id

    def __repr__(self) -> str:
        return f"<CurrentUser id={self.user_id} email={self.email}>"


def create_access_token(user_id: int, email: str) -> str:
    """Generate a signed JWT token containing user_id, email, exp (7 days), and iat."""
    now = datetime.now(dt_timezone.utc)
    payload = {
        "user_id": user_id,
        "sub": str(user_id),
        "email": email,
        "exp": now + timedelta(days=7),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Validate JWT Bearer token and extract user information.
    Decodes token using settings.JWT_SECRET.
    Raises HTTP 401 if missing, invalid, expired, or user deleted.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id_val = payload.get("user_id") or payload.get("sub")
        if user_id_val is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorized", "message": "Token payload missing user identifier"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_val)
        email = payload.get("email", "")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_not_found", "message": "User not found"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "user_deleted", "message": "This account has been deleted"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return CurrentUser(
            user_id=user.id,
            email=user.email,
            timezone=user.timezone or "Europe/London",
            weekly_limit=float(user.weekly_work_hour_limit or 20.0),
            display_name=getattr(user, "display_name", None) or getattr(user, "name", None),
            avatar_url=getattr(user, "avatar_url", None),
            currency=getattr(user, "currency", "INR") or "INR",
            language=getattr(user, "language", "en") or "en",
            theme=getattr(user, "theme", "dark") or "dark",
            minimum_transition_minutes=int(getattr(user, "minimum_transition_minutes", 15) or 15),
            oauth_provider=getattr(user, "oauth_provider", None),
            deleted_at=getattr(user, "deleted_at", None),
        )


    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Token has expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Could not validate JWT credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )


class InstitutionContext:
    """Encapsulates the verified tenant institution, membership, and user context."""

    def __init__(self, institution, membership, user: CurrentUser):
        self.institution = institution
        self.membership = membership
        self.user = user

    @property
    def institution_id(self) -> int:
        return self.institution.id

    @property
    def role(self) -> str:
        return self.membership.role

    @property
    def user_id(self) -> int:
        return self.user.user_id

    def is_admin(self) -> bool:
        return self.membership.role in ("admin", "super_admin")

    def is_faculty_or_admin(self) -> bool:
        return self.membership.role in ("faculty", "professor", "admin", "super_admin")


def get_institution_context(
    institution_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstitutionContext:
    """
    Validate that the authenticated user belongs to the specified institution.
    Blocks unauthorized and cross-tenant access with 403 Forbidden.
    """
    from app.models.institution import Institution, InstitutionMembership

    institution = (
        db.query(Institution)
        .filter(
            Institution.id == institution_id,
            Institution.deleted_at.is_(None),
            Institution.is_active.is_(True),
        )
        .first()
    )
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "institution_not_found", "message": f"Institution {institution_id} not found or inactive"},
        )

    membership = (
        db.query(InstitutionMembership)
        .filter(
            InstitutionMembership.user_id == current_user.user_id,
            InstitutionMembership.institution_id == institution_id,
            InstitutionMembership.deleted_at.is_(None),
            InstitutionMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "unauthorized_institution_access",
                "message": "You do not have active membership in this institution",
            },
        )

    return InstitutionContext(institution=institution, membership=membership, user=current_user)


def require_institution_admin(
    context: InstitutionContext = Depends(get_institution_context),
) -> InstitutionContext:
    """
    Ensure the current user has 'admin' or 'super_admin' role in this institution.
    """
    if not context.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": f"Action requires administrator privileges. Your current role is '{context.role}'",
            },
        )
    return context


def require_institution_faculty_or_admin(
    context: InstitutionContext = Depends(get_institution_context),
) -> InstitutionContext:
    """
    Ensure the current user has 'faculty', 'professor', 'admin', or 'super_admin' role in this institution.
    """
    if not context.is_faculty_or_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": f"Action requires faculty or administrator privileges. Your current role is '{context.role}'",
            },
        )
    return context

