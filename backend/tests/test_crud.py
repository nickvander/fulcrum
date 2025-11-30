import pytest
from sqlalchemy.orm import Session
from src.crud import crud_product
from src.schemas.product import ProductCreate
from src.models.product import Product
import numpy as np

@pytest.mark.postgres
@pytest.mark.db
def test_product_search(db: Session):
    """
    Tests the vector search functionality for products.
    """
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Vector search test requires PostgreSQL")

    # 1. Create two products with known embeddings
    product_a_in = ProductCreate(
        name="Product A",
        description="This is a test product.",
        sku="SKUA123",
    )
    embedding_a = np.array([0.1, 0.2, 0.3, 0.4] + [0] * 380)
    crud_product.product.create(db, obj_in=product_a_in)
    # Manually update embedding since the celery task is mocked in tests
    product_a = db.query(Product).filter(Product.sku == "SKUA123").first()
    product_a.embedding = embedding_a
    db.commit()


    product_b_in = ProductCreate(
        name="Product B",
        description="This is another test product.",
        sku="SKUB456",
    )
    embedding_b = np.array([0.9, 0.8, 0.7, 0.6] + [0] * 380)
    crud_product.product.create(db, obj_in=product_b_in)
    product_b = db.query(Product).filter(Product.sku == "SKUB456").first()
    product_b.embedding = embedding_b
    db.commit()

    # 2. Create a search embedding that is very close to Product A
    search_embedding = np.array([0.11, 0.22, 0.33, 0.44] + [0] * 380)

    # 3. Perform the search
    results = crud_product.product.get_similar(db, embedding=search_embedding.tolist(), limit=1)

    # 4. Verify that the closest result is Product A
    assert len(results) == 1
    assert results[0].name == "Product A"
