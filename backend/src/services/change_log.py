"""
Change logging utility for tracking entity modifications.

This provides a simple interface to log changes to EntityChangeLog 
with source attribution (direct_edit, sheets_import, api).
"""
from sqlalchemy.orm import Session
from typing import Optional, Any
from src.models.pending_sync import EntityChangeLog


def log_entity_change(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    entity_name: Optional[str],
    field: str,
    old_value: Any,
    new_value: Any,
    source: str,
    changed_by_id: int,
    source_batch_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> EntityChangeLog:
    """
    Log a single field change to the EntityChangeLog.
    
    Args:
        entity_type: Type of entity (product, supplier, etc.)
        entity_id: ID of the entity
        entity_name: Display name for readability
        field: Name of the changed field
        old_value: Previous value
        new_value: New value
        source: Origin of change (direct_edit, sheets_import, api)
        changed_by_id: User ID who made the change
        source_batch_id: Optional SyncBatch ID if from import
        ip_address: Optional IP address
    """
    # Convert values to strings for storage
    old_str = str(old_value) if old_value is not None else None
    new_str = str(new_value) if new_value is not None else None
    
    log_entry = EntityChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        field=field,
        old_value=old_str,
        new_value=new_str,
        source=source,
        source_batch_id=source_batch_id,
        changed_by_id=changed_by_id,
        ip_address=ip_address,
    )
    db.add(log_entry)
    return log_entry


def log_product_changes(
    db: Session,
    *,
    product_id: int,
    product_name: str,
    old_values: dict,
    new_values: dict,
    source: str,
    changed_by_id: int,
    source_batch_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> list[EntityChangeLog]:
    """
    Log multiple field changes for a product.
    
    Compares old_values and new_values dicts, only logs fields that changed.
    
    Args:
        old_values: Dict of field -> previous value
        new_values: Dict of field -> new value (only changed fields)
        
    Returns:
        List of created EntityChangeLog entries
    """
    entries = []
    
    # Fields we want to track changes for
    trackable_fields = {
        'name', 'cost_price', 'default_resale_price', 'sku', 
        'description', 'category', 'brand', 'weight', 'dimensions'
    }
    
    for field, new_value in new_values.items():
        if field not in trackable_fields:
            continue
            
        old_value = old_values.get(field)
        
        # Skip if values are the same
        if old_value == new_value:
            continue
            
        entry = log_entity_change(
            db,
            entity_type="product",
            entity_id=product_id,
            entity_name=product_name,
            field=field,
            old_value=old_value,
            new_value=new_value,
            source=source,
            changed_by_id=changed_by_id,
            source_batch_id=source_batch_id,
            ip_address=ip_address,
        )
        entries.append(entry)
    
    return entries
