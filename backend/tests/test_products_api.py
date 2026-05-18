from fastapi.testclient import TestClient
from src.models.product import Product, ProductImage
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import event
import io
import os
from datetime import datetime

from unittest.mock import patch
from src.config import settings

@pytest.mark.db
def test_create_product(client: TestClient):
    """
    Test creating a product successfully and that the embedding task is called.
    """
    with patch("src.tasks.generate_product_embedding.delay") as mock_delay:
        response = client.post(
            "/api/v1/products/",
            json={
                "name": "Test Product",
                "description": "A product for testing",
                "sku": "TESTSKU123",
                "default_resale_price": 19.99,
                "cost_price": 10.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Product"
        assert data["sku"] == "TESTSKU123"
        assert "id" in data
        mock_delay.assert_called_once_with(data["id"])

@pytest.mark.db
def test_create_product_duplicate_sku(client: TestClient, test_product: Product):
    """
    Test creating a product with a duplicate SKU fails.
    """
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Another Product",
            "description": "A product with a duplicate SKU",
            "sku": test_product.sku, # Use the same SKU as the fixture
        },
    )
    assert response.status_code == 409
    assert response.status_code == 409
    assert "A product with this SKU already exists" in response.text

@pytest.mark.db
def test_search_products(client: TestClient, db: Session, test_product: Product):
    """
    Test semantic search for products.
    """
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Vector search test requires PostgreSQL")

    # The dummy AI service will return a random embedding, but for a single product
    # the search should still return that product.
    response = client.post(f"/api/v1/products/search?query={test_product.name}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # The exact order isn't guaranteed with random embeddings,
    # so we just check if the product is in the results.
    assert test_product.name in [p["name"] for p in data]

@pytest.mark.db
def test_search_products_stock_filter(client: TestClient, db: Session, test_product: Product):
    """
    Test filtering products by stock level.
    """
    # Create inventory for the test product
    from src.models.inventory import InventoryItem
    inventory = InventoryItem(product_id=test_product.id, quantity=10, location="default")
    db.add(inventory)
    db.commit()

    # Test min_stock matches
    response = client.get("/api/v1/products/?min_stock=5")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert test_product.id in [p["id"] for p in data]

    # Test min_stock filters out
    response = client.get("/api/v1/products/?min_stock=15")
    assert response.status_code == 200
    data = response.json().get("data", [])
    assert test_product.id not in [p["id"] for p in data]


@pytest.mark.db
def test_product_list_uses_batched_computed_metrics(
    client: TestClient, db: Session, test_product: Product, test_admin_user
):
    """
    Product list responses should include computed metrics populated from bulk queries.
    """
    from src.models.inventory import InventoryItem
    from src.models.order import SalesOrder, SalesOrderItem, OrderSource
    from src.models.product_inventory_settings import ProductInventorySettings
    from src.models.store_settings import StoreSettings
    from src.models.marketing import Campaign, CampaignStatus

    db.add(StoreSettings(low_inventory_days_default=45, low_stock_quantity_default=7))
    db.add(InventoryItem(product_id=test_product.id, quantity=10, location="default"))
    db.add(
        ProductInventorySettings(
            product_id=test_product.id,
            low_inventory_days_threshold=12,
            low_stock_quantity_threshold=3,
        )
    )

    order = SalesOrder(
        status="COMPLETED",
        total_price=100.0,
        created_at=datetime.utcnow(),
        source=OrderSource.FULCRUM,
        external_order_id="BATCH-METRICS-ORDER",
    )
    db.add(order)
    db.flush()
    db.add(
        SalesOrderItem(
            order_id=order.id,
            product_id=test_product.id,
            quantity=15,
            price_per_unit=10.0,
        )
    )

    campaign = Campaign(
        user_id=test_admin_user.id,
        name="Active Campaign",
        status=CampaignStatus.ACTIVE.value,
    )
    campaign.products.append(test_product)
    db.add(campaign)
    db.commit()

    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    listed_product = next(
        item for item in response.json()["data"] if item["id"] == test_product.id
    )

    assert listed_product["stock_quantity"] == 10
    assert listed_product["sales_velocity"] == 0.5
    assert listed_product["days_of_inventory"] == 20.0
    assert listed_product["low_inventory_threshold"] == 12
    assert listed_product["low_stock_quantity_threshold"] == 3
    assert listed_product["active_campaign_count"] == 1
    # New count-aggregate: no adjustments on this product, so the
    # endpoint returns 0 (not null) — UI uses this to gate the
    # "Stock history" menu item without eager-loading every row.
    assert listed_product["inventory_adjustment_count"] == 0
    # The list payload deliberately does NOT include the full
    # `inventory_adjustments` array — the dialog lazy-fetches it from
    # `GET /products/{id}`. An empty list is acceptable.
    assert listed_product["inventory_adjustments"] == []


@pytest.mark.db
def test_product_list_inventory_adjustment_count_reflects_state(
    client: TestClient, db: Session, test_product: Product
):
    """The list endpoint's `inventory_adjustment_count` is a cheap
    aggregate (not a relationship eager-load). Insert 3 adjustments on
    `test_product`, leave another product clean, and confirm the
    counts are correct and the list does NOT include the actual rows.
    """
    from src.models.inventory import InventoryAdjustment
    from src.schemas.product import ProductCreate
    from src.crud import crud_product

    clean_product = crud_product.product.create(
        db=db,
        obj_in=ProductCreate(
            name="No-Adjustments Product",
            sku="NO-ADJ-1",
            default_resale_price=10.0,
            cost_price=5.0,
        ),
    )

    for delta in (5, -2, 3):
        db.add(InventoryAdjustment(
            product_id=test_product.id,
            adjustment=delta,
            reason="test",
            created_by="tester",
        ))
    db.commit()

    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    items_by_id = {item["id"]: item for item in response.json()["data"]}

    assert items_by_id[test_product.id]["inventory_adjustment_count"] == 3
    assert items_by_id[clean_product.id]["inventory_adjustment_count"] == 0
    # The list path uses `noload` for `inventory_adjustments`, so the
    # field renders as an empty list regardless of how many rows exist
    # in the DB. The detail endpoint is still the canonical source.
    assert items_by_id[test_product.id]["inventory_adjustments"] == []


@pytest.mark.db
def test_product_detail_still_returns_full_inventory_adjustments(
    client: TestClient, db: Session, test_product: Product
):
    """The detail endpoint must keep eager-loading the actual rows so
    the stock-history dialog (which calls `GET /products/{id}` on
    demand) has the data the list endpoint deliberately skips."""
    from src.models.inventory import InventoryAdjustment

    for delta in (1, 2, 3):
        db.add(InventoryAdjustment(
            product_id=test_product.id,
            adjustment=delta,
            reason="seed",
            created_by="tester",
        ))
    db.commit()

    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["inventory_adjustments"]) == 3


