from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.flat import Flat
from app.models.fund import FundTransaction, TransactionType
from app.repositories.flat_repo import FlatRepository
from app.repositories.fund_repo import FundRepository


@dataclass
class FundSummary:
    fund_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    recent_transactions: List[FundTransaction]
    member_count: int


class FundService:
    @classmethod
    async def create_collection(
        cls,
        session: AsyncSession,
        flat_id: int,
        per_person_amount: Decimal,
        participants: List[int],
        description: Optional[str] = None,
    ) -> Decimal:
        """
        Increases flat.fund_balance by per_person_amount * len(participants)
        and logs individual INCOME transactions for each participant.
        """
        if not participants:
            raise ValueError("Yig'im uchun xonadoshlar tanlanmadi.")
        if per_person_amount <= 0:
            raise ValueError("Yig'im summasi musbat bo'lishi lozim.")

        stmt = select(Flat).where(Flat.id == flat_id)
        result = await session.execute(stmt)
        flat = result.scalar_one_or_none()
        if not flat:
            raise ValueError("Kvartira topilmadi.")

        total_collected = per_person_amount * Decimal(len(participants))
        new_balance = flat.fund_balance + total_collected
        flat.fund_balance = new_balance

        tx_desc = description or f"Kassa yig'imi ({int(per_person_amount):,} so'm/kishi)"

        for uid in participants:
            await FundRepository.create_transaction(
                session=session,
                flat_id=flat_id,
                user_id=uid,
                tx_type=TransactionType.INCOME,
                amount=per_person_amount,
                balance_after=new_balance,
                description=tx_desc,
            )

        await session.flush()
        return new_balance

    @classmethod
    async def record_market_expense(
        cls,
        session: AsyncSession,
        flat_id: int,
        spender_id: int,
        amount: Decimal,
        description: str,
    ) -> FundTransaction:
        """
        Deducts expense from flat.fund_balance (handling exact sums like 370,293 UZS
        from a 400,000 UZS fund, preserving the remainder 29,707 UZS in the balance)
        and logs an EXPENSE transaction.
        """
        if amount <= 0:
            raise ValueError("Xarajat summasi musbat bo'lishi lozim.")
        if not description or not description.strip():
            raise ValueError("Xarid tavsifi bo'sh bo'lishi mumkin emas.")

        stmt = select(Flat).where(Flat.id == flat_id)
        result = await session.execute(stmt)
        flat = result.scalar_one_or_none()
        if not flat:
            raise ValueError("Kvartira topilmadi.")

        new_balance = flat.fund_balance - amount
        flat.fund_balance = new_balance

        tx = await FundRepository.create_transaction(
            session=session,
            flat_id=flat_id,
            user_id=spender_id,
            tx_type=TransactionType.EXPENSE,
            amount=amount,
            balance_after=new_balance,
            description=description.strip(),
        )

        await session.flush()
        return tx

    @classmethod
    async def get_fund_summary(
        cls,
        session: AsyncSession,
        flat_id: int,
        recent_limit: int = 5,
    ) -> FundSummary:
        """
        Returns current fund balance, latest transactions, and financial aggregates.
        """
        stmt = select(Flat).where(Flat.id == flat_id)
        result = await session.execute(stmt)
        flat = result.scalar_one_or_none()
        if not flat:
            raise ValueError("Kvartira topilmadi.")

        recent_txs = await FundRepository.get_recent_transactions(
            session=session,
            flat_id=flat_id,
            limit=recent_limit,
        )
        total_income, total_expense = await FundRepository.get_totals(session, flat_id)
        members = await FlatRepository.get_members(session, flat_id)

        return FundSummary(
            fund_balance=flat.fund_balance,
            total_income=total_income,
            total_expense=total_expense,
            recent_transactions=recent_txs,
            member_count=len(members),
        )

