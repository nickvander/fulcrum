import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Body
from sqlalchemy.orm import Session

from src.api import dependencies
from src.api.dependencies import get_db, get_ai_service
from src.crud import crud_product, crud_product_image, crud_custom_field
from src.models.user import User
from src.schemas import product as product_schema, inventory as inventory_schema
from src.services.base import AIService
from src.tasks import generate_product_embedding

router = APIRouter()



@router.get("/{product_id}/purchase-history", response_model=List[product_schema.ProductPurchaseHistory])
def get_product_purchase_history(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get purchase history for a product.
    """
    from src.models.purchase_order_item import PurchaseOrderItem
    from src.models.purchase_order import PurchaseOrder
    from src.models.supplier import Supplier
    from sqlalchemy import desc

    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Query PurchaseOrderItems for this product, joined with PO and Supplier
    query = (
        db.query(
            PurchaseOrderItem.quantity_ordered,
            PurchaseOrderItem.unit_cost,
            PurchaseOrderItem.base_cost,
            PurchaseOrderItem.shipping_allocated,
            PurchaseOrderItem.taxes_allocated,
            PurchaseOrderItem.other_allocated,
            PurchaseOrderItem.quantity_received,
            PurchaseOrder.id.label("po_id"),
            PurchaseOrder.created_at.label("date"),
            PurchaseOrder.status,
            Supplier.name.label("supplier_name")
        )
        .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.id)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .filter(PurchaseOrderItem.product_id == product_id)
        .order_by(desc(PurchaseOrder.created_at), desc(PurchaseOrder.id))
    )
    
    results = query.all()
    
    return [
        {
            "po_id": row.po_id,
            "date": row.date,
            "supplier_name": row.supplier_name,
            "quantity": row.quantity_ordered,
            "unit_cost": row.unit_cost,
            "base_cost": row.base_cost,
            "shipping_allocated": row.shipping_allocated,
            "taxes_allocated": row.taxes_allocated,
            "other_allocated": row.other_allocated,
            "status": row.status
        }
        for row in results
    ]


@router.get("", response_model=product_schema.PaginatedProducts)
def read_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    sku: str = None,
    q: str = None,
    is_bundle: bool = None,
    min_stock: int = None,
    max_stock: int = None,
    min_price: float = None,
    max_price: float = None,
):
    """
    Retrieve products.
    """
    if sku:
        products = crud_product.product.get_by_sku(db, sku=sku)
        if not products:
            raise HTTPException(status_code=404, detail="Product not found")
        # Wrap single product in paginated response
        return {
            "data": [products],
            "currentPage": 1,
            "totalPages": 1,
            "totalItems": 1,
            "pageSize": 1,
            "hasNextPage": False,
            "hasPrevPage": False
        }
    
    filters = {}
    if q:
        filters['search_term'] = q
    if is_bundle is not None:
        filters['is_bundle'] = is_bundle
    if min_stock is not None:
        filters['min_stock'] = min_stock
    if max_stock is not None:
        filters['max_stock'] = max_stock
    if min_price is not None:
        filters['min_price'] = min_price
    if max_price is not None:
        filters['max_price'] = max_price
        
    print(f"DEBUG: read_products filters={filters}, is_bundle={is_bundle}")
    products = crud_product.product.get_multi_paginated(db, skip=skip, limit=limit, filters=filters)
    
    # Calculate metrics for each product in the list
    from src.services.inventory_service import inventory_service
    from src.models.marketing import Campaign, CampaignStatus
    
    # Pre-fetch active campaign counts in a single query if possible, or per product
    # For simplicity in this iteration, we'll do it per product (consider optimizing if slow)
    for p in products["data"]:
        p.sales_velocity = inventory_service.calculate_sales_velocity(db, p.id)
        p.days_of_inventory = inventory_service.calculate_days_of_inventory(db, p.id)
        p.low_inventory_threshold = inventory_service.get_effective_low_inventory_threshold(db, p.id)
        p.low_stock_quantity_threshold = inventory_service.get_effective_low_stock_quantity_threshold(db, p.id)
        p.stock_quantity = inventory_service.get_total_stock_quantity(db, p.id)
        
        # Count active campaigns
        active_campaigns = (
            db.query(Campaign)
            .join(Campaign.products)
            .filter(Campaign.products.any(id=p.id))
            .filter(Campaign.status == CampaignStatus.ACTIVE.value)
            .count()
        )
        p.active_campaign_count = active_campaigns
        
    return products


@router.post("", response_model=product_schema.Product)
def create_product(
    *,
    db: Session = Depends(get_db),
    product_in: product_schema.ProductCreate,
):
    """
    Create new product.
    """
    product = crud_product.product.get_by_sku(db, sku=product_in.sku)
    if product:
        raise HTTPException(
            status_code=409,
            detail="A product with this SKU already exists.",
        )
    product = crud_product.product.create(db, obj_in=product_in)
    
    # Try to generate embedding, but don't fail product creation if it fails
    try:
        generate_product_embedding.delay(product.id)
    except Exception as e:
        # Log the error but don't block product creation
        print(f"Warning: Failed to queue embedding generation: {e}")
    
    return product


@router.put("/{product_id}", response_model=product_schema.Product)
def update_product(
    *,
    db: Session = Depends(get_db),
    product_id: int,
    product_in: product_schema.ProductUpdate,
    current_user: User = Depends(dependencies.get_current_user),
):
    """
    Update a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    
    # Capture old values for change logging
    old_values = {
        'name': product.name,
        'cost_price': product.cost_price,
        'default_resale_price': product.default_resale_price,
        'sku': product.sku,
        'description': product.description,
        'category': product.category,
        'brand': product.brand,
        'weight': product.weight,
        'width': product.width,
        'height': product.height,
        'depth': product.depth,
    }

    
    # Get new values from update payload
    update_data = product_in.model_dump(exclude_unset=True, exclude={'bundle_components'})
    
    # Perform the update
    product = crud_product.product.update(db, db_obj=product, obj_in=product_in)
    
    # Log changes with source='direct_edit'
    from src.services.change_log import log_product_changes
    log_product_changes(
        db,
        product_id=product_id,
        product_name=product.name,
        old_values=old_values,
        new_values=update_data,
        source="direct_edit",
        changed_by_id=current_user.id,
    )
    db.commit()
    
    generate_product_embedding.delay(product.id)
    return product


@router.get("/{product_id}", response_model=product_schema.Product)
def read_product(*, db: Session = Depends(get_db), product_id: int):
    """
    Get product by ID.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    
    # Calculate metrics
    from src.services.inventory_service import inventory_service
    product.sales_velocity = inventory_service.calculate_sales_velocity(db, product_id)
    product.days_of_inventory = inventory_service.calculate_days_of_inventory(db, product_id)
    product.low_stock_quantity_threshold = inventory_service.get_effective_low_stock_quantity_threshold(db, product_id)
    product.stock_quantity = inventory_service.get_total_stock_quantity(db, product_id)
    
    # Fetch active campaigns
    from src.models.marketing import Campaign, CampaignStatus
    active_campaigns = (
        db.query(Campaign)
        .join(Campaign.products)
        .filter(Campaign.products.any(id=product.id))
        .filter(Campaign.status == CampaignStatus.ACTIVE.value)
        .all()
    )
    
    product.active_campaigns = [
        {"id": c.id, "name": c.name, "start_date": c.start_date, "end_date": c.end_date, "is_smart_boost": c.is_smart_boost}
        for c in active_campaigns
    ]
    product.active_campaign_count = len(active_campaigns)

    # Fetch quick posts
    from src.models.marketing import CampaignEvent
    quick_posts = (
        db.query(CampaignEvent)
        .join(CampaignEvent.products)
        .filter(CampaignEvent.products.any(id=product.id))
        .filter(CampaignEvent.campaign_id.is_(None))
        .order_by(CampaignEvent.created_at.desc())
        .limit(5)
        .all()
    )
    product.quick_posts = [
        {"id": e.id, "name": e.name, "status": e.status, "scheduled_at": e.scheduled_at, "published_at": e.published_at, "channel_type": e.channel_type}
        for e in quick_posts
    ]
    
    return product


@router.delete("/{product_id}", response_model=product_schema.Product)
def delete_product(*, db: Session = Depends(get_db), product_id: int):
    """
    Delete a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail="The product with this ID does not exist in the system.",
        )
    product = crud_product.product.remove(db, id=product_id)
    return product


