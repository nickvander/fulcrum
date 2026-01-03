from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from src.crud.base import CRUDBase
from src.models.product import Product, BundleComponent
from src.schemas.product import ProductCreate, ProductUpdate
from typing import List, Any

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def get(self, db: Session, id: int) -> Product | None:
        return db.query(self.model).options(
            joinedload(self.model.images),
            joinedload(self.model.marketplace_listings),
            joinedload(self.model.inventory_items),
            joinedload(self.model.variants),
            # Load bundle components and their nested component product + inventory
            joinedload(self.model.bundle_components).joinedload(BundleComponent.component).joinedload(Product.inventory_items),
            # Load bundles this product is part of + their inventory
            joinedload(self.model.part_of_bundles).joinedload(BundleComponent.bundle).joinedload(Product.inventory_items)
        ).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, filters: dict = {}
    ) -> List[Product]:
        query = db.query(self.model).options(
            joinedload(self.model.images),
            joinedload(self.model.marketplace_listings),
            joinedload(self.model.inventory_items)
        )
        
        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if field == 'search_term':
                    from sqlalchemy import or_
                    query = query.filter(
                        or_(
                            self.model.name.ilike(f"%{value}%"),
                            self.model.sku.ilike(f"%{value}%"),
                            self.model.description.ilike(f"%{value}%")
                        )
                    )
                elif field == 'min_price':
                    query = query.filter(self.model.default_resale_price >= value)
                elif field == 'max_price':
                    query = query.filter(self.model.default_resale_price <= value)
                elif field == 'min_stock':
                     # optimized stock query needed
                     pass
                elif field == 'max_stock':
                     # optimized stock query needed
                     pass
                elif field == 'category':
                    query = query.filter(self.model.category == value)
                elif field == 'brand':
                    query = query.filter(self.model.brand == value)
                elif isinstance(value, dict) and 'min' in value and 'max' in value:
                     if hasattr(self.model, field):
                        attr = getattr(self.model, field)
                        query = query.filter(attr >= value['min'], attr <= value['max'])
                elif hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        
        return (
            query
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_paginated(
        self, db: Session, *, skip: int = 0, limit: int = 10, filters: dict = {}
    ) -> dict:
        print(f"DEBUG: get_multi_paginated called with filters={filters}")
        query = db.query(self.model).options(
            joinedload(self.model.images),
            joinedload(self.model.marketplace_listings),
            joinedload(self.model.inventory_items)
        )
        
        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if field == 'search_term':
                    from sqlalchemy import or_
                    query = query.filter(
                        or_(
                            self.model.name.ilike(f"%{value}%"),
                            self.model.sku.ilike(f"%{value}%"),
                            self.model.description.ilike(f"%{value}%")
                        )
                    )
                elif field == 'min_price':
                    query = query.filter(self.model.default_resale_price >= value)
                elif field == 'max_price':
                    query = query.filter(self.model.default_resale_price <= value)
                elif field == 'min_stock':
                     # optimized stock query needed
                     from src.models.inventory import InventoryItem
                     from sqlalchemy import func
                     subquery = (
                         db.query(InventoryItem.product_id)
                         .group_by(InventoryItem.product_id)
                         .having(func.sum(InventoryItem.quantity) >= value)
                         .subquery()
                     )
                     query = query.filter(self.model.id.in_(subquery))
                elif field == 'max_stock':
                     # optimized stock query needed
                     from src.models.inventory import InventoryItem
                     from sqlalchemy import func
                     # This includes products with NO inventory items (count 0) if value >= 0
                     # But solving "no inventory items" via having is tricky in one go
                     # Simplified: products with inventory sum <= value
                     
                     # First, get products with inventory > value
                     subquery_exceed = (
                         db.query(InventoryItem.product_id)
                         .group_by(InventoryItem.product_id)
                         .having(func.sum(InventoryItem.quantity) > value)
                         .subquery()
                     )
                     # Filter OUT those products
                     query = query.filter(self.model.id.not_in(subquery_exceed))

                elif field == 'category':
                    query = query.filter(self.model.category == value)
                elif field == 'brand':
                    query = query.filter(self.model.brand == value)
                elif field == 'is_bundle':
                    if value is not None:
                        query = query.filter(self.model.is_bundle == value)
                elif isinstance(value, dict) and 'min' in value and 'max' in value:
                     if hasattr(self.model, field):
                        attr = getattr(self.model, field)
                        query = query.filter(attr >= value['min'], attr <= value['max'])
                elif hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        
        total_items = query.count()
        data = query.offset(skip).limit(limit).all()
        
        current_page = (skip // limit) + 1
        total_pages = (total_items + limit - 1) // limit  # Ceiling division
        
        return {
            "data": data,
            "currentPage": current_page,
            "totalPages": total_pages,
            "totalItems": total_items,
            "pageSize": limit,
            "hasNextPage": current_page < total_pages,
            "hasPrevPage": current_page > 1
        }

    def get_by_sku(self, db: Session, *, sku: str) -> Product | None:
        return db.query(Product).filter(Product.sku == sku).first()

    def get_by_barcode(self, db: Session, *, barcode_value: str) -> Product | None:
        return db.query(Product).filter(
            (Product.barcode_value == barcode_value) | 
            (Product.qrcode_value == barcode_value) |
            (Product.sku == barcode_value) # Fallback to SKU for robustness
        ).first()

    def generate_unique_sku(self, db: Session, prefix: str = "PRD") -> str:
        """Generate a unique SKU with format: PREFIX-YYYYMMDD-XXXX"""
        import secrets
        from datetime import datetime
        
        date_part = datetime.now().strftime("%Y%m%d")
        
        # Try up to 10 times to generate a unique SKU
        for _ in range(10):
            random_part = secrets.token_hex(2).upper()  # 4 hex characters
            sku = f"{prefix}-{date_part}-{random_part}"
            
            if not self.get_by_sku(db, sku=sku):
                return sku
        
        # Fallback with timestamp for uniqueness
        import time
        return f"{prefix}-{date_part}-{int(time.time()) % 10000:04d}"

    def create(self, db: Session, *, obj_in: ProductCreate) -> Product:
        obj_in_data = obj_in.model_dump(exclude={"bundle_components"})
        bundle_components = obj_in.bundle_components

        # Auto-generate SKU if not provided
        if not obj_in_data.get("sku"):
            obj_in_data["sku"] = self.generate_unique_sku(db)
        elif self.get_by_sku(db, sku=obj_in_data["sku"]):
            raise HTTPException(status_code=409, detail="Product with this SKU already exists.")
        
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush() # Get the ID for the new product
        
        # Generate Barcodes & QR Codes
        try:
            from src.services.barcode_service import BarcodeService
            import os
            
            # Ensure directories exist
            barcode_dir = "uploads/barcodes"
            qr_dir = "uploads/qrcodes"
            os.makedirs(barcode_dir, exist_ok=True)
            os.makedirs(qr_dir, exist_ok=True)

            barcode_bytes, qr_bytes = BarcodeService.generate_codes_for_product(db_obj.id, db_obj.sku)
            
            if barcode_bytes:
                b_filename = f"{db_obj.sku}.png"
                b_path = os.path.join(barcode_dir, b_filename)
                with open(b_path, "wb") as f:
                    f.write(barcode_bytes)
                db_obj.barcode_image_url = f"/uploads/barcodes/{b_filename}"
                db_obj.barcode_value = db_obj.sku # Code128 uses SKU by default in BarcodeService
            
            if qr_bytes:
                q_filename = f"{db_obj.id}_qr.png"
                q_path = os.path.join(qr_dir, q_filename)
                with open(q_path, "wb") as f:
                    f.write(qr_bytes)
                db_obj.qrcode_image_url = f"/uploads/qrcodes/{q_filename}"
                db_obj.qrcode_value = f"fulcrum-product:{db_obj.id}" # Standard logic in BarcodeService
                
        except Exception as e:
            print(f"Error generating barcodes for product {db_obj.id}: {e}")
            # Don't fail the transaction just for barcodes
        
        if bundle_components:
            for bc in bundle_components:
                db_bc = BundleComponent(bundle_id=db_obj.id, **bc.model_dump())
                db.add(db_bc)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Product, obj_in: ProductUpdate | dict[str, Any]
    ) -> Product:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True, exclude={"bundle_components"})
        
        if not isinstance(obj_in, dict) and obj_in.bundle_components is not None:
            # Clear existing bundle components
            db.query(BundleComponent).filter(BundleComponent.bundle_id == db_obj.id).delete()
            # Add new bundle components
            for bc in obj_in.bundle_components:
                db_bc = BundleComponent(bundle_id=db_obj.id, **bc.model_dump())
                db.add(db_bc)
        
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_similar(self, db: Session, *, embedding: list[float], limit: int = 10) -> list[Product]:
        """
        Performs a vector similarity search for products.
        """
        return db.query(Product).order_by(Product.embedding.l2_distance(embedding)).limit(limit).all()

product = CRUDProduct(Product)
