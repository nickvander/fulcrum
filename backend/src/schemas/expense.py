from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

class ExpenseBase(BaseModel):
    description: str
    amount: float
    currency: str = "USD"
    category: str
    date: date
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
    date: Optional[date] = None
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None

class ExpenseInDBBase(ExpenseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Expense(ExpenseInDBBase):
    pass
