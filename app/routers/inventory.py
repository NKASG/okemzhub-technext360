from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_current_user, get_db, require_admin
from app.models.inventory import InventoryItem, ItemStatus
from app.models.sale import Sale
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    inventory_read_for,
)
from app.services.stock_swap import settle_owed_swaps

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# Eager-load the sale + seller + business so the shared "who sold it" fields
# resolve in one query instead of N+1 lazy loads.
_load_seller = [
    selectinload(InventoryItem.business),
    selectinload(InventoryItem.sale).selectinload(Sale.sold_by),
    selectinload(InventoryItem.sale).selectinload(Sale.business),
]

# The only fields staff may change on a unit: flag it faulty (with a note) or
# put it back to available. Prices, batch and business are owner-only.
_STAFF_EDITABLE = {"status", "fault_description"}


@router.get("/", response_model=list[InventoryItemRead])
async def list_inventory(
    product_id: Optional[int] = None,
    item_status: Optional[ItemStatus] = None,
    business_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inventory units. Optionally filter by product, status or business.
    Cost price is only included for owners (admins)."""
    query = select(InventoryItem).options(*_load_seller)
    if product_id is not None:
        query = query.where(InventoryItem.product_id == product_id)
    if item_status is not None:
        query = query.where(InventoryItem.status == item_status)
    if business_id is not None:
        query = query.where(InventoryItem.business_id == business_id)
    return [inventory_read_for(i, current_user) for i in db.execute(query).scalars().all()]


@router.post("/", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def add_inventory_item(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """Add a new individual unit to stock. Serial number must be unique."""
    if db.execute(
        select(InventoryItem).where(InventoryItem.serial_number == payload.serial_number)
    ).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A unit with this serial number already exists",
        )
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    db.flush()
    settle_owed_swaps(db, item.product_id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=InventoryItemRead)
async def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single inventory unit by ID."""
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    return inventory_read_for(item, current_user)


@router.patch("/{item_id}", response_model=InventoryItemRead)
async def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a unit's status (e.g. mark as Faulty with a description).
    Staff may only switch a unit between Available and Faulty; everything else
    is owner-only, and units become Sold only by recording a sale."""
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    changes = payload.model_dump(exclude_unset=True)
    if current_user.role == UserRole.staff:
        if set(changes) - _STAFF_EDITABLE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can change prices, batch or business",
            )
        if item.status == ItemStatus.sold or changes.get("status") == ItemStatus.sold:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Units are marked Sold by recording a sale; only the owner can change a sold unit",
            )
    for field, value in changes.items():
        setattr(item, field, value)
    db.flush()
    # A unit that is (back) in available stock may pay off an owed swap
    settle_owed_swaps(db, item.product_id)
    db.commit()
    db.refresh(item)
    return inventory_read_for(item, current_user)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    """[Admin] Permanently remove an inventory record."""
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    db.delete(item)
    db.commit()
