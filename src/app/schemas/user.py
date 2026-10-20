from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.user import UserRole
from app.schemas.business import BusinessRead


class UserBase(BaseModel):
    name: str
    username: str
    role: UserRole = UserRole.staff
    monthly_sales_target: Optional[Decimal] = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    monthly_sales_target: Optional[Decimal] = None


class UserRead(UserBase):
    id: int
    business_id: Optional[int] = None
    business: Optional[BusinessRead] = None
    model_config = ConfigDict(from_attributes=True)


class UserReadWithStats(UserRead):
    """Extended read schema that includes computed sales statistics."""
    total_sales: int = 0
    total_revenue: Decimal = Decimal("0.00")
