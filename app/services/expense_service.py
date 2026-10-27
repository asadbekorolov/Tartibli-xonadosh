from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.expense import Expense, ExpenseCategory, Settlement, SettlementStatus
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.flat_repo import FlatRepository
from app.services.ledger_calculator import DebtTransfer, LedgerCalculator, UserBalance


class ExpenseService:
    @classmethod
    async def add_communal_expense(
        cls,
        session: AsyncSession,
        flat_id: int,
        payer_id: int,
        title: str,
        category: ExpenseCategory,
        amount: Decimal,
        participant_ids: Optional[List[int]] = None,
    ) -> Expense:
        """
        Splits an expense evenly across all active flatmates or designated participants.
        Guarantees that sum(individual_shares) == total_amount without rounding loss.
        """
        members = await FlatRepository.get_members(session, flat_id)
        if not members:
            raise ValueError("Kvartirada birorta ham a'zo topilmadi.")

        if not participant_ids:
            participant_ids = [m.user_id for m in members]

        n = len(participant_ids)
        if n == 0:
            raise ValueError("Xarajat qatnashchilari tanlanmadi.")

        # Exact integer division for currency (e.g. UZS)
        total_cents = int(amount)
        base_share = total_cents // n
        remainder = total_cents % n

        splits: Dict[int, Decimal] = {}
        for idx, uid in enumerate(participant_ids):
            share = base_share + (1 if idx < remainder else 0)
            splits[uid] = Decimal(str(share))

        return await ExpenseRepository.create_expense(
            session=session,
            flat_id=flat_id,
            payer_id=payer_id,
            title=title,
            category=category,
            amount=amount,
            splits=splits,
        )

    @classmethod
    async def get_flat_ledger(
        cls,
        session: AsyncSession,
        flat_id: int,
    ) -> Tuple[Dict[int, UserBalance], List[DebtTransfer], Decimal]:
        """
        Calculates balances and computes simplified direct debt settlements.
        """
        members = await FlatRepository.get_members(session, flat_id)
        user_names = {m.user_id: m.user.first_name for m in members}

        expenses = await ExpenseRepository.get_flat_expenses(session, flat_id, limit=200)
        settlements = await ExpenseRepository.get_flat_settlements(session, flat_id, limit=200)

        total_spent = sum((e.amount for e in expenses), Decimal("0.00"))

        balances = LedgerCalculator.calculate_net_balances(
            user_names=user_names,
            expenses=expenses,
            settlements=settlements,
        )

        simplified_debts = LedgerCalculator.simplify_debts(balances)

        return balances, simplified_debts, total_spent

    @classmethod
    async def settle_debt(
        cls,
        session: AsyncSession,
        flat_id: int,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        note: Optional[str] = None,
        status: SettlementStatus = SettlementStatus.CONFIRMED,
    ) -> Settlement:
        """Records a direct payment between flatmates clearing debt balance."""
        return await ExpenseRepository.create_settlement(
            session=session,
            flat_id=flat_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            note=note or "Qarz to'liq uzildi",
            status=status,
        )

