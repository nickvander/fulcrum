from src.crud.base import CRUDBase
from src.models.product_template import ProductTemplate
from src.schemas.product_template import ProductTemplateCreate, ProductTemplateUpdate



class CRUDProductTemplate(CRUDBase[ProductTemplate, ProductTemplateCreate, ProductTemplateUpdate]):
    def get_by_name(self, db, *, name: str) -> ProductTemplate | None:
        """Get a template by its name."""
        return db.query(self.model).filter(self.model.name == name).first()


product_template = CRUDProductTemplate(ProductTemplate)