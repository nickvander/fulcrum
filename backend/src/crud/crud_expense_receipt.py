from src.crud.base import CRUDBase
from src.models.expense_receipt import ExpenseReceipt
from src.schemas import expense_receipt as expense_receipt_schema
from typing import List
from sqlalchemy.orm import Session

class CRUDExpenseReceipt(CRUDBase[ExpenseReceipt, expense_receipt_schema.ExpenseReceiptCreate, expense_receipt_schema.ExpenseReceiptUpdate]):
    def get_by_expense(self, db: Session, *, expense_id: int) -> List[ExpenseReceipt]:
        return db.query(self.model).filter(self.model.expense_id == expense_id).all()

expense_receipt = CRUDExpenseReceipt(ExpenseReceipt)
