from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    auth_router,
    blocks_router,
    conflicts_router,
    courses_router,
    file_import_router,
    import_router,
    today_router,
    week_router,
    dashboard_router,
    tasks_router,
    notifications_router,
    debug_router,
    analytics_router,
    audit_logs_router,
    privacy_router,
    assistant_router,
    institutions_router,
    students_router,
    timetables_router,
    student_planning_router,
    university_analytics_router,
)
from app.services.rate_limiter import close_redis_connection, is_redis_available
from app.services.reminders import start_reminder_scheduler, stop_reminder_scheduler

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


EXPECTED_ALEMBIC_HEAD = "0019"


def check_db_migrated() -> None:
    """Verify that Alembic migrations have been applied up to the expected head revision.

    Raises RuntimeError if alembic_version table is missing or unmigrated.
    """
    if settings.ENV == "test":
        return

    from sqlalchemy import inspect, text
    from app.database import engine

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "alembic_version" not in tables:
        raise RuntimeError(
            "Database schema has not been initialized. Table 'alembic_version' is missing.\n"
            "Please run 'alembic upgrade head' before starting the application."
        )
    with engine.connect() as conn:
        current_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if not current_rev:
            raise RuntimeError(
                "No migration revision found in 'alembic_version'.\n"
                "Please run 'alembic upgrade head' before starting the application."
            )
        if current_rev != EXPECTED_ALEMBIC_HEAD:
            raise RuntimeError(
                f"Database migration mismatch: found revision '{current_rev}', expected '{EXPECTED_ALEMBIC_HEAD}'.\n"
                "Please run 'alembic upgrade head' before starting the application."
            )
    print(f"Database schema verified at revision: {current_rev}")


@app.on_event("startup")
def on_startup():
    print("Connected to DB:", settings.DATABASE_URL[:20])
    check_db_migrated()
    start_reminder_scheduler()
    redis_status = "Available" if is_redis_available() else "Unavailable (fallback mode active)"
    print(f"Distributed Rate Limiter Redis: {redis_status}")


@app.on_event("shutdown")
def on_shutdown():
    stop_reminder_scheduler()
    close_redis_connection()



# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
    }
    if origin:
        if (
            "*" in settings.BACKEND_CORS_ORIGINS
            or origin in settings.BACKEND_CORS_ORIGINS
            or "localhost" in origin
            or "127.0.0.1" in origin
        ):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
    return headers


# ---------------------------------------------------------------------------
# Error Handling: Enforces Rule 1 & Rule 4 format { error: { code, message } }
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Formats Pydantic / FastAPI validation errors into:
    { "error": { "code": "validation_error", "message": "..." } }
    """
    errors = exc.errors()
    # Build a clean user-friendly summary
    error_messages = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_messages.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "; ".join(error_messages) if error_messages else "Request validation failed",
            }
        },
        headers=_cors_headers(request),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Formats HTTPExceptions into:
    { "error": { "code": "...", "message": "..." } }
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        payload = exc.detail
    else:
        payload = {
            "code": "http_error",
            "message": str(exc.detail),
        }

    headers = _cors_headers(request)
    if exc.headers:
        headers.update(exc.headers)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": payload},
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all 500 error handler.
    """
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected internal server error occurred",
            }
        },
        headers=_cors_headers(request),
    )


# ---------------------------------------------------------------------------
# Security Response Headers Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        import traceback
        traceback.print_exc()
        headers = _cors_headers(request)
        headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        })
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected internal server error occurred",
                }
            },
            headers=headers,
        )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# ---------------------------------------------------------------------------
# Mount Routers under Base URL: /api/v1/
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(courses_router, prefix=settings.API_V1_STR)
app.include_router(blocks_router, prefix=settings.API_V1_STR)
app.include_router(conflicts_router, prefix=settings.API_V1_STR)
app.include_router(week_router, prefix=settings.API_V1_STR)
app.include_router(today_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(tasks_router, prefix=settings.API_V1_STR)
app.include_router(import_router, prefix=settings.API_V1_STR)
app.include_router(file_import_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(debug_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_logs_router, prefix=settings.API_V1_STR)
app.include_router(privacy_router, prefix=settings.API_V1_STR)
app.include_router(assistant_router, prefix=settings.API_V1_STR)
app.include_router(institutions_router, prefix=settings.API_V1_STR)
app.include_router(students_router, prefix=settings.API_V1_STR)
app.include_router(timetables_router, prefix=settings.API_V1_STR)
app.include_router(student_planning_router, prefix=settings.API_V1_STR)
app.include_router(university_analytics_router, prefix=settings.API_V1_STR)



@app.get("/health", tags=["Health"])
def health_check():
    """Service health probe."""
    return {"status": "ok", "service": settings.PROJECT_NAME}
