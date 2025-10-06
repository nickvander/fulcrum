from src.crud.base import CRUDBase
from src.models.supplier import Supplier
from src.schemas.supplier import SupplierCreate

class CRUDSupplier(CRUDBase[Supplier, SupplierCreate]):
    pass

supplier = CRUDSupplier(Supplier)
