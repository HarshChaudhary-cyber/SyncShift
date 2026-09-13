from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.blocks import router as blocks_router
from app.routers.conflicts import router as conflicts_router
from app.routers.week import router as week_router
from app.routers.import_ics import router as import_router
from app.routers.import_file import router as file_import_router
from app.routers.today import router as today_router
from app.routers.dashboard import router as dashboard_router
from app.routers.tasks import router as tasks_router
from app.routers.notifications import router as notifications_router
from app.routers.debug import router as debug_router
from app.routers.analytics import router as analytics_router
from app.routers.audit_logs import router as audit_logs_router
from app.routers.privacy import router as privacy_router
from app.routers.assistant import router as assistant_router
from app.routers.institutions import router as institutions_router
from app.routers.students import router as students_router
from app.routers.timetables import router as timetables_router
from app.routers.student_planning import router as student_planning_router

__all__ = [
    "auth_router",
    "courses_router",
    "blocks_router",
    "conflicts_router",
    "week_router",
    "import_router",
    "file_import_router",
    "today_router",
    "dashboard_router",
    "tasks_router",
    "notifications_router",
    "debug_router",
    "analytics_router",
    "audit_logs_router",
    "privacy_router",
    "assistant_router",
    "institutions_router",
    "students_router",
    "timetables_router",
    "student_planning_router",
]

