from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class ExpenseBase(BaseModel):
    description: str
    amount: float
    currency: str = "USD"
    category: str
    is_custom_category: Optional[bool] = False
    date: date
    expense_type: str = "one_time"  # "one_time" or "recurring"
    recurrence_interval: Optional[str] = None  # "weekly", "monthly", "quarterly", "yearly"
    reference_number: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    # User who paid (for reimbursement tracking)
    paid_by_user_id: Optional[int] = None
    paid_by_name: Optional[str] = None  # For non-system users
    is_reimbursed: Optional[bool] = False
    # Optional associations
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    is_custom_category: Optional[bool] = None
    date: Optional[date] = None
    expense_type: Optional[str] = None
    recurrence_interval: Optional[str] = None
    reference_number: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    paid_by_user_id: Optional[int] = None
    paid_by_name: Optional[str] = None
    is_reimbursed: Optional[bool] = None
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None

class ExpenseInDBBase(ExpenseBase):
    id: int
    reimbursed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Expense(ExpenseInDBBase):
    pass

class ExpenseSummary(BaseModel):
    """Summary of expenses for a time period"""
    total_amount: float
    by_category: dict[str, float]
    by_type: dict[str, float]  # one_time vs recurring
    by_user: dict[str, float]  # Totals by user/contributor
    unreimbursed_total: float  # Total outstanding reimbursements
    count: int


