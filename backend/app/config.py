import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SyncShift API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = os.getenv("ENV", "development")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./syncshift.db",
    )

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "syncshift-dev-secret-key-32-chars-minimum!!"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "syncshift-dev-secret-key-32-chars-minimum!!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # OAuth Settings
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
    FACEBOOK_APP_ID: str | None = os.getenv("FACEBOOK_APP_ID", None)
    FACEBOOK_APP_SECRET: str | None = os.getenv("FACEBOOK_APP_SECRET", None)
    APPLE_KEY_ID: str | None = os.getenv("APPLE_KEY_ID", None)
    APPLE_TEAM_ID: str | None = os.getenv("APPLE_TEAM_ID", None)
    APPLE_BUNDLE_ID: str | None = os.getenv("APPLE_BUNDLE_ID", None)

    # AI Settings
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini")

    # Push Notifications & VAPID
    VAPID_PUBLIC_KEY: str | None = os.getenv("VAPID_PUBLIC_KEY", None)
    VAPID_PRIVATE_KEY: str | None = os.getenv("VAPID_PRIVATE_KEY", None)
    VAPID_SUBJECT: str = os.getenv("VAPID_SUBJECT", "mailto:support@syncshift.app")

    # Email / SMTP Settings
    SMTP_HOST: str | None = os.getenv("SMTP_HOST", None)
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.getenv("SMTP_USER", None)
    SMTP_PASS: str | None = os.getenv("SMTP_PASS", None)
    SMTP_FROM: str = os.getenv("SMTP_FROM", "notifications@syncshift.app")

    # CORS

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
