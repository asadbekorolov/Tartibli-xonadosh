from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rule import FlatRule


class RuleRepository:
    @staticmethod
    async def get_flat_rules(session: AsyncSession, flat_id: int) -> List[FlatRule]:
        stmt = (
            select(FlatRule)
            .where(FlatRule.flat_id == flat_id)
            .order_by(FlatRule.order_num.asc(), FlatRule.id.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, rule_id: int) -> Optional[FlatRule]:
        stmt = select(FlatRule).where(FlatRule.id == rule_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_rule(
        session: AsyncSession,
        flat_id: int,
        title: str,
        content: str,
        order_num: Optional[int] = None,
    ) -> FlatRule:
        if order_num is None:
            max_order_stmt = select(func.coalesce(func.max(FlatRule.order_num), 0)).where(
                FlatRule.flat_id == flat_id
            )
            res = await session.execute(max_order_stmt)
            order_num = int(res.scalar() or 0) + 1

        rule = FlatRule(
            flat_id=flat_id,
            title=title.strip(),
            content=content.strip(),
            order_num=order_num,
        )
        session.add(rule)
        await session.flush()
        return rule

    @staticmethod
    async def delete_rule(session: AsyncSession, rule_id: int, flat_id: int) -> bool:
        stmt = select(FlatRule).where(FlatRule.id == rule_id, FlatRule.flat_id == flat_id)
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule:
            await session.delete(rule)
            await session.flush()
            return True
        return False
