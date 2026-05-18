"""
Catalog Ingestion Service.

Parses a CSV / spreadsheet upload into a list of `ExtractedCatalogItem` dicts
that the import-review flow stages for human review before approval. Approval
turns each selected row into a `Product` (and optionally a `SupplierProduct`
link).

CSV is the first slice. PDF / AI parsing is a follow-up that will produce the
same `ExtractedCatalogItem` shape so the review/approve UI can stay stable.

Column header matching is case-insensitive and accepts EN + es-MX aliases so
suppliers can hand us their export as-is.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedCatalogItem:
    """One staged row from a catalog upload. Mirrors the shape the review UI
    expects so CSV and PDF/AI parsers can be swapped freely."""

    sku: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    cost_price: Optional[float] = None
    default_resale_price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    supplier_sku: Optional[str] = None
    raw: dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    selected: bool = True  # user can toggle in the review dialog


@dataclass
class ExtractedCatalogData:
    items: List[ExtractedCatalogItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extraction_method: str = "csv"
    vendor_name: Optional[str] = None  # AI-extracted supplier name (when source is a PDF/image)


# Header aliases: keys are canonical fields, values are accepted column titles
# (case-insensitive, trimmed). Order in the list does not matter; the matcher
# accepts an exact match on any alias.
COLUMN_ALIASES: dict[str, list[str]] = {
    "sku": ["sku", "código", "codigo", "code", "item code", "product code"],
    "name": ["name", "nombre", "title", "product name", "producto", "descripción corta"],
    "description": ["description", "descripción", "descripcion", "long description", "details"],
    "cost_price": ["cost", "cost price", "costo", "precio costo", "wholesale", "unit cost"],
    "default_resale_price": [
        "price",
        "resale price",
        "retail price",
        "msrp",
        "precio",
        "precio venta",
        "precio público",
        "precio publico",
    ],
    "category": ["category", "categoría", "categoria"],
    "brand": ["brand", "marca"],
    "supplier_sku": [
        "supplier sku",
        "supplier code",
        "sku proveedor",
        "código proveedor",
        "codigo proveedor",
    ],
}


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _build_field_map(fieldnames: Iterable[str]) -> dict[str, str]:
    """Map canonical fields → actual header text in the uploaded CSV."""
    alias_to_field: dict[str, str] = {}
    for field_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_to_field[_normalize_header(alias)] = field_name

    field_map: dict[str, str] = {}
    for header in fieldnames or []:
        canonical = alias_to_field.get(_normalize_header(header))
        if canonical and canonical not in field_map:
            field_map[canonical] = header
    return field_map


def _coerce_amount(value) -> Optional[float]:
    """Accept the loose shapes the AI agent might return (number, numeric
    string, None) and normalize to float-or-None. Strings are routed through
    `_parse_amount` so currency symbols / decimal-comma still work."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return _parse_amount(str(value))


def _parse_amount(value: Optional[str]) -> Optional[float]:
    """Parse a money-ish string ('$1,234.50', '1.234,50', '79.90 MXN') → float.

    Returns None when the cell is empty or unparseable so the review UI can show
    'price missing' rather than a misleading 0.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # Drop currency codes/symbols and surrounding whitespace
    cleaned = re.sub(r"[^\d.,\-]", "", text)
    if not cleaned:
        return None

    # Handle European decimal comma if there's no '.', e.g. '1.234,50'
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.get_dialect("excel")  # safe default


CSV_SUFFIXES = {"csv", "tsv", "txt"}
AI_SUFFIXES = {"pdf", "png", "jpg", "jpeg", "webp", "avif"}


def file_suffix(file_name: str) -> str:
    return file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""


def is_ai_required(file_name: str) -> bool:
    """True when the upload's extension is one the CSV parser can't handle and
    that we'd route to the AI catalog parser instead."""
    return file_suffix(file_name) in AI_SUFFIXES


