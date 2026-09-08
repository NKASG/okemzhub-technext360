from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem


class StockBatch(Base):
    __tablename__ = "stock_batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    date_received: Mapped[date] = mapped_column(Date)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    other_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="stock_batch", lazy="select"
    )
