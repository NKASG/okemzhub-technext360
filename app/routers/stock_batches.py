from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_db, require_admin
from app.models.inventory import InventoryItem
from app.models.stock_batch import StockBatch
from app.schemas.inventory import InventoryItemRead
from app.schemas.stock_batch import (
    StockBatchCreate,
    StockBatchDetail,
    StockBatchRead,
    StockBatchUpdate,
)

router = APIRouter(prefix="/stock-batches", tags=["Stock Batches"])

_load_items = [selectinload(StockBatch.items)]


def _to_read(batch: StockBatch) -> StockBatchRead:
    total = sum(i.cost_price or Decimal("0") for i in batch.items)
    return StockBatchRead(
        id=batch.id,
        label=batch.label,
        date_received=batch.date_received,
        shipping_fee=batch.shipping_fee,
        other_expenses=batch.other_expenses,
        notes=batch.notes,
        unit_count=len(batch.items),
        total_unit_cost=total,
        total_landed_cost=total + batch.shipping_fee + batch.other_expenses,
    )


def _to_detail(batch: StockBatch) -> StockBatchDetail:
    read = _to_read(batch)
    sorted_items = sorted(batch.items, key=lambda i: i.date_added)
    return StockBatchDetail(
        **read.model_dump(),
        items=[InventoryItemRead.model_validate(i) for i in sorted_items],
    )


@router.get("/", response_model=list[StockBatchRead], dependencies=[Depends(require_admin)])
async def list_batches(db: Session = Depends(get_db)):
    """[Admin] List all stock batches with cost summaries."""
    batches = db.execute(
        select(StockBatch).options(*_load_items).order_by(StockBatch.date_received.desc())
    ).scalars().all()
    return [_to_read(b) for b in batches]


@router.post(
    "/",
    response_model=StockBatchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_batch(payload: StockBatchCreate, db: Session = Depends(get_db)):
    """[Admin] Create a new stock batch."""
    batch = StockBatch(**payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    # No items yet, safe to construct directly
    return StockBatchRead(
        id=batch.id, label=batch.label, date_received=batch.date_received,
        shipping_fee=batch.shipping_fee, other_expenses=batch.other_expenses,
        notes=batch.notes, unit_count=0,
        total_unit_cost=Decimal("0"), total_landed_cost=batch.shipping_fee + batch.other_expenses,
    )


@router.get("/{batch_id}", response_model=StockBatchDetail, dependencies=[Depends(require_admin)])
async def get_batch(batch_id: int, db: Session = Depends(get_db)):
    """[Admin] Get a batch with its full list of inventory units (FIFO order)."""
    batch = db.execute(
        select(StockBatch).options(*_load_items).where(StockBatch.id == batch_id)
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock batch not found")
    return _to_detail(batch)


@router.put("/{batch_id}", response_model=StockBatchRead, dependencies=[Depends(require_admin)])
async def update_batch(
    batch_id: int, payload: StockBatchUpdate, db: Session = Depends(get_db)
):
    """[Admin] Update batch details (label, dates, fees)."""
    batch = db.execute(
        select(StockBatch).options(*_load_items).where(StockBatch.id == batch_id)
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock batch not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(batch, field, value)
    db.commit()
    # Reload with items to recompute totals
    batch = db.execute(
        select(StockBatch).options(*_load_items).where(StockBatch.id == batch_id)
    ).scalar_one()
    return _to_read(batch)


@router.delete(
    "/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_batch(batch_id: int, db: Session = Depends(get_db)):
    """[Admin] Delete a batch. Fails if units are still assigned."""
    batch = db.execute(
        select(StockBatch).options(*_load_items).where(StockBatch.id == batch_id)
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock batch not found")
    if batch.items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete a batch with {len(batch.items)} assigned unit(s). "
                   "Unassign all units first.",
        )
    db.delete(batch)
    db.commit()
