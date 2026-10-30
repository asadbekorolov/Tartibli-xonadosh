from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.flat import Flat
    from app.models.user import User


class RotationType(str, Enum):
    ROUND_ROBIN = "ROUND_ROBIN"      # Cyclic queue through members (1 person)
    FIXED_DAYS = "FIXED_DAYS"        # Fixed days or daily assignments
    PAIR_ROTATION = "PAIR_ROTATION"  # Pair duty rotation (2 people per task)


class ChoreFrequencyType(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    CUSTOM = "CUSTOM"


class ChoreStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class Chore(Base, TimestampMixin):
    """
    Template or recurring duty definition for a flat.
    E.g. Kitchen cleaning, Trash disposal, 10L Water refill, Weekly deep cleaning.
    """
    __tablename__ = "chores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rotation_type: Mapped[RotationType] = mapped_column(
        SQLEnum(RotationType, name="rotation_type_enum"),
        default=RotationType.ROUND_ROBIN,
        nullable=False
    )
    frequency_type: Mapped[ChoreFrequencyType] = mapped_column(
        SQLEnum(ChoreFrequencyType, name="chore_frequency_type_enum"),
        default=ChoreFrequencyType.DAILY,
        nullable=False
    )
    frequency_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1 = daily, 7 = weekly
    execution_time: Mapped[str] = mapped_column(String(5), default="21:00", nullable=False)  # HH:MM format
    current_member_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checklist: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    assignee_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Advanced custom scheduling
    assigned_weekdays: Mapped[Optional[Dict[str, int]]] = mapped_column(JSON, nullable=True)  # {"MON": user_id, ...}
    assigned_pairs: Mapped[Optional[List[List[int]]]] = mapped_column(JSON, nullable=True)     # [[u1, u2], [u3, u4]]

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def status(self) -> str:
        """String representation of chore active status."""
        return "ACTIVE" if self.is_active else "INACTIVE"

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="chores")
    assignments: Mapped[List["ChoreAssignment"]] = relationship(
        "ChoreAssignment", back_populates="chore", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Chore id={self.id} title='{self.title}' rotation={self.rotation_type} time='{self.execution_time}'>"


class ChoreAssignment(Base, TimestampMixin):
    """
    Specific instance of a chore assigned to flatmates on a given date.
    Supports both single assignee and pair assignees.
    """
    __tablename__ = "chore_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chore_id: Mapped[int] = mapped_column(Integer, ForeignKey("chores.id", ondelete="CASCADE"), nullable=False)
    flat_id: Mapped[int] = mapped_column(Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False)
    assignee_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    assignee_ids: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ChoreStatus] = mapped_column(
        SQLEnum(ChoreStatus, name="chore_status_enum"),
        default=ChoreStatus.PENDING,
        nullable=False,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    chore: Mapped["Chore"] = relationship("Chore", back_populates="assignments", lazy="selectin")
    flat: Mapped["Flat"] = relationship("Flat", back_populates="chore_assignments")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", back_populates="chore_assignments", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ChoreAssignment id={self.id} chore_id={self.chore_id} assignee_id={self.assignee_id} status={self.status}>"
