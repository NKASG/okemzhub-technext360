from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.inventory import InventoryItem, ItemStatus
from app.models.sale import Sale
from app.models.user import User, UserRole
from app.schemas.sale import SaleCreate, SaleRead, SaleReadDetailed

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
    Raises 409 if the unit is not currently Available.
    """
    item = db.get(InventoryItem, payload.inventory_item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    if item.status != ItemStatus.available:
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
    db.add(sale)
    item.status = ItemStatus.sold  # atomic status update in the same transaction
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

    db.delete(sale)
    db.commit()
