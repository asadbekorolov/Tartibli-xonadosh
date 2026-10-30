from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.flat import Flat, FlatMember, FlatRole, FlatTemplateType


class FlatRepository:
    @staticmethod
    async def create_flat(
        session: AsyncSession,
        name: str,
        created_by_id: int,
        invite_code: str,
        address: Optional[str] = None,
        max_members: int = 10,
        template_type: FlatTemplateType = FlatTemplateType.LARGE_FLAT,
    ) -> Flat:
        flat = Flat(
            name=name,
            created_by_id=created_by_id,
            invite_code=invite_code,
            address=address,
            max_members=max_members,
            template_type=template_type,
            is_active=True
        )
        session.add(flat)
        await session.flush()

        # Add creator as ADMIN member
        admin_member = FlatMember(
            flat_id=flat.id,
            user_id=created_by_id,
            role=FlatRole.ADMIN,
            is_active=True
        )
        session.add(admin_member)
        await session.flush()
        return flat

    @staticmethod
    async def get_by_id(session: AsyncSession, flat_id: int) -> Optional[Flat]:
        stmt = (
            select(Flat)
            .where(Flat.id == flat_id)
            .options(selectinload(Flat.members).selectinload(FlatMember.user))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_invite_code(session: AsyncSession, invite_code: str) -> Optional[Flat]:
        stmt = (
            select(Flat)
            .where(Flat.invite_code == invite_code, Flat.is_active.is_(True))
            .options(selectinload(Flat.members).selectinload(FlatMember.user))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_active_flat(session: AsyncSession, user_id: int) -> Optional[Flat]:
        stmt = (
            select(Flat)
            .join(FlatMember, FlatMember.flat_id == Flat.id)
            .where(
                FlatMember.user_id == user_id,
                FlatMember.is_active.is_(True),
                Flat.is_active.is_(True)
            )
            .options(selectinload(Flat.members).selectinload(FlatMember.user))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_membership(
        session: AsyncSession, flat_id: int, user_id: int
    ) -> Optional[FlatMember]:
        stmt = select(FlatMember).where(
            FlatMember.flat_id == flat_id,
            FlatMember.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def add_member(
        session: AsyncSession,
        flat_id: int,
        user_id: int,
        role: FlatRole = FlatRole.MEMBER
    ) -> FlatMember:
        existing = await FlatRepository.get_membership(session, flat_id, user_id)
        if existing:
            existing.is_active = True
            existing.role = role
            return existing

        member = FlatMember(
            flat_id=flat_id,
            user_id=user_id,
            role=role,
            is_active=True
        )
        session.add(member)
        await session.flush()
        return member

    @staticmethod
    async def get_members(session: AsyncSession, flat_id: int) -> List[FlatMember]:
        stmt = (
            select(FlatMember)
            .where(FlatMember.flat_id == flat_id, FlatMember.is_active.is_(True))
            .options(selectinload(FlatMember.user))
            .order_by(FlatMember.id.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_quiet_hours(
        session: AsyncSession, flat_id: int, quiet_hours_start: str
    ) -> Optional[Flat]:
        stmt = select(Flat).where(Flat.id == flat_id)
        result = await session.execute(stmt)
        flat = result.scalar_one_or_none()
        if flat:
            flat.quiet_hours_start = quiet_hours_start
            await session.flush()
        return flat
