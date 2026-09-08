from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.inventory import InventoryItemRead


class StockBatchBase(BaseModel):
    label: str
    date_received: date
    shipping_fee: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    notes: Optional[str] = None


class StockBatchCreate(StockBatchBase):
    pass


class StockBatchUpdate(BaseModel):
    label: Optional[str] = None
    date_received: Optional[date] = None
    shipping_fee: Optional[Decimal] = None
    other_expenses: Optional[Decimal] = None
    notes: Optional[str] = None


class StockBatchRead(StockBatchBase):
    id: int
    unit_count: int = 0
    total_unit_cost: Decimal = Decimal("0")
    total_landed_cost: Decimal = Decimal("0")


class StockBatchDetail(StockBatchRead):
    items: List[InventoryItemRead] = []
