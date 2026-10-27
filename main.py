import asyncio
import logging
import sys
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.bot.dispatcher import create_dispatcher
from app.config import get_settings
from app.database.session import close_db, init_db
from app.scheduler.chore_scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    logger.info("Starting 'Talabalar Kvartira Boshqaruvi' Telegram Bot...")

    # 1. Initialize database schema
    logger.info("Initializing database schema...")
    try:
        await init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")
        # Note: In production with Docker, postgres service healthcheck ensures availability.

    # 2. Initialize Bot instance
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    # 3. Create Dispatcher with FSM and Routers
    dp = create_dispatcher()

    # 4. Start APScheduler for automated chore reminders
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Chore duty rotation and reminder scheduler started.")

    # 5. Launch Polling
    try:
        logger.info("Bot polling started. Listening for updates...")
        # Drop pending updates to avoid processing obsolete messages on startup
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        logger.info("Shutting down bot and cleaning up resources...")
        scheduler.shutdown(wait=False)
        await close_db()
        await bot.session.close()
        logger.info("Application stopped gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated by user.")
