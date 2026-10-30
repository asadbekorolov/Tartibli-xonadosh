from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.flat import Flat
from app.models.fund import FundTransaction, TransactionType


class FundRepository:
    @staticmethod
    async def create_transaction(
        session: AsyncSession,
        flat_id: int,
        user_id: int,
        tx_type: TransactionType,
        amount: Decimal,
        balance_after: Decimal,
        description: str,
    ) -> FundTransaction:
        tx = FundTransaction(
            flat_id=flat_id,
            user_id=user_id,
            tx_type=tx_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
        )
        session.add(tx)
        await session.flush()
        return tx

    @staticmethod
    async def get_recent_transactions(
        session: AsyncSession,
        flat_id: int,
        limit: int = 5,
    ) -> List[FundTransaction]:
        stmt = (
            select(FundTransaction)
            .where(FundTransaction.flat_id == flat_id)
            .options(selectinload(FundTransaction.user))
            .order_by(FundTransaction.created_at.desc(), FundTransaction.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_flat_balance(
        session: AsyncSession,
        flat_id: int,
        new_balance: Decimal,
    ) -> Optional[Flat]:
        stmt = select(Flat).where(Flat.id == flat_id)
        result = await session.execute(stmt)
        flat = result.scalar_one_or_none()
        if flat:
            flat.fund_balance = new_balance
            await session.flush()
        return flat

    @staticmethod
    async def get_totals(
        session: AsyncSession,
        flat_id: int,
    ) -> Tuple[Decimal, Decimal]:
        """Returns (total_income, total_expense)."""
        stmt_inc = (
            select(func.coalesce(func.sum(FundTransaction.amount), 0))
            .where(FundTransaction.flat_id == flat_id, FundTransaction.tx_type == TransactionType.INCOME)
        )
        stmt_exp = (
            select(func.coalesce(func.sum(FundTransaction.amount), 0))
            .where(FundTransaction.flat_id == flat_id, FundTransaction.tx_type == TransactionType.EXPENSE)
        )
        inc_res = await session.execute(stmt_inc)
        exp_res = await session.execute(stmt_exp)
        total_income = Decimal(str(inc_res.scalar() or 0))
        total_expense = Decimal(str(exp_res.scalar() or 0))
        return total_income, total_expense
