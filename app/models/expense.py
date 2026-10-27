from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    BigInteger,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.flat import Flat
    from app.models.user import User


class ExpenseCategory(str, Enum):
    GROCERY = "GROCERY"        # Oziq-ovqat, go'sht, non, meva-sabzavot
    UTILITIES = "UTILITIES"    # Kommunal, gaz, elektr, Wi-Fi
    CLEANING = "CLEANING"      # Tozalash vositalari, poroshok, sovun
    WATER = "WATER"            # 19L toza ichimlik suvi
    OTHER = "OTHER"            # Boshqa kutilmagan xarajatlar


class Expense(Base, TimestampMixin):
    """
    Communal shared purchase logged by a flatmate.
    """
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    payer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        SQLEnum(ExpenseCategory, name="expense_category_enum"),
        default=ExpenseCategory.GROCERY,
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="expenses")
    payer: Mapped["User"] = relationship("User", back_populates="paid_expenses", lazy="selectin")
    splits: Mapped[List["ExpenseParticipant"]] = relationship(
        "ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Expense id={self.id} title='{self.title}' amount={self.amount} payer_id={self.payer_id}>"


class ExpenseParticipant(Base, TimestampMixin):
    """
    Explicit breakdown of an expense owed by a specific flatmate.
    """
    __tablename__ = "expense_participants"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_participant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    expense: Mapped["Expense"] = relationship("Expense", back_populates="splits")
    user: Mapped["User"] = relationship("User", back_populates="expense_splits", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ExpenseParticipant expense_id={self.expense_id} user_id={self.user_id} share={self.share_amount}>"


class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Settlement(Base, TimestampMixin):
    """
    Direct payment between two flatmates clearing debt balance.
    """
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    from_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)  # Debtor
    to_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)    # Creditor
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[SettlementStatus] = mapped_column(
        SQLEnum(SettlementStatus, name="settlement_status_enum"),
        default=SettlementStatus.CONFIRMED,
        nullable=False,
        index=True
    )

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="settlements")
    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id], back_populates="sent_settlements", lazy="selectin")
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id], back_populates="received_settlements", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Settlement id={self.id} from={self.from_user_id} to={self.to_user_id} amount={self.amount} status={self.status}>"

