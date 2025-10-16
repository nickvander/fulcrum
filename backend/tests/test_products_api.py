from fastapi.testclient import TestClient
from src.models.product import Product, ProductImage
import pytest
from sqlalchemy.orm import Session
import io
import os

from unittest.mock import patch

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
    assert "Product with this SKU already exists" in response.text

@pytest.mark.db
def test_search_products(client: TestClient, db: Session, test_product: Product):
    """
    Test semantic search for products.
    """
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Vector search test requires PostgreSQL")

    # The dummy AI service will return a random embedding, but for a single product
    # the search should still return that product.
    response = client.get(f"/api/v1/products/search/?q={test_product.name}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # The exact order isn't guaranteed with random embeddings,
    # so we just check if the product is in the results.
    assert test_product.name in [p["name"] for p in data]

@pytest.mark.db
def test_update_product(client: TestClient, test_product: Product):
    """
    Test updating a product successfully and that the embedding task is called.
    """
    with patch("src.tasks.generate_product_embedding.delay") as mock_delay:
        updated_name = "Updated Test Product"
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            json={"name": updated_name},
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
    with open(data["image_path"], "rb") as f:
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
def test_adjust_stock(client: TestClient, test_product: Product, db: Session):
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
    response = client.post(f"/api/v1/products/{test_product.id}/adjust-stock", json=adjustment_data)
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
    assert adjustment_record.created_by == "system"


@pytest.mark.db
def test_adjust_stock_negative(client: TestClient, test_product: Product, db: Session):
    """
    Test reducing stock for a product successfully.
    """
    # Make a negative adjustment
    adjustment_data = {
        "adjustment": -5,
        "reason": "Stock reduction"
    }
    response = client.post(f"/api/v1/products/{test_product.id}/adjust-stock", json=adjustment_data)
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
def test_adjust_stock_product_not_found(client: TestClient):
    """
    Test adjusting stock for a non-existent product returns 404.
    """
    adjustment_data = {
        "adjustment": 10,
        "reason": "Test adjustment"
    }
    response = client.post("/api/v1/products/99999/adjust-stock", json=adjustment_data)
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
        },
    )
    assert response.status_code == 200
    product2_data = response.json()

    delete_ids = [test_product.id, product2_data["id"]]
    response = client.delete(f"{environment.API_V1_STR}/products/", json=delete_ids)
    
    assert response.status_code == 200
    data = response.json()
    assert data["deleted_count"] == 2
    assert "Successfully deleted 2 products" in data["message"]

    # Verify the products are gone
    response = client.get(f"{environment.API_V1_STR}/products/{test_product.id}")
    assert response.status_code == 404
    
    response = client.get(f"{environment.API_V1_STR}/products/{product2_data['id']}")
    assert response.status_code == 404


@pytest.mark.db
def test_delete_multiple_products_with_nonexistent(client: TestClient, test_product: Product, db: Session):
    """
    Test deleting multiple products where one does not exist returns 404.
    """
    delete_ids = [test_product.id, 99999]  # Second ID doesn't exist
    response = client.delete(f"{environment.API_V1_STR}/products/", json=delete_ids)
    
    assert response.status_code == 404
    assert "Product with id 99999 not found" in response.text