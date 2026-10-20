import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.expense import Expense
    from app.models.sale import Sale


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="userrole"), default=UserRole.staff)
    monthly_sales_target: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    business_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("businesses.id"), nullable=True, index=True
    )

    business: Mapped[Optional["Business"]] = relationship("Business", back_populates="users")
    sales: Mapped[list["Sale"]] = relationship("Sale", back_populates="sold_by")
    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="submitted_by")
