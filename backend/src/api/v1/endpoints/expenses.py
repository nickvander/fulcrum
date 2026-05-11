from typing import Any, List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session


from src.crud import crud_expense
from src.models.expense import Expense as ExpenseModel
from src.schemas import expense as expense_schema
from src.api.dependencies import get_db
import os
import uuid
import shutil
from fastapi import File, UploadFile
from src.crud.crud_expense_receipt import expense_receipt as crud_expense_receipt
from src.schemas import expense_receipt as receipt_schema
from pydantic import BaseModel

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
    filters = []
    
    if start_date:
        filters.append(ExpenseModel.date >= start_date)
    if end_date:
        filters.append(ExpenseModel.date <= end_date)

    summary_query = db.query(
        func.coalesce(func.sum(ExpenseModel.amount), 0.0).label("total_amount"),
        func.count(ExpenseModel.id).label("count"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (~ExpenseModel.is_reimbursed)
                        & (
                            ExpenseModel.paid_by_user_id.isnot(None)
                            | ExpenseModel.paid_by_name.isnot(None)
                        ),
                        ExpenseModel.amount,
                    ),
                    else_=0.0,
                )
            ),
            0.0,
        ).label("unreimbursed_total"),
    )
    if filters:
        summary_query = summary_query.filter(*filters)
    summary = summary_query.one()

    category_query = db.query(
        ExpenseModel.category,
        func.coalesce(func.sum(ExpenseModel.amount), 0.0),
    )
    type_query = db.query(
        func.coalesce(ExpenseModel.expense_type, "one_time"),
        func.coalesce(func.sum(ExpenseModel.amount), 0.0),
    )
    user_query = db.query(
        func.coalesce(ExpenseModel.paid_by_name, "Company"),
        func.coalesce(func.sum(ExpenseModel.amount), 0.0),
    )
    if filters:
        category_query = category_query.filter(*filters)
        type_query = type_query.filter(*filters)
        user_query = user_query.filter(*filters)

    by_category = {
        category: float(amount or 0.0)
        for category, amount in category_query.group_by(ExpenseModel.category).all()
    }
    by_type = {"one_time": 0.0, "recurring": 0.0}
    by_type.update(
        {
            expense_type: float(amount or 0.0)
            for expense_type, amount in type_query.group_by(
                func.coalesce(ExpenseModel.expense_type, "one_time")
            ).all()
        }
    )
    by_user = {
        user_name: float(amount or 0.0)
        for user_name, amount in user_query.group_by(
            func.coalesce(ExpenseModel.paid_by_name, "Company")
        ).all()
    }
    
    return expense_schema.ExpenseSummary(
        total_amount=float(summary.total_amount or 0.0),
        by_category=by_category,
        by_type=by_type,
        by_user=by_user,
        unreimbursed_total=float(summary.unreimbursed_total or 0.0),
        count=int(summary.count or 0)
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


# --- Receipt Management ---


UPLOAD_RECEIPT_DIR = "uploads/receipts"

@router.post("/{id}/receipts", response_model=receipt_schema.ExpenseReceipt)
async def upload_receipt(
    *,
    db: Session = Depends(get_db),
    id: int,
    file: UploadFile = File(...),
):
    """
    Upload a receipt for an Expense.
    """
    expense = crud_expense.expense.get(db, id=id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Validate file type (image or pdf)
    allowed_types = {".jpg", ".jpeg", ".png", ".pdf", ".heic"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_types}")

    # Ensure upload dir exists
    save_dir = f"{UPLOAD_RECEIPT_DIR}/{id}"
    os.makedirs(save_dir, exist_ok=True)
    
    # Secure filename
    secure_name = f"{uuid.uuid4().hex}{file_ext}"
    file_path = f"{save_dir}/{secure_name}"
    
    # Save file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    created = crud_expense_receipt.create(db, obj_in=receipt_schema.ExpenseReceiptCreate(
        expense_id=id,
        file_path=file_path,
        file_name=file.filename,
        content_type=file.content_type,
        file_size_bytes=os.path.getsize(file_path)
    ))
    return created

@router.get("/{id}/receipts", response_model=List[receipt_schema.ExpenseReceipt])
def list_receipts(
    *,
    db: Session = Depends(get_db),
    id: int,
):
    """
    List receipts for an Expense.
    """
    return crud_expense_receipt.get_by_expense(db, expense_id=id)

@router.delete("/receipts/{receipt_id}", response_model=dict)
def delete_receipt(
    *,
    db: Session = Depends(get_db),
    receipt_id: int,
):
    """
    Delete a receipt.
    """
    receipt = crud_expense_receipt.get(db, id=receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Delete file
    if os.path.exists(receipt.file_path):
        try:
            os.remove(receipt.file_path)
        except OSError:
            pass
            
    crud_expense_receipt.remove(db, id=receipt_id)
    return {"message": "Receipt deleted"}

# --- AI Receipt Parsing ---


class ReceiptItem(BaseModel):
    description: str
    quantity: float
    amount: float

class ReceiptExtractionResult(BaseModel):
    merchant_name: str | None = None
    receipt_number: str | None = None
    date: str | None = None
    currency: str = "USD"
    total_amount: float = 0.0
    tax_amount: float = 0.0
    tip_amount: float = 0.0
    category: str | None = None
    items: List[ReceiptItem] = []
    confidence: float = 0.0

@router.post("/parse-receipt", response_model=ReceiptExtractionResult)
async def parse_receipt(
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Parse a receipt using AI to extract details.
    """
    from src.services.adk.manager import ADKManager
    from src.services.adk.orchestrator import AgentOrchestrator
    from src.crud.crud_store_settings import store_settings as crud_store_settings

    # Check Settings
    settings = crud_store_settings.get_settings(db)
    if not settings or not settings.ai_enabled:
        raise HTTPException(status_code=400, detail="AI features disabled.")

    # Read file
    content = await file.read()
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    mime_type = file.content_type or "application/octet-stream"
    
    # Map common extensions if mime type generic
    if mime_type == "application/octet-stream":
        if file_ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif file_ext == ".png":
            mime_type = "image/png"
        elif file_ext == ".pdf":
            mime_type = "application/pdf"

    # Orchestrator
    adk_manager = ADKManager(db)
    orchestrator = AgentOrchestrator(adk_manager)
    
    result = await orchestrator.parse_receipt(content, mime_type)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result
