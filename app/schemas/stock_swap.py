from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.stock_swap import SwapStatus


class StockSwapRead(BaseModel):
    """A cross-shop swap. Serials and shop names only, never prices."""
    id: int
    sale_id: Optional[int] = None
    product_id: int
    status: SwapStatus
    sold_item_id: int
    sold_serial: Optional[str] = None
    replacement_item_id: Optional[int] = None
    replacement_serial: Optional[str] = None
    owner_business_id: int
    owner_business_name: Optional[str] = None
    seller_business_id: int
    seller_business_name: Optional[str] = None
    created_at: datetime
    settled_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
