"""Cross-shop serial swap.

Both sisters share one physical stock, but every unit is registered to one
shop. When shop A sells a unit registered to shop B, the sold unit is
re-registered to A (so A's count drops) and one of A's own available units of
the same product is re-registered to B (so B's count is unchanged). If A has
no spare unit of that product, the swap is logged as "owed" and settled
automatically the next time A gets an available unit of that product.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem, ItemStatus
from app.models.sale import Sale
from app.models.stock_swap import StockSwap, SwapStatus


def _spare_unit(db: Session, product_id: int, business_id: int,
                exclude_id: Optional[int] = None) -> Optional[InventoryItem]:
    """Oldest available unit of this product registered to this business (FIFO).
    Row-locked so two simultaneous sales can't hand over the same unit."""
    query = (
        select(InventoryItem)
        .where(
            InventoryItem.product_id == product_id,
            InventoryItem.business_id == business_id,
            InventoryItem.status == ItemStatus.available,
        )
        .order_by(InventoryItem.date_added, InventoryItem.id)
        .limit(1)
        .with_for_update()
    )
    if exclude_id is not None:
        query = query.where(InventoryItem.id != exclude_id)
    return db.execute(query).scalar_one_or_none()


def swap_for_sale(db: Session, sale: Sale, item: InventoryItem) -> Optional[StockSwap]:
    """Call while recording a sale, before commit. Returns the swap log entry,
    or None when the unit already belonged to the selling shop."""
    owner_id, seller_id = item.business_id, sale.business_id
    if owner_id is None or seller_id is None or owner_id == seller_id:
        return None

    replacement = _spare_unit(db, item.product_id, seller_id, exclude_id=item.id)
    item.business_id = seller_id  # the seller takes over the unit it sold
    swap = StockSwap(
        sale=sale,
        product_id=item.product_id,
        sold_item_id=item.id,
        owner_business_id=owner_id,
        seller_business_id=seller_id,
        status=SwapStatus.owed,
    )
    if replacement:
        _hand_over(swap, replacement)
    db.add(swap)
    return swap


def _hand_over(swap: StockSwap, unit: InventoryItem) -> None:
    unit.business_id = swap.owner_business_id
    swap.replacement_item_id = unit.id
    swap.replacement_item = unit
    swap.status = SwapStatus.swapped
    swap.settled_at = datetime.now(timezone.utc)


def settle_owed_swaps(db: Session, product_id: int) -> int:
    """Pay back owed swaps for this product from the seller's available stock,
    oldest debt first. Call before commit whenever a unit becomes available."""
    owed = db.execute(
        select(StockSwap)
        .where(StockSwap.product_id == product_id, StockSwap.status == SwapStatus.owed)
        .order_by(StockSwap.created_at, StockSwap.id)
    ).scalars().all()
    settled = 0
    for swap in owed:
        db.flush()  # make earlier hand-overs visible to the next lookup
        unit = _spare_unit(db, product_id, swap.seller_business_id)
        if unit:
            _hand_over(swap, unit)
            settled += 1
    return settled


def undo_for_reversal(db: Session, sale: Sale, item: InventoryItem) -> None:
    """On sale reversal: an unsettled debt is cancelled and the unit goes back
    to its original owner. A completed swap is left as is, since both shops
    already hold the right number of units."""
    swap = sale.swap
    if not swap:
        return
    if swap.status == SwapStatus.owed:
        item.business_id = swap.owner_business_id
        swap.status = SwapStatus.cancelled
        swap.settled_at = datetime.now(timezone.utc)
    swap.sale_id = None  # keep the log after the sale row is deleted
