import pytest
from sqlalchemy.orm import Session
from unittest.mock import Mock

from src.models import Product, InventoryItem, User
from src.schemas.inventory import StockAdjustment
from src.api.v1.endpoints.products import adjust_stock


@pytest.fixture
def db_session(db: Session):
    """
    Create test data using the properly initialized database session.
    """
    # Create a test user and product for testing
    test_user = User(email="stocktest@example.com", hashed_password="HashedTestPassword123!", role="user")
    db.add(test_user)
    db.flush()  # Get the user ID
    
    test_product = Product(
        name="Test Product For Stock",
        description="Test Description",
        sku="STOCKTEST001",
        default_resale_price=10.0
    )
    db.add(test_product)
    db.flush()  # Get the product ID
    
    # Create initial inventory
    initial_inventory = InventoryItem(
        product_id=test_product.id,
        quantity=10,
        location="default"
    )
    db.add(initial_inventory)
    db.flush()  # Use flush instead of commit to maintain transaction
    
    yield db
    
    # Test data will be cleaned up automatically by the transaction rollback in the db fixture



@pytest.mark.db
def test_adjust_stock_functionality(db_session: Session):
    """Test the direct functionality of the adjust_stock function."""
    # Get test data
    test_product = db_session.query(Product).filter(Product.sku == "STOCKTEST001").first()

    
    # Create a mock current_user
    mock_current_user = Mock()
    mock_current_user.email = "test@example.com"
    mock_current_user.id = 1
    
    # Create stock adjustment schema
    stock_adjustment = StockAdjustment(adjustment=5, reason="Test adjustment")
    
    # Call the function directly
    result = adjust_stock(
        product_id=test_product.id,
        stock_adjustment=stock_adjustment,
        current_user=mock_current_user,
        db=db_session
    )
    
    # Verify the result
    assert result is not None
    assert hasattr(result, 'inventory_items')
    assert hasattr(result, 'inventory_adjustments')
    
    # Verify inventory was updated
    main_inventory = next((item for item in result.inventory_items if item.location == "default"), None)
    assert main_inventory is not None
    assert main_inventory.quantity == 15  # 10 (original) + 5 (adjustment)
    
    # Verify adjustment history was created
    adjustments = result.inventory_adjustments
    assert len(adjustments) > 0
    latest_adjustment = adjustments[0]  # Most recent first due to ordering
    assert latest_adjustment.adjustment == 5
    assert latest_adjustment.reason == "Test adjustment"
    assert latest_adjustment.created_by == "test@example.com"


@pytest.mark.db
def test_adjust_stock_negative_value(db_session: Session):
    """Test that negative adjustments (decreases) work properly."""
    # Get the existing inventory item and update its quantity for testing
    test_product = db_session.query(Product).filter(Product.sku == "STOCKTEST001").first()
    existing_inventory = db_session.query(InventoryItem).filter(
        InventoryItem.product_id == test_product.id,
        InventoryItem.location == "default"
    ).first()
    
    # Update the quantity to 20 for the test
    existing_inventory.quantity = 20
    db_session.commit()
    
    # Create a mock current_user
    mock_current_user = Mock()
    mock_current_user.email = "test@example.com"
    mock_current_user.id = 1
    
    # Create stock adjustment schema
    stock_adjustment = StockAdjustment(adjustment=-3, reason="Test decrease")
    
    # Call the function directly
    result = adjust_stock(
        product_id=test_product.id,
        stock_adjustment=stock_adjustment,
        current_user=mock_current_user,
        db=db_session
    )
    
    # Verify the result
    main_inventory = next((item for item in result.inventory_items if item.location == "default"), None)
    assert main_inventory is not None
    assert main_inventory.quantity == 17  # 20 - 3 = 17


@pytest.mark.db
def test_adjust_stock_without_reason(db_session: Session):
    """Test that adjustments work without providing a reason."""
    test_product = db_session.query(Product).filter(Product.sku == "STOCKTEST001").first()
    
    # Create a mock current_user
    mock_current_user = Mock()
    mock_current_user.email = "test@example.com"
    mock_current_user.id = 1
    
    # Create stock adjustment schema without reason
    stock_adjustment = StockAdjustment(adjustment=7)
    
    # Call the function directly
    result = adjust_stock(
        product_id=test_product.id,
        stock_adjustment=stock_adjustment,
        current_user=mock_current_user,
        db=db_session
    )
    
    # Verify the result
    main_inventory = next((item for item in result.inventory_items if item.location == "default"), None)
    assert main_inventory is not None
    assert main_inventory.quantity == 17  # 10 + 7 = 17
    
    # Check that an adjustment record was created without a reason
    adjustments = result.inventory_adjustments
    latest_adjustment = adjustments[0]
    assert latest_adjustment.adjustment == 7
    assert latest_adjustment.reason is None


@pytest.mark.db
def test_adjust_stock_zero_value(db_session: Session):
    """Test that zero adjustments are handled correctly (should probably be allowed or no-op)."""
    test_product = db_session.query(Product).filter(Product.sku == "STOCKTEST001").first()
    
    mock_current_user = Mock()
    mock_current_user.email = "test@example.com"
    mock_current_user.id = 1
    
    stock_adjustment = StockAdjustment(adjustment=0, reason="Zero adjustment")
    
    result = adjust_stock(
        product_id=test_product.id,
        stock_adjustment=stock_adjustment,
        current_user=mock_current_user,
        db=db_session
    )
    
    main_inventory = next((item for item in result.inventory_items if item.location == "default"), None)
    assert main_inventory.quantity == 10
    
    # Check if adjustment record was created
    adjustments = result.inventory_adjustments
    assert len(adjustments) > 0
    assert adjustments[0].adjustment == 0


@pytest.mark.db
def test_adjust_stock_large_value(db_session: Session):
    """Test that large adjustments are handled correctly."""
    test_product = db_session.query(Product).filter(Product.sku == "STOCKTEST001").first()
    
    mock_current_user = Mock()
    mock_current_user.email = "test@example.com"
    mock_current_user.id = 1
    
    stock_adjustment = StockAdjustment(adjustment=1000000, reason="Large adjustment")
    
    result = adjust_stock(
        product_id=test_product.id,
        stock_adjustment=stock_adjustment,
        current_user=mock_current_user,
        db=db_session
    )
    
    main_inventory = next((item for item in result.inventory_items if item.location == "default"), None)
    assert main_inventory.quantity == 1000010