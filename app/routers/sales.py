from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.inventory import InventoryItem, ItemStatus
from app.models.sale import Sale
from app.models.sale_buyer import SaleBuyer
from app.models.user import User, UserRole
from app.schemas.inventory import inventory_read_for
from app.schemas.sale import SaleBuyerBase, SaleCreate, SaleRead, SaleReadDetailed
from app.services.stock_swap import settle_owed_swaps, swap_for_sale, undo_for_reversal

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/", response_model=list[SaleRead])
async def list_sales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sales for the current user's business.
    Owners (admins) see all sales in their business; staff see only their own."""
    query = select(Sale).where(Sale.business_id == current_user.business_id)
    if current_user.role == UserRole.staff:
        query = query.where(Sale.sold_by_user_id == current_user.id)
    return db.execute(query).scalars().all()


@router.post("/", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
async def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record a sale. Automatically marks the inventory unit as Sold.
    Outward units can be sold too (the person who took it decided to buy).
    Raises 409 if the unit is not currently Available or Outward.
    If the unit is registered to the sister shop, it is swapped for one of the
    seller's own available units of the same product (see services/stock_swap).
    """
    # Row-locked so two shops can't sell the same unit at the same moment
    item = db.get(InventoryItem, payload.inventory_item_id, with_for_update=True)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    if item.status not in (ItemStatus.available, ItemStatus.outward):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unit is not available for sale (current status: '{item.status.value}')",
        )

    sale = Sale(
        inventory_item_id=payload.inventory_item_id,
        sold_by_user_id=current_user.id,
        business_id=current_user.business_id,
        selling_price=payload.selling_price,
    )
    # Buyer info is optional: only save it if at least one field was filled in
    if payload.buyer:
        buyer_data = {
            k: v.strip() for k, v in payload.buyer.model_dump().items() if v and v.strip()
        }
        if buyer_data:
            sale.buyer = SaleBuyer(**buyer_data)
    db.add(sale)
    item.status = ItemStatus.sold  # atomic status update in the same transaction
    item.clear_outward()
    swap_for_sale(db, sale, item)
    db.commit()
    db.refresh(sale)
    return sale


@router.get("/{sale_id}", response_model=SaleReadDetailed)
async def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a sale with full inventory item details. Scoped to the user's business;
    staff can only view their own sales."""
    sale = db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    if sale.business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this sale",
        )
    if current_user.role == UserRole.staff and sale.sold_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this sale",
        )
    read = SaleReadDetailed.model_validate(sale)
    read.inventory_item = inventory_read_for(sale.inventory_item, current_user)
    return read


@router.put("/{sale_id}/buyer", response_model=SaleRead)
async def update_sale_buyer(
    sale_id: int,
    payload: SaleBuyerBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add or edit the optional buyer details on an existing sale.
    Clearing every field removes the buyer info. Staff can only edit their own sales."""
    sale = db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    if sale.business_id != current_user.business_id or (
        current_user.role == UserRole.staff and sale.sold_by_user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to edit this sale",
        )

    buyer_data = {k: (v.strip() if v and v.strip() else None) for k, v in payload.model_dump().items()}
    if not any(buyer_data.values()):
        sale.buyer = None  # delete-orphan cascade removes the row
    elif sale.buyer:
        for k, v in buyer_data.items():
            setattr(sale.buyer, k, v)
    else:
        sale.buyer = SaleBuyer(**buyer_data)
    db.commit()
    db.refresh(sale)
    return sale


@router.delete(
    "/{sale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reverse_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Reverse a sale and restore the inventory unit to Available."""
    sale = db.get(Sale, sale_id)
    if not sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    if sale.business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to reverse this sale",
        )

    item = db.get(InventoryItem, sale.inventory_item_id)
    if item:
        item.status = ItemStatus.available  # reinstate the unit on reversal
        undo_for_reversal(db, sale, item)

    db.delete(sale)
    if item:
        db.flush()
        settle_owed_swaps(db, item.product_id)
    db.commit()
