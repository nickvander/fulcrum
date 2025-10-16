import pytest
from sqlalchemy.orm import Session
from unittest.mock import Mock
from sqlalchemy import create_engine

from src.config import settings
from src.models import Product, InventoryItem, User
from src.schemas.inventory import StockAdjustment
from src.api.v1.endpoints.products import adjust_stock


@pytest.fixture
def db_session():
    """Create a new database session for testing."""
    # Create a test engine using the same settings as the main application
    test_engine = create_engine(settings.DATABASE_URL)
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Create a test user and product for testing
    test_user = User(email="test@example.com", hashed_password="hashed_testpassword", role="user")
    session.add(test_user)
    session.flush()  # Get the user ID
    
    test_product = Product(
        name="Test Product",
        description="Test Description",
        sku="TEST001",
        default_resale_price=10.0
    )
    session.add(test_product)
    session.flush()  # Get the product ID
    
    # Create initial inventory
    initial_inventory = InventoryItem(
        product_id=test_product.id,
        quantity=10,
        location="default"
    )
    session.add(initial_inventory)
    session.commit()
    
    yield session
    
    # Rollback the transaction to clean up test data
    session.close()
    transaction.rollback()
    connection.close()
    # Dispose of the test engine
    test_engine.dispose()


@pytest.mark.db
def test_adjust_stock_functionality(db_session: Session):
    """Test the direct functionality of the adjust_stock function."""
    # Get test data
    test_product = db_session.query(Product).first()
    
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
    # Add more inventory for testing
    test_product = db_session.query(Product).first()
    inventory_item = InventoryItem(
        product_id=test_product.id,
        quantity=20,
        location="default"
    )
    db_session.add(inventory_item)
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
    test_product = db_session.query(Product).first()
    
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
    assert main_inventory.quantity == 17  # 10 (original) + 7 (adjustment)
    
    # Check that an adjustment record was created without a reason
    adjustments = result.inventory_adjustments
    latest_adjustment = adjustments[0]
    assert latest_adjustment.adjustment == 7
    assert latest_adjustment.reason is None