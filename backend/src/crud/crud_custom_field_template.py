from src.crud.base import CRUDBase
from src.models.custom_field_template import CustomFieldTemplate
from src.schemas.product_template import CustomFieldTemplateCreate, CustomFieldTemplateUpdate
from typing import List


class CRUDCustomFieldTemplate(CRUDBase[CustomFieldTemplate, CustomFieldTemplateCreate, CustomFieldTemplateUpdate]):
    def get_by_template_id(self, db, *, template_id: int) -> List[CustomFieldTemplate]:
        """Get all custom field templates for a specific template."""
        return db.query(self.model).filter(self.model.template_id == template_id).all()


custom_field_template = CRUDCustomFieldTemplate(CustomFieldTemplate)