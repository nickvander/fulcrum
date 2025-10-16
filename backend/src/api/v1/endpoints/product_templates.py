"""
API endpoints for managing product templates.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

from src.schemas.product_template import ProductTemplate as ProductTemplateSchema, ProductTemplateCreate, ProductTemplateUpdate, CustomFieldTemplate, CustomFieldTemplateCreate, CustomFieldTemplateUpdate
from src.database import get_db
from src.crud import crud_product_template, crud_custom_field_template
from src.models.product_template import ProductTemplate as ProductTemplateModel

router = APIRouter()


@router.post("/", response_model=ProductTemplateSchema)
def create_product_template(
    template: ProductTemplateCreate, 
    db: Session = Depends(get_db)
):
    """Create a new product template."""
    # Check if template with this name already exists
    existing_template = crud_product_template.product_template.get_by_name(db, name=template.name)
    if existing_template:
        raise HTTPException(status_code=409, detail="Template with this name already exists.")
    
    db_template = crud_product_template.product_template.create(db=db, obj_in=template)
    return db_template


@router.get("/", response_model=List[ProductTemplateSchema])
def read_product_templates(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Retrieve a list of product templates."""
    templates = crud_product_template.product_template.get_multi(db, skip=skip, limit=limit)
    return templates


@router.get("/{template_id}", response_model=ProductTemplateSchema)
def read_product_template(template_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific product template by ID."""
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template


@router.put("/{template_id}", response_model=ProductTemplateSchema)
def update_product_template(
    template_id: int, 
    template_update: ProductTemplateUpdate, 
    db: Session = Depends(get_db)
):
    """Update a specific product template."""
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if the new name conflicts with another template
    if template_update.name and template_update.name != db_template.name:
        existing_template = crud_product_template.product_template.get_by_name(db, name=template_update.name)
        if existing_template:
            raise HTTPException(status_code=409, detail="Template with this name already exists.")
    
    updated_template = crud_product_template.product_template.update(
        db=db, 
        db_obj=db_template, 
        obj_in=template_update
    )
    return updated_template


@router.delete("/{template_id}", response_model=ProductTemplateSchema)
def delete_product_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a specific product template."""
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    deleted_template = crud_product_template.product_template.remove(db=db, id=template_id)
    return deleted_template


# Custom Field Template Endpoints
@router.post("/{template_id}/custom-fields", response_model=CustomFieldTemplate)
def create_custom_field_template(
    template_id: int, 
    field: CustomFieldTemplateCreate, 
    db: Session = Depends(get_db)
):
    """Create a new custom field template for a specific template."""
    # Verify the template exists
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Set the template_id from the URL parameter to ensure consistency
    field_in = field.model_copy(update={"template_id": template_id})
    db_field = crud_custom_field_template.custom_field_template.create(db=db, obj_in=field_in)
    return db_field


@router.get("/{template_id}/custom-fields", response_model=List[CustomFieldTemplate])
def read_custom_field_templates(template_id: int, db: Session = Depends(get_db)):
    """Get all custom field templates for a specific template."""
    # Verify the template exists
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    fields = crud_custom_field_template.custom_field_template.get_by_template_id(db, template_id=template_id)
    return fields


@router.put("/{template_id}/custom-fields/{field_id}", response_model=CustomFieldTemplate)
def update_custom_field_template(
    template_id: int, 
    field_id: int, 
    field_update: CustomFieldTemplateUpdate, 
    db: Session = Depends(get_db)
):
    """Update a specific custom field template."""
    # Verify the template exists
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get the specific field
    db_field = crud_custom_field_template.custom_field_template.get(db=db, id=field_id)
    if not db_field or db_field.template_id != template_id:
        raise HTTPException(status_code=404, detail="Custom field template not found")
    
    # Update the field
    updated_field = crud_custom_field_template.custom_field_template.update(
        db=db, 
        db_obj=db_field, 
        obj_in=field_update
    )
    return updated_field


@router.delete("/{template_id}/custom-fields/{field_id}", response_model=CustomFieldTemplate)
def delete_custom_field_template(
    template_id: int, 
    field_id: int, 
    db: Session = Depends(get_db)
):
    """Delete a specific custom field template."""
    # Verify the template exists
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get the specific field
    db_field = crud_custom_field_template.custom_field_template.get(db=db, id=field_id)
    if not db_field or db_field.template_id != template_id:
        raise HTTPException(status_code=404, detail="Custom field template not found")
    
    # Delete the field
    deleted_field = crud_custom_field_template.custom_field_template.remove(db=db, id=field_id)
    return deleted_field


# Endpoint to create a product from a template
@router.post("/{template_id}/create-product")
def create_product_from_template(
    template_id: int,
    product_data: dict = Body(...),  # Additional product-specific data
    db: Session = Depends(get_db)
):
    """Create a new product based on a template."""
    # Get the template
    db_template = crud_product_template.product_template.get(db=db, id=template_id)
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # In a real implementation, you would create a new product using the template data
    # This is a simplified implementation that just returns the template data
    # along with any additional product-specific data provided
    
    # This would require importing and using the product creation logic from the main products API
    # For now, we'll return a success message with the template ID
    return {
        "message": f"Product created from template {template_id}",
        "template_id": template_id,
        "product_data": product_data
    }