@pytest.mark.db
def test_product_list_query_count_stays_bounded(
    client: TestClient, db: Session, test_product: Product
):
    """
    Product list should avoid per-product metric queries as page size grows.

    The ceiling is deliberately tight: bumping it should require a
    code-review conversation. Today the path issues at most:
      - 1 product count (pagination total)
      - 1 product list query
      - 7 selectinload queries (images / marketplace_listings /
        inventory_items / custom_fields / variants /
        bundle_components / part_of_bundles)
      - 2 nested selectinloads (bundle.component.inventory_items +
        part_of_bundles.bundle.inventory_items)
      - 6 aggregate metric queries (stock / sales / thresholds /
        store_settings / campaigns / adjustment_count)

    That's ~17 queries — well under the ceiling and independent of
    page size.
    """
    from src.schemas.product import ProductCreate
    from src.crud import crud_product
    from src.models.inventory import InventoryItem

    for index in range(5):
        product = crud_product.product.create(
            db=db,
            obj_in=ProductCreate(
                name=f"Query Count Product {index}",
                sku=f"QUERY-COUNT-{index}",
                default_resale_price=10.0,
                cost_price=5.0,
            ),
        )
        db.add(InventoryItem(product_id=product.id, quantity=index + 1, location="default"))

    db.add(InventoryItem(product_id=test_product.id, quantity=10, location="default"))
    db.commit()

    statements = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
    try:
        response = client.get("/api/v1/products/?limit=100")
    finally:
        event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    assert len(response.json()["data"]) >= 6
    assert len(statements) <= 20


