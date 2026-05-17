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


class CatalogIngestionService:
    """Stateless parser for catalog uploads. Inject for testing or swap parser
    backends per file type."""

    MAX_ROWS = 5000  # hard cap; protects the staging table from runaway uploads

    def ingest(self, *, file_name: str, content: bytes) -> ExtractedCatalogData:
        suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
        if suffix in {"csv", "tsv", "txt"} or not suffix:
            return self._parse_csv(content)

        return ExtractedCatalogData(
            warnings=[f"Unsupported file type: .{suffix}. CSV / TSV uploads only."],
            extraction_method="failed",
        )

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
