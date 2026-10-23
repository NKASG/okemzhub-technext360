import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.inventory import InventoryItem
    from app.models.product import Product
    from app.models.sale import Sale


class SwapStatus(str, enum.Enum):
    swapped = "swapped"      # a replacement unit was handed to the owner
    owed = "owed"            # seller had no spare unit yet; settled on next stock-in
    cancelled = "cancelled"  # the sale was reversed before the debt was settled


class StockSwap(Base):
    """Log of one shop selling a unit registered to its sister shop. The seller
    takes over the sold unit, and gives the owner one of its own available
    units of the same product so the owner's count is unchanged."""

    __tablename__ = "stock_swaps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Nulled if the sale is reversed; the swap log itself is kept as history
    sale_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sales.id"), nullable=True, unique=True, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sold_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"))
    replacement_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=True
    )
    # owner = shop the sold serial was registered to; seller = shop that sold it
    owner_business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    seller_business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    status: Mapped[SwapStatus] = mapped_column(SAEnum(SwapStatus, name="swapstatus"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sale: Mapped[Optional["Sale"]] = relationship("Sale", back_populates="swap")
    product: Mapped["Product"] = relationship("Product")
    sold_item: Mapped["InventoryItem"] = relationship("InventoryItem", foreign_keys=[sold_item_id])
    replacement_item: Mapped[Optional["InventoryItem"]] = relationship(
        "InventoryItem", foreign_keys=[replacement_item_id]
    )
    owner_business: Mapped["Business"] = relationship("Business", foreign_keys=[owner_business_id])
    seller_business: Mapped["Business"] = relationship("Business", foreign_keys=[seller_business_id])

    @property
    def sold_serial(self) -> Optional[str]:
        return self.sold_item.serial_number if self.sold_item else None

    @property
    def replacement_serial(self) -> Optional[str]:
        return self.replacement_item.serial_number if self.replacement_item else None

    @property
    def owner_business_name(self) -> Optional[str]:
        return self.owner_business.name if self.owner_business else None

    @property
    def seller_business_name(self) -> Optional[str]:
        return self.seller_business.name if self.seller_business else None