@router.delete("", response_model=Dict[str, Any])
def delete_multiple_products(
    *,
    db: Session = Depends(get_db),
    product_ids: List[int],
):
    """
    Delete multiple products.
    """
    deleted_count = 0
    for product_id in product_ids:
        product = crud_product.product.get(db, id=product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with id {product_id} not found",
            )
        crud_product.product.remove(db, id=product_id)
        deleted_count += 1
    
    return {
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} products"
    }


@router.post("/{product_id}/images", response_model=product_schema.ProductImage)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a product image.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Ensure the upload directory exists
    upload_dir = "uploads/product_images"
    os.makedirs(upload_dir, exist_ok=True)

    # Save the file
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Create the product image record
    image_in = product_schema.ProductImageCreate(
        product_id=product_id, image_path=file.filename
    )
    image = crud_product_image.product_image.create(db, obj_in=image_in)
    return image


@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a product image.
    """
    image = crud_product_image.product_image.get(db=db, id=image_id)
    if not image or image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product image not found")
    
    # Delete the actual file from storage
    if image.image_path and os.path.exists(image.image_path):
        os.remove(image.image_path)
    
    crud_product_image.product_image.remove(db=db, id=image_id)
    return Response(status_code=204)

@router.put("/{product_id}/images/{image_id}", response_model=product_schema.ProductImage)
def update_product_image(
    product_id: int,
    image_id: int,
    image_update: product_schema.ProductImageUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a product image's details (title, description).
    """
    db_image = crud_product_image.product_image.get(db=db, id=image_id)
    if not db_image or db_image.product_id != product_id:
        raise HTTPException(status_code=404, detail="Product image not found")
    
    updated_image = crud_product_image.product_image.update(
        db=db, db_obj=db_image, obj_in=image_update
    )
    return updated_image


