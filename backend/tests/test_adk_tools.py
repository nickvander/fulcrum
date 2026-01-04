"""
Tests for ADK Tools.

Unit tests for the Fulcrum internal database tools.
These tests mock the database layer to avoid requiring a live database.
"""
from unittest.mock import MagicMock, patch


class TestFulcrumProductTool:
    """Tests for the Fulcrum product lookup tool."""

    def test_find_internal_product_not_found(self):
        """Test product lookup when product doesn't exist."""
        # This test verifies the function handles missing products gracefully
        # by checking that it returns found=False (regardless of exact error)
        with patch.dict('sys.modules', {}):
            with patch('src.services.adk.tools.fulcrum_tool.DB_AVAILABLE', True):
                with patch('src.services.adk.tools.fulcrum_tool.SessionLocal') as mock_session_cls:
                    mock_db = MagicMock()
                    mock_db.query.return_value.filter.return_value.first.return_value = None
                    mock_session_cls.return_value = mock_db
                    
                    # Import after patching
                    from src.services.adk.tools import fulcrum_tool
                    # Patch the module-level variables
                    fulcrum_tool.DB_AVAILABLE = True
                    fulcrum_tool.SessionLocal = mock_session_cls
                    
                    result = fulcrum_tool.find_internal_product("NONEXISTENT-SKU")
                    
                    # The key assertion is that found is False
                    assert result["found"] is False


    def test_find_internal_product_db_unavailable(self):
        """Test graceful degradation when DB is not available."""
        from src.services.adk.tools import fulcrum_tool
        
        # Temporarily set DB_AVAILABLE to False
        original_value = fulcrum_tool.DB_AVAILABLE
        fulcrum_tool.DB_AVAILABLE = False
        
        try:
            result = fulcrum_tool.find_internal_product("ANY-SKU")
            assert result["found"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            fulcrum_tool.DB_AVAILABLE = original_value


class TestInventoryTool:
    """Tests for the inventory lookup tool."""

    def test_get_inventory_status_db_unavailable(self):
        """Test inventory lookup when DB is unavailable."""
        from src.services.adk.tools import inventory_tool
        
        original_value = inventory_tool.DB_AVAILABLE
        inventory_tool.DB_AVAILABLE = False
        
        try:
            result = inventory_tool.get_inventory_status("ANY-SKU")
            assert result["found"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            inventory_tool.DB_AVAILABLE = original_value

    def test_get_low_stock_db_unavailable(self):
        """Test low stock query when DB is unavailable."""
        from src.services.adk.tools import inventory_tool
        
        original_value = inventory_tool.DB_AVAILABLE
        inventory_tool.DB_AVAILABLE = False
        
        try:
            result = inventory_tool.get_low_stock_products(threshold=10)
            assert result["success"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            inventory_tool.DB_AVAILABLE = original_value


class TestPricingTool:
    """Tests for the pricing tool."""

    def test_calculate_resale_price(self):
        """Test margin calculation."""
        from src.services.adk.tools.pricing_tool import calculate_resale_price
        
        result = calculate_resale_price(cost=70.0, target_margin_percent=30.0)
        
        assert result["success"] is True
        assert result["cost"] == 70.0
        assert result["recommended_resale_price"] == 100.0  # 70 / 0.7 = 100
        assert result["margin_amount"] == 30.0

    def test_calculate_resale_price_invalid_cost(self):
        """Test margin calculation with invalid cost."""
        from src.services.adk.tools.pricing_tool import calculate_resale_price
        
        result = calculate_resale_price(cost=0, target_margin_percent=30.0)
        
        assert result["success"] is False
        assert "error" in result

    def test_calculate_resale_price_negative_cost(self):
        """Test margin calculation with negative cost."""
        from src.services.adk.tools.pricing_tool import calculate_resale_price
        
        result = calculate_resale_price(cost=-10, target_margin_percent=30.0)
        
        assert result["success"] is False

    def test_pricing_db_unavailable(self):
        """Test pricing lookup when DB is unavailable."""
        from src.services.adk.tools import pricing_tool
        
        original_value = pricing_tool.DB_AVAILABLE
        pricing_tool.DB_AVAILABLE = False
        
        try:
            result = pricing_tool.get_product_pricing("ANY-SKU")
            assert result["found"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            pricing_tool.DB_AVAILABLE = original_value


class TestSupplierTool:
    """Tests for the supplier lookup tool."""

    def test_find_suppliers_db_unavailable(self):
        """Test supplier lookup when DB is unavailable."""
        from src.services.adk.tools import supplier_tool
        
        original_value = supplier_tool.DB_AVAILABLE
        supplier_tool.DB_AVAILABLE = False
        
        try:
            result = supplier_tool.find_suppliers_for_product("ANY-SKU")
            assert result["found"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            supplier_tool.DB_AVAILABLE = original_value

    def test_get_supplier_details_db_unavailable(self):
        """Test supplier details when DB is unavailable."""
        from src.services.adk.tools import supplier_tool
        
        original_value = supplier_tool.DB_AVAILABLE
        supplier_tool.DB_AVAILABLE = False
        
        try:
            result = supplier_tool.get_supplier_details("ANY-SUPPLIER")
            assert result["found"] is False
            assert "not available" in result.get("error", "").lower()
        finally:
            supplier_tool.DB_AVAILABLE = original_value


class TestSearchTool:
    """Tests for the Google Search tool wrapper."""

    def test_search_tool_initialization(self):
        """Test SearchTool can be instantiated."""
        from src.services.adk.tools.search_tool import SearchTool
        
        tool = SearchTool()
        # is_available may be True or False depending on environment
        assert hasattr(tool, 'is_available')
        assert hasattr(tool, 'tool')
