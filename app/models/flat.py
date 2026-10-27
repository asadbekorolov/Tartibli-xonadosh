from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chore import Chore, ChoreAssignment
    from app.models.expense import Expense, Settlement


class FlatRole(str, Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class Flat(Base, TimestampMixin):
    """
    Shared apartment or dormitory room entity (typically 7-8 students).
    """
    __tablename__ = "flats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    created_by_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def status(self) -> str:
        """String representation of flat activity state."""
        return "ACTIVE" if self.is_active else "INACTIVE"

    # Relationships
    members: Mapped[List["FlatMember"]] = relationship(
        "FlatMember", back_populates="flat", cascade="all, delete-orphan", lazy="selectin"
    )
    chores: Mapped[List["Chore"]] = relationship(
        "Chore", back_populates="flat", cascade="all, delete-orphan"
    )
    chore_assignments: Mapped[List["ChoreAssignment"]] = relationship(
        "ChoreAssignment", back_populates="flat", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="flat", cascade="all, delete-orphan"
    )
    settlements: Mapped[List["Settlement"]] = relationship(
        "Settlement", back_populates="flat", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Flat id={self.id} name='{self.name}' invite_code='{self.invite_code}'>"


class FlatMember(Base, TimestampMixin):
    """
    Association table binding Users to Flats with designated roles.
    """
    __tablename__ = "flat_members"
    __table_args__ = (
        UniqueConstraint("flat_id", "user_id", name="uq_flat_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[FlatRole] = mapped_column(
        SQLEnum(FlatRole, name="flat_role_enum"), default=FlatRole.MEMBER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    @property
    def status(self) -> str:
        """String representation of member status."""
        return "ACTIVE" if self.is_active else "INACTIVE"

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="flat_memberships", lazy="selectin")

    def __repr__(self) -> str:
        return f"<FlatMember flat_id={self.flat_id} user_id={self.user_id} role={self.role}>"
