"""
Purchase Order Ingestion Service.

Provides hybrid ingestion for PDF, HTML, and plain text PO documents.
- Traditional Layer: Uses PyMuPDF (PDF) and BeautifulSoup (HTML) for text extraction
  with regex-based field identification.
- AI Layer (Optional): Can be enabled in settings to handle complex/unstructured documents.
"""
import re
from typing import Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedLineItem:
    """Represents a line item extracted from a PO document."""
    sku: Optional[str] = None
    description: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    line_total: float = 0.0
    product_id: Optional[int] = None  # Matched product ID from database


@dataclass
class ExtractedPOData:
    """Represents extracted data from a PO document."""
    supplier_name: Optional[str] = None
    po_number: Optional[str] = None
    po_date: Optional[datetime] = None
    currency: str = "USD"
    payment_terms: Optional[str] = None
    items: List[ExtractedLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    shipping_cost: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    raw_text: str = ""
    extraction_method: str = "traditional"
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)


class POIngestionService:
    """
    Service for ingesting and parsing Purchase Order documents.
    Supports PDF, HTML, and plain text formats.
    """

    # Common patterns for field extraction
    PATTERNS = {
        "po_number": [
            r"(?:Order number|Orden de compra|Receipt)\s*[\s\S]{0,100}#([A-Z0-9\-]+)",
            r"(?:PO|P\.O\.|Purchase Order|Order)[\s#:]*([A-Z0-9\-]+)",
            r"(?:Número|Orden de Compra|OC)[\s#:]*([A-Z0-9\-]+)",
        ],
        "date": [
            r"(?:Order date|Fecha de orden|Issue Date)\s*[\s\S]{0,100}\n?([\d\w\s,]+?)(?:\s\([A-Z]+\))?(?:\n|$)",
            r"(?:Date|Fecha|Issue Date)[\s:]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(?:Date|Fecha)[\s:]*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
        ],
        "currency": [
            r"(?:Currency|Moneda)[\s:]*([A-Z]{3})",
            r"\b(USD|MXN|EUR|GBP|CAD)\b",
        ],
        "payment_terms": [
            r"(?:Payment Terms|Terms|Condiciones de Pago)[\s:]*([A-Za-z0-9\s]+?)(?:\n|$)",
            r"(Net\s*\d+)",
            r"(Due on Receipt)",
        ],
        "subtotal": [
            r"(?:Subtotal|Sub[\s-]?total)(?:\s*\(excl\. tax\))?[\s:$]*\n?(?:[A-Z]{3}\s*)?([0-9,]+\.?\d*)",
        ],
        "shipping": [
            r"(?:Shipping|Freight|Envío|Shipping fee|Shipping & Handling)[\s:$]*\n?(?:[A-Z]{3}\s*)?([0-9,]+\.?\d*)",
        ],
        "tax": [
            r"(?:Tax|IVA|Sales Tax)(?:\s*\([^)]+\))?[\s:$]*\n?(?:[A-Z]{3}\s*)?([0-9,]+\.?\d*)",
        ],
        "total": [
            r"(?:Grand Total|Total|Total Due|Order total|Importe Total)[\s:$]*\n?(?:[A-Z]{3}\s*)?([0-9,]+\.?\d*)",
        ],
        "supplier": [
            r"Sold by\s+([\s\S]+?)\s+Ship to",
            r"(?:Supplier|Vendor|Seller|Vendedor|Proveedor)[\s:]*([A-Za-z0-9\s\.\,\-]+)",
            r"(?:From|De)[\s:]*([A-Za-z0-9\s\.\,\-]+)",
        ]
    }

    def __init__(self, ai_enabled: bool = False, ai_service=None):
        """
        Initialize the ingestion service.
        
        Args:
            ai_enabled: Whether to use AI enhancement for complex documents.
            ai_service: Optional AI service for enhanced parsing.
        """
        self.ai_enabled = ai_enabled
        self.ai_service = ai_service

    def ingest_file(self, file_path: str, content: Optional[bytes] = None) -> ExtractedPOData:
        """
        Ingest a PO document from file path or content.
        
        Args:
            file_path: Path to the file (for type detection).
            content: Optional file content bytes.
            
        Returns:
            ExtractedPOData with parsed information.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        # Read content if not provided
        if content is None:
            with open(file_path, "rb") as f:
                content = f.read()

        # Route to appropriate parser
        if suffix == ".pdf":
            return self._parse_pdf(content)
        elif suffix in (".html", ".htm"):
            return self._parse_html(content.decode("utf-8", errors="ignore"))
        elif suffix in (".txt", ".text"):
            return self._parse_text(content.decode("utf-8", errors="ignore"))
        else:
            # Attempt text parsing as fallback
            try:
                text = content.decode("utf-8", errors="ignore")
                return self._parse_text(text)
            except Exception as e:
                logger.error(f"Failed to parse file: {e}")
                return ExtractedPOData(
                    warnings=[f"Unsupported file format: {suffix}"]
                )

    def _parse_pdf(self, content: bytes) -> ExtractedPOData:
        """Parse PDF content using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return ExtractedPOData(
                warnings=["PyMuPDF not installed. Cannot parse PDF files."],
                extraction_method="failed"
            )

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            full_text = "\n".join(text_parts)
            doc.close()

            return self._extract_from_text(full_text, source="pdf")
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return ExtractedPOData(
                warnings=[f"PDF parsing error: {str(e)}"],
                extraction_method="failed"
            )

    def _parse_html(self, html_content: str) -> ExtractedPOData:
        """Parse HTML content using BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            # Fallback: basic HTML tag stripping
            import html
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = html.unescape(text)
            return self._extract_from_text(text, source="html_fallback")

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract text preserving some structure
        full_text = soup.get_text(separator="\n", strip=True)

        # Also try to extract table data directly
        extracted = self._extract_from_text(full_text, source="html")
        
        # Enhancement: Parse HTML tables for more accurate line items
        tables = soup.find_all("table")
        if tables:
            table_items = self._extract_items_from_html_tables(tables)
            if table_items and len(table_items) > len(extracted.items):
                extracted.items = table_items
                extracted.confidence_score += 0.1  # Boost confidence for table extraction

        extracted.raw_text = full_text
        return extracted

    def _parse_text(self, text: str) -> ExtractedPOData:
        """Parse plain text content."""
        return self._extract_from_text(text, source="text")

    def _extract_from_text(self, text: str, source: str = "unknown") -> ExtractedPOData:
        """
        Extract PO data from text using regex patterns.
        
        Args:
            text: The text content to parse.
            source: Source type for logging.
            
        Returns:
            ExtractedPOData with extracted fields.
        """
        result = ExtractedPOData(
            raw_text=text,
            extraction_method=f"traditional_{source}"
        )
        confidence = 0.0
        warnings = []

        # Extract Supplier
        supplier = self._find_first_match(text, self.PATTERNS["supplier"])
        if supplier:
            # Clean up: take first line only if multiline block
            result.supplier_name = supplier.strip().split('\n')[0]
            confidence += 0.1

        # Extract PO Number
        po_number = self._find_first_match(text, self.PATTERNS["po_number"])
        if po_number:
            result.po_number = po_number
            confidence += 0.15

        # Extract Date
        date_str = self._find_first_match(text, self.PATTERNS["date"])
        if date_str:
            result.po_date = self._parse_date(date_str)
            if result.po_date:
                confidence += 0.1

        # Extract Currency
        currency = self._find_first_match(text, self.PATTERNS["currency"])
        if currency:
            result.currency = currency.upper()
            confidence += 0.05

        # Extract Payment Terms
        terms = self._find_first_match(text, self.PATTERNS["payment_terms"])
        if terms:
            result.payment_terms = terms.strip()

        # Extract financial fields
        result.subtotal = self._parse_amount(
            self._find_first_match(text, self.PATTERNS["subtotal"])
        )
        result.shipping_cost = self._parse_amount(
            self._find_first_match(text, self.PATTERNS["shipping"])
        )
        result.tax_amount = self._parse_amount(
            self._find_first_match(text, self.PATTERNS["tax"])
        )
        result.total_amount = self._parse_amount(
            self._find_first_match(text, self.PATTERNS["total"])
        )

        if result.total_amount > 0:
            confidence += 0.2

        # Extract line items from text
        result.items = self._extract_line_items_from_text(text)
        if result.items:
            confidence += 0.3
        else:
            warnings.append("Could not extract line items automatically.")

        # Try to identify supplier from first lines IF not already found
        if not result.supplier_name:
            lines = text.strip().split("\n")
            if lines:
                # First non-empty line is often the company name
                for line in lines[:5]:
                    cleaned = line.strip()
                    if cleaned and len(cleaned) > 3 and not cleaned.startswith(("=", "-", "*", "#")):
                        result.supplier_name = cleaned
                        confidence += 0.05
                        break

        result.confidence_score = min(confidence, 1.0)
        result.warnings = warnings
        return result

    def _extract_items_from_html_tables(self, tables) -> List[ExtractedLineItem]:
        """Extract line items from HTML table elements."""
        items = []
        
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:  # Need header + at least one data row
                continue

            # Try to identify header row
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

            # Map column indices
            col_map = {}
            for i, h in enumerate(headers):
                if any(x in h for x in ["sku", "code", "código", "item code", "product code"]):
                    col_map["sku"] = i
                elif any(x in h for x in ["description", "descripción", "item", "product", "name"]):
                    col_map["description"] = i
                elif any(x in h for x in ["qty", "quantity", "cantidad"]):
                    col_map["quantity"] = i
                elif any(x in h for x in ["unit", "price", "precio", "rate", "cost"]):
                    col_map["unit_cost"] = i
                elif any(x in h for x in ["total", "amount", "importe", "line total"]):
                    col_map["line_total"] = i

            if not col_map:
                continue

            # Extract data rows
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                item = ExtractedLineItem()
                
                if "sku" in col_map and col_map["sku"] < len(cells):
                    item.sku = cells[col_map["sku"]].get_text(strip=True)
                
                if "description" in col_map and col_map["description"] < len(cells):
                    item.description = cells[col_map["description"]].get_text(strip=True)
                elif not item.description and "sku" in col_map:
                    # Use next cell after SKU as description
                    desc_idx = col_map.get("sku", 0) + 1
                    if desc_idx < len(cells):
                        item.description = cells[desc_idx].get_text(strip=True)

                if "quantity" in col_map and col_map["quantity"] < len(cells):
                    item.quantity = self._parse_amount(
                        cells[col_map["quantity"]].get_text(strip=True)
                    )

                if "unit_cost" in col_map and col_map["unit_cost"] < len(cells):
                    item.unit_cost = self._parse_amount(
                        cells[col_map["unit_cost"]].get_text(strip=True)
                    )

                if "line_total" in col_map and col_map["line_total"] < len(cells):
                    item.line_total = self._parse_amount(
                        cells[col_map["line_total"]].get_text(strip=True)
                    )

                # Only add if we have meaningful data
                if item.description or item.sku:
                    items.append(item)

        return items

    def _extract_line_items_from_text(self, text: str) -> List[ExtractedLineItem]:
        """
        Extract line items from plain text using pattern matching.
        """
        items = []
        
        # 1. Vertical Blocks (Alibaba/Modern Style)
        # Sequence: Description (multiline), Quantity, Unit Price, Total
        # Use a more specific header to avoid matching totals at the bottom
        items_section = re.search(r"(?:Order details|Item\nQuantity)\s*[\s\S]+?Amount\s*\n([\s\S]+?)\s+(?:Items total|Payment details|Order total|Subtotal|Resumen)", text, re.IGNORECASE)
        if items_section:
            section_text = items_section.group(1).strip()
            # print(f"DEBUG: Parsed section text: {section_text[:100]}...") # Helpful for docker logs
            lines = [l.strip() for l in section_text.split('\n') if l.strip()]
            
            last_item_end_idx = -1
            for i, line in enumerate(lines):
                # Look for a quantity-like line (numeric only, no currency)
                if re.match(r"^[0-9,]+\.?\d*$", line) and not any(c in line for c in "USDMXNEUR"):
                    # Everything since the last item end is the description
                    desc_lines = lines[last_item_end_idx + 1 : i]
                    # Filter out any headers that might be at the start
                    desc_lines = [l for l in desc_lines if l.lower() not in 
                                ["item", "description", "quantity", "amount", "unit price", "order details"]]
                    
                    if desc_lines:
                        qty = self._parse_amount(line)
                        price = 0.0
                        total = 0.0
                        
                        # Unit price usually follows quantity
                        k = i + 1
                        if k < len(lines) and any(c in lines[k] for c in "USDMXNEUR"):
                            price = self._parse_amount(lines[k])
                            k += 1
                        # Line total follows unit price
                        if k < len(lines) and any(c in lines[k] for c in "USDMXNEUR"):
                            total = self._parse_amount(lines[k])
                            k += 1
                        
                        items.append(ExtractedLineItem(
                            description=" ".join(desc_lines),
                            quantity=qty, unit_cost=price, line_total=total
                        ))
                        last_item_end_idx = k - 1

        # 2. SKU, Description, Qty, Price, Total (Horizontal Table)
        if not items:
            sku_desc_qty_price_total = r"([A-Z0-9]{3,}[\-][A-Z0-9\-]+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+\$?([0-9,]+\.?\d*)\s+\$?([0-9,]+\.?\d*)"
            matches = re.findall(sku_desc_qty_price_total, text, re.IGNORECASE | re.MULTILINE)
            for m in matches:
                items.append(ExtractedLineItem(
                    sku=m[0].strip(), description=m[1].strip(),
                    quantity=self._parse_amount(m[2]), unit_cost=self._parse_amount(m[3]),
                    line_total=self._parse_amount(m[4])
                ))

        # 3. Index, Description, Unit Price, Qty, Total (Horizontal Table style 2)
        if not items:
            index_desc_price_qty_total = r"(\d+)\s+([A-Za-z0-9\s\-\.\(\)\/]{5,100})\s+\$?([0-9,]+\.?\d*)\s+(\d+(?:\.\d+)?)\s+\$?([0-9,]+\.?\d*)"
            matches = re.findall(index_desc_price_qty_total, text, re.IGNORECASE | re.MULTILINE)
            for m in matches:
                items.append(ExtractedLineItem(
                    description=m[1].strip(), unit_cost=self._parse_amount(m[2]),
                    quantity=self._parse_amount(m[3]), line_total=self._parse_amount(m[4])
                ))

        # Filter out duplicates or invalid items
        seen_items = set()
        unique_items = []
        for item in items:
            # Use desc + qty + cost for uniqueness to allow multiple entries of same product
            item_key = (item.description, item.quantity, item.unit_cost)
            if item.description and item.quantity > 0 and item_key not in seen_items:
                unique_items.append(item)
                seen_items.add(item_key)

        return unique_items

    def _find_first_match(self, text: str, patterns: List[str]) -> Optional[str]:
        """Find the first matching pattern in text."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1)
        return None

    def _parse_amount(self, value: Optional[str]) -> float:
        """Parse a monetary amount string to float."""
        if not value:
            return 0.0
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string in various formats."""
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d/%m/%y",
            "%m-%d-%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None


# Singleton instance
po_ingestion_service = POIngestionService()