@router.post(
    "/{product_id}/images/{image_id}/set-primary",
    response_model=product_schema.ProductImage
)
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
):
    """
    Set a product image as the primary image.
    """
    image = crud_product_image.product_image.set_primary_image(
        db=db, product_id=product_id, image_id=image_id
    )
    if not image:
        raise HTTPException(status_code=404, detail="Product image not found")
    return image


@router.post(
    "/{product_id}/images/reorder",
    response_model=List[product_schema.ProductImage]
)
def reorder_product_images(
    product_id: int,
    image_ids: List[int] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Reorder product images.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all images for this product
    images = db.query(crud_product_image.product_image.model).filter(
        crud_product_image.product_image.model.product_id == product_id
    ).all()
    
    image_map = {img.id: img for img in images}
    
    for idx, img_id in enumerate(image_ids):
        if img_id in image_map:
            image_map[img_id].order = idx
            db.add(image_map[img_id])
            
    db.commit()
    
    # Return sorted images
    return sorted(images, key=lambda x: x.order)


@router.post("/search", response_model=List[product_schema.Product])
def search_products(
    query: str,
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Search for products using a semantic query.
    """
    embedding = ai_service.generate_embedding(query)
    products = crud_product.product.get_similar(db, embedding=embedding)
    return products


@router.get("/lookup/barcode", response_model=product_schema.Product)
def lookup_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
):
    """
    Lookup a product by its barcode, QR value, or SKU.
    """
    product = crud_product.product.get_by_barcode(db, barcode_value=barcode)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/{product_id}/assemble", response_model=product_schema.Product)
def assemble_bundle(
    product_id: int,
    quantity: int = Body(..., embed=True),
    current_user: User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assemble a bundle (kit) from its components.
    """
    from src.services.inventory_service import inventory_service
    
    try:
        inventory_service.assemble_bundle(
            db=db,
            bundle_id=product_id,
            quantity=quantity,
            user_id=current_user.email if current_user.email else f"user_{current_user.id}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db.commit()
    
    # Refresh product data
    from sqlalchemy.orm import joinedload
    from src.models.product import Product
    
    refreshed_product = db.query(Product)\
        .options(joinedload(Product.inventory_items))\
        .options(joinedload(Product.inventory_adjustments))\
        .filter(Product.id == product_id).first()
        
    return refreshed_product


@router.post("/{product_id}/adjust-stock", response_model=product_schema.Product)
def adjust_stock(
    product_id: int,
    stock_adjustment: inventory_schema.StockAdjustment,
    current_user: User = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adjust the stock level for a product.
    """
    from src.services.inventory_service import inventory_service
    
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Use centralized service
    inventory_service.adjust_stock(
        db=db,
        product_id=product_id,
        adjustment=stock_adjustment.adjustment,
        reason=stock_adjustment.reason,
        location=getattr(stock_adjustment, 'location', 'default'),
        user_id=current_user.email if current_user.email else f"user_{current_user.id}"
    )
    
    db.commit()
    
    # Explicitly query the product with its inventory items and adjustments to ensure fresh data is returned
    from sqlalchemy.orm import joinedload
    from src.models.product import Product
    
    # Re-query the product with its inventory items and adjustments to ensure fresh data is returned
    refreshed_product = db.query(Product)\
        .options(joinedload(Product.inventory_items))\
        .options(joinedload(Product.inventory_adjustments))\
        .filter(Product.id == product_id).first()
    
    if not refreshed_product:
        raise HTTPException(status_code=404, detail="Product not found after adjustment")
    
    return refreshed_product





@router.post("/{product_id}/custom-fields")
def save_product_custom_fields(
    product_id: int,
    custom_fields: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Save custom field values for a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud_custom_field.product_custom_field.save_for_product(
        db=db, product_id=product_id, custom_fields_in=custom_fields
    )
    return {"message": "Custom fields saved successfully"}

@router.get("/{product_id}/variants", response_model=List[product_schema.ProductVariant])
def get_product_variants(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all variants for a product.
    """
    product = crud_product.product.get(db, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Since we don't have a specific CRUD for variants yet, we rely on relationship
    # Ensure variants are loaded. The default get() might not join them.
    # We can use the relationship if it's eagerly loaded or lazy loading (if session active).
    # To be safe and efficient, we can check if they are loaded or query them directly.
    return product.variants

