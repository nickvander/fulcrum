from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..schemas.custom_field import ProductCustomField
from ..schemas.inventory import InventoryItem as InventoryItemSchema, InventoryAdjustment as InventoryAdjustmentSchema
from ..schemas.product_variant import ProductVariant
from ..schemas.marketplace import MarketplaceListing


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


# Schema for Bundle Components
class BundleComponentBase(BaseModel):
    component_id: int
    quantity: int = 1

class BundleComponentCreate(BundleComponentBase):
    pass

class BundleComponent(BundleComponentBase):
    id: int
    bundle_id: int
    bundle_name: Optional[str] = None
    bundle_image: Optional[str] = None
    component_name: Optional[str] = None
    component_image: Optional[str] = None
    bundle_stock: Optional[int] = 0
    component_stock: Optional[int] = 0
    component_cost: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)


# Schema for Products
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: Optional[str] = None  # Optional - auto-generated if not provided
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    # Barcodes
    # Barcodes
    barcode_image_url: Optional[str] = None
    barcode_value: Optional[str] = None
    qrcode_image_url: Optional[str] = None
    qrcode_value: Optional[str] = None
    
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    average_cost: Optional[float] = None
    is_bundle: bool = False

class ProductCreate(ProductBase):
    bundle_components: Optional[List[BundleComponentCreate]] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    default_resale_price: Optional[float] = None
    cost_price: Optional[float] = None
    average_cost: Optional[float] = None
    properties: Optional[dict] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    weight: Optional[float] = None
    is_bundle: Optional[bool] = None
    bundle_components: Optional[List[BundleComponentCreate]] = None
    # Allow manually saving/updating generated barcodes
    barcode_value: Optional[str] = None
    qrcode_value: Optional[str] = None
    barcode_image_url: Optional[str] = None
    qrcode_image_url: Optional[str] = None



class Product(ProductBase):
    id: int
    supplier_id: Optional[int] = None
    images: List[ProductImage] = []
    primary_image: Optional[ProductImage] = None
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
    marketplace_listings: List[MarketplaceListing] = []
    bundle_components: List[BundleComponent] = []
    part_of_bundles: List[BundleComponent] = []
    
    sales_velocity: Optional[float] = None
    days_of_inventory: Optional[float] = None
    low_inventory_threshold: Optional[int] = None
    low_inventory_threshold: Optional[int] = None
    low_stock_quantity_threshold: Optional[int] = None
    stock_quantity: Optional[int] = None
    active_campaign_count: int = 0
    
    # Marketing data
    active_campaigns: List[Dict[str, Any]] = []
    quick_posts: List[Dict[str, Any]] = []
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

class PaginatedProducts(BaseModel):
    data: List[Product]
    currentPage: int
    totalPages: int
    totalItems: int
    pageSize: int
    hasNextPage: bool
    hasPrevPage: bool

class ProductPurchaseHistory(BaseModel):
    po_id: int
    date: datetime
    supplier_name: str
    quantity: float
    unit_cost: float
    base_cost: Optional[float] = 0.0
    shipping_allocated: Optional[float] = 0.0
    taxes_allocated: Optional[float] = 0.0
    other_allocated: Optional[float] = 0.0
    status: str

    model_config = ConfigDict(from_attributes=True)