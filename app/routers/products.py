from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.inventory import InventoryItem, ItemStatus
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductReadWithStock, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductRead])
async def list_products(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """List all products in the catalog."""
    return db.execute(select(Product)).scalars().all()


@router.post(
    "/",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """[Admin] Add a new product to the catalog."""
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductReadWithStock)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """Get a product with its current available-unit count."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    available_units: int = db.execute(
        select(func.count()).where(
            InventoryItem.product_id == product_id,
            InventoryItem.status == ItemStatus.available,
        )
    ).scalar_one()

    product_dict = ProductRead.model_validate(product).model_dump()
    return ProductReadWithStock(**product_dict, available_units=available_units)


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_admin)],
)
async def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
):
    """[Admin] Update product details."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """[Admin] Remove a product from the catalog."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.delete(product)
    db.commit()
