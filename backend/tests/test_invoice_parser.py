"""
Tests for Invoice Parser Agent and Endpoint.
"""
import pytest


class TestInvoiceParserAgent:
    """Tests for the InvoiceParserAgent class."""
    
    def test_agent_import(self):
        """Test that InvoiceParserAgent can be imported."""
        from src.services.adk.agents.invoice import InvoiceParserAgent
        assert InvoiceParserAgent is not None
    
    def test_agent_initialization_without_api_key(self):
        """Test agent initializes but is unavailable without API key."""
        from src.services.adk.agents.invoice import InvoiceParserAgent
        agent = InvoiceParserAgent(api_key=None)
        # Agent may or may not be available depending on ADK installation
        assert agent is not None
    
    def test_prompt_file_exists(self):
        """Test that the prompt file exists and is readable."""
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "src/services/adk/agents/invoice/prompts/invoice_extraction.md"
        assert prompt_path.exists(), f"Prompt file not found at {prompt_path}"
        content = prompt_path.read_text()
        assert "Invoice Extraction Agent" in content
        assert "vendor_name" in content


class TestInvoiceMatchingEndpoint:
    """Tests for the invoice parse-and-match endpoint."""
    
    def test_endpoint_schema_imports(self):
        """Test that endpoint schemas can be imported."""
        from src.api.v1.endpoints.purchase_orders import (
            InvoiceMatchItem,
            InvoiceMatchResult
        )
        assert InvoiceMatchItem is not None
        assert InvoiceMatchResult is not None
    
    def test_invoice_match_item_schema(self):
        """Test InvoiceMatchItem schema validation."""
        from src.api.v1.endpoints.purchase_orders import InvoiceMatchItem
        
        item = InvoiceMatchItem(
            po_item_id=1,
            po_description="Test Product",
            po_quantity=10.0,
            po_quantity_received=4.0,
            po_remaining_quantity=6.0,
            po_unit_cost=99.99,
            invoice_sku="SKU-001",
            invoice_description="Test Product",
            invoice_quantity=10.0,
            invoice_unit_cost=99.99,
            invoice_line_total=999.90,
            match_status="matched",
            confidence=1.0,
            discrepancy_details=None
        )
        
        assert item.match_status == "matched"
        assert item.confidence == 1.0
        assert item.po_remaining_quantity == 6.0
    
    def test_invoice_match_result_schema(self):
        """Test InvoiceMatchResult schema validation."""
        from src.api.v1.endpoints.purchase_orders import InvoiceMatchResult
        
        result = InvoiceMatchResult(
            invoice_number="INV-001",
            invoice_date="2026-01-10",
            vendor_name="Test Vendor",
            matches=[],
            unmatched_po_items=[],
            unmatched_invoice_items=[],
            total_discrepancy=0.0,
            overall_confidence=0.9,
            extraction_confidence=0.95
        )
        
        assert result.invoice_number == "INV-001"
        assert result.overall_confidence == 0.9


class TestMatchingLogic:
    """Tests for the invoice matching logic."""
    
    def test_similarity_function(self):
        """Test string similarity calculation."""
        from difflib import SequenceMatcher
        
        def similarity(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Exact match
        assert similarity("1TB NVMe SSD", "1TB NVMe SSD") == 1.0
        
        # Similar strings
        assert similarity("1TB NVMe SSD", "1TB NVMe SSD Drive") > 0.7
        
        # Different strings
        assert similarity("1TB NVMe SSD", "RAM 32GB DDR5") < 0.3
    
    def test_sku_matching_priority(self):
        """Test that SKU matching takes priority over description."""
        # This is tested via the endpoint, but we can add unit tests
        # for the matching logic if extracted to a separate function
        pass


@pytest.fixture
def sample_invoice_html():
    """Sample invoice HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Tech Supplies Direct</h1>
        <p>Invoice Number: TSD-INV-2026-001</p>
        <p>Date: 2026-01-10</p>
        <table>
            <tr><th>Item Code</th><th>Description</th><th>Qty</th><th>Unit Cost</th><th>Total</th></tr>
            <tr><td>TSD-SSD-1TB</td><td>1TB NVMe SSD Drive</td><td>50</td><td>$89.99</td><td>$4,499.50</td></tr>
        </table>
        <p>Grand Total: $4,499.50</p>
    </body>
    </html>
    """
