import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.config import get_settings
from bot.database.base import async_session_maker
from bot.database.models import Chore, Flat, User
from bot.keyboards.inline import get_chore_action_kb

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_morning_chore_reminders(bot: Bot) -> None:
    """
    Daily Morning Job (08:00 Asia/Tashkent):
    Iterates all active chores across flats and sends duty reminders to current assignees.
    """
    logger.info("Executing 08:00 AM morning chore reminder job...")
    async with async_session_maker() as session:
        stmt = (
            select(Chore)
            .options(selectinload(Chore.current_assignee), selectinload(Chore.flat))
        )
        result = await session.execute(stmt)
        chores = result.scalars().all()

        for chore in chores:
            if not chore.current_assignee_id or not chore.current_assignee:
                continue

            try:
                text = (
                    "🌅 **Xayrli tong! Bugungi navbatchilik eslatmasi:**\n\n"
                    f"🏠 **Kvartira:** {chore.flat.name}\n"
                    f"📌 **Vazifa:** {chore.title}\n"
                    f"👤 **Mas'ul:** {chore.current_assignee.full_name}\n\n"
                    "Iltimos, vazifani bajarganingizdan so'ng quyidagi tugma orqali tasdiqlang:"
                )
                await bot.send_message(
                    chat_id=chore.current_assignee_id,
                    text=text,
                    reply_markup=get_chore_action_kb(chore.id),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(
                    f"Could not send reminder to assignee {chore.current_assignee_id} for chore {chore.id}: {e}"
                )


async def check_and_balance_chore_assignments(bot: Bot) -> None:
    """
    Midnight Job (00:01 Asia/Tashkent):
    Ensures all chores have a valid current assignee from the flat's active member list.
    """
    logger.info("Verifying chore assignments integrity...")
    async with async_session_maker() as session:
        stmt = select(Flat).options(selectinload(Flat.members), selectinload(Flat.chores))
        result = await session.execute(stmt)
        flats = result.scalars().all()

        for flat in flats:
            if not flat.members:
                continue
            member_ids = [m.id for m in flat.members]
            for chore in flat.chores:
                if chore.current_assignee_id not in member_ids:
                    chore.current_assignee_id = member_ids[0]
                    chore.status = "PENDING"
        await session.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configures APScheduler with Asia/Tashkent timezone."""
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # 1. Daily morning reminder at 08:00 AM (Asia/Tashkent)
    scheduler.add_job(
        send_morning_chore_reminders,
        trigger=CronTrigger(hour=8, minute=0, timezone=tz),
        args=[bot],
        id="morning_chore_reminders",
        replace_existing=True,
    )

    # 2. Daily midnight assignment check at 00:01 AM (Asia/Tashkent)
    scheduler.add_job(
        check_and_balance_chore_assignments,
        trigger=CronTrigger(hour=0, minute=1, timezone=tz),
        args=[bot],
        id="midnight_chore_check",
        replace_existing=True,
    )

    return scheduler
