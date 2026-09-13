from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
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
)
from app.services.reminders import start_reminder_scheduler, stop_reminder_scheduler

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


@app.on_event("startup")
def on_startup():
    print("Connected to DB:", settings.DATABASE_URL[:20])
    init_db()
    start_reminder_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_reminder_scheduler()



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

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": payload},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all 500 error handler.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected internal server error occurred",
            }
        },
    )


# ---------------------------------------------------------------------------
# Security Response Headers Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
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



@app.get("/health", tags=["Health"])
def health_check():
    """Service health probe."""
    return {"status": "ok", "service": settings.PROJECT_NAME}
