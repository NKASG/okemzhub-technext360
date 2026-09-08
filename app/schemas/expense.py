from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.expense import ExpenseStatus
from app.schemas.user import UserRead


class ExpenseBase(BaseModel):
    amount: Decimal
    description: str


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseStatusUpdate(BaseModel):
    status: ExpenseStatus


class ExpenseRead(ExpenseBase):
    id: int
    submitted_by_user_id: int
    business_id: Optional[int] = None
    submitted_by: Optional[UserRead] = None
    status: ExpenseStatus
    date: datetime
    model_config = ConfigDict(from_attributes=True)