class CatalogIngestionService:
    """Stateless parser for catalog uploads. Inject for testing or swap parser
    backends per file type."""

    MAX_ROWS = 5000  # hard cap; protects the staging table from runaway uploads

    def ingest(self, *, file_name: str, content: bytes) -> ExtractedCatalogData:
        """Parse CSV/TSV deterministically. Non-CSV file types (PDF, images)
        require AI and are handled by the endpoint via `ingest_ai_result` —
        keeping the service stateless and easy to unit-test."""
        suffix = file_suffix(file_name)
        if suffix in CSV_SUFFIXES or not suffix:
            return self._parse_csv(content)

        if suffix in AI_SUFFIXES:
            # The endpoint routes these through the AI parser. This branch
            # only fires when the caller forgot to gate on `is_ai_required`.
            return ExtractedCatalogData(
                warnings=[
                    f".{suffix} files require AI parsing. "
                    "Enable AI in Settings and try again."
                ],
                extraction_method="ai_required",
            )

        return ExtractedCatalogData(
            warnings=[f"Unsupported file type: .{suffix}."],
            extraction_method="failed",
        )

    def ingest_ai_result(self, ai_result: dict) -> ExtractedCatalogData:
        """Turn the catalog AI agent's JSON payload into the same
        `ExtractedCatalogData` shape the CSV parser emits, so downstream code
        (review storage + approval) is identical for both sources."""
        result = ExtractedCatalogData(extraction_method="ai")
        vendor = (ai_result.get("vendor_name") or "").strip()
        result.vendor_name = vendor or None
        items_raw = ai_result.get("items") or []
        if not isinstance(items_raw, list):
            result.warnings.append("AI returned a non-list 'items' field.")
            return result

        for entry in items_raw:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            item = ExtractedCatalogItem(
                sku=(entry.get("sku") or None),
                name=name,
                description=(entry.get("description") or None),
                cost_price=_coerce_amount(entry.get("cost_price")),
                default_resale_price=_coerce_amount(entry.get("default_resale_price")),
                category=(entry.get("category") or None),
                brand=(entry.get("brand") or None),
                supplier_sku=(entry.get("supplier_sku") or None),
                raw=entry,
                warnings=[],
                selected=True,
            )
            result.items.append(item)

        confidence = ai_result.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < 0.6:
            result.warnings.append(
                f"AI extraction confidence is low ({confidence:.2f}). "
                "Review each row carefully before approving."
            )

        if not result.items:
            result.warnings.append("AI returned no importable rows.")

        return result

    def _parse_csv(self, content: bytes) -> ExtractedCatalogData:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")

        if not text.strip():
            return ExtractedCatalogData(warnings=["File is empty."], extraction_method="csv")

        sample = text[:4096]
        dialect = _sniff_dialect(sample)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        if not reader.fieldnames:
            return ExtractedCatalogData(
                warnings=["No header row detected."],
                extraction_method="csv",
            )

        field_map = _build_field_map(reader.fieldnames)
        result = ExtractedCatalogData(extraction_method="csv")

        if "name" not in field_map:
            result.warnings.append(
                "No 'name' column found. Add a column titled 'Name' or 'Nombre'."
            )
            return result

        for row_idx, row in enumerate(reader, start=2):  # row 1 is the header
            if row_idx - 1 > self.MAX_ROWS:
                result.warnings.append(
                    f"File exceeds the {self.MAX_ROWS}-row limit. Extra rows skipped."
                )
                break

            if not any((v or "").strip() for v in row.values()):
                continue  # blank line

            item_warnings: list[str] = []

            def cell(canonical: str) -> str:
                header = field_map.get(canonical)
                return (row.get(header) or "").strip() if header else ""

            name = cell("name")
            if not name:
                item_warnings.append("Missing name; row will be skipped on approve.")

            cost = _parse_amount(cell("cost_price")) if "cost_price" in field_map else None
            price = (
                _parse_amount(cell("default_resale_price"))
                if "default_resale_price" in field_map
                else None
            )

            if cost is None and "cost_price" in field_map and cell("cost_price"):
                item_warnings.append(f"Could not parse cost '{cell('cost_price')}'.")
            if price is None and "default_resale_price" in field_map and cell("default_resale_price"):
                item_warnings.append(
                    f"Could not parse price '{cell('default_resale_price')}'."
                )

            item = ExtractedCatalogItem(
                sku=cell("sku") or None,
                name=name,
                description=cell("description") or None,
                cost_price=cost,
                default_resale_price=price,
                category=cell("category") or None,
                brand=cell("brand") or None,
                supplier_sku=cell("supplier_sku") or None,
                raw={k: (v or "").strip() for k, v in row.items() if k},
                warnings=item_warnings,
                selected=bool(name),
            )
            result.items.append(item)

        if not result.items:
            result.warnings.append("No data rows found.")

        return result


catalog_ingestion_service = CatalogIngestionService()


def extracted_item_to_dict(item: ExtractedCatalogItem) -> dict:
    """JSON-safe form used in `CatalogImport.extracted_data['items']`."""
    return asdict(item)
