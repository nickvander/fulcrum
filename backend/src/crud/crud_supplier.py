from src.crud.base import CRUDBase
from src.models.supplier import Supplier
from src.schemas.supplier import SupplierCreate, SupplierUpdate

class CRUDSupplier(CRUDBase[Supplier, SupplierCreate, SupplierUpdate]):
    pass

supplier = CRUDSupplier(Supplier)
