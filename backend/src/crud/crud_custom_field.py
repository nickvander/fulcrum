from ..models.custom_field import CustomField, ProductCustomField
from ..schemas.custom_field import CustomFieldCreate, CustomFieldUpdate, ProductCustomFieldCreate, ProductCustomFieldUpdate
from .base import CRUDBase

class CRUDCustomField(CRUDBase[CustomField, CustomFieldCreate, CustomFieldUpdate]):
    pass

custom_field = CRUDCustomField(CustomField)

class CRUDProductCustomField(CRUDBase[ProductCustomField, ProductCustomFieldCreate, ProductCustomFieldUpdate]):
    pass

product_custom_field = CRUDProductCustomField(ProductCustomField)
