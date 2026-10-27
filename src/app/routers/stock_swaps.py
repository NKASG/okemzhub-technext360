from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_current_user, get_db
from app.models.stock_swap import StockSwap, SwapStatus
from app.models.user import User
from app.schemas.stock_swap import StockSwapRead

router = APIRouter(prefix="/stock-swaps", tags=["Stock Swaps"])


@router.get("/", response_model=list[StockSwapRead])
async def list_stock_swaps(
    swap_status: Optional[SwapStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Swaps involving the current user's shop, newest first. Read-only: swaps
    are made automatically when a sale is recorded."""
    query = (
        select(StockSwap)
        # Serials and shop names in batched queries, not 4 queries per swap
        .options(
            selectinload(StockSwap.sold_item),
            selectinload(StockSwap.replacement_item),
            selectinload(StockSwap.owner_business),
            selectinload(StockSwap.seller_business),
        )
        .where(or_(
            StockSwap.owner_business_id == current_user.business_id,
            StockSwap.seller_business_id == current_user.business_id,
        ))
        .order_by(StockSwap.created_at.desc(), StockSwap.id.desc())
    )
    if swap_status is not None:
        query = query.where(StockSwap.status == swap_status)
    return db.execute(query).scalars().all()
