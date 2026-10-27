from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.expense import (
    Expense,
    ExpenseCategory,
    ExpenseParticipant,
    Settlement,
    SettlementStatus,
)



class ExpenseRepository:
    @staticmethod
    async def create_expense(
        session: AsyncSession,
        flat_id: int,
        payer_id: int,
        title: str,
        category: ExpenseCategory,
        amount: Decimal,
        splits: Dict[int, Decimal],
    ) -> Expense:
        """
        Creates an Expense record along with its participants' exact share amounts.
        """
        expense = Expense(
            flat_id=flat_id,
            payer_id=payer_id,
            title=title,
            category=category,
            amount=amount
        )
        session.add(expense)
        await session.flush()

        for user_id, share in splits.items():
            participant = ExpenseParticipant(
                expense_id=expense.id,
                user_id=user_id,
                share_amount=share
            )
            session.add(participant)

        await session.flush()
        return expense

    @staticmethod
    async def get_flat_expenses(
        session: AsyncSession, flat_id: int, limit: int = 50
    ) -> List[Expense]:
        stmt = (
            select(Expense)
            .where(Expense.flat_id == flat_id)
            .options(
                selectinload(Expense.payer),
                selectinload(Expense.splits).selectinload(ExpenseParticipant.user)
            )
            .order_by(Expense.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_splits_for_flat(
        session: AsyncSession, flat_id: int
    ) -> List[ExpenseParticipant]:
        stmt = (
            select(ExpenseParticipant)
            .join(Expense, Expense.id == ExpenseParticipant.expense_id)
            .where(Expense.flat_id == flat_id)
            .options(
                selectinload(ExpenseParticipant.expense),
                selectinload(ExpenseParticipant.user)
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_settlement(
        session: AsyncSession,
        flat_id: int,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        note: Optional[str] = None,
        status: SettlementStatus = SettlementStatus.CONFIRMED,
    ) -> Settlement:
        settlement = Settlement(
            flat_id=flat_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            note=note,
            status=status,
        )
        session.add(settlement)
        await session.flush()
        return settlement


    @staticmethod
    async def get_flat_settlements(
        session: AsyncSession, flat_id: int, limit: int = 50
    ) -> List[Settlement]:
        stmt = (
            select(Settlement)
            .where(Settlement.flat_id == flat_id)
            .options(
                selectinload(Settlement.from_user),
                selectinload(Settlement.to_user)
            )
            .order_by(Settlement.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
