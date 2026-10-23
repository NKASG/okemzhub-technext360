from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.inventory import InventoryItemRead


class SaleBuyerBase(BaseModel):
    """Buyer details - every field is optional."""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SaleBuyerRead(SaleBuyerBase):
    model_config = ConfigDict(from_attributes=True)


class SaleBase(BaseModel):
    inventory_item_id: int
    selling_price: Decimal


class SaleCreate(SaleBase):
    buyer: Optional[SaleBuyerBase] = None


class SaleRead(SaleBase):
    id: int
    sold_by_user_id: int
    business_id: Optional[int] = None
    date_sold: datetime
    buyer: Optional[SaleBuyerRead] = None
    model_config = ConfigDict(from_attributes=True)


class SaleReadDetailed(SaleRead):
    """SaleRead with the full inventory item record nested in."""
    inventory_item: InventoryItemRead
