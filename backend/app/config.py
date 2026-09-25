import os
from pydantic import model_validator
from pydantic_settings import BaseSettings

DEFAULT_DEV_SECRET = "syncshift-dev-secret-key-32-chars-minimum!!"


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
    JWT_SECRET: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET))
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET", DEFAULT_DEV_SECRET))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # OAuth Settings
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID", None)
    MICROSOFT_CLIENT_ID: str | None = os.getenv("MICROSOFT_CLIENT_ID", None)
    MICROSOFT_CLIENT_SECRET: str | None = os.getenv("MICROSOFT_CLIENT_SECRET", None)
    MICROSOFT_TENANT_ID: str = os.getenv("MICROSOFT_TENANT_ID", "common")

    # Bot Protection / CAPTCHA (Cloudflare Turnstile)
    CAPTCHA_SECRET_KEY: str | None = os.getenv("CAPTCHA_SECRET_KEY", None)
    CAPTCHA_ENFORCE: bool = os.getenv("CAPTCHA_ENFORCE", "false").lower() in ("true", "1", "yes")

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
        o.strip().rstrip("/")
        for o in (os.getenv("ALLOWED_ORIGINS") or os.getenv("BACKEND_CORS_ORIGINS", "")).split(",")
        if o.strip() and o.strip() != "*"
    ] or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Redis & Distributed Rate Limiter
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    REDIS_SOCKET_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "2.0"))
    REDIS_CONNECT_TIMEOUT: float = float(os.getenv("REDIS_CONNECT_TIMEOUT", "2.0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_FAIL_CLOSED_ALL: bool = os.getenv("RATE_LIMIT_FAIL_CLOSED_ALL", "false").lower() in ("true", "1", "yes")
    TRUSTED_PROXIES: str = os.getenv(
        "TRUSTED_PROXIES",
        "127.0.0.1,::1,testclient,localhost,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        # Synchronize secrets if one is configured securely and the other has the dev fallback
        if (not self.SECRET_KEY or self.SECRET_KEY == DEFAULT_DEV_SECRET) and (self.JWT_SECRET and self.JWT_SECRET != DEFAULT_DEV_SECRET):
            self.SECRET_KEY = self.JWT_SECRET
        elif (not self.JWT_SECRET or self.JWT_SECRET == DEFAULT_DEV_SECRET) and (self.SECRET_KEY and self.SECRET_KEY != DEFAULT_DEV_SECRET):
            self.JWT_SECRET = self.SECRET_KEY

        if (self.ENV or "").strip().lower() == "production":
            jwt_sec = (self.JWT_SECRET or "").strip()
            if not jwt_sec or jwt_sec == DEFAULT_DEV_SECRET or len(jwt_sec) < 32:
                raise RuntimeError(
                    "JWT_SECRET must be set to a unique value >= 32 characters when ENV=production. "
                    "Refusing to start with an insecure default secret."
                )

            sec_key = (self.SECRET_KEY or "").strip()
            if not sec_key or sec_key == DEFAULT_DEV_SECRET or len(sec_key) < 32:
                raise RuntimeError(
                    "SECRET_KEY must be set to a unique value >= 32 characters when ENV=production. "
                    "Refusing to start with an insecure default secret."
                )

        return self

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
