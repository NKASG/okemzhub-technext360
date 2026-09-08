from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.dependencies import get_current_user, get_db, require_admin
from app.models.expense import Expense, ExpenseStatus
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCreate, ExpenseRead, ExpenseStatusUpdate

router = APIRouter(prefix="/expenses", tags=["Expenses"])

_load_submitter = [selectinload(Expense.submitted_by)]


@router.get("/", response_model=list[ExpenseRead])
async def list_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List expenses for the current user's business.
    Owners (admins) see all; staff see only their own submissions."""
    query = (
        select(Expense)
        .options(*_load_submitter)
        .where(Expense.business_id == current_user.business_id)
    )
    if current_user.role == UserRole.staff:
        query = query.where(Expense.submitted_by_user_id == current_user.id)
    return db.execute(query).scalars().all()


@router.post("/", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
async def submit_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an expense. Owner (admin) expenses are auto-approved."""
    auto_status = (
        ExpenseStatus.approved if current_user.role == UserRole.admin else ExpenseStatus.pending
    )
    expense = Expense(
        submitted_by_user_id=current_user.id,
        business_id=current_user.business_id,
        amount=payload.amount,
        description=payload.description,
        status=auto_status,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return db.execute(
        select(Expense).options(*_load_submitter).where(Expense.id == expense.id)
    ).scalar_one()


@router.get("/{expense_id}", response_model=ExpenseRead)
async def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an expense. Scoped to the user's business; staff can only view their own."""
    expense = db.execute(
        select(Expense).options(*_load_submitter).where(Expense.id == expense_id)
    ).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this expense",
        )
    if current_user.role == UserRole.staff and expense.submitted_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to view this expense",
        )
    return expense


@router.patch("/{expense_id}/status", response_model=ExpenseRead)
async def update_expense_status(
    expense_id: int,
    payload: ExpenseStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Approve or reject a pending expense in your business."""
    expense = db.execute(
        select(Expense).options(*_load_submitter).where(Expense.id == expense_id)
    ).scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to review this expense",
        )
    expense.status = payload.status
    db.commit()
    db.refresh(expense)
    return db.execute(
        select(Expense).options(*_load_submitter).where(Expense.id == expense_id)
    ).scalar_one()


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """[Owner] Delete an expense record in your business."""
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised to delete this expense",
        )
    db.delete(expense)
    db.commit()
