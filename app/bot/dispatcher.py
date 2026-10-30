import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from app.bot.handlers import (
    admin_router,
    chores_router,
    common_router,
    expenses_router,
    onboarding_router,
)
from app.bot.middlewares import AuthMiddleware, DbSessionMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_dispatcher() -> Dispatcher:
    """
    Constructs and configures the main Aiogram 3 Dispatcher with FSM storage,
    middlewares, and hierarchical handler routers.
    """
    # 1. Setup FSM Storage (Redis with graceful fallback to in-memory)
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        storage = RedisStorage(redis=redis_client)
        logger.info("Aiogram FSM configured with RedisStorage.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}. Falling back to MemoryStorage.")
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # 2. Register global middlewares (executed for every update/message/callback)
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AuthMiddleware())

    # 3. Include handler routers
    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(onboarding_router)
    dp.include_router(chores_router)
    dp.include_router(expenses_router)

    return dp
