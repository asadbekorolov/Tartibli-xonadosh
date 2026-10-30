from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
        """Fetch user by Telegram ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(
        session: AsyncSession,
        user_id: int,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> User:
        """Create or update user details upon bot interaction."""
        safe_first_name = first_name or "Foydalanuvchi"
        user = await UserRepository.get_by_id(session, user_id)
        if user:
            user.first_name = safe_first_name
            user.username = username
            user.last_name = last_name
            if phone_number:
                user.phone_number = phone_number
        else:
            user = User(
                id=user_id,
                username=username,
                first_name=safe_first_name,
                last_name=last_name,
                phone_number=phone_number,
                is_active=True
            )
            session.add(user)
        await session.flush()
        return user
