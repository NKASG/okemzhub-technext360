from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    brand: str
    model_name: str
    specifications: Optional[str] = None
    base_price: Decimal


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    brand: Optional[str] = None
    model_name: Optional[str] = None
    specifications: Optional[str] = None
    base_price: Optional[Decimal] = None


class ProductRead(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class ProductReadWithStock(ProductRead):
    """Extends ProductRead with a dynamically computed available unit count."""
    available_units: int = 0
