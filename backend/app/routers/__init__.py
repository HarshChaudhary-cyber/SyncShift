from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.blocks import router as blocks_router
from app.routers.conflicts import router as conflicts_router
from app.routers.week import router as week_router
from app.routers.import_ics import router as import_router

__all__ = [
    "auth_router",
    "courses_router",
    "blocks_router",
    "conflicts_router",
    "week_router",
    "import_router",
]
