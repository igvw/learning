from .auth import router as auth_router
from .authoring import router as authoring_router
from .catalog import router as catalog_router
from .imports import router as imports_router
from .moderation import router as moderation_router
from .quiz import router as quiz_router
from .stats import router as stats_router
from .system import router as system_router


ALL_ROUTERS = (
    system_router,
    auth_router,
    catalog_router,
    moderation_router,
    quiz_router,
    stats_router,
    authoring_router,
    imports_router,
)
