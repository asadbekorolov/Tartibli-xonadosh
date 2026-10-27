from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.flat_repo import FlatRepository
from app.repositories.user_repo import UserRepository


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
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        telegram_user = None
        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

        if telegram_user:
            # Upsert user record
            current_user = await UserRepository.upsert(
                session=session,
                user_id=telegram_user.id,
                first_name=telegram_user.first_name,
                username=telegram_user.username,
                last_name=telegram_user.last_name,
            )
            data["current_user"] = current_user

            # Retrieve active flat if user belongs to one
            current_flat = await FlatRepository.get_user_active_flat(
                session=session,
                user_id=telegram_user.id
            )
            data["current_flat"] = current_flat
        else:
            data["current_user"] = None
            data["current_flat"] = None

        return await handler(event, data)
