from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.crud import crud_expense
from src.schemas import expense as expense_schema
from src.api.dependencies import get_db

router = APIRouter()

@router.get("/", response_model=List[expense_schema.Expense])
def read_expenses(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve expenses.
    """
    expenses = crud_expense.expense.get_multi(db, skip=skip, limit=limit)
    return expenses

@router.post("/", response_model=expense_schema.Expense)
def create_expense(
    *,
    db: Session = Depends(get_db),
    expense_in: expense_schema.ExpenseCreate,
) -> Any:
    """
    Create new expense.
    """
    expense = crud_expense.expense.create(db, obj_in=expense_in)
    return expense

@router.put("/{id}", response_model=expense_schema.Expense)
def update_expense(
    *,
    db: Session = Depends(get_db),
    id: int,
    expense_in: expense_schema.ExpenseUpdate,
) -> Any:
    """
    Update an expense.
    """
    expense = crud_expense.expense.get(db, id=id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense = crud_expense.expense.update(db, db_obj=expense, obj_in=expense_in)
    return expense

@router.get("/{id}", response_model=expense_schema.Expense)
def read_expense(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get expense by ID.
    """
    expense = crud_expense.expense.get(db, id=id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.delete("/{id}", response_model=expense_schema.Expense)
def delete_expense(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Delete an expense.
    """
    expense = crud_expense.expense.get(db, id=id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense = crud_expense.expense.remove(db, id=id)
    return expense
