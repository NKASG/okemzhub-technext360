from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.dependencies import get_current_user, get_db, require_admin
from app.models.expense import Expense
from app.models.inventory_request import InventoryRequest
from app.models.sale import Sale
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user


@router.get("/", response_model=list[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] List staff and admin accounts within your business."""
    return db.execute(
        select(User).where(User.business_id == current_user.business_id)
    ).scalars().all()


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Create a new user account within your business."""
    if db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )
    user = User(
        name=payload.name,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        monthly_sales_target=payload.monthly_sales_target,
        business_id=current_user.business_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Get a single user in your business by ID."""
    user = db.get(User, user_id)
    if not user or user.business_id != current_user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Update a user's role or sales target within your business."""
    user = db.get(User, user_id)
    if not user or user.business_id != current_user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Delete a user account within your business.
    The user's sales, expenses and stock requests are preserved and reassigned
    to you (the owner) so the business books stay intact."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    user = db.get(User, user_id)
    if not user or user.business_id != current_user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Reassign the user's records to the owner before deletion (NOT NULL FKs).
    db.execute(
        update(Sale)
        .where(Sale.sold_by_user_id == user_id)
        .values(sold_by_user_id=current_user.id)
    )
    db.execute(
        update(Expense)
        .where(Expense.submitted_by_user_id == user_id)
        .values(submitted_by_user_id=current_user.id)
    )
    db.execute(
        update(InventoryRequest)
        .where(InventoryRequest.requested_by_user_id == user_id)
        .values(requested_by_user_id=current_user.id)
    )
    db.delete(user)
    db.commit()
