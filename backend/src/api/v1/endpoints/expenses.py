from typing import Any, List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session


from src.crud import crud_expense
from src.models.expense import Expense as ExpenseModel
from src.schemas import expense as expense_schema
from src.api.dependencies import get_db

router = APIRouter()

# Default expense categories
DEFAULT_CATEGORIES = [
    "Marketing", "Software", "Rent", "Shipping", "Office Supplies",
    "Legal", "Gas/Transportation", "Utilities", "Packing Materials", "Other"
]

@router.get("/summary", response_model=expense_schema.ExpenseSummary)
def get_expense_summary(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Start date for summary period"),
    end_date: Optional[date] = Query(None, description="End date for summary period"),
) -> Any:
    """
    Get expense summary for a time period.
    """
    query = db.query(ExpenseModel)
    
    if start_date:
        query = query.filter(ExpenseModel.date >= start_date)
    if end_date:
        query = query.filter(ExpenseModel.date <= end_date)
    
    expenses = query.all()
    
    # Calculate totals
    total_amount = sum(e.amount for e in expenses)
    
    # Group by category
    by_category: dict[str, float] = {}
    for e in expenses:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount
    
    # Group by type (one_time vs recurring)
    by_type: dict[str, float] = {"one_time": 0, "recurring": 0}
    for e in expenses:
        expense_type = e.expense_type or "one_time"
        by_type[expense_type] = by_type.get(expense_type, 0) + e.amount
    
    # Group by user/contributor
    by_user: dict[str, float] = {}
    unreimbursed_total = 0.0
    for e in expenses:
        # Use paid_by_name if set, otherwise try to get user name
        user_name = e.paid_by_name or "Company"
        by_user[user_name] = by_user.get(user_name, 0) + e.amount
        if not e.is_reimbursed and (e.paid_by_user_id or e.paid_by_name):
            unreimbursed_total += e.amount
    
    return expense_schema.ExpenseSummary(
        total_amount=total_amount,
        by_category=by_category,
        by_type=by_type,
        by_user=by_user,
        unreimbursed_total=unreimbursed_total,
        count=len(expenses)
    )

@router.get("/categories", response_model=List[str])
def get_expense_categories(
    db: Session = Depends(get_db),
) -> Any:
    """
    Get all expense categories (default + custom).
    """
    # Get unique custom categories from database
    custom_cats = db.query(ExpenseModel.category).filter(
        ExpenseModel.is_custom_category
    ).distinct().all()
    
    custom_list = [c[0] for c in custom_cats if c[0]]
    
    # Combine default + custom, dedupe
    all_categories = list(set(DEFAULT_CATEGORIES + custom_list))
    return sorted(all_categories)

@router.get("/", response_model=List[expense_schema.Expense])
def read_expenses(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(None),
    expense_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> Any:
    """
    Retrieve expenses with optional filters.
    """
    query = db.query(ExpenseModel)
    
    if category:
        query = query.filter(ExpenseModel.category == category)
    if expense_type:
        query = query.filter(ExpenseModel.expense_type == expense_type)
    if start_date:
        query = query.filter(ExpenseModel.date >= start_date)
    if end_date:
        query = query.filter(ExpenseModel.date <= end_date)
    
    expenses = query.order_by(ExpenseModel.date.desc()).offset(skip).limit(limit).all()
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

