from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.inventory import InventoryItem
    from app.models.user import User


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # unique=True enforces one-sale-per-unit at the database level
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), unique=True)
    sold_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    business_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("businesses.id"), nullable=True, index=True
    )
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    date_sold: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="sale")
    sold_by: Mapped["User"] = relationship("User", back_populates="sales")
    business: Mapped[Optional["Business"]] = relationship("Business", back_populates="sales")
