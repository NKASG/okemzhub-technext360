from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.expense import Expense
    from app.models.sale import Sale
    from app.models.user import User


class Business(Base):
    """A separately-managed store identity. Products & inventory are shared across
    businesses, but sales, expenses, staff and branding are scoped per business."""

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    tagline: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    users: Mapped[List["User"]] = relationship("User", back_populates="business")
    sales: Mapped[List["Sale"]] = relationship("Sale", back_populates="business")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="business")
