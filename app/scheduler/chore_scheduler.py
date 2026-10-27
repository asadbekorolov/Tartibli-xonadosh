import logging
from datetime import datetime
from aiogram import Bot
from aiogram.html import quote
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.bot.keyboards.chore_kb import get_chore_actions_kb
from app.config import get_settings
from app.database.session import async_session_maker
from app.models.chore import ChoreAssignment, ChoreStatus
from app.models.flat import Flat, FlatMember
from app.services.chore_service import ChoreService

logger = logging.getLogger(__name__)
settings = get_settings()


def get_current_tashkent_date():
    """Returns the current date in Asia/Tashkent timezone."""
    tz = pytz.timezone(settings.TIMEZONE)
    return datetime.now(tz).date()


async def run_daily_rotation_job(bot: Bot) -> None:
    """
    Midnight Job (00:01 Asia/Tashkent):
    Calculates cyclic round-robin assignments for all active flats for the new day.
    """
    logger.info("Starting midnight chore rotation across all flats...")
    today = get_current_tashkent_date()

    async with async_session_maker() as session:
        stmt = select(Flat).where(Flat.is_active.is_(True))
        result = await session.execute(stmt)
        flats = result.scalars().all()

        for flat in flats:
            try:
                await ChoreService.ensure_daily_assignments(
                    session=session,
                    flat_id=flat.id,
                    target_date=today
                )
            except Exception as e:
                logger.error(f"Error rotating chores for flat {flat.id}: {e}")
        await session.commit()
    logger.info("Midnight chore rotation completed.")


async def run_morning_notification_job(bot: Bot) -> None:
    """
    Morning Notification (08:30 Asia/Tashkent):
    Broadcasts the day's duty roster to all flatmates.
    """
    logger.info("Dispatching morning chore summary notifications...")
    today = get_current_tashkent_date()

    async with async_session_maker() as session:
        stmt = (
            select(Flat)
            .where(Flat.is_active.is_(True))
            .options(selectinload(Flat.members).selectinload(FlatMember.user))
        )
        result = await session.execute(stmt)
        flats = result.scalars().all()

        for flat in flats:
            try:
                assignments = await ChoreService.get_today_assignments(
                    session=session,
                    flat_id=flat.id,
                    target_date=today
                )
                if not assignments:
                    continue

                lines = [
                    f"🌅 <b>Xayrli tong! Bugungi navbatchilik ro'yxati ({today.strftime('%d.%m.%Y')}):</b>\n"
                ]
                for idx, a in enumerate(assignments, start=1):
                    safe_title = quote(a.chore.title)
                    safe_assignee = quote(a.assignee.display_name)
                    safe_time = quote(a.chore.execution_time)
                    lines.append(
                        f"{idx}. 📌 <b>{safe_title}</b> — {safe_assignee} (⏰ {safe_time})"
                    )
                lines.append("\nKuningiz barakali va unumli o'tsin! ✨")
                summary_text = "\n".join(lines)

                # Send morning summary to all active members of the flat
                for member in flat.members:
                    if member.is_active:
                        try:
                            await bot.send_message(
                                chat_id=member.user_id,
                                text=summary_text,
                                parse_mode="HTML"
                            )
                        except Exception as send_err:
                            logger.debug(f"Could not notify member {member.user_id}: {send_err}")
            except Exception as e:
                logger.error(f"Error broadcasting morning notification for flat {flat.id}: {e}")


async def run_evening_reminder_job(bot: Bot) -> None:
    """
    Evening Reminder (20:30 Asia/Tashkent):
    Sends urgent pings to assignees whose chores are still in PENDING status.
    """
    logger.info("Dispatching evening reminders for uncompleted chores...")
    today = get_current_tashkent_date()

    async with async_session_maker() as session:
        stmt = (
            select(ChoreAssignment)
            .where(
                ChoreAssignment.due_date == today,
                ChoreAssignment.status == ChoreStatus.PENDING
            )
            .options(
                selectinload(ChoreAssignment.chore),
                selectinload(ChoreAssignment.assignee)
            )
        )
        result = await session.execute(stmt)
        pending_assignments = result.scalars().all()

        for a in pending_assignments:
            try:
                safe_name = quote(a.assignee.first_name)
                safe_title = quote(a.chore.title)
                safe_time = quote(a.chore.execution_time)
                safe_desc = quote(a.chore.description or "Izoh yo'q")
                text = (
                    "🌙 <b>Kechki eslatma!</b>\n\n"
                    f"Salom, <b>{safe_name}</b>! Bugungi navbatchilik vazifangiz hali yakunlanmagan:\n\n"
                    f"📌 <b>Vazifa:</b> {safe_title}\n"
                    f"⏰ <b>Belgilangan vaqt:</b> {safe_time}\n"
                    f"📋 <b>Izoh:</b> {safe_desc}\n\n"
                    "Iltimos, vazifani bajargach, quyidagi tugma orqali tasdiqlang:"
                )
                await bot.send_message(
                    chat_id=a.assignee_id,
                    text=text,
                    reply_markup=get_chore_actions_kb(a.id, a.status),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not send evening reminder to user {a.assignee_id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Configures and returns the AsyncIOScheduler instance with Asia/Tashkent cron triggers.
    """
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # 1. Midnight job: Calculates and generates assignments for the upcoming day (00:01)
    scheduler.add_job(
        run_daily_rotation_job,
        trigger=CronTrigger(hour=0, minute=1, timezone=tz),
        args=[bot],
        id="daily_chore_rotation",
        replace_existing=True,
    )

    # 2. Morning notification (08:30 Asia/Tashkent): Details assigned flatmates for each chore
    scheduler.add_job(
        run_morning_notification_job,
        trigger=CronTrigger(hour=8, minute=30, timezone=tz),
        args=[bot],
        id="morning_chore_notification",
        replace_existing=True,
    )

    # 3. Evening reminder (20:30 Asia/Tashkent): Targets assignees with uncompleted (PENDING) chores
    scheduler.add_job(
        run_evening_reminder_job,
        trigger=CronTrigger(hour=20, minute=30, timezone=tz),
        args=[bot],
        id="evening_chore_reminder",
        replace_existing=True,
    )

    return scheduler
