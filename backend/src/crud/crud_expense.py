from src.crud.base import CRUDBase
from src.models.expense import Expense
from src.schemas.expense import ExpenseCreate, ExpenseUpdate

class CRUDExpense(CRUDBase[Expense, ExpenseCreate, ExpenseUpdate]):
    pass

expense = CRUDExpense(Expense)
