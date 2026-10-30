import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.flat_repo import FlatRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Middleware ensuring the Telegram user is persisted in the database
    and injecting their active flat context into handler data.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session: Optional[AsyncSession] = data.get("session")

        # 1. Reliably resolve telegram user from data or event
        telegram_user: Optional[TgUser] = data.get("event_from_user")
        if not telegram_user:
            if isinstance(event, Message):
                telegram_user = event.from_user
            elif isinstance(event, CallbackQuery):
                telegram_user = event.from_user
            elif isinstance(event, Update):
                if event.message:
                    telegram_user = event.message.from_user
                elif event.callback_query:
                    telegram_user = event.callback_query.from_user
                elif getattr(event, "event", None) and hasattr(event.event, "from_user"):
                    telegram_user = event.event.from_user
            elif hasattr(event, "from_user"):
                telegram_user = getattr(event, "from_user", None)

        current_user: Optional[User] = None
        current_flat = None

        if telegram_user:
            if session:
                try:
                    # Upsert user record in database
                    current_user = await UserRepository.upsert(
                        session=session,
                        user_id=telegram_user.id,
                        first_name=telegram_user.first_name,
                        username=telegram_user.username,
                        last_name=telegram_user.last_name,
                    )
                    await session.flush()

                    # Retrieve active flat if user belongs to one
                    current_flat = await FlatRepository.get_user_active_flat(
                        session=session,
                        user_id=telegram_user.id
                    )
                except Exception as e:
                    logger.error(f"Error in AuthMiddleware persisting user {telegram_user.id}: {e}", exc_info=True)

            # Robust fallback object if DB upsert was skipped or failed
            if not current_user:
                current_user = User(
                    id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name or "Foydalanuvchi",
                    last_name=telegram_user.last_name,
                    is_active=True
                )

        data["current_user"] = current_user
        data["current_flat"] = current_flat

        return await handler(event, data)
