from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.flat import FlatMember
    from app.models.chore import ChoreAssignment
    from app.models.expense import Expense, ExpenseParticipant, Settlement
    from app.models.fund import FundTransaction


class User(Base, TimestampMixin):
    """
    Telegram User representation in the system.
    """
    __tablename__ = "users"

    # Telegram user_id is a 64-bit integer
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    flat_memberships: Mapped[List["FlatMember"]] = relationship(
        "FlatMember", back_populates="user", cascade="all, delete-orphan"
    )
    chore_assignments: Mapped[List["ChoreAssignment"]] = relationship(
        "ChoreAssignment", back_populates="assignee"
    )
    fund_transactions: Mapped[List["FundTransaction"]] = relationship(
        "FundTransaction", back_populates="user"
    )

    # Deprecated pairwise ledger relationships (kept for backwards compatibility)
    paid_expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="payer"
    )
    expense_splits: Mapped[List["ExpenseParticipant"]] = relationship(
        "ExpenseParticipant", back_populates="user"
    )
    sent_settlements: Mapped[List["Settlement"]] = relationship(
        "Settlement", foreign_keys="Settlement.from_user_id", back_populates="from_user"
    )
    received_settlements: Mapped[List["Settlement"]] = relationship(
        "Settlement", foreign_keys="Settlement.to_user_id", back_populates="to_user"
    )

    @property
    def display_name(self) -> str:
        """Formatted user display name (First name + Last name or username)."""
        if self.last_name:
            name = f"{self.first_name} {self.last_name}"
        else:
            name = self.first_name
        if self.username:
            name += f" (@{self.username})"
        return name

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} name={self.first_name}>"
