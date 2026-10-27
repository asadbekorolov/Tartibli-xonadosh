from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Telegram User entity."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    flat_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("flats.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    flat: Mapped[Optional["Flat"]] = relationship("Flat", foreign_keys=[flat_id], back_populates="members")
    chores: Mapped[List["Chore"]] = relationship("Chore", back_populates="current_assignee")
    expenses_paid: Mapped[List["Expense"]] = relationship("Expense", back_populates="payer")
    expenses_shared: Mapped[List["ExpenseParticipant"]] = relationship("ExpenseParticipant", back_populates="user")
    settlements_sent: Mapped[List["Settlement"]] = relationship(
        "Settlement", foreign_keys="Settlement.debtor_id", back_populates="debtor"
    )
    settlements_received: Mapped[List["Settlement"]] = relationship(
        "Settlement", foreign_keys="Settlement.creditor_id", back_populates="creditor"
    )

    @property
    def mention(self) -> str:
        """Formatted mention string (username or full name)."""
        if self.username:
            return f"@{self.username}"
        return self.full_name

    def __repr__(self) -> str:
        return f"<User id={self.id} name='{self.full_name}' flat_id={self.flat_id}>"


class Flat(Base, TimestampMixin):
    """Apartment/Dormitory group entity (holds 2-10 students)."""
    __tablename__ = "flats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Relationships
    members: Mapped[List["User"]] = relationship(
        "User", foreign_keys=[User.flat_id], back_populates="flat", lazy="selectin"
    )
    chores: Mapped[List["Chore"]] = relationship(
        "Chore", back_populates="flat", cascade="all, delete-orphan", lazy="selectin"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="flat", cascade="all, delete-orphan", lazy="selectin"
    )
    settlements: Mapped[List["Settlement"]] = relationship(
        "Settlement", back_populates="flat", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Flat id={self.id} name='{self.name}' invite_code='{self.invite_code}'>"


class Chore(Base, TimestampMixin):
    """Rotating duty task entity (Cleaning, Trash, Water)."""
    __tablename__ = "chores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    current_assignee_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, COMPLETED

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="chores")
    current_assignee: Mapped[Optional["User"]] = relationship("User", back_populates="chores", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Chore id={self.id} title='{self.title}' assignee={self.current_assignee_id} status='{self.status}'>"


class Expense(Base, TimestampMixin):
    """Shared grocery or communal expense purchase."""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    payer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="expenses")
    payer: Mapped["User"] = relationship("User", back_populates="expenses_paid", lazy="selectin")
    splits: Mapped[List["ExpenseParticipant"]] = relationship(
        "ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Expense id={self.id} title='{self.title}' amount={self.amount} payer_id={self.payer_id}>"


class ExpenseParticipant(Base, TimestampMixin):
    """User share owed for a given expense purchase."""
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
    user: Mapped["User"] = relationship("User", back_populates="expenses_shared", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ExpenseParticipant expense_id={self.expense_id} user_id={self.user_id} share={self.share_amount}>"


class Settlement(Base, TimestampMixin):
    """Direct payment record between flatmates clearing debt balance."""
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    debtor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    creditor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMED", nullable=False)  # CONFIRMED, PENDING

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="settlements")
    debtor: Mapped["User"] = relationship("User", foreign_keys=[debtor_id], back_populates="settlements_sent", lazy="selectin")
    creditor: Mapped["User"] = relationship("User", foreign_keys=[creditor_id], back_populates="settlements_received", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Settlement id={self.id} debtor={self.debtor_id} creditor={self.creditor_id} amount={self.amount}>"
