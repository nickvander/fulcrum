from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ExpenseReceiptBase(BaseModel):
    expense_id: int
    file_path: str
    file_name: Optional[str] = None
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None

class ExpenseReceiptCreate(ExpenseReceiptBase):
    pass

class ExpenseReceiptUpdate(BaseModel):
    pass

class ExpenseReceipt(ExpenseReceiptBase):
    id: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