@pytest.mark.db
def test_update_product(client: TestClient, test_product: Product, admin_headers: dict):
    """
    Test updating a product successfully and that the embedding task is called.
    """
    with patch("src.tasks.generate_product_embedding.delay") as mock_delay:
        updated_name = "Updated Test Product"
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": updated_name},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == updated_name
        assert data["id"] == test_product.id
        mock_delay.assert_called_once_with(test_product.id)


@pytest.mark.db
def test_upload_product_image(client: TestClient, test_product: Product):
    """
    Test uploading an image for a product.
    """
    image_content = b"fake image data"
    response = client.post(
        f"/api/v1/products/{test_product.id}/images",
        files={"file": ("test_image.jpg", io.BytesIO(image_content), "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == test_product.id
    assert "image_path" in data
    # Verify the file was created
    # The path returned is relative to the project root or upload dir
    # We need to ensure we check the correct location
    # The path returned is relative to the project root or upload dir
    # We need to ensure we check the correct location
    full_path = os.path.join("uploads/product_images", data["image_path"])
    assert os.path.exists(full_path)
    with open(full_path, "rb") as f:
        assert f.read() == image_content

@pytest.mark.db
def test_delete_product_image(client: TestClient, db: Session, test_product_with_image: ProductImage):
    """
    Test deleting a product image.
    """
    image_path = test_product_with_image.image_path
    image_id = test_product_with_image.id
    product_id = test_product_with_image.product_id

    response = client.delete(f"/api/v1/products/{product_id}/images/{image_id}")
    assert response.status_code == 204

    # Verify the file was deleted
    assert not os.path.exists(image_path)

    # Verify the database record is gone
    db_image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    assert db_image is None

@pytest.mark.db
def test_set_primary_product_image(client: TestClient, db: Session, test_product: Product):
    """
    Test setting a primary image for a product.
    """
    # Upload two images
    image1_resp = client.post(
        f"/api/v1/products/{test_product.id}/images",
        files={"file": ("image1.jpg", io.BytesIO(b"img1"), "image/jpeg")},
    )
    image2_resp = client.post(
        f"/api/v1/products/{test_product.id}/images",
        files={"file": ("image2.jpg", io.BytesIO(b"img2"), "image/jpeg")},
    )
    image1_id = image1_resp.json()["id"]
    image2_id = image2_resp.json()["id"]

    # Set image 2 as primary
    response = client.post(f"/api/v1/products/{test_product.id}/images/{image2_id}/set-primary")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == image2_id
    assert data["is_primary"] == 1

    # Verify in DB
    db.expire_all() # Ensure we get fresh data from the DB
    image1_db = db.query(ProductImage).filter(ProductImage.id == image1_id).first()
    image2_db = db.query(ProductImage).filter(ProductImage.id == image2_id).first()
    assert image1_db.is_primary == 0
    assert image2_db.is_primary == 1

@pytest.mark.db
def test_delete_nonexistent_product_image(client: TestClient, test_product: Product):
    """
    Test that deleting a product image that does not exist returns a 404.
    """
    response = client.delete(f"/api/v1/products/{test_product.id}/images/9999")
    assert response.status_code == 404

@pytest.mark.db
def test_set_primary_nonexistent_product_image(client: TestClient, test_product: Product):
    """
    Test that setting a primary image that does not exist returns a 404.
    """
    response = client.post(f"/api/v1/products/{test_product.id}/images/9999/set-primary")
    assert response.status_code == 404


@pytest.mark.db
def test_delete_product(client: TestClient, test_product: Product, db: Session):
    """
    Test deleting a product successfully.
    """
    # First verify the product exists
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_product.id

    # Delete the product
    response = client.delete(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_product.id

    # Verify the product is gone
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 404


@pytest.mark.db
def test_adjust_stock(client: TestClient, test_product: Product, db: Session, admin_headers: dict):
    """
    Test adjusting stock for a product successfully.
    """
    # Verify the product exists
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    
    # Make an adjustment
    adjustment_data = {
        "adjustment": 10,
        "reason": "Test adjustment"
    }
    response = client.post(f"/api/v1/products/{test_product.id}/adjust-stock", json=adjustment_data, headers=admin_headers)
    assert response.status_code == 200
    
    # Verify the response contains the updated product
    data = response.json()
    assert data["id"] == test_product.id
    
    # Verify an inventory adjustment record was created
    from src.models.inventory import InventoryAdjustment
    adjustment_record = db.query(InventoryAdjustment).filter(InventoryAdjustment.product_id == test_product.id).first()
    assert adjustment_record is not None
    assert adjustment_record.adjustment == 10
    assert adjustment_record.reason == "Test adjustment"
    # created_by will be the admin user's email
    assert adjustment_record.created_by == "admin@test.com"


@pytest.mark.db
def test_adjust_stock_negative(client: TestClient, test_product: Product, db: Session, admin_headers: dict):
    """
    Test reducing stock for a product successfully.
    """
    # Make a negative adjustment
    adjustment_data = {
        "adjustment": -5,
        "reason": "Stock reduction"
    }
    response = client.post(f"/api/v1/products/{test_product.id}/adjust-stock", json=adjustment_data, headers=admin_headers)
    assert response.status_code == 200
    
    # Verify the response contains the updated product
    data = response.json()
    assert data["id"] == test_product.id
    
    # Verify an inventory adjustment record was created with negative value
    from src.models.inventory import InventoryAdjustment
    adjustment_record = db.query(InventoryAdjustment).filter(InventoryAdjustment.product_id == test_product.id).first()
    assert adjustment_record is not None
    assert adjustment_record.adjustment == -5
    assert adjustment_record.reason == "Stock reduction"


@pytest.mark.db
def test_adjust_stock_product_not_found(client: TestClient, admin_headers: dict):
    """
    Test adjusting stock for a non-existent product returns 404.
    """
    adjustment_data = {
        "adjustment": 10,
        "reason": "Test adjustment"
    }
    response = client.post("/api/v1/products/99999/adjust-stock", json=adjustment_data, headers=admin_headers)
    assert response.status_code == 404
    assert "Product not found" in response.text


@pytest.mark.db
def test_delete_multiple_products(client: TestClient, test_product: Product, db: Session):
    """
    Test deleting multiple products successfully.
    """
    # Create additional products for testing
    response = client.post(
        "/api/v1/products/",
        json={
            "name": "Test Product 2",
            "description": "A product for testing",
            "sku": "TESTSKU456",
            "default_resale_price": 29.99,
            "cost_price": 15.0,
        },
    )
    assert response.status_code == 200
    product2_data = response.json()

    delete_ids = [test_product.id, product2_data["id"]]
    # Use request method for delete with body
    response = client.request("DELETE", f"{settings.API_V1_STR}/products/", json=delete_ids)
    
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 2
    assert "Successfully deleted 2 products" in data["message"]

    # Verify the products are gone
    response = client.get(f"{settings.API_V1_STR}/products/{test_product.id}")
    assert response.status_code == 404
    
    response = client.get(f"{settings.API_V1_STR}/products/{product2_data['id']}")
    assert response.status_code == 404


@pytest.mark.db
def test_delete_multiple_products_with_nonexistent(client: TestClient, test_product: Product, db: Session):
    """
    Test deleting multiple products where one does not exist returns 404.
    """
    delete_ids = [test_product.id, 99999]  # Second ID doesn't exist
    # Use request method for delete with body
    response = client.request("DELETE", f"{settings.API_V1_STR}/products/", json=delete_ids)
    
    assert response.status_code == 404
    assert "Product with id 99999 not found" in response.text
