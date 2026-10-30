from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.flat import Flat


class FlatRule(Base):
    """
    Dynamic house rule entity for a flat, managed by apartment admins.
    """
    __tablename__ = "flat_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("flats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_num: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    flat: Mapped["Flat"] = relationship("Flat", back_populates="rules")

    def __repr__(self) -> str:
        return f"<FlatRule id={self.id} flat_id={self.flat_id} order={self.order_num} title='{self.title}'>"
