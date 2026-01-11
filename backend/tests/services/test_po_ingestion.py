"""
Tests for Purchase Order Ingestion Service.
"""
import pytest
from pathlib import Path
from src.services.purchase_order_ingestion_service import POIngestionService


# Path to sample files
SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples" / "purchase_orders"


class TestPOIngestionService:
    """Test cases for PO ingestion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = POIngestionService(ai_enabled=False)

    def test_parse_html_global_electronics(self):
        """Test parsing a structured HTML PO from Global Electronics."""
        html_file = SAMPLES_DIR / "global_electronics_po.html"
        if not html_file.exists():
            pytest.skip("Sample file not found")
        
        result = self.service.ingest_file(str(html_file))
        
        # Verify header extraction
        assert result.supplier_name is not None
        assert "Global Electronics" in result.supplier_name or result.supplier_name == "Global Electronics Ltd"
        assert result.po_number is not None
        assert result.currency == "USD"
        
        # Verify financials
        assert result.total_amount > 0
        assert result.shipping_cost > 0
        
        # Verify line items were extracted
        assert len(result.items) >= 3
        
        # Check a specific item
        skus = [item.sku for item in result.items if item.sku]
        assert any("LAPTOP" in sku for sku in skus) or len(skus) > 0

    def test_parse_html_spanish_po(self):
        """Test parsing a Spanish-language HTML PO."""
        html_file = SAMPLES_DIR / "mexitech_po_spanish.html"
        if not html_file.exists():
            pytest.skip("Sample file not found")
        
        result = self.service.ingest_file(str(html_file))
        
        # Should detect MXN currency
        assert result.currency == "MXN"
        
        # Should extract items
        assert len(result.items) >= 3
        
        # Should have a high total (MXN values are larger)
        assert result.total_amount > 100000

    def test_parse_text_fashion_forward(self):
        """Test parsing a plain text PO."""
        txt_file = SAMPLES_DIR / "fashion_forward_po.txt"
        if not txt_file.exists():
            pytest.skip("Sample file not found")
        
        result = self.service.ingest_file(str(txt_file))
        
        # Should extract PO number
        assert result.po_number is not None
        
        # Should extract totals
        assert result.total_amount > 0 or result.subtotal > 0
        
        # Extraction method should indicate text
        assert "text" in result.extraction_method.lower()

    def test_parse_html_home_essentials(self):
        """Test parsing another HTML format."""
        html_file = SAMPLES_DIR / "home_essentials_po.html"
        if not html_file.exists():
            pytest.skip("Sample file not found")
        
        result = self.service.ingest_file(str(html_file))
        
        # Should extract items from table
        assert len(result.items) >= 4
        
        # Check for freight/shipping
        assert result.shipping_cost > 0 or result.total_amount > result.subtotal

    def test_unsupported_format_warning(self):
        """Test that unsupported formats return warnings."""
        # Create a fake path with unsupported extension
        result = self.service.ingest_file("document.xyz", b"some content")
        
        assert len(result.warnings) > 0 or result.extraction_method == "failed"

    def test_confidence_scoring(self):
        """Test that confidence scores are calculated."""
        html_file = SAMPLES_DIR / "global_electronics_po.html"
        if not html_file.exists():
            pytest.skip("Sample file not found")
        
        result = self.service.ingest_file(str(html_file))
        
        # Should have a non-zero confidence
        assert result.confidence_score > 0
        # Well-structured HTML should have higher confidence
        assert result.confidence_score >= 0.3


class TestAmountParsing:
    """Test amount parsing utilities."""

    def setup_method(self):
        self.service = POIngestionService()

    def test_parse_amount_with_comma(self):
        """Test parsing amounts with comma separators."""
        assert self.service._parse_amount("1,234.56") == 1234.56
        assert self.service._parse_amount("$1,234.56") == 1234.56
        assert self.service._parse_amount("12,499.15") == 12499.15

    def test_parse_amount_without_decimals(self):
        """Test parsing whole number amounts."""
        assert self.service._parse_amount("150") == 150.0
        assert self.service._parse_amount("$200") == 200.0

    def test_parse_amount_empty(self):
        """Test parsing empty/None values."""
        assert self.service._parse_amount(None) == 0.0
        assert self.service._parse_amount("") == 0.0
