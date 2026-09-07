import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SyncShift API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

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
