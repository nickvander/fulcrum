from typing import Dict, Any
from sqlalchemy.orm import Session

from ..models.custom_field import CustomField, ProductCustomField
from ..schemas.custom_field import CustomFieldCreate, CustomFieldUpdate, ProductCustomFieldCreate, ProductCustomFieldUpdate
from .base import CRUDBase

class CRUDCustomField(CRUDBase[CustomField, CustomFieldCreate, CustomFieldUpdate]):
    pass

custom_field = CRUDCustomField(CustomField)

class CRUDProductCustomField(CRUDBase[ProductCustomField, ProductCustomFieldCreate, ProductCustomFieldUpdate]):
    def save_for_product(self, db: Session, *, product_id: int, custom_fields_in: Dict[str, Any]):
        for field_id, value in custom_fields_in.items():
            # Check if a value already exists for this product and custom field
            existing_value = db.query(self.model).filter(
                self.model.product_id == product_id,
                self.model.custom_field_id == int(field_id)
            ).first()

            if existing_value:
                # Update existing value
                update_data = {"value": str(value)}
                self.update(db, db_obj=existing_value, obj_in=update_data)
            else:
                # Create new value
                create_data = {
                    "product_id": product_id,
                    "custom_field_id": int(field_id),
                    "value": str(value)
                }
                self.create(db, obj_in=create_data)

product_custom_field = CRUDProductCustomField(ProductCustomField)
