from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


@dataclass
class DebtTransfer:
    """Represents a simplified payment required to settle debts."""
    debtor_id: int
    debtor_name: str
    creditor_id: int
    creditor_name: str
    amount: Decimal


@dataclass
class UserBalance:
    """Financial balance summary for a specific flatmate."""
    user_id: int
    user_name: str
    total_paid: Decimal
    total_owed: Decimal
    net_balance: Decimal  # Positive = Creditor (is owed), Negative = Debtor (owes)


class LedgerCalculator:
    """
    Financial engine calculating net member balances and computing
    minimal debt settlements using the Greedy Min-Cash-Flow algorithm.
    """

    @staticmethod
    def calculate_net_balances(
        user_names: Dict[int, str],
        expenses: List,
        settlements: List,
    ) -> Dict[int, UserBalance]:
        """
        Calculates total paid, total share owed, and net balance for each user.
        Formula:
          Net = (Total Paid as Buyer) - (Total Owed across Splits)
                + (Settlements Paid by User) - (Settlements Received by User)
        """
        balances: Dict[int, Dict[str, Decimal]] = {
            uid: {
                "paid": Decimal("0.00"),
                "owed": Decimal("0.00"),
                "settled_paid": Decimal("0.00"),
                "settled_received": Decimal("0.00"),
            }
            for uid in user_names.keys()
        }

        # 1. Process expenses and splits
        for exp in expenses:
            if exp.payer_id in balances:
                balances[exp.payer_id]["paid"] += Decimal(str(exp.amount))
            for split in exp.splits:
                if split.user_id in balances:
                    balances[split.user_id]["owed"] += Decimal(str(split.share_amount))

        # 2. Process direct settlements
        for setl in settlements:
            if setl.from_user_id in balances:
                balances[setl.from_user_id]["settled_paid"] += Decimal(str(setl.amount))
            if setl.to_user_id in balances:
                balances[setl.to_user_id]["settled_received"] += Decimal(str(setl.amount))

        result: Dict[int, UserBalance] = {}
        for uid, name in user_names.items():
            b = balances[uid]
            # Net position:
            # Positive (+) means user has paid more than their share -> Others owe this user
            # Negative (-) means user has paid less than their share -> User owes others
            net = (b["paid"] - b["owed"]) + (b["settled_paid"] - b["settled_received"])
            result[uid] = UserBalance(
                user_id=uid,
                user_name=name,
                total_paid=b["paid"],
                total_owed=b["owed"],
                net_balance=net,
            )
        return result

    @staticmethod
    def simplify_debts(
        balances: Dict[int, UserBalance]
    ) -> List[DebtTransfer]:
        """
        Greedy Min-Cash-Flow Debt Simplification Algorithm.
        Reduces multi-lateral debts into minimum number of direct transfers.
        """
        # Separate debtors (negative net) and creditors (positive net)
        # Using [user_id, balance, name]
        debtors: List[List] = []
        creditors: List[List] = []

        for b in balances.values():
            if b.net_balance < Decimal("-0.01"):
                # balance is positive amount owed
                debtors.append([b.user_id, -b.net_balance, b.user_name])
            elif b.net_balance > Decimal("0.01"):
                creditors.append([b.user_id, b.net_balance, b.user_name])

        # Sort descending by balance to minimize total number of settlement transfers
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        transfers: List[DebtTransfer] = []

        d_idx = 0
        c_idx = 0


        while d_idx < len(debtors) and c_idx < len(creditors):
            debtor = debtors[d_idx]
            creditor = creditors[c_idx]

            debtor_owed = debtor[1]
            creditor_expected = creditor[1]

            min_amount = min(debtor_owed, creditor_expected)

            transfers.append(
                DebtTransfer(
                    debtor_id=debtor[0],
                    debtor_name=debtor[2],
                    creditor_id=creditor[0],
                    creditor_name=creditor[2],
                    amount=min_amount.quantize(Decimal("1.00")),
                )
            )

            debtor[1] -= min_amount
            creditor[1] -= min_amount

            if debtor[1] < Decimal("0.01"):
                d_idx += 1
            if creditor[1] < Decimal("0.01"):
                c_idx += 1

        return transfers
