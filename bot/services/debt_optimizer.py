from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import (
    get_flat_expenses,
    get_flat_members,
    get_flat_settlements,
)


@dataclass
class TransferSuggestion:
    """Represents an optimized peer-to-peer payment settlement."""
    debtor_id: int
    debtor_name: str
    creditor_id: int
    creditor_name: str
    amount: Decimal


@dataclass
class MemberBalance:
    """Financial status for a single flatmate."""
    user_id: int
    user_name: str
    total_paid: Decimal
    total_owed: Decimal
    net_balance: Decimal  # Positive = Creditor (is owed), Negative = Debtor (owes)


class DebtOptimizer:
    """
    Greedy Min-Cash-Flow engine that calculates net balances and simplifies
    all multi-party flatmate debts down to the minimal transaction count.
    """

    @staticmethod
    def calculate_net_balances(
        members: List,
        expenses: List,
        settlements: List,
    ) -> Dict[int, MemberBalance]:
        """
        Net balance formula:
          Net = (Total Paid as Buyer) - (Total Owed across Splits)
                + (Settlements Sent) - (Settlements Received)
        """
        user_names = {m.id: m.full_name for m in members}
        raw: Dict[int, Dict[str, Decimal]] = {
            m.id: {
                "paid": Decimal("0.00"),
                "owed": Decimal("0.00"),
                "settled_sent": Decimal("0.00"),
                "settled_received": Decimal("0.00"),
            }
            for m in members
        }

        # 1. Process expenses and splits
        for exp in expenses:
            if exp.payer_id in raw:
                raw[exp.payer_id]["paid"] += Decimal(str(exp.amount))
            for split in exp.splits:
                if split.user_id in raw:
                    raw[split.user_id]["owed"] += Decimal(str(split.share_amount))

        # 2. Process direct settlements
        for setl in settlements:
            if setl.debtor_id in raw:
                raw[setl.debtor_id]["settled_sent"] += Decimal(str(setl.amount))
            if setl.creditor_id in raw:
                raw[setl.creditor_id]["settled_received"] += Decimal(str(setl.amount))

        balances: Dict[int, MemberBalance] = {}
        for uid, name in user_names.items():
            b = raw[uid]
            net = (b["paid"] - b["owed"]) + (b["settled_sent"] - b["settled_received"])
            balances[uid] = MemberBalance(
                user_id=uid,
                user_name=name,
                total_paid=b["paid"],
                total_owed=b["owed"],
                net_balance=net,
            )
        return balances

    @staticmethod
    def minimize_cash_flow(
        balances: Dict[int, MemberBalance]
    ) -> List[TransferSuggestion]:
        """
        Greedy Min-Cash-Flow Algorithm:
        Pairs the largest debtor with the largest creditor iteratively.
        """
        debtors: List[List] = []
        creditors: List[List] = []

        for b in balances.values():
            if b.net_balance < Decimal("-0.01"):
                # Store [user_id, name, amount_owed]
                debtors.append([b.user_id, b.user_name, -b.net_balance])
            elif b.net_balance > Decimal("0.01"):
                # Store [user_id, name, amount_expected]
                creditors.append([b.user_id, b.user_name, b.net_balance])

        # Sort descending by balance to achieve maximal reduction per transfer
        debtors.sort(key=lambda x: x[2], reverse=True)
        creditors.sort(key=lambda x: x[2], reverse=True)

        transfers: List[TransferSuggestion] = []
        d_idx = 0
        c_idx = 0

        while d_idx < len(debtors) and c_idx < len(creditors):
            debtor = debtors[d_idx]
            creditor = creditors[c_idx]

            debtor_owes = debtor[2]
            creditor_expects = creditor[2]

            min_transfer = min(debtor_owes, creditor_expects)

            transfers.append(
                TransferSuggestion(
                    debtor_id=debtor[0],
                    debtor_name=debtor[1],
                    creditor_id=creditor[0],
                    creditor_name=creditor[1],
                    amount=min_transfer.quantize(Decimal("1.00")),
                )
            )

            debtor[2] -= min_transfer
            creditor[2] -= min_transfer

            if debtor[2] < Decimal("0.01"):
                d_idx += 1
            if creditor[2] < Decimal("0.01"):
                c_idx += 1

        return transfers

    @classmethod
    async def get_flat_ledger(
        cls,
        session: AsyncSession,
        flat_id: int,
    ) -> Tuple[Dict[int, MemberBalance], List[TransferSuggestion], Decimal]:
        """Calculates total spent, net balances, and minimal settlement transfers."""
        members = await get_flat_members(session, flat_id)
        expenses = await get_flat_expenses(session, flat_id)
        settlements = await get_flat_settlements(session, flat_id)

        total_spent = sum((e.amount for e in expenses), Decimal("0.00"))
        balances = cls.calculate_net_balances(members, expenses, settlements)
        transfers = cls.minimize_cash_flow(balances)

        return balances, transfers, total_spent
