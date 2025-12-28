from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from src.crud.base import CRUDBase
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate
from typing import List

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def get(self, db: Session, id: int) -> Product | None:
        return db.query(self.model).options(joinedload(self.model.images)).filter(self.model.id == id).first()

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
        # Auto-generate SKU if not provided
        if not obj_in.sku:
            generated_sku = self.generate_unique_sku(db)
            # Create a copy with the generated SKU
            obj_in = ProductCreate(**{**obj_in.model_dump(), "sku": generated_sku})
        elif self.get_by_sku(db, sku=obj_in.sku):
            raise HTTPException(status_code=409, detail="Product with this SKU already exists.")
        
        return super().create(db, obj_in=obj_in)

    def get_similar(self, db: Session, *, embedding: list[float], limit: int = 10) -> list[Product]:
        """
        Performs a vector similarity search for products.
        """
        return db.query(Product).order_by(Product.embedding.l2_distance(embedding)).limit(limit).all()

product = CRUDProduct(Product)
