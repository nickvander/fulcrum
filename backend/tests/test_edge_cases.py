import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.crud.crud_product import product as crud_product
from src.schemas.product import ProductCreate

@pytest.mark.db
def test_special_characters_in_sku(db: Session):
    special_sku = "SKU/WITH#SPECIAL?CHARS"
    product_in = ProductCreate(
        name="Special Char Product",
        sku=special_sku,
        default_resale_price=20.0
    )
    product = crud_product.create(db, obj_in=product_in)
    assert product.sku == special_sku
    
    fetched = crud_product.get_by_sku(db, sku=special_sku)
    assert fetched is not None
    assert fetched.id == product.id

@pytest.mark.db
def test_transaction_rollback(db: Session):
    # Create a product
    product_in = ProductCreate(
        name="Rollback Test Product",
        sku="ROLL001",
        default_resale_price=30.0
    )
    crud_product.create(db, obj_in=product_in)
    
    # Attempt an operation that fails halfway
    # Try to create another product with the SAME SKU (should fail unique constraint)
    product_dup = ProductCreate(
        name="Duplicate Product",
        sku="ROLL001", # Duplicate SKU
        default_resale_price=40.0
    )
    
    # We need to wrap in a nested transaction (savepoint) so we don't kill the main test session
    # Use a try-except block to catch the exception and ensure rollback
    try:
        with db.begin_nested():
            crud_product.create(db, obj_in=product_dup)
        pytest.fail("Should have raised IntegrityError or HTTPException")
    except (IntegrityError, Exception):
        # The nested transaction should have been rolled back by the context manager
        pass
        
    # Verify the first product still exists
    fetched = crud_product.get_by_sku(db, sku="ROLL001")
    assert fetched is not None
    assert fetched.name == "Rollback Test Product"

# Concurrency test is omitted for now as it requires complex setup with separate sessions/threads
# and might interfere with the transactional test fixture.
