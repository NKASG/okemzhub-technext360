from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.inventory import ItemStatus
from app.models.user import UserRole


class InventoryItemBase(BaseModel):
    product_id: int
    serial_number: str
    status: ItemStatus = ItemStatus.available
    fault_description: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    stock_batch_id: Optional[int] = None
    business_id: Optional[int] = None

    @model_validator(mode="after")
    def fault_description_required_when_faulty(self) -> "InventoryItemBase":
        if self.status == ItemStatus.faulty and not self.fault_description:
            raise ValueError("fault_description is required when status is 'faulty'")
        return self


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    status: Optional[ItemStatus] = None
    fault_description: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    stock_batch_id: Optional[int] = None
    business_id: Optional[int] = None

    @model_validator(mode="after")
    def fault_description_required_when_faulty(self) -> "InventoryItemUpdate":
        if self.status == ItemStatus.faulty and not self.fault_description:
            raise ValueError("fault_description is required when status is 'faulty'")
        return self


class InventoryOutward(BaseModel):
    """Mark a unit Outward: someone took it out of the shop without buying yet."""
    taken_by: str = Field(min_length=1, max_length=150)
    note: Optional[str] = None


class InventoryItemRead(InventoryItemBase):
    id: int
    date_added: datetime
    business_name: Optional[str] = None
    # Shared visibility: who sold this unit (name only, never the price)
    sold_by_name: Optional[str] = None
    sold_by_business: Optional[str] = None
    date_sold: Optional[datetime] = None
    # Shared visibility: who has an Outward unit, since when, and who released it
    outward_to: Optional[str] = None
    outward_note: Optional[str] = None
    outward_at: Optional[datetime] = None
    outward_by_name: Optional[str] = None
    outward_by_business: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


def inventory_read_for(item, user) -> InventoryItemRead:
    """Serialise a unit for this user. Cost price is owner-only, so it is
    removed for staff (the frontend hiding it is not enough)."""
    read = InventoryItemRead.model_validate(item)
    if user.role != UserRole.admin:
        read.cost_price = None
    return read
