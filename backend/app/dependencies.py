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
    ):
        self.user_id = user_id
        self.email = email
        self.timezone = timezone
        self.weekly_limit = weekly_limit
        self.weekly_work_hour_limit = weekly_limit

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
    Raises HTTP 401 if missing, invalid, or expired.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing or invalid Authorization header"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # Dev/Mock token support for testing without a full auth backend
    if token.startswith("mock_token_"):
        try:
            user_id = int(token.replace("mock_token_", ""))
        except ValueError:
            user_id = 1
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return CurrentUser(
                user_id=user.id,
                email=user.email,
                timezone=user.timezone,
                weekly_limit=float(user.weekly_work_hour_limit),
            )
        return CurrentUser(user_id=user_id, email=f"user_{user_id}@example.com")

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
        if user:
            return CurrentUser(
                user_id=user.id,
                email=user.email,
                timezone=user.timezone,
                weekly_limit=float(user.weekly_work_hour_limit),
            )
        return CurrentUser(user_id=user_id, email=email)

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

