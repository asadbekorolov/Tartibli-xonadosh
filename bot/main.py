import asyncio
import logging
import sys
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import TelegramObject
from redis.asyncio import Redis
from bot.config import get_settings
from bot.database.base import async_session_maker, close_engine, init_models
from bot.handlers import (
    chores_router,
    expenses_router,
    flat_router,
    start_router,
)
from bot.services.scheduler import setup_scheduler

# Setup unified logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("tartibli_bot")
settings = get_settings()


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware injecting an asynchronous SQLAlchemy session into every update handler.
    Automatically commits on success or rolls back if an unhandled exception occurs.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


async def main() -> None:
    logger.info("Starting 'Tartibli Xonadosh' 24/7 Telegram Bot...")

    # 1. Initialize Database Schema
    logger.info("Initializing database schema and tables...")
    try:
        await init_models()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")

    # 2. Setup Aiogram Bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    # 3. Setup FSM Storage (Redis with graceful fallback to In-Memory)
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        storage = RedisStorage(redis=redis_client)
        logger.info("FSM Storage: RedisStorage connected.")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using MemoryStorage fallback.")
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # 4. Attach Session Middleware
    dp.update.middleware(DbSessionMiddleware())

    # 5. Register Handler Routers
    dp.include_router(start_router)
    dp.include_router(flat_router)
    dp.include_router(chores_router)
    dp.include_router(expenses_router)

    # 6. Start APScheduler (08:00 AM Morning Reminders in Asia/Tashkent)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info(f"APScheduler active. Timezone: {settings.TIMEZONE} (08:00 AM daily duty alarms).")

    # 7. Start Polling with clean lifecycle
    try:
        logger.info("Bot polling initiated. Listening for user updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Stopping bot and releasing all resources...")
        scheduler.shutdown(wait=False)
        await close_engine()
        await bot.session.close()
        logger.info("Shutdown completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated by user.")
