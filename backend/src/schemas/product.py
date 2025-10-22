from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from ..schemas.custom_field import ProductCustomField
from ..schemas.inventory import InventoryItem as InventoryItemSchema, InventoryAdjustment as InventoryAdjustmentSchema
from ..schemas.product_variant import ProductVariant


# Schema for Product Images
class ProductImageBase(BaseModel):
    image_path: str
    is_primary: Optional[int] = 0
    source: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

class ProductImageCreate(ProductImageBase):
    product_id: int

class ProductImageUpdate(BaseModel):
    is_primary: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None

class ProductImage(ProductImageBase):
    id: int
    product_id: int

    model_config = ConfigDict(from_attributes=True)


# Schema for Products
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    properties: Optional[dict] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None



class Product(ProductBase):
    id: int
    supplier_id: Optional[int] = None
    images: List[ProductImage] = []
    inventory_items: List[InventoryItemSchema] = []
    inventory_adjustments: List[InventoryAdjustmentSchema] = []
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    custom_fields: List[ProductCustomField] = []
    variants: List[ProductVariant] = []

    @classmethod
    def from_orm(cls, obj):
        # Convert datetime objects to strings for JSON serialization
        data = {}
        for field_name in cls.model_fields:
            value = getattr(obj, field_name, None)
            if value is not None:
                # Handle nested datetime objects in related models
                if field_name in ['inventory_items', 'inventory_adjustments']:
                    if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                        # Convert lists of related objects using their own from_orm methods
                        converted_value = []
                        for item in value:
                            if hasattr(item, '__dict__') and not item.__dict__.get('_sa_instance_state'):
                                # If the item has custom fields, ensure datetime conversion
                                item_data = {}
                                for item_field in item.__dict__:
                                    if not item_field.startswith('_'):  # Skip private attributes
                                        item_val = getattr(item, item_field)
                                        if isinstance(item_val, datetime):
                                            item_data[item_field] = item_val.isoformat()
                                        else:
                                            item_data[item_field] = item_val
                                converted_value.append(item_data)
                            else:
                                # Use the from_orm method of the related schema
                                if field_name == 'inventory_items':
                                    # Use the InventoryItemSchema to convert the item
                                    from .inventory import InventoryItem as InventoryItemSchema
                                    try:
                                        converted_value.append(InventoryItemSchema.model_validate(item))
                                    except Exception:
                                        # Fallback to manual conversion if model_validate fails
                                        item_dict = {}
                                        for field in InventoryItemSchema.model_fields:
                                            item_val = getattr(item, field, None)
                                            if isinstance(item_val, datetime):
                                                item_dict[field] = item_val.isoformat()
                                            else:
                                                item_dict[field] = item_val
                                        converted_value.append(item_dict)
                                elif field_name == 'inventory_adjustments':
                                    # Use the InventoryAdjustmentSchema to convert the item
                                    from .inventory import InventoryAdjustment as InventoryAdjustmentSchema
                                    try:
                                        converted_value.append(InventoryAdjustmentSchema.model_validate(item))
                                    except Exception:
                                        # Fallback to manual conversion if model_validate fails
                                        item_dict = {}
                                        for field in InventoryAdjustmentSchema.model_fields:
                                            item_val = getattr(item, field, None)
                                            if isinstance(item_val, datetime):
                                                item_dict[field] = item_val.isoformat()
                                            else:
                                                item_dict[field] = item_val
                                        converted_value.append(item_dict)
                        data[field_name] = converted_value
                    else:
                        data[field_name] = value
                elif isinstance(value, datetime):
                    data[field_name] = value.isoformat()
                else:
                    data[field_name] = value
            else:
                data[field_name] = value
        return cls(**data)

    model_config = ConfigDict(from_attributes=True)