from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.flat import Flat
    from app.models.user import User


class TransactionType(str, Enum):
    INCOME = "INCOME"      # Pul yig'ish (contribution into communal fund)
    EXPENSE = "EXPENSE"    # Bozorlik / umumiy xarajat (communal market expense)


class FundTransaction(Base):
    """
    Unified communal fund ledger tracking all income collections and market expenses.
    """
    __tablename__ = "fund_transactions"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    flat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tx_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, name="transaction_type_enum"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="fund_transactions")
    user: Mapped["User"] = relationship("User", back_populates="fund_transactions", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<FundTransaction id={self.id} flat_id={self.flat_id} "
            f"type={self.tx_type} amount={self.amount} balance_after={self.balance_after}>"
        )
