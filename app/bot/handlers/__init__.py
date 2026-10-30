from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.chores import router as chores_router
from app.bot.handlers.common import router as common_router
from app.bot.handlers.expenses import router as expenses_router
from app.bot.handlers.onboarding import router as onboarding_router

__all__ = [
    "common_router",
    "onboarding_router",
    "chores_router",
    "expenses_router",
    "admin_router",
]
