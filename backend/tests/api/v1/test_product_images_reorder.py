import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from src.crud import crud_product, crud_product_image
from src.schemas import product as product_schema


@pytest.mark.integration
def test_reorder_product_images(
    client: TestClient, db: Session, admin_headers: dict
) -> None:
    # 1. Create a product
    product_in = product_schema.ProductCreate(
        name="Reorder Test Product",
        sku="REORDER-001",
        default_resale_price=10.0,
        cost_price=5.0
    )
    product = crud_product.product.create(db, obj_in=product_in)
    
    # 2. Add 3 images directly to DB (mocking upload)
    img1 = crud_product_image.product_image.create(
        db, obj_in=product_schema.ProductImageCreate(
            product_id=product.id,
            image_path="img1.jpg",
            order=0
        )
    )
    img2 = crud_product_image.product_image.create(
        db, obj_in=product_schema.ProductImageCreate(
            product_id=product.id,
            image_path="img2.jpg",
            order=1
        )
    )
    img3 = crud_product_image.product_image.create(
        db, obj_in=product_schema.ProductImageCreate(
            product_id=product.id,
            image_path="img3.jpg",
            order=2
        )
    )
    
    # 3. Call reorder endpoint: [3, 1, 2]
    new_order_ids = [img3.id, img1.id, img2.id]
    
    response = client.post(
        f"/api/v1/products/{product.id}/images/reorder",
        headers=admin_headers,
        json=new_order_ids,
    )
    
    assert response.status_code == 200
    content = response.json()
    assert len(content) == 3
    
    # Verify response order
    assert content[0]["id"] == img3.id
    assert content[0]["order"] == 0
    assert content[1]["id"] == img1.id
    assert content[1]["order"] == 1
    assert content[2]["id"] == img2.id
    assert content[2]["order"] == 2
    
    # Verify DB state
    db.refresh(img1)
    db.refresh(img2)
    db.refresh(img3)
    
    assert img3.order == 0
    assert img1.order == 1
    assert img2.order == 2